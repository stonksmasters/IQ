import cv2

def test_camera():
    """
    Tests the camera feed using an updated GStreamer pipeline.
    Displays the video feed in a window.
    Press 'q' to exit the feed.
    """
    print("Attempting to open camera using GStreamer pipeline...")

    # Updated GStreamer pipeline
    gst_pipeline = (
        "libcamerasrc ! "
        "video/x-raw,format=I420,width=1280,height=1080,framerate=30/1 ! "
        "videoconvert ! appsink"
    )

    # Initialize VideoCapture
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Failed to open the camera. Ensure the camera is connected and the pipeline is correct.")
        return

    print("Camera opened successfully. Press 'q' to exit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame from the camera. Exiting...")
            break

        # Display the video feed in a window
        cv2.imshow("Camera Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Exiting camera feed...")
            break

    # Release the camera and close any OpenCV windows
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_camera()
