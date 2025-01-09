from flask import Flask, render_template, request, jsonify, Response, Blueprint
import subprocess
from hud import overlay_hud
from utils.autodetect import AutoDetection
from utils.signal_detection import detect_wifi, detect_bluetooth
from flipper import fetch_flipper_data
from utils.triangulation import triangulate
import threading
import time
import cv2
import numpy as np
import os
import logging
import shutil
import signal
import yaml

# Load configuration
def load_config(config_path='config.yaml'):
    """
    Load configuration from a YAML file.

    Args:
        config_path (str, optional): Path to the config file. Defaults to 'config.yaml'.

    Returns:
        dict: Configuration parameters.
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize AutoDetection for object detection
autodetect = AutoDetection()

# Shared data structures for signals
signals_data = {
    "wifi": [],
    "bluetooth": [],
    "flipper": []
}
# Updated: track position within the selected signal
selected_signal = {"type": None, "name": None, "position": None}

# Lock for thread-safe operations
signals_lock = threading.Lock()

# Blueprint for main routes
main_bp = Blueprint('main', __name__)


def update_signals():
    """
    Periodically updates Wi-Fi, Bluetooth, and Flipper Zero signals in a separate thread.
    Also updates the tracked signal's position if one is selected.
    """
    global selected_signal
    while True:
        with signals_lock:
            try:
                logger.info("Updating signals from all sources...")
                signals_data["wifi"] = detect_wifi()
                signals_data["bluetooth"] = detect_bluetooth()
                signals_data["flipper"] = fetch_flipper_data()

                # If a signal is being tracked, update its position
                if selected_signal["type"] and selected_signal["name"]:
                    # Iterate over relevant signals
                    signal_list = signals_data[selected_signal["type"]]
                    for sig in signal_list:
                        # Match the tracked signal by name or address
                        if sig.get("name") == selected_signal["name"]:
                            selected_signal["position"] = sig.get("position")
                            logger.info(
                                f"Tracked signal position updated: {selected_signal['position']}"
                            )
                            break
            except Exception as e:
                logger.error(f"Signal update error: {e}")
        time.sleep(config.get('signal_update_interval', 5))


# Start the signal update thread
signal_thread = threading.Thread(target=update_signals, daemon=True)
signal_thread.start()


def generate_frames():
    """
    Generates video frames by reading from libcamera-vid subprocess,
    decoding JPEG frames, overlaying HUD data, and yielding them for streaming.
    """
    libcamera_path = shutil.which("libcamera-vid")
    if libcamera_path is None:
        logger.error("libcamera-vid not found. Ensure it is installed and in the PATH.")
        return

    # Camera settings from config
    cam_width = str(config.get('camera', {}).get('width', 640))
    cam_height = str(config.get('camera', {}).get('height', 480))

    process = subprocess.Popen(
        [
            "libcamera-vid",
            "--codec", "mjpeg",
            "--width", cam_width,
            "--height", cam_height,
            "-o", "-",
            "-t", "0",
            "--inline",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    buffer = b""
    start_marker = b"\xff\xd8"
    end_marker = b"\xff\xd9"

    try:
        while True:
            chunk = process.stdout.read(1024)
            if not chunk:
                logger.error("Failed to read frame from camera.")
                break
            buffer += chunk

            while True:
                start = buffer.find(start_marker)
                end = buffer.find(end_marker)
                if start != -1 and end != -1 and end > start:
                    # Extract the JPEG frame
                    jpeg = buffer[start:end + 2]
                    buffer = buffer[end + 2:]

                    # Decode the frame
                    frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        logger.warning("Failed to decode frame, skipping...")
                        continue

                    logger.debug("Frame successfully decoded.")

                    # Perform object detection
                    detected_objects = autodetect.detect_objects(frame)

                    with signals_lock:
                        try:
                            # Aggregate all signals (Wi-Fi, Bluetooth, Flipper)
                            all_signals = (
                                signals_data["wifi"]
                                + signals_data["bluetooth"]
                                + signals_data["flipper"]
                            )

                            # Overlay data
                            frame = overlay_hud(frame, all_signals, selected_signal, detected_objects)
                            logger.debug("HUD overlay applied successfully.")
                        except Exception as e:
                            logger.error(f"Error applying HUD overlay: {e}")

                    # Encode frame for streaming
                    _, buffer_encoded = cv2.imencode(".jpg", frame)
                    frame_bytes = buffer_encoded.tobytes()
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                    )
                else:
                    break  # Wait for more data to complete the frame
    except Exception as e:
        logger.error(f"Error in generate_frames: {e}")
    finally:
        process.terminate()
        process.wait()


@main_bp.route("/")
def index():
    """
    Renders the main HTML page with lists of signals and options to track them.
    """
    return render_template("index.html")


@main_bp.route("/signals", methods=["GET"])
def get_signals():
    """
    API to fetch the current Wi-Fi, Bluetooth, and Flipper Zero signals
    with triangulated positions if available.
    """
    with signals_lock:
        all_signals = []
        for wifi_sig in signals_data["wifi"]:
            all_signals.append({**wifi_sig, "type": "wifi"})
        for bt_sig in signals_data["bluetooth"]:
            all_signals.append({**bt_sig, "type": "bluetooth"})
        for fl_sig in signals_data["flipper"]:
            all_signals.append({**fl_sig, "type": "flipper"})

    logger.info(f"Signals returned: {all_signals}")
    return jsonify({"signals": all_signals})


@main_bp.route("/track_signal", methods=["POST"])
def track_signal():
    """
    API to track a selected signal (Wi-Fi, Bluetooth, or Flipper Zero).
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    signal_type = data.get("type")
    signal_name = data.get("name")

    if signal_type not in ["wifi", "bluetooth", "flipper"]:
        return jsonify({"status": "error", "message": "Invalid signal type"}), 400

    if not signal_name:
        return jsonify({"status": "error", "message": "Signal name is required"}), 400

    with signals_lock:
        selected_signal["type"] = signal_type
        selected_signal["name"] = signal_name
        selected_signal["position"] = None  # Reset position initially
        logger.info(f"Tracking {signal_type} signal: {signal_name}")

    return jsonify({"status": "success", "tracked_signal": selected_signal})


@main_bp.route("/clear_signal", methods=["POST"])
def clear_signal():
    """
    API to clear the selected signal and reset tracking.
    """
    with signals_lock:
        selected_signal["type"] = None
        selected_signal["name"] = None
        selected_signal["position"] = None
        logger.info("Cleared tracking signal.")
    return jsonify({"status": "success"})


@main_bp.route("/video_feed")
def video_feed():
    """
    Provides the video feed with HUD overlays as a streaming response.
    """
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


def handle_exit(signum, frame):
    """
    Gracefully handle server shutdown.
    """
    logger.info("Shutting down server...")
    signal_thread.join(timeout=2)
    logger.info("Shutdown complete.")
    exit(0)


# Register Blueprint
app.register_blueprint(main_bp)

# Handle graceful shutdown
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


if __name__ == "__main__":
    try:
        logger.info("Starting Flask server.")
        # Use a production-ready server like Gunicorn in production
        app.run(host="0.0.0.0", port=5000, debug=config.get('debug', False))
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
