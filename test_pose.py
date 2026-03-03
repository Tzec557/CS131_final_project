from ultralytics import YOLO
import cv2

# 1. Load the Pose model (Nano version for speed)
model = YOLO('yolov8n-pose.pt')

# 2. GStreamer Pipeline for the CSI Camera
def gstreamer_pipeline(w=640, h=480, fps=30, flip=0):
    return (
        f"nvarguscamerasrc ! video/x-raw(memory:NVMM), width={w}, height={h}, format=NV12, framerate={fps}/1 ! "
        f"nvvidconv flip-method={flip} ! video/x-raw, width={w}, height={h}, format=BGRx ! "
        f"videoconvert ! video/x-raw, format=BGR ! appsink"
    )

# 3. Initialize Camera
cap = cv2.VideoCapture(gstreamer_pipeline(flip=0), cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Error: Could not open camera. Check your ribbon cable!")
    exit()

print("Starting Pose Estimation... Press 'q' to stop.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLOv8 Pose inference
    # stream=True helps with memory management on Jetson
    results = model(frame, stream=True, conf=0.5)

    for r in results:
        # Plot results on the frame
        annotated_frame = r.plot()
        
        # Show the output
        cv2.imshow("YOLOv8 Pose - Jetson Nano", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()