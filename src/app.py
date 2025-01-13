# src/app.py

import eventlet
eventlet.monkey_patch()  # Must be the first import to ensure proper monkey patching

from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import threading
import time
import cv2
import logging
import signal

from flipper import fetch_flipper_data  # Ensure flipper.py is in the correct path
from shared import signals_data, signals_lock, selected_signal  # Import shared data structures
from config import config  # Import configuration from config.py

# Initialize Flask app and SocketIO with eventlet
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# GStreamer pipeline configuration (updated to match the working manual pipeline)
gst_pipeline = (
    "libcamerasrc ! "
    "queue ! "
    "videoconvert ! "
    "video/x-raw,format=BGR,width=640,height=480,framerate=15/1 ! "
    "appsink sync=false"
)

class CameraStream:
    def __init__(self):
        self.cap = cv2.VideoCapture(
            gst_pipeline, cv2.CAP_GSTREAMER
        )
        if not self.cap.isOpened():
            logging.error("Failed to open GStreamer pipeline for the camera. Check the pipeline and permissions.")
        else:
            logging.info("Camera pipeline opened successfully.")

    def generate_frames(self):
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                logging.error("Camera is not opened. Attempting to reopen...")
                self.cap.release()
                time.sleep(5)  # Wait before retrying
                self.cap = cv2.VideoCapture(
                    gst_pipeline, cv2.CAP_GSTREAMER
                )
                if not self.cap.isOpened():
                    logging.error("Reopening camera failed. Retrying in 5 seconds...")
                    continue
                else:
                    logging.info("Camera reopened successfully.")
                    continue

            # Encode the frame in JPEG format
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                logging.error("Failed to encode frame.")
                continue
            frame = buffer.tobytes()

            # Yield frame in byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(camera_stream.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def emit_signals():
    """
    Emit signal updates to all connected clients.
    """
    while True:
        with signals_lock:
            all_signals = []
            for signal_type, data_list in signals_data.items():
                for item in data_list:
                    all_signals.append({**item, "type": signal_type})

        # Emit the signals to all connected clients
        socketio.emit('update_signals', {'signals': all_signals})

        # Use socketio.sleep for non-blocking sleep in SocketIO context
        socketio.sleep(config.get('signal_update_interval', 5))  # Default to 5 seconds if not specified

# Initialize CameraStream
camera_stream = CameraStream()

# Start emit_signals thread
signals_thread = threading.Thread(target=emit_signals)
signals_thread.daemon = True
signals_thread.start()

def handle_shutdown(signal_num, frame):
    """Handle application shutdown gracefully."""
    logging.info("Received shutdown signal.")
    if camera_stream.cap.isOpened():
        camera_stream.cap.release()
    socketio.stop()

# Register shutdown handler
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

if __name__ == '__main__':
    try:
        logging.info("Starting the application with SocketIO...")
        socketio.run(app, host='0.0.0.0', port=5000)
    except Exception as e:
        logging.error(f"Application failed to start: {e}")
