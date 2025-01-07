from flask import Flask, render_template, request, jsonify, Response
import subprocess
from hud import overlay_hud
from utils.autodetect import autodetect
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

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

app = Flask(__name__)

# Shared data structures for signals
wifi_signals = []
bluetooth_signals = []
flipper_signals = []
selected_signal = {"type": None, "name": None}  # Store signal type and name to track

# Lock for thread-safe operations
lock = threading.Lock()


def update_signals():
    """
    Periodically updates Wi-Fi, Bluetooth, and Flipper Zero signals in a separate thread.
    """
    global wifi_signals, bluetooth_signals, flipper_signals
    while True:
        with lock:
            try:
                logging.info("Updating signals from all sources...")
                wifi_signals = detect_wifi()
                bluetooth_signals = detect_bluetooth()
                flipper_signals = fetch_flipper_data()
                logging.info(f"Wi-Fi signals: {wifi_signals}")
                logging.info(f"Bluetooth signals: {bluetooth_signals}")
                logging.info(f"Flipper signals: {flipper_signals}")
            except Exception as e:
                logging.error(f"Signal update error: {e}")
        time.sleep(5)


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
        logging.error("libcamera-vid not found. Ensure it is installed and in the PATH.")
        return

    process = subprocess.Popen(
        [
            "libcamera-vid",
            "--codec", "mjpeg",
            "--width", "640",
            "--height", "480",
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
                logging.error("Failed to read frame from camera.")
                break
            buffer += chunk

            start = buffer.find(start_marker)
            end = buffer.find(end_marker)

            if start != -1 and end != -1 and end > start:
                jpeg = buffer[start:end + 2]
                buffer = buffer[end + 2:]

                frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    logging.warning("Failed to decode frame, skipping...")
                    continue

                logging.info("Frame successfully decoded.")

                # Perform object detection
                detected_objects = autodetect.detect_objects(frame)

                with lock:
                    try:
                        # Filter selected signal
                        if selected_signal["type"] and selected_signal["name"]:
                            filtered_signals = [
                                signal for signal in (wifi_signals + bluetooth_signals + flipper_signals)
                                if signal.get("type") == selected_signal["type"]
                                and signal.get("name") == selected_signal["name"]
                            ]
                        else:
                            filtered_signals = wifi_signals + bluetooth_signals + flipper_signals

                        # Overlay data
                        frame = overlay_hud(frame, filtered_signals, selected_signal, detected_objects)
                        logging.info("HUD overlay applied successfully.")
                    except Exception as e:
                        logging.error(f"Error applying HUD overlay: {e}")

                _, buffer_encoded = cv2.imencode(".jpg", frame)
                frame_bytes = buffer_encoded.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
    except Exception as e:
        logging.error(f"Error in generate_frames: {e}")
    finally:
        process.terminate()
        process.wait()


@app.route("/")
def index():
    """
    Renders the main HTML page with lists of signals and options to track them.
    """
    return render_template("index.html")


@app.route("/signals", methods=["GET"])
def get_signals():
    """
    API to fetch the current Wi-Fi, Bluetooth, and Flipper Zero signals with triangulated positions.
    """
    with lock:
        all_signals = []
        for signal in wifi_signals:
            all_signals.append({**signal, "type": "wifi"})
        for signal in bluetooth_signals:
            all_signals.append({**signal, "type": "bluetooth"})
        for signal in flipper_signals:
            all_signals.append({**signal, "type": "flipper"})

    logging.info(f"Signals returned: {all_signals}")
    return jsonify({"signals": all_signals})


@app.route("/track_signal", methods=["POST"])
def track_signal():
    """
    API to track a selected signal (Wi-Fi, Bluetooth, or Flipper Zero).
    """
    data = request.json
    signal_type = data.get("type")
    signal_name = data.get("name")

    with lock:
        selected_signal["type"] = signal_type
        selected_signal["name"] = signal_name
        logging.info(f"Tracking {signal_type} signal: {signal_name}")

    return jsonify({"status": "success"})


@app.route("/clear_signal", methods=["POST"])
def clear_signal():
    """
    API to clear the selected signal and reset tracking.
    """
    with lock:
        selected_signal["type"] = None
        selected_signal["name"] = None
        logging.info("Cleared tracking signal.")
    return jsonify({"status": "success"})


@app.route("/video_feed")
def video_feed():
    """
    Provides the video feed with HUD overlays as a streaming response.
    """
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


def handle_exit(signum, frame):
    """
    Gracefully handle server shutdown.
    """
    logging.info("Shutting down server...")
    signal_thread.join(timeout=1)
    exit(0)


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

if __name__ == "__main__":
    try:
        logging.info("Starting Flask server.")
        app.run(host="0.0.0.0", port=5000, debug=True)
    except KeyboardInterrupt:
        logging.info("Shutting down server...")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
