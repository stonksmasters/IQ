import cv2

def main():
    # Initialize the camera
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Cannot open camera")
        return

    print("Camera successfully opened. Saving frames to disk...")

    while True:
        # Capture frame-by-frame
        ret, frame = camera.read()

        # If frame reading was not successful, break the loop
        if not ret:
            print("Failed to grab frame")
            break

        # Save the frame to disk
        cv2.imwrite('frame.jpg', frame)
        print("Saved frame to frame.jpg")
        break  # Exit after saving one frame

    # When everything done, release the capture
    camera.release()

if __name__ == "__main__":
    main()
