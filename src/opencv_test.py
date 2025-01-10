import cv2
import time

def test_camera():
    print("Attempting to open camera...")
    # Use VideoCapture with V4L2 and set format to YUYV
    gst_pipeline = (
        "v4l2src device=/dev/video0 ! "
        "video/x-raw,format=YUY2,width=640,height=480,framerate=30/1 ! "
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

        # Display the frame
        cv2.imshow("Camera Test", frame)

        # Exit if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Camera test completed.")

if __name__ == "__main__":
    test_camera()
