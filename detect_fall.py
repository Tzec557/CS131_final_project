from ultralytics import YOLO
import cv2

model = YOLO("yolov8n-pose.pt")
cap = cv2.VideoCapture(0)

# Get frame dimensions to calculate the "Floor Zone"
ret, frame = cap.read()
if ret:
    H, W, _ = frame.shape
    floor_line = int(H * 0.8) # Bottom 20% of the screen is the floor
else:
    floor_line = 400

while True:
    ret, frame = cap.read()
    if not ret: break

    results = model(frame, imgsz=320, conf=0.5)
    annotated_frame = results[0].plot()

    # Draw a line representing the "Floor Zone" for debugging
    cv2.line(annotated_frame, (0, floor_line), (W, floor_line), (255, 255, 0), 2)

    if results[0].keypoints is not None:
        for kpts in results[0].keypoints.data:
            # 0: Nose, 13: Left Knee, 14: Right Knee
            nose = kpts[0]
            l_knee = kpts[13]
            r_knee = kpts[14]

            # 1. Check if knees are detected
            if l_knee[2] > 0.5 or r_knee[2] > 0.5:
                # Use whichever knee is more visible
                knee_y = l_knee[1] if l_knee[2] > r_knee[2] else r_knee[1]
                
                # FALL LOGIC: 
                # Is the knee below the floor line? 
                # AND is the nose close to the knee? (Person is crumpled/lying)
                vertical_gap = abs(nose[1] - knee_y)
                
                if knee_y > floor_line and vertical_gap < (H * 0.25):
                    cv2.putText(annotated_frame, "FALL ON FLOOR!", (50, 80), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

    cv2.imshow("Bedside Fall Monitor", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()