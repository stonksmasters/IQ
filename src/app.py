# src/app.py

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
    Generates video frames by reading from libcamera-vid subprocess,
    decoding JPEG frames, overlaying HUD data, and yielding them for streaming.
    """
    process = subprocess.Popen(
        ["libcamera-vid", "--codec", "mjpeg", "-o", "-", "-t", "0", "--inline"],
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
                print("Failed to read frame from camera")
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
                    print("Failed to decode frame, skipping...")
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
