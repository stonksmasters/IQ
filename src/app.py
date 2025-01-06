from flask import Flask, render_template, Response
import subprocess
from hud import overlay_hud
from utils.signal_detection import detect_wifi, detect_bluetooth
import threading
import time
import cv2
import numpy as np

app = Flask(__name__)

# Shared data structures for signals
wifi_signals = []
bluetooth_signals = []

# Lock for thread-safe operations
lock = threading.Lock()

def update_signals():
    """
    Periodically updates Wi-Fi and Bluetooth signals in a separate thread.
    """
    global wifi_signals, bluetooth_signals
    while True:
        with lock:
            try:
                wifi_signals = detect_wifi()
                bluetooth_signals = detect_bluetooth()
            except Exception as e:
                print(f"Signal update error: {e}")
        time.sleep(5)

# Start the signal update thread
signal_thread = threading.Thread(target=update_signals, daemon=True)
signal_thread.start()

def generate_frames():
    """
    Generates video frames using libcamera-vid and overlays HUD data.
    """
    process = subprocess.Popen(
        ["libcamera-vid", "--codec", "mjpeg", "-o", "-", "-t", "0", "--inline"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        while True:
            # Read frame data
            frame_data = process.stdout.read(2 * 1024 * 1024)  # Increase buffer size
            if not frame_data:
                print("Failed to read frame from camera")
                break

            # Decode MJPEG frame
            np_frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)
            if frame is None:
                print("Failed to decode frame, skipping...")
                continue

            with lock:
                # Overlay HUD data
                frame = overlay_hud(frame, wifi_signals, bluetooth_signals, [])

            # Encode frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    except Exception as e:
        print(f"Error in generate_frames: {e}")
    finally:
        process.terminate()
        process.wait()

@app.route('/')
def index():
    """
    Renders the main HTML page for the application.
    """
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """
    Provides the video feed with HUD overlays as a streaming response.
    """
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=True)
    except KeyboardInterrupt:
        print("\nShutting down server...")
