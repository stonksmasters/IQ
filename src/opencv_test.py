import cv2

def test_camera():
    print("Attempting to open camera...")
    cap = cv2.VideoCapture(0)  # Use /dev/video0

    if not cap.isOpened():
        print("Failed to open the camera. Ensure the camera is connected and accessible.")
        return

    print("Camera opened successfully. Press 'q' to exit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame from the camera.")
            break

        # Display the frame in a window
        cv2.imshow("Camera Test", frame)

        # Press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Camera test completed.")

if __name__ == "__main__":
    test_camera()
