import cv2
import os

def main():
    # Define GStreamer pipeline matching the working command
    gst_pipeline = (
        "libcamerasrc ! "
        "queue ! "
        "videoconvert ! "
        "video/x-raw,format=BGR,width=640,height=480,framerate=15/1 ! "
        "appsink sync=false"
    )

    # Initialize VideoCapture with the GStreamer pipeline
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("Error: Unable to open the camera.")
        return

    print("Camera is streaming. Capturing 5 frames...")

    # Directory to save captured frames
    save_dir = "captured_frames"
    os.makedirs(save_dir, exist_ok=True)

    for i in range(1, 6):
        ret, frame = cap.read()
        if not ret:
            print(f"Error: Unable to read frame {i}.")
            continue

        # Define filename for the captured frame
        frame_filename = os.path.join(save_dir, f"frame_{i}.jpg")

        # Save the captured frame as a JPEG file
        success = cv2.imwrite(frame_filename, frame)
        if success:
            print(f"Captured and saved {frame_filename}")
        else:
            print(f"Failed to save {frame_filename}")

    cap.release()
    print("Camera pipeline closed.")

if __name__ == "__main__":
    main()
