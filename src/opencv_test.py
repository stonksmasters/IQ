import cv2

def test_camera():
    print("Attempting to open camera using GStreamer pipeline...")
    gst_pipeline = (
        "libcamerasrc ! "
        "queue ! videoconvert ! "
        "queue ! video/x-raw,format=BGR,width=1280,height=1080,framerate=30/1 ! "
        "appsink"
    )

    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Failed to open the camera using pipeline:")
        print(gst_pipeline)
        print("Ensure the camera is connected and accessible.")
        return

    print("Camera opened successfully. Press 'q' to exit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame from the camera.")
            break

        cv2.imshow("Camera Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

test_camera()
