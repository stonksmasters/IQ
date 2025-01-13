#/src/app.py

import eventlet
eventlet.monkey_patch()  # Ensure this is the first line for proper monkey patching

from flask import Flask, render_template, request, jsonify, Response, Blueprint
from flask_socketio import SocketIO, emit
import threading
import time
import cv2
import logging
import signal

from flipper import fetch_flipper_data  # Ensure flipper.py is in the correct path
from shared import signals_data, signals_lock, selected_signal  # Import shared data structures
from config import config  # Import configuration from config.py

# ------------------------------
# Logging Configuration
# ------------------------------
def setup_logging(log_level=logging.INFO, log_file="app.log"):
    """
    Setup logging configuration.
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Stream handler (console)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

setup_logging()

logger = logging.getLogger(__name__)

# ------------------------------
# Flask App Initialization
# ------------------------------
app = Flask(__name__)

# ------------------------------
# Initialize SocketIO
# ------------------------------
socketio = SocketIO(app, async_mode='eventlet')

# ------------------------------
# Video Feed Generation (MJPEG)
# ------------------------------
class CameraStream:
    """
    Singleton class to handle camera streaming using GStreamer and OpenCV.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, gst_pipeline):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CameraStream, cls).__new__(cls)
                cls._instance.init_camera(gst_pipeline)
            return cls._instance

    def init_camera(self, gst_pipeline):
        self.gst_pipeline = gst_pipeline
        self.cap = cv2.VideoCapture(self.gst_pipeline, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            logger.error("Failed to open GStreamer pipeline for the camera. Check the pipeline and permissions.")
        else:
            logger.info("Camera pipeline opened successfully.")
        self.running = True
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()
        self.frame = None

    def update(self):
        while self.running:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    if frame is not None and frame.size != 0:
                        self.frame = frame
                        logger.debug("Frame captured successfully.")
                    else:
                        logger.error("Received an invalid frame.")
                else:
                    logger.warning("Failed to grab frame from the camera.")
                    time.sleep(1)  # Wait before retrying
            else:
                logger.error("Camera is not opened. Attempting to reopen...")
                self.cap = cv2.VideoCapture(self.gst_pipeline, cv2.CAP_GSTREAMER)
                if not self.cap.isOpened():
                    logger.error("Reopening camera failed. Retrying in 5 seconds...")
                    time.sleep(5)

    def get_frame(self):
        return self.frame

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
        if self.cap.isOpened():
            self.cap.release()
        logger.info("Camera pipeline closed.")

def generate_frames(camera_stream):
    """
    Generator function that yields MJPEG frames from the camera.
    """
    while True:
        frame = camera_stream.get_frame()
        if frame is not None:
            # Encode the frame as JPEG
            success, buffer_encoded = cv2.imencode(".jpg", frame)
            if success:
                frame_bytes = buffer_encoded.tobytes()
                logger.debug("Frame encoded successfully.")
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
            else:
                logger.error("JPEG encoding failed.")
        else:
            logger.debug("No frame available yet.")
        socketio.sleep(0.033)  # Approximately 30 FPS

# Initialize CameraStream with configuration
cam_width = config.get('camera', {}).get('width', 640)
cam_height = config.get('camera', {}).get('height', 480)
cam_framerate = config.get('camera', {}).get('framerate', 15)

gst_pipeline = (
    "libcamerasrc ! "
    "queue ! "
    "videoconvert ! "
    "video/x-raw,format=BGR,width=640,height=480,framerate=15/1 ! "
    "appsink sync=false"
)





camera_stream = CameraStream(gst_pipeline)

# ------------------------------
# Flask Routes
# ------------------------------
main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/video_feed")
def video_feed():
    if camera_stream.cap.isOpened():
        logger.info("Video feed endpoint hit.")
        return Response(generate_frames(camera_stream), mimetype="multipart/x-mixed-replace; boundary=frame")
    else:
        logger.error("Camera not available for video feed.")
        return Response(status=503)  # Service Unavailable

@main_bp.route("/signals", methods=["GET"])
def get_signals():
    with signals_lock:
        all_signals = []
        for signal_type, data_list in signals_data.items():
            for item in data_list:
                all_signals.append({**item, "type": signal_type})
    logger.info(f"Signals returned: {all_signals}")
    return jsonify({"signals": all_signals})

@main_bp.route("/track_signal", methods=["POST"])
def track_signal_route():
    data = request.get_json()
    if not data:
        logger.warning("No data received in track_signal request.")
        return jsonify({"status": "failure", "message": "No data provided."}), 400
    signal_type = data.get("type")
    signal_name = data.get("name")
    if not signal_type or not signal_name:
        logger.warning("Incomplete data received in track_signal request.")
        return jsonify({"status": "failure", "message": "Incomplete data provided."}), 400
    with signals_lock:
        selected_signal.update({"type": signal_type, "name": signal_name, "position": None})
        logger.info(f"Tracking: {selected_signal}")
    return jsonify({"status": "success"})

@main_bp.route("/clear_signal", methods=["POST"])
def clear_signal_route():
    with signals_lock:
        selected_signal.update({"type": None, "name": None, "position": None})
    logger.info("Tracking cleared.")
    return jsonify({"status": "success"})

@main_bp.route("/flipper_bluetooth", methods=["GET"])
def flipper_bluetooth():
    try:
        known_positions = config.get("known_positions", {})
        bluetooth_data = fetch_flipper_data(known_positions)
        with signals_lock:
            signals_data["bluetooth"] = bluetooth_data
        logger.info(f"Flipper Bluetooth signals: {bluetooth_data}")
        return jsonify({"bluetooth_signals": bluetooth_data})
    except Exception as e:
        logger.error(f"Error fetching Flipper Bluetooth data: {e}")
        return jsonify({"status": "failure", "message": "Failed to fetch Bluetooth data."}), 500

@main_bp.route("/flipper_subghz", methods=["GET"])
def flipper_subghz():
    # Placeholder: Fetch SubGHz data from Flipper
    try:
        subghz_data = []  # Replace with actual implementation
        with signals_lock:
            signals_data["subghz"] = subghz_data
        logger.info(f"Flipper SubGHz signals: {subghz_data}")
        return jsonify({"subghz_signals": subghz_data})
    except Exception as e:
        logger.error(f"Error fetching Flipper SubGHz data: {e}")
        return jsonify({"status": "failure", "message": "Failed to fetch SubGHz data."}), 500

@main_bp.route("/flipper_nfc", methods=["GET"])
def flipper_nfc():
    # Placeholder: Fetch NFC data from Flipper
    try:
        nfc_data = []  # Replace with actual implementation
        with signals_lock:
            signals_data["nfc"] = nfc_data
        logger.info(f"Flipper NFC signals: {nfc_data}")
        return jsonify({"nfc_signals": nfc_data})
    except Exception as e:
        logger.error(f"Error fetching Flipper NFC data: {e}")
        return jsonify({"status": "failure", "message": "Failed to fetch NFC data."}), 500

@main_bp.route("/flipper_rfid", methods=["GET"])
def flipper_rfid():
    # Placeholder: Fetch RFID data from Flipper
    try:
        rfid_data = []  # Replace with actual implementation
        with signals_lock:
            signals_data["rfid"] = rfid_data
        logger.info(f"Flipper RFID signals: {rfid_data}")
        return jsonify({"rfid_signals": rfid_data})
    except Exception as e:
        logger.error(f"Error fetching Flipper RFID data: {e}")
        return jsonify({"status": "failure", "message": "Failed to fetch RFID data."}), 500

app.register_blueprint(main_bp)

# ------------------------------
# WebSocket Event Handlers
# ------------------------------

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit('connection_response', {'message': 'Connected to server.'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

# Function to emit signals to all connected clients
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

        # Emit the signals to all connected clients (broadcast by default)
        socketio.emit('update_signals', {'signals': all_signals})
        
        # Use socketio.sleep for non-blocking sleep in SocketIO context
        socketio.sleep(config.get('signal_update_interval', 5))  # Default to 5 seconds if not specified


# Start the signal emitter thread
signal_thread = threading.Thread(target=emit_signals, daemon=True)
signal_thread.start()

# ------------------------------
# Graceful Shutdown
# ------------------------------
def handle_exit(signum, frame):
    logger.info(f"Received signal {signum}. Shutting down server...")
    camera_stream.stop()
    socketio.stop()  # Ensure SocketIO stops gracefully
    logger.info("Server shutdown complete.")
    exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# ------------------------------
# Main Entry Point
# ------------------------------
# Note: main.py will handle running the server with SocketIO
