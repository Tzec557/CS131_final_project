import argparse
import time
import cv2
import numpy as np
import json
from ultralytics import YOLO
import paho.mqtt.client as mqtt

# -----------------------------
# Argument Parsing
# -----------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--camera_id", required=True)
parser.add_argument("--broker_ip", required=True)
parser.add_argument("--video", default=None)  # optional video file
args = parser.parse_args()

CAMERA_ID = args.camera_id
BROKER_IP = args.broker_ip

# -----------------------------
# MQTT Setup
# -----------------------------
client = mqtt.Client()
client.connect(BROKER_IP, 1883, 60)

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

# Tunable thresholds (adjust for your demo)
ANGLE_THRESHOLD = 55
VELOCITY_THRESHOLD = 0.15   # normalized velocity
INACTIVITY_TIME = 3        # seconds
EMA_ALPHA = 0.4            # smoothing factor

def compute_body_angle(kpts):
    l_shoulder = kpts[5]
    r_shoulder = kpts[6]
    l_hip = kpts[11]
    r_hip = kpts[12]

    if min(l_shoulder[2], r_shoulder[2], l_hip[2], r_hip[2]) < 0.5:
        return None

    shoulder_mid = (l_shoulder[:2] + r_shoulder[:2]) / 2
    hip_mid = (l_hip[:2] + r_hip[:2]) / 2

    dx = hip_mid[0] - shoulder_mid[0]
    dy = hip_mid[1] - shoulder_mid[1]

    angle = np.degrees(np.arctan2(abs(dx), abs(dy)))
    return angle


while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, imgsz=320, conf=0.5)
    annotated = results[0].plot()

    if results[0].keypoints is not None:
        for kpts in results[0].keypoints.data:

            nose = kpts[0]
            angle = compute_body_angle(kpts)

            if nose[2] < 0.5 or angle is None:
                continue

            current_nose_y = nose[1]

            # Estimate body height for normalization
            top = min(kpts[:,1])
            bottom = max(kpts[:,1])
            body_height = bottom - top
            if body_height < 1:
                continue

            # Compute normalized velocity
            if prev_nose_y is not None:
                raw_velocity = (current_nose_y - prev_nose_y) / body_height
            else:
                raw_velocity = 0

            prev_nose_y = current_nose_y

            # Exponential Moving Average smoothing
            ema_velocity = EMA_ALPHA * raw_velocity + (1 - EMA_ALPHA) * ema_velocity

            # -----------------------------
            # Finite State Machine
            # -----------------------------

            if STATE == "STANDING":
                if ema_velocity > VELOCITY_THRESHOLD:
                    STATE = "FALLING"
                    fall_time = time.time()

            elif STATE == "FALLING":
                if angle > ANGLE_THRESHOLD:
                    if inactivity_start is None:
                        inactivity_start = time.time()

                    # Confirm fall after inactivity
                    if time.time() - inactivity_start > INACTIVITY_TIME:
                        STATE = "FALLEN"

                        payload = {
                            "camera_id": CAMERA_ID,
                            "state": "FALLEN",
                            "timestamp": time.time()
                        }

                        client.publish("fall/events", json.dumps(payload))
                else:
                    STATE = "STANDING"
                    inactivity_start = None

            elif STATE == "FALLEN":
                if angle < 30:
                    STATE = "STANDING"
                    inactivity_start = None

            # Display debug info
            cv2.putText(annotated, f"State: {STATE}", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv2.imshow(CAMERA_ID, annotated)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()