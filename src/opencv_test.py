import cv2

def test_camera():
    """
    Test the camera using a GStreamer pipeline and display the live feed.
    Press 'q' to exit the feed.
    """
    # Define the GStreamer pipeline for accessing the camera
    gst_pipeline = (
        "libcamerasrc ! "
        "video/x-raw,format=YUY2,width=320,height=240,framerate=30/1 ! "
        "videoconvert ! appsink"
    )

    print("Attempting to open camera using GStreamer pipeline...")
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

    # Check if the camera was successfully opened
    if not cap.isOpened():
        print("ERROR: Failed to open the camera.")
        print("Ensure the camera is connected, accessible, and the GStreamer pipeline is correct.")
        return

    print("Camera opened successfully. Press 'q' to exit the feed.")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("ERROR: Failed to read frame from the camera.")
                break

            # Display the camera feed
            cv2.imshow("Camera Feed", frame)

            # Exit if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Exiting camera feed...")
                break
    except KeyboardInterrupt:
        print("\nCamera feed interrupted by user.")
    finally:
        # Release resources and close windows
        cap.release()
        cv2.destroyAllWindows()
        print("Camera resources released. All windows closed.")

if __name__ == "__main__":
    test_camera()
