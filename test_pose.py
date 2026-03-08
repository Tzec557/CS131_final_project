from ultralytics import YOLO

import cv2


# Load YOLOv8n (smallest model)

model = YOLO("yolov8n.pt")


# Open webcam (USB)

cap = cv2.VideoCapture(0)


while True:

    ret, frame = cap.read()

    if not ret:

        break


    # Run inference

    results = model(frame, imgsz=640)


    # Annotate frame

    annotated = results[0].plot()


    cv2.imshow("YOLOv8 Jetson Nano", annotated)

    if cv2.waitKey(1) & 0xFF == ord('q'):

        break


cap.release()

cv2.destroyAllWindows()
