# src/opencv_test.py

import cv2
import logging

def test_camera(device_index=1):
    """
    Test camera access by capturing a single frame.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s:%(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    cap = cv2.VideoCapture(device_index, cv2.CAP_V4L2)

    if not cap.isOpened():
        logging.error(f"Error: Unable to open the camera at /dev/video{device_index}.")
        return

    ret, frame = cap.read()
    if not ret:
        logging.error(f"Error: Can't receive frame from /dev/video{device_index} (stream end?). Exiting ...")
    else:
        # Save the captured frame as an image file
        cv2.imwrite(f"test_frame_video{device_index}.jpg", frame)
        logging.info(f"Frame captured from /dev/video{device_index} and saved as test_frame_video{device_index}.jpg")

    cap.release()

if __name__ == "__main__":
    # Attempt to open /dev/video1
    test_camera(device_index=1)
