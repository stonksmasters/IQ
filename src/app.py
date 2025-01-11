from flask import Flask, render_template, request, jsonify, Response, Blueprint
import threading
import time
import cv2
import logging
import signal
import yaml
import asyncio
from src.utils.signal_detection import detect_wifi, detect_bluetooth, prepare_triangulation_data
from src.utils.triangulation import calculate_distances_and_triangulate
from src.flipper import fetch_flipper_data
from src.hud import overlay_hud

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
    except FileNotFoundError:
        logging.warning(f"Configuration file '{config_path}' not found. Using defaults.")
        return {}
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
known_positions = {}  # Mapping of known device addresses to positions for triangulation

# ------------------------------
# Video Feed Generation (MJPEG)
# ------------------------------
def generate_frames():
    """
    Generates MJPEG frames with HUD overlays from the Pi camera using GStreamer + OpenCV.
    """
    # Fetch configuration values
    cam_width = config.get('camera', {}).get('width', 640)
    cam_height = config.get('camera', {}).get('height', 480)
    cam_framerate = config.get('camera', {}).get('framerate', 24)

    # Define GStreamer pipeline
    gst_pipeline = (
        f"libcamerasrc ! queue ! "
        f"videoconvert ! queue ! "
        f"video/x-raw,format=BGR,width={cam_width},height={cam_height},framerate={cam_framerate}/1 ! "
        f"appsink"
    )

    logger.info(f"Using GStreamer pipeline: {gst_pipeline}")
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        logger.error("Failed to open GStreamer pipeline. Check the camera connection and pipeline configuration.")
        yield b""  # Return empty bytes if camera initialization fails
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to grab frame from camera. Retrying...")
                time.sleep(0.5)
                continue

            # Add HUD overlays
            with signals_lock:
                frame = overlay_hud(frame, signals_data["wifi"] + signals_data["bluetooth"] + signals_data["flipper"], selected_signal)

            # Encode the frame in JPEG format
            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                logger.error("JPEG encoding failed.")
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
    except Exception as e:
        logger.error(f"Error in generate_frames: {e}")
    finally:
        cap.release()
        logger.info("Camera pipeline closed.")

# ------------------------------
# Signal Detection Thread
# ------------------------------
def detect_signals():
    """
    Continuously detects Wi-Fi, Bluetooth, and Flipper Zero signals.
    """
    global signals_data
    while True:
        try:
            wifi_results = detect_wifi()
            bluetooth_results = detect_bluetooth()
            flipper_results = fetch_flipper_data(known_positions)

            with signals_lock:
                signals_data["wifi"] = wifi_results
                signals_data["bluetooth"] = bluetooth_results
                signals_data["flipper"] = flipper_results

            logger.info(f"Signals detected: {len(wifi_results)} Wi-Fi, {len(bluetooth_results)} Bluetooth, {len(flipper_results)} Flipper")
        except Exception as e:
            logger.error(f"Error detecting signals: {e}")

        time.sleep(10)  # Adjust the interval as needed

signal_thread = threading.Thread(target=detect_signals, daemon=True)
signal_thread.start()

# ------------------------------
# Flask Routes
# ------------------------------
main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@main_bp.route("/signals", methods=["GET"])
def get_signals():
    with signals_lock:
        all_signals = signals_data["wifi"] + signals_data["bluetooth"] + signals_data["flipper"]
    return jsonify({"signals": all_signals})

@main_bp.route("/track_signal", methods=["POST"])
def track_signal_route():
    data = request.get_json()
    with signals_lock:
        selected_signal.update({"type": data.get("type"), "name": data.get("name"), "position": None})
        logger.info(f"Tracking signal: {selected_signal}")
    return jsonify({"status": "success"})

@main_bp.route("/clear_signal", methods=["POST"])
def clear_signal_route():
    with signals_lock:
        selected_signal.update({"type": None, "name": None, "position": None})
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
    app.run(host="0.0.0.0", port=5000, debug=config.get('debug', False))
