import cv2

def test_camera():
    """
    Tests the camera feed using a verified GStreamer pipeline.
    """
    print("Attempting to open camera using GStreamer pipeline...")

    # Verified GStreamer pipeline
    gst_pipeline = (
        "libcamerasrc ! "
        "videoconvert ! "
        "video/x-raw,format=I420,width=1280,height=1080,framerate=30/1 ! "
        "appsink"
    )

    # Initialize VideoCapture with the pipeline
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print(f"Failed to open the camera using pipeline:\n{gst_pipeline}")
        print("Ensure the camera is connected and accessible.")
        return

    print("Camera opened successfully. Press 'q' to exit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame from the camera. Exiting...")
            break

        # Display the video feed
        cv2.imshow("Camera Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Exiting camera feed...")
            break

    # Clean up
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_camera()
