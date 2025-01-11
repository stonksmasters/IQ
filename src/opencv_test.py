import cv2

pipeline = (
    "libcamerasrc ! queue ! videoconvert ! video/x-raw,format=BGR,width=1280,height=1080,framerate=30/1 ! appsink sync=false"
)

cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Error: Unable to open the camera.")
else:
    print("Camera is streaming. Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Unable to read frame.")
            break

        cv2.imshow("Camera Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
