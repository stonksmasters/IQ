from flask import Flask, render_template, request, jsonify, Response, Blueprint, send_from_directory
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
import bleak

# ------------------------------
# Configuration Management
# ------------------------------

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

# ------------------------------
# Logging Configuration
# ------------------------------

logging.basicConfig(
    level=logging.INFO if not config.get('debug', False) else logging.DEBUG,
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

# ------------------------------
# Initialize Components
# ------------------------------

# Initialize AutoDetection for object detection
autodetect = AutoDetection()

# Shared data structures for signals
signals_data = {
    "wifi": [],
    "bluetooth": [],
    "flipper": []
}

# Track position within the selected signal
selected_signal = {"type": None, "name": None, "position": None}

# Lock for thread-safe operations
signals_lock = threading.Lock()

# Blueprint for main routes
main_bp = Blueprint('main', __name__)

# ------------------------------
# HLS Configuration (Optional)
# ------------------------------

HLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'hls'))
os.makedirs(HLS_DIR, exist_ok=True)

GST_COMMAND = [
    "gst-launch-1.0",
    "-v",
    "rtspsrc",
    f"location={config.get('rtsp_url', 'rtsp://127.0.0.1:8554/test')}",
    "latency=0",
    "!",
    "rtph264depay",
    "!",
    "h264parse",
    "!",
    "mpegtsmux",
    "!",
    "hlssink",
    f"max-files={config.get('hls_max_files', 5)}",
    f"target-duration={config.get('hls_target_duration', 2)}",
    f"playlist-location={os.path.join(HLS_DIR, 'playlist.m3u8')}",
    f"location={os.path.join(HLS_DIR, 'segment%05d.ts')}"
]

def start_gst_pipeline():
    """
    Starts the GStreamer pipeline to convert RTSP to HLS (optional).
    """
    try:
        logger.info("Starting GStreamer pipeline for RTSP to HLS conversion.")
        gst_process = subprocess.Popen(GST_COMMAND, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("GStreamer pipeline started.")
        return gst_process
    except Exception as e:
        logger.error(f"Failed to start GStreamer pipeline: {e}")
        return None

def monitor_gst_pipeline(gst_process):
    """
    Monitors the GStreamer pipeline and restarts it if it crashes (optional).
    """
    while True:
        if gst_process.poll() is not None:
            logger.warning("GStreamer pipeline crashed. Restarting...")
            gst_process = start_gst_pipeline()
        time.sleep(5)

# Start the optional HLS pipeline in a separate thread
gst_process = start_gst_pipeline()
if gst_process:
    gst_thread = threading.Thread(target=monitor_gst_pipeline, args=(gst_process,), daemon=True)
    gst_thread.start()

# ------------------------------
# Signal Update Thread
# ------------------------------

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
                    signal_list = signals_data[selected_signal["type"]]
                    for sig in signal_list:
                        if sig.get("name") == selected_signal["name"]:
                            selected_signal["position"] = sig.get("position")
                            logger.info(f"Tracked signal position updated: {selected_signal['position']}")
                            break
            except Exception as e:
                logger.error(f"Signal update error: {e}")
        time.sleep(config.get('signal_update_interval', 5))

signal_thread = threading.Thread(target=update_signals, daemon=True)
signal_thread.start()

# ------------------------------
# Video Feed Generation
# ------------------------------

def generate_frames():
    """
    Generates video frames for either:
    1) local display on the Pi (if config['local_display'] == True), or
    2) MJPEG streaming if local_display is False.
    """
    local_display = config.get('local_display', False)
    cam_width = config.get('camera', {}).get('width', 640)
    cam_height = config.get('camera', {}).get('height', 480)
    cam_framerate = config.get('camera', {}).get('framerate', 24)

    if local_display:
        # Pipeline for local display (shows window on Pi desktop)
        gst_pipeline = (
            f"v4l2src device=/dev/video0 ! "
            f"video/x-raw,width={cam_width},height={cam_height},framerate={cam_framerate}/1 ! "
            f"videoconvert ! autovideosink"
        )
    else:
        # Pipeline for MJPEG streaming
        gst_pipeline = (
            f"v4l2src device=/dev/video0 ! "
            f"video/x-raw,width={cam_width},height={cam_height},framerate={cam_framerate}/1 ! "
            f"videoconvert ! appsink drop=true"
        )

    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        logger.error("Failed to open GStreamer pipeline.")
        return

    # Local Display Mode
    if local_display:
        logger.info("Displaying video locally on the Pi.")
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to read frame from pipeline.")
                break

            cv2.imshow("Camera Feed (Press 'q' to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
    else:
        # MJPEG streaming mode
        logger.info("Serving frames as MJPEG over /video_feed.")
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Failed to read frame from pipeline.")
                    break

                # Optionally, apply detection or overlay logic
                # e.g.:
                # detected_objects = autodetect.detect_objects(frame)
                # frame = overlay_hud(frame, signals, selected_signal, detected_objects)

                success, buffer_encoded = cv2.imencode(".jpg", frame)
                if not success:
                    logger.error("Failed to encode frame as JPEG.")
                    continue

                frame_bytes = buffer_encoded.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
        except Exception as e:
            logger.error(f"Error in generate_frames: {e}")
        finally:
            logger.info("Releasing GStreamer pipeline.")
            cap.release()

# ------------------------------
# Flask Routes
# ------------------------------

@main_bp.route("/")
def index():
    """
    Renders the main HTML page with lists of signals and options to track them.
    """
    return render_template("index.html")

@main_bp.route("/signals", methods=["GET"])
def get_signals():
    """
    Returns the current Wi-Fi, Bluetooth, and Flipper signals with positions.
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
def track_signal_route():
    """
    API to track a selected signal (Wi-Fi, Bluetooth, or Flipper).
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
        selected_signal["position"] = None
        logger.info(f"Tracking {signal_type} signal: {signal_name}")

    return jsonify({"status": "success", "tracked_signal": selected_signal})

@main_bp.route("/clear_signal", methods=["POST"])
def clear_signal_route():
    """
    Clears the selected signal and resets tracking.
    """
    with signals_lock:
        selected_signal["type"] = None
        selected_signal["name"] = None
        selected_signal["position"] = None
        logger.info("Cleared tracking signal.")
    return jsonify({"status": "success"})

@main_bp.route("/toggle_display", methods=["POST"])
def toggle_display():
    """
    Toggles between local display and MJPEG streaming by updating config in-memory.
    """
    data = request.get_json()
    if not data or "local_display" not in data:
        return jsonify({"status": "error", "message": "Missing 'local_display' parameter"}), 400

    config['local_display'] = bool(data["local_display"])
    logger.info(f"Local display mode set to: {config['local_display']}")
    return jsonify({"status": "success", "local_display": config['local_display']})

@main_bp.route("/video_feed")
def video_feed():
    """
    Provides MJPEG frames from the camera if local_display is False.
    """
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@main_bp.route("/hls/<path:filename>")
def hls_files(filename):
    """
    Serves HLS playlist and segment files if using HLS.
    """
    return send_from_directory(HLS_DIR, filename)

# ------------------------------
# Graceful Shutdown Handler
# ------------------------------

def handle_exit(signum, frame):
    """
    Gracefully handle server shutdown.
    """
    logger.info("Shutting down server...")

    # Stop the signal update thread
    signal_thread.join(timeout=2)

    # Terminate optional GStreamer pipeline
    if gst_process:
        gst_process.terminate()
        try:
            gst_process.wait(timeout=5)
            logger.info("GStreamer pipeline terminated.")
        except subprocess.TimeoutExpired:
            logger.warning("GStreamer pipeline did not terminate in time. Killing it.")
            gst_process.kill()

    logger.info("Shutdown complete.")
    exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# ------------------------------
# Register Blueprint
# ------------------------------

app.register_blueprint(main_bp)

# ------------------------------
# Main Entry Point
# ------------------------------

if __name__ == "__main__":
    try:
        logger.info("Starting Flask server.")
        # Use a production-ready server like Gunicorn in production
        app.run(host="0.0.0.0", port=5000, debug=config.get('debug', False))
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
