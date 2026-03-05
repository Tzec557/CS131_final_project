import argparse
import time
import cv2
import numpy as np
import json
import zmq  # Replaced paho.mqtt with pyzmq
from ultralytics import YOLO

# -----------------------------
# Argument Parsing
# -----------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--port", default="5555", help="Port to publish data on")
parser.add_argument("--video", default=None, help="Path to video file (optional)")
args = parser.parse_args()

# -----------------------------
# ZMQ Setup (Publisher)
# -----------------------------
context = zmq.Context()
socket = context.socket(zmq.PUB)
# Bind to all interfaces on the specified port
socket.bind(f"tcp://*:{args.port}")
print(f"ZMQ Publisher started on port {args.port}")

# -----------------------------
# Load YOLOv8 Pose Model
# -----------------------------
model = YOLO("yolov8n-pose.pt")

if args.video:
    cap = cv2.VideoCapture(args.video)
else:
    cap = cv2.VideoCapture(0)

# -----------------------------
# State Machine Variables
# -----------------------------
STATE = "STANDING"
fall_time = None
inactivity_start = None
prev_nose_y = None
ema_velocity = 0

# Tunable thresholds
ANGLE_THRESHOLD = 55
VELOCITY_THRESHOLD = 0.15
INACTIVITY_TIME = 2
EMA_ALPHA = 0.4

def compute_body_angle(kpts):
    l_shoulder, r_shoulder = kpts[5], kpts[6]
    l_hip, r_hip = kpts[11], kpts[12]

    if min(l_shoulder[2], r_shoulder[2], l_hip[2], r_hip[2]) < 0.5:
        return None

    shoulder_mid = (l_shoulder[:2] + r_shoulder[:2]) / 2
    hip_mid = (l_hip[:2] + r_hip[:2]) / 2
    dx, dy = hip_mid[0] - shoulder_mid[0], hip_mid[1] - shoulder_mid[1]
    return np.degrees(np.arctan2(abs(dx), abs(dy)))

while True:
    ret, frame = cap.read()
    if not ret: break

    results = model(frame, imgsz=320, conf=0.5, verbose=False)
    annotated = results[0].plot()

    if results[0].keypoints is not None and len(results[0].keypoints.data) > 0:
        for kpts in results[0].keypoints.data:
            nose = kpts[0]
            angle = compute_body_angle(kpts)

            if nose[2] < 0.5 or angle is None: continue

            current_nose_y = nose[1]
            valid_kpts = kpts[kpts[:, 2] > 0.3]
            if len(valid_kpts) < 2: continue
            
            body_height = max(valid_kpts[:, 1]) - min(valid_kpts[:, 1])
            if body_height < 10: continue

            raw_velocity = (current_nose_y - prev_nose_y) / body_height if prev_nose_y else 0
            prev_nose_y = current_nose_y
            ema_velocity = EMA_ALPHA * raw_velocity + (1 - EMA_ALPHA) * ema_velocity

            # --- State Machine ---
            if STATE == "STANDING":
                if ema_velocity > VELOCITY_THRESHOLD:
                    STATE = "FALLING"

            elif STATE == "FALLING":
                if angle > ANGLE_THRESHOLD:
                    if inactivity_start is None: inactivity_start = time.time()
                    if time.time() - inactivity_start > INACTIVITY_TIME:
                        STATE = "FALLEN"
                        
                        # ZMQ Publish Logic
                        payload = {
                            "event": "FALL_DETECTED",
                            "angle": round(float(angle), 2),
                            "timestamp": time.time()
                        }
                        # We send a multi-part message: [Topic, Data]
                        socket.send_multipart([b"fall_events", json.dumps(payload).encode('utf-8')])
                        print("Sent ZMQ Alert")
                else:
                    STATE = "STANDING"
                    inactivity_start = None

            elif STATE == "FALLEN":
                if angle < 30:
                    STATE = "STANDING"
                    inactivity_start = None

            cv2.putText(annotated, f"State: {STATE}", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255) if STATE == "FALLEN" else (0, 255, 0), 2)

    cv2.imshow("ZMQ Fall Detection", annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()

