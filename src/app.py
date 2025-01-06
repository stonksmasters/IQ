from flask import Flask, render_template, Response
import cv2
from hud import overlay_hud
from utils.signal_detection import detect_wifi, detect_bluetooth
import threading
import time

app = Flask(__name__)

# Initialize the camera
camera = cv2.VideoCapture(0)
if not camera.isOpened():
    print("Error: Unable to access the camera.")
    exit(1)

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
                # Update Wi-Fi signals
                wifi_signals = detect_wifi()

                # Update Bluetooth signals
                bluetooth_signals = detect_bluetooth()
            except Exception as e:
                print(f"Signal update error: {e}")
        # Adjust the sleep duration as needed
        time.sleep(5)

# Start the signal update thread
signal_thread = threading.Thread(target=update_signals, daemon=True)
signal_thread.start()

def generate_frames():
    """
    Continuously generates video frames from the camera with overlaid HUD data.
    """
    while True:
        success, frame = camera.read()
        if not success:
            print("Failed to read frame from camera")
            break
        else:
            with lock:
                # Overlay the HUD with detected signals
                frame = overlay_hud(frame, wifi_signals, bluetooth_signals, [])
            # Encode the frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

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
        if camera.isOpened():
            camera.release()
