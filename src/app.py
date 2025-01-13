# src/app.py

import eventlet
eventlet.monkey_patch()  # Must be the first import to ensure proper monkey patching

from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import logging
import time
import signal
import os
import threading

# Placeholder imports; ensure these modules exist or remove if not used
# from flipper import fetch_flipper_data
# from shared import signals_data, signals_lock, selected_signal
# from config import config

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for maximum verbosity
    format='%(asctime)s %(levelname)s:%(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Named pipe path
named_pipe_path = 'named_pipes/video_pipe'

# Global frame buffer and lock
latest_frame = None
frame_lock = threading.Lock()

# Frame counters
frames_read = 0
frames_yielded = 0

# Global signal data structures
signals_data = {}
signals_lock = threading.Lock()
selected_signal = None  # Define if used

def create_named_pipe(pipe_path):
    """Create a named pipe if it doesn't exist."""
    if not os.path.exists(pipe_path):
        os.makedirs(os.path.dirname(pipe_path), exist_ok=True)
        try:
            os.mkfifo(pipe_path)
            logging.info(f"Named pipe created at {pipe_path}")
        except OSError as e:
            logging.error(f"Failed to create named pipe: {e}")
    else:
        logging.info(f"Named pipe already exists at {pipe_path}")

def frame_reader():
    global latest_frame
    logging.info(f"Starting frame reader thread. Opening named pipe {named_pipe_path} for reading.")
    try:
        with open(named_pipe_path, 'rb') as pipe:
            logging.info("Named pipe opened successfully for reading.")
            while True:
                # Read boundary line
                boundary_line = pipe.readline()
                logging.debug(f"Boundary line read: {boundary_line.strip()}")
                if not boundary_line:
                    logging.warning("No data from pipe. Retrying...")
                    time.sleep(1)
                    continue

                boundary = b'--frame\r\n'
                if boundary_line.strip() == boundary.strip():
                    logging.debug("Detected frame boundary. Reading headers.")
                    headers = {}
                    while True:
                        header_line = pipe.readline()
                        if header_line == b'\r\n':  # End of headers
                            break
                        header_parts = header_line.decode('utf-8', errors='replace').split(':', 1)
                        if len(header_parts) == 2:
                            headers[header_parts[0].strip().lower()] = header_parts[1].strip()

                    content_length = headers.get('content-length')
                    if not content_length:
                        logging.warning("Content-Length header missing. Skipping frame.")
                        continue

                    try:
                        content_length = int(content_length)
                    except ValueError:
                        logging.error(f"Invalid Content-Length: {content_length}. Skipping frame.")
                        continue

                    frame_data = pipe.read(content_length)
                    if len(frame_data) != content_length:
                        logging.warning(f"Frame size mismatch. Expected {content_length}, got {len(frame_data)}.")
                        continue

                    with frame_lock:
                        latest_frame = frame_data
                        logging.debug(f"Updated latest_frame. Size: {len(latest_frame)} bytes.")
                else:
                    logging.warning(f"Unexpected boundary: {boundary_line.strip()}")
    except Exception as e:
        logging.error(f"Error in frame_reader: {e}")
    finally:
        logging.info("Frame reader thread terminated.")

def generate_frames():
    global latest_frame
    logging.info("Client started streaming frames.")
    while True:
        with frame_lock:
            frame = latest_frame

        if frame:
            try:
                logging.debug(f"Yielding frame of size {len(frame)} bytes to client.")
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
                )
            except Exception as e:
                logging.error(f"Error while yielding frame: {e}")
                break
        else:
            logging.debug("No frame available. Retrying in 0.1 seconds.")
            time.sleep(0.1)

@app.route('/')
def index():
    """Main page with HTML/JS to display the video stream and signals."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """
    Route to provide MJPEG video feed.
    Each client gets the latest frames without interfering with each other.
    """
    logging.info("Client connected to /video_feed. Starting frame generator.")
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/add_signal', methods=['POST'])
def add_signal():
    """
    A simple REST endpoint to allow remote computers
    to add signals that appear on the Pi's HUD.
    """
    data = request.get_json()
    if not data or 'type' not in data or 'name' not in data:
        logging.warning("Received invalid signal data.")
        return jsonify({'error': 'Invalid data'}), 400

    signal_type = data['type'].lower()
    signal_name = data['name']
    signal_rssi = data.get('rssi', -60)  # default RSSI

    with signals_lock:
        if signal_type not in signals_data:
            signals_data[signal_type] = []
        signals_data[signal_type].append({
            'name': signal_name,
            'rssi': signal_rssi,
            'type': signal_type
        })
        logging.info(f"Added signal: {data}")

    return jsonify({'status': 'success'}), 200

def emit_signals():
    """
    Continuously emit signal data to all connected SocketIO clients for the HUD.
    """
    while True:
        with signals_lock:
            all_signals = []
            for signal_type, data_list in signals_data.items():
                for item in data_list:
                    all_signals.append({**item, "type": signal_type})

        # Emit to all connected clients
        socketio.emit('update_signals', {'signals': all_signals})
        logging.debug(f"Emitted signals: {all_signals}")
        socketio.sleep(5)  # Replace with config.get('signal_update_interval', 5) if config is defined

@socketio.on('connect')
def handle_connect():
    logging.info(f"SocketIO client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logging.info(f"SocketIO client disconnected: {request.sid}")

def handle_shutdown(sig, frame):
    """Gracefully shut down SocketIO on SIGINT/SIGTERM."""
    logging.info("Received shutdown signal, stopping SocketIO...")
    socketio.stop()

@app.route('/health')
def health_check():
    """
    Health check endpoint to verify application status and frame counts.
    """
    with frame_lock:
        status = {
            'status': 'running',
            'frames_read': frames_read,
            'frames_yielded': frames_yielded,
            'latest_frame_size': len(latest_frame) if latest_frame else 0
        }
    logging.info("Health check requested.")
    return jsonify(status), 200

if __name__ == '__main__':
    # Prepare the named pipe before reading
    create_named_pipe(named_pipe_path)

    # Start the background frame reader thread
    frame_thread = threading.Thread(target=frame_reader, daemon=True)
    frame_thread.start()

    # Start the background signals emitter thread
    signals_thread = threading.Thread(target=emit_signals, daemon=True)
    signals_thread.start()

    # Register signal handlers for clean exit
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logging.info("Starting SocketIO server on 0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
