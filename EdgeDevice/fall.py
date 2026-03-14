import argparse
import time
import cv2
import numpy as np
import json
import zmq
from ultralytics import YOLO

parser = argparse.ArgumentParser()
parser.add_argument("--port", default="5555")
parser.add_argument("--video", default=0, help="Video source (0, 1, or file path)")
parser.add_argument("--device_id", default="cam_01", help="Unique ID for this camera")
args = parser.parse_args()

# ZMQ Setup (Publisher)
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind(f"tcp://*:{args.port}")

model = YOLO("yolov8n-pose.pt")

# Ensure video source is handled as int for webcams
video_source = int(args.video) if str(args.video).isdigit() else args.video
cap = cv2.VideoCapture(video_source)

person_data = {}

def compute_metrics(kpts):
    s_mid = (kpts[5][:2] + kpts[6][:2]) / 2
    h_mid = (kpts[11][:2] + kpts[12][:2]) / 2
    dx, dy = h_mid[0] - s_mid[0], h_mid[1] - s_mid[1]
    angle = np.degrees(np.arctan2(abs(dx), abs(dy)))
    valid = kpts[kpts[:, 2] > 0.3]
    height = max(valid[:, 1]) - min(valid[:, 1]) if len(valid) > 1 else 1
    return angle, s_mid[1], height

while True:
    ret, frame = cap.read()
    if not ret: break

    results = model.track(frame, imgsz=320, conf=0.4, persist=True, verbose=False)
    
    if results[0].keypoints is not None and results[0].boxes.id is not None:
        ids = results[0].boxes.id.int().cpu().tolist()
        keypoints = results[0].keypoints.data 

        for i, p_id in enumerate(ids):
            kpts = keypoints[i]
            angle, curr_y, height = compute_metrics(kpts)
            
            if p_id not in person_data:
                person_data[p_id] = {"state": "STANDING", "prev_y": curr_y, "ema": 0, "inactivity": None}
            
            
            p = person_data[p_id]
            vel = (curr_y - p["prev_y"]) / height if p["prev_y"] else 0
            p["ema"] = 0.4 * vel + 0.6 * p["ema"]
            p["prev_y"] = curr_y

            if p["state"] == "STANDING":
                if p["ema"] > 0.15 or angle > 60:
                    p["state"] = "FALLING"
            
            elif p["state"] == "FALLING":
                if angle > 55:
                    if p["inactivity"] is None: p["inactivity"] = time.time()
                    if time.time() - p["inactivity"] > 2:
                        p["state"] = "FALLEN"
                        
                        # Payload with Device ID
                        payload = {
                            "device_id": args.device_id,
                            "person_id": p_id,
                            "event": "FALL",
                            "timestamp": time.time()
                        }
                        socket.send_multipart([b"fall_events", json.dumps(payload).encode()])
                        print(f"!!! FALL DETECTED - Camera: {args.device_id}, Person ID: {p_id} !!!")
                else:
                    if angle < 30: p["state"] = "STANDING"

            elif p["state"] == "FALLEN":
                if angle < 30: 
                    p["state"] = "STANDING"
                    p["inactivity"] = None

            # UI logic
            color = (0, 0, 255) if p["state"] == "FALLEN" else (0, 255, 0)
            cv2.putText(frame, f"ID {p_id}: {p['state']}", (int(kpts[0][0]), int(kpts[0][1] - 20)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow(f"Detection - {args.device_id}", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()


