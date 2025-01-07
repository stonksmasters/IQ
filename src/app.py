# src/app.py

from flask import Flask, render_template, Response
import subprocess
from hud import overlay_hud
from utils.signal_detection import detect_wifi, detect_bluetooth
import threading
import time
import cv2
import numpy as np
import os
import logging
import shutil  # Added import for shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

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
                logging.info("Updating Wi-Fi and Bluetooth signals.")
                wifi_signals = detect_wifi()
                bluetooth_signals = detect_bluetooth()
            except Exception as e:
                logging.error(f"Signal update error: {e}")
        time.sleep(5)

# Start the signal update thread
signal_thread = threading.Thread(target=update_signals, daemon=True)
signal_thread.start()

def generate_frames():
    """
    Generates video frames by reading from libcamera-vid subprocess,
    decoding JPEG frames, overlaying HUD data, and yielding them for streaming.
    """
    # Get the absolute path for libcamera-vid
    libcamera_path = shutil.which("libcamera-vid")
    if libcamera_path is None:
        logging.error("libcamera-vid not found. Ensure it is installed and in the PATH.")
        return

    # Launch libcamera-vid subprocess
    process = subprocess.Popen(
        ["libcamera-vid", "--codec", "mjpeg", "--width", "640", "--height", "480", "-o", "-", "-t", "0", "--inline"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    buffer = b""
    start_marker = b'\xff\xd8'  # JPEG start
    end_marker = b'\xff\xd9'    # JPEG end

    try:
        while True:
            chunk = process.stdout.read(1024)
            if not chunk:
                logging.error("Failed to read frame from camera.")
                break
            buffer += chunk

            # Search for JPEG start and end
            start = buffer.find(start_marker)
            end = buffer.find(end_marker)

            if start != -1 and end != -1 and end > start:
                jpeg = buffer[start:end+2]
                buffer = buffer[end+2:]

                # Decode JPEG
                frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    logging.warning("Failed to decode frame, skipping...")
                    continue

                with lock:
                    # Overlay HUD data
                    frame = overlay_hud(frame, wifi_signals, bluetooth_signals, [])

                # Encode frame as JPEG
                _, buffer_encoded = cv2.imencode('.jpg', frame)
                frame_bytes = buffer_encoded.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    except Exception as e:
        logging.error(f"Error in generate_frames: {e}")
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
        logging.info("Starting Flask server.")
        app.run(host="0.0.0.0", port=5000, debug=True)
    except KeyboardInterrupt:
        logging.info("Shutting down server...")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
