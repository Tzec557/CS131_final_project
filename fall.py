import argparse
import time
import cv2
import numpy as np
import json
import zmq
from ultralytics import YOLO

parser = argparse.ArgumentParser()
parser.add_argument("--port", default="5555")
parser.add_argument("--video", default=None)
args = parser.parse_args()

# ZMQ Setup
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:" + args.port)

model = YOLO("yolov8n-pose.pt")
cap = cv2.VideoCapture(args.video if args.video else 0)

# --- Multi-Person Tracking Storage ---
# Stores { id: {"state": "STANDING", "prev_y": None, "inactivity": None, "ema": 0} }
person_data = {}

def compute_metrics(kpts):
    # Use shoulders (5,6) and hips (11,12)
    # If nose (0) is missing, we can still calculate angle
    s_mid = (kpts[5][:2] + kpts[6][:2]) / 2
    h_mid = (kpts[11][:2] + kpts[12][:2]) / 2
    
    # Body Angle
    dx, dy = h_mid[0] - s_mid[0], h_mid[1] - s_mid[1]
    angle = np.degrees(np.arctan2(abs(dx), abs(dy)))
    
    # Body Height for normalization
    valid = kpts[kpts[:, 2] > 0.3]
    height = max(valid[:, 1]) - min(valid[:, 1]) if len(valid) > 1 else 1
    
    return angle, s_mid[1], height

while True:
    ret, frame = cap.read()
    if not ret: break

    # Use .track() instead of just calling model() to get persistent IDs
    results = model.track(frame, imgsz=320, conf=0.4, persist=True, verbose=False)
    
    if results[0].keypoints is not None and results[0].boxes.id is not None:
        ids = results[0].boxes.id.int().cpu().tolist()
        keypoints = results[0].keypoints.data # Shape: [N, 17, 3]

        for i, p_id in enumerate(ids):
            kpts = keypoints[i]
            angle, curr_y, height = compute_metrics(kpts)
            
            # Initialize data for new person
            if p_id not in person_data:
                person_data[p_id] = {"state": "STANDING", "prev_y": curr_y, "ema": 0, "inactivity": None}
            
            p = person_data[p_id]
            
            # Velocity Calculation (Normalized)
            vel = (curr_y - p["prev_y"]) / height if p["prev_y"] else 0
            p["ema"] = 0.4 * vel + 0.6 * p["ema"]
            p["prev_y"] = curr_y

            # --- Logic: Fall Verification ---
            if p["state"] == "STANDING":
                if p["ema"] > 0.15 or angle > 60: # Detect drop OR sudden tilt
                    p["state"] = "FALLING"
            
            elif p["state"] == "FALLING":
                if angle > 55: # Horizontal check
                    if p["inactivity"] is None: p["inactivity"] = time.time()
                    if time.time() - p["inactivity"] > 2:
                        p["state"] = "FALLEN"
                        socket.send_multipart([b"fall_events", json.dumps({"id": p_id, "event": "FALL"}).encode()])
                else:
                    if angle < 30: p["state"] = "STANDING"

            elif p["state"] == "FALLEN":
                if angle < 30: p["state"] = "STANDING"

            # Visual Feedback per person
            color = (0, 0, 255) if p["state"] == "FALLEN" else (0, 255, 0)
            cv2.putText(frame, "ID {}: {}".format(p_id, p["state"]), 
                        (int(kpts[0][0]), int(kpts[0][1] - 20)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("Multi-Person Fall Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()