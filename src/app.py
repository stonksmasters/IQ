from flask import Flask, render_template, request, jsonify, Response, Blueprint, send_from_directory
import subprocess
import threading
import time
import cv2
import os
import logging
import signal
import yaml
import sys

# If you still need these from your code:
from hud import overlay_hud
from utils.autodetect import AutoDetection
from utils.signal_detection import detect_wifi, detect_bluetooth
from flipper import fetch_flipper_data
from utils.triangulation import triangulate

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
main_bp = Blueprint('main', __name__)

# ------------------------------
# Global Data: Signals
# ------------------------------

signals_data = {
    "wifi": [],
    "bluetooth": [],
    "flipper": []
}
selected_signal = {"type": None, "name": None, "position": None}
signals_lock = threading.Lock()

# ------------------------------
# Optional HLS Configuration
# ------------------------------

HLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'hls'))
os.makedirs(HLS_DIR, exist_ok=True)

# Optional GStreamer pipeline command for RTSP->HLS
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
    Optionally starts a GStreamer pipeline for RTSP->HLS.
    """
    try:
        logger.info("Starting optional GStreamer pipeline for RTSP->HLS.")
        gst_process = subprocess.Popen(
            GST_COMMAND,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info("GStreamer RTSP->HLS pipeline started.")
        return gst_process
    except Exception as e:
        logger.error(f"Failed to start GStreamer pipeline: {e}")
        return None

def monitor_gst_pipeline(gst_process):
    """
    Monitors the optional GStreamer pipeline and restarts if it crashes.
    """
    while True:
        if gst_process.poll() is not None:
            logger.warning("GStreamer pipeline crashed. Restarting...")
            gst_process = start_gst_pipeline()
        time.sleep(5)

# Start the optional pipeline in a background thread (if you want HLS)
gst_process = start_gst_pipeline()
if gst_process:
    gst_thread = threading.Thread(target=monitor_gst_pipeline, args=(gst_process,), daemon=True)
    gst_thread.start()

# ------------------------------
# Background Thread: Update Signals
# ------------------------------

def update_signals():
    """
    Periodically fetch Wi-Fi, Bluetooth, and Flipper signals.
    """
    while True:
        with signals_lock:
            try:
                logger.info("Updating signals from all sources...")
                signals_data["wifi"] = detect_wifi()
                signals_data["bluetooth"] = detect_bluetooth()
                signals_data["flipper"] = fetch_flipper_data()

                # If a signal is being tracked, optionally update its position
                if selected_signal["type"] and selected_signal["name"]:
                    sig_list = signals_data[selected_signal["type"]]
                    for sig in sig_list:
                        if sig.get("name") == selected_signal["name"]:
                            selected_signal["position"] = sig.get("position")
                            logger.info(
                                f"Tracked signal position updated: {selected_signal['position']}"
                            )
                            break
            except Exception as e:
                logger.error(f"Signal update error: {e}")

        # Sleep a bit before next scan
        time.sleep(config.get('signal_update_interval', 5))

signal_thread = threading.Thread(target=update_signals, daemon=True)
signal_thread.start()

# ------------------------------
# MJPEG Video Feed
# ------------------------------

def generate_frames():
    """
    Grabs frames directly from /dev/video0 using OpenCV and yields them as MJPEG.
    """
    logger.info("Opening camera (/dev/video0) for MJPEG streaming...")

    # Attempt to open /dev/video0 directly
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Failed to open /dev/video0. Check camera and permissions.")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to read frame from camera.")
                break

            # Optionally apply detection or overlays
            # e.g.:
            # detected_objects = autodetect.detect_objects(frame)
            # frame = overlay_hud(frame, signals_data, selected_signal, detected_objects)

            # Encode as JPEG
            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                continue

            # MJPEG boundary
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" +
                   buffer.tobytes() +
                   b"\r\n")
    except Exception as e:
        logger.error(f"Error in generate_frames: {e}")
    finally:
        cap.release()
        logger.info("Camera capture released.")

# ------------------------------
# Flask Routes
# ------------------------------

@main_bp.route("/")
def index():
    """
    Main HTML page showing signals and a placeholder for video feed.
    """
    return render_template("index.html")

@main_bp.route("/signals", methods=["GET"])
def get_signals():
    """
    Returns the current Wi-Fi, Bluetooth, and Flipper signals as JSON.
    """
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
    """
    API to track a selected signal.
    """
    data = request.get_json() or {}
    sig_type = data.get("type")
    sig_name = data.get("name")

    if sig_type not in ["wifi", "bluetooth", "flipper"]:
        return jsonify({"status": "error", "message": "Invalid signal type"}), 400
    if not sig_name:
        return jsonify({"status": "error", "message": "Signal name is required"}), 400

    with signals_lock:
        selected_signal["type"] = sig_type
        selected_signal["name"] = sig_name
        selected_signal["position"] = None
        logger.info(f"Tracking {sig_type} signal: {sig_name}")

    return jsonify({"status": "success", "tracked_signal": selected_signal})

@main_bp.route("/clear_signal", methods=["POST"])
def clear_signal_route():
    """
    Clears the currently tracked signal.
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
    MJPEG stream of Pi camera frames from /dev/video0.
    Embed in HTML with: <img src="/video_feed" />
    """
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@main_bp.route("/hls/<path:filename>")
def hls_files(filename):
    """
    Serves HLS playlist and segments if using the optional GStreamer RTSP->HLS pipeline.
    """
    return send_from_directory(HLS_DIR, filename)

# ------------------------------
# Graceful Shutdown
# ------------------------------

def handle_exit(signum, frame):
    logger.info("Shutting down server gracefully...")

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

    logger.info("Server shutdown complete.")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# ------------------------------
# Register Blueprint & Run
# ------------------------------

app.register_blueprint(main_bp)

if __name__ == "__main__":
    logger.info("Starting Flask server on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=config.get('debug', False))
