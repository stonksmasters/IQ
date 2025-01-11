from flask import Flask, render_template, request, jsonify, Response, Blueprint
import threading
import time
import cv2
import logging
import signal
import yaml
from flipper import fetch_flipper_data  # Import Flipper functionality

# ------------------------------
# Configuration Management
# ------------------------------
def load_config(config_path='config/config.yaml'):
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
    "bluetooth": [],
    "subghz": [],
    "nfc": [],
    "rfid": []
}
selected_signal = {"type": None, "name": None, "position": None}

# ------------------------------
# Video Feed Generation (MJPEG)
# ------------------------------
def generate_frames():
    cam_width = config.get('camera', {}).get('width', 640)
    cam_height = config.get('camera', {}).get('height', 480)
    cam_framerate = config.get('camera', {}).get('framerate', 24)

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
# Flask Routes
# ------------------------------
main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@main_bp.route("/flipper_bluetooth", methods=["GET"])
def flipper_bluetooth():
    known_positions = config.get("known_positions", {})
    bluetooth_data = fetch_flipper_data(known_positions)  # BLE data
    with signals_lock:
        signals_data["bluetooth"] = bluetooth_data
    
    logger.info(f"Flipper Bluetooth signals: {bluetooth_data}")
    return jsonify({"bluetooth_signals": bluetooth_data})

@main_bp.route("/flipper_subghz", methods=["GET"])
def flipper_subghz():
    # Placeholder: Fetch SubGHz data from Flipper
    subghz_data = []  # Replace with actual implementation
    with signals_lock:
        signals_data["subghz"] = subghz_data

    logger.info(f"Flipper SubGHz signals: {subghz_data}")
    return jsonify({"subghz_signals": subghz_data})

@main_bp.route("/flipper_nfc", methods=["GET"])
def flipper_nfc():
    # Placeholder: Fetch NFC data from Flipper
    nfc_data = []  # Replace with actual implementation
    with signals_lock:
        signals_data["nfc"] = nfc_data

    logger.info(f"Flipper NFC signals: {nfc_data}")
    return jsonify({"nfc_signals": nfc_data})

@main_bp.route("/flipper_rfid", methods=["GET"])
def flipper_rfid():
    # Placeholder: Fetch RFID data from Flipper
    rfid_data = []  # Replace with actual implementation
    with signals_lock:
        signals_data["rfid"] = rfid_data

    logger.info(f"Flipper RFID signals: {rfid_data}")
    return jsonify({"rfid_signals": rfid_data})

@main_bp.route("/signals", methods=["GET"])
def get_signals():
    with signals_lock:
        all_signals = []
        for key, data in signals_data.items():
            for item in data:
                all_signals.append({**item, "type": key})

    logger.info(f"Signals returned: {all_signals}")
    return jsonify({"signals": all_signals})

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
