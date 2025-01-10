# app.py

from flask import Flask, render_template, request, jsonify, Response, Blueprint
import threading
import time
import cv2
import numpy as np
import os
import logging
import signal
import yaml

# If you rely on these in your environment, keep them; otherwise comment them out:
# from hud import overlay_hud
# from utils.autodetect import AutoDetection
# from utils.signal_detection import detect_wifi, detect_bluetooth
# from flipper import fetch_flipper_data
# from utils.triangulation import triangulate

# ------------------------------
# Configuration Management
# ------------------------------

def load_config(config_path='config/config.yaml'):
    """
    Load configuration from a YAML file.
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logging.info("Configuration loaded successfully.")
        return config
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return {}

config = load_config()

# ------------------------------
# Logging Configuration
# ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ------------------------------
# Flask App Initialization
# ------------------------------
app = Flask(__name__)

# If you have any signal structures or detection code, you can keep or remove them:
signals_data = {
    "wifi": [],
    "bluetooth": [],
    "flipper": []
}
selected_signal = {"type": None, "name": None, "position": None}
signals_lock = threading.Lock()

# (Optional) If you do not need these update threads or detection, remove them
def update_signals():
    """
    Stub function or your real scanning code.
    """
    while True:
        with signals_lock:
            # Example: logging or scanning code goes here
            pass
        time.sleep(5)

signal_thread = threading.Thread(target=update_signals, daemon=True)
signal_thread.start()

main_bp = Blueprint('main', __name__)

# ------------------------------
# Video Feed Generation (MJPEG)
# ------------------------------

def generate_frames():
    """
    Generates MJPEG frames from the Pi camera using GStreamer + OpenCV.
    """
    # Modify your camera resolution, etc., here if needed:
    cam_width = config.get('camera', {}).get('width', 640)
    cam_height = config.get('camera', {}).get('height', 480)
    cam_framerate = config.get('camera', {}).get('framerate', 24)

    gst_pipeline = (
        f"v4l2src device=/dev/video0 ! "
        f"video/x-raw,width={cam_width},height={cam_height},framerate={cam_framerate}/1 ! "
        f"videoconvert ! appsink drop=true"
    )

    logger.info("Opening camera (/dev/video0) for MJPEG streaming...")
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        logger.error("Failed to open GStreamer pipeline for the camera.")
        return  # End the generator if camera fails

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to grab frame from camera.")
                break

            # If you want to apply any overlay/detections, do it here:
            # frame = overlay_hud(frame, ... )  # etc.

            success, buffer_encoded = cv2.imencode(".jpg", frame)
            if not success:
                logger.error("JPEG encode failed.")
                continue

            frame_bytes = buffer_encoded.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
    except Exception as e:
        logger.error(f"Error in generate_frames: {e}")
    finally:
        cap.release()
        logger.info("Camera pipeline closed.")

# ------------------------------
# Flask Routes
# ------------------------------

@main_bp.route("/")
def index():
    """
    Serve a simple HTML page that references /video_feed as the camera source.
    """
    return render_template("index.html")

@main_bp.route("/video_feed")
def video_feed():
    """
    MJPEG stream route: embed via <img src="/video_feed" /> in HTML.
    """
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

# (Optional) Minimal endpoints for signals or other data:

@main_bp.route("/signals", methods=["GET"])
def get_signals():
    """
    Returns any stub signals if you want to fetch them on your page.
    """
    with signals_lock:
        # Return an empty or mock data if not scanning
        all_signals = []
        for w in signals_data["wifi"]:
            all_signals.append({**w, "type": "wifi"})
        for b in signals_data["bluetooth"]:
            all_signals.append({**b, "type": "bluetooth"})
        for f in signals_data["flipper"]:
            all_signals.append({**f, "type": "flipper"})

    logger.info(f"Signals returned: {all_signals}")
    return jsonify({"signals": all_signals})

# (Optional) If you track signals
@main_bp.route("/track_signal", methods=["POST"])
def track_signal_route():
    data = request.get_json()
    with signals_lock:
        selected_signal["type"] = data.get("type")
        selected_signal["name"] = data.get("name")
        selected_signal["position"] = None
        logger.info(f"Tracking: {selected_signal}")
    return jsonify({"status": "success"})

@main_bp.route("/clear_signal", methods=["POST"])
def clear_signal_route():
    with signals_lock:
        selected_signal["type"] = None
        selected_signal["name"] = None
        selected_signal["position"] = None
    return jsonify({"status": "success"})

# ------------------------------
# Graceful Shutdown
# ------------------------------
def handle_exit(signum, frame):
    logger.info("Shutting down server...")
    signal_thread.join(timeout=2)
    logger.info("Shutdown complete.")
    exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

app.register_blueprint(main_bp)

# ------------------------------
# Main
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
