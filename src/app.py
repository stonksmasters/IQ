from flask import Flask, render_template, Response
import cv2
from hud import overlay_hud
from utils.signal_detection import detect_wifi, detect_bluetooth
from utils.flipper_integration import get_flipper_signals
import threading
import time

app = Flask(__name__)

# Initialize the camera
camera = cv2.VideoCapture(0)

# Shared data structures for signals
wifi_signals = []
bluetooth_signals = []
flipper_signals = []

# Lock for thread-safe operations
lock = threading.Lock()

def update_signals():
    global wifi_signals, bluetooth_signals, flipper_signals
    while True:
        with lock:
            wifi_signals = detect_wifi()
            bluetooth_signals = detect_bluetooth()
            flipper_signals = get_flipper_signals()
        # Adjust the sleep duration as needed
        time.sleep(5)

# Start the signal update thread
signal_thread = threading.Thread(target=update_signals, daemon=True)
signal_thread.start()

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            with lock:
                # Overlay the HUD with detected signals
                frame = overlay_hud(frame, wifi_signals, bluetooth_signals, flipper_signals)
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
