#/src/app.py

from flask import Flask, render_template, request, jsonify, Response, Blueprint
import threading
import time
import cv2
import logging
import signal
import yaml

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
    format="%(asctime)s %(levelname)s: %(message)s",
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

signals_lock = threading.Lock()
signals_data = {
    "wifi": [],
    "bluetooth": [],
    "flipper": []
}
selected_signal = {"type": None, "name": None, "position": None}

# ------------------------------
# Video Feed Generation (MJPEG)
# ------------------------------
def generate_frames():
    """
    Generates MJPEG frames from the Pi camera using GStreamer + OpenCV.
    """
    cam_width = config.get('camera', {}).get('width', 1280)
    cam_height = config.get('camera', {}).get('height', 1080)
    cam_framerate = config.get('camera', {}).get('framerate', 30)

    gst_pipeline = (
        "libcamerasrc ! "
        "queue ! "
        "videoconvert ! "
        f"video/x-raw,format=BGR,width={cam_width},height={cam_height},framerate={cam_framerate}/1 ! "
        "appsink sync=false"
    )

    logger.info(f"Using GStreamer pipeline: {gst_pipeline}")
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        logger.error("Failed to open GStreamer pipeline for the camera. Check the pipeline and permissions.")
        yield b""
        return

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                logger.warning("Failed to grab frame from the camera. Retrying in 1 second...")
                time.sleep(1)  # Wait and retry if the camera fails to capture a frame
                continue

            # Check if the frame is valid
            if frame is None or frame.size == 0:
                logger.error("Received an invalid frame. Skipping...")
                continue

            # Encode the frame as JPEG
            success, buffer_encoded = cv2.imencode(".jpg", frame)
            if not success:
                logger.error("JPEG encoding failed. Skipping this frame...")
                continue

            frame_bytes = buffer_encoded.tobytes()
            logger.debug("Frame encoded successfully.")

            # Yield the frame bytes as an MJPEG stream
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )

    except Exception as e:
        logger.error(f"Error in generate_frames: {e}")
    finally:
        # Ensure the video capture resource is released
        cap.release()
        logger.info("Camera pipeline closed.")

# ------------------------------
# Flask Routes
# ------------------------------
main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/video_feed")
def video_feed():
    logger.info("Video feed endpoint hit.")
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@main_bp.route("/signals", methods=["GET"])
def get_signals():
    with signals_lock:
        all_signals = []
        for w in signals_data["wifi"]:
            all_signals.append({**w, "type": "wifi"})
        for b in signals_data["bluetooth"]:
            all_signals.append({**b, "type": "bluetooth"})
        for f in signals_data["flipper"]:
            all_signals.append({**f, "type": "flipper"})

    logger.info(f"Signals returned: {all_signals}")
    return jsonify({"signals": all_signals})

@main_bp.route("/track_signal", methods=["POST"])
def track_signal_route():
    data = request.get_json()
    logger.debug(f"Track signal request data: {data}")
    with signals_lock:
        selected_signal.update({"type": data.get("type"), "name": data.get("name"), "position": None})
        logger.info(f"Tracking: {selected_signal}")
    return jsonify({"status": "success"})

@main_bp.route("/clear_signal", methods=["POST"])
def clear_signal_route():
    with signals_lock:
        selected_signal.update({"type": None, "name": None, "position": None})
    logger.info("Tracking cleared.")
    return jsonify({"status": "success"})

# ------------------------------
# Graceful Shutdown
# ------------------------------
def handle_exit(signum, frame):
    logger.info("Shutting down server...")
    exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

app.register_blueprint(main_bp)

# ------------------------------
# Main
# ------------------------------
if __name__ == "__main__":
    logger.info("Starting Flask app.")
    app.run(host="0.0.0.0", port=5000, debug=config.get('debug', False))
