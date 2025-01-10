import cv2

def test_camera():
    print("Attempting to open camera using GStreamer pipeline...")
    gst_pipeline = (
        "libcamerasrc ! "
        "video/x-raw,width=640,height=480,framerate=30/1 ! "
        "videoconvert ! appsink"
    )
    
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Failed to open the camera. Ensure the camera is connected and accessible.")
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
