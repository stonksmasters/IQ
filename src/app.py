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
    """
    Background thread function to read frames from the named pipe
    and update the global latest_frame variable.
    """
    global latest_frame
    logging.info(f"Starting frame reader thread. Opening named pipe {named_pipe_path} for reading.")
    try:
        with open(named_pipe_path, 'rb') as pipe:
            logging.info("Named pipe opened successfully for reading.")
            buffer = b''

            while True:
                chunk = pipe.read(4096)
                if not chunk:
                    logging.warning("No data read from pipe. Waiting for data...")
                    time.sleep(1)
                    continue

                buffer += chunk
                logging.debug(f"Read {len(chunk)} bytes from pipe. Buffer size: {len(buffer)} bytes.")

                while True:
                    boundary = b'--frame\r\n'
                    start = buffer.find(boundary)
                    if start == -1:
                        # Boundary not found, keep buffer as is
                        break

                    end = buffer.find(boundary, start + len(boundary))
                    if end == -1:
                        # Complete frame not yet received
                        break

                    # Extract frame data between boundaries
                    frame_data = buffer[start + len(boundary):end]
                    buffer = buffer[end:]  # Remove processed frame from buffer

                    # Parse headers
                    headers_end = frame_data.find(b'\r\n\r\n')
                    if headers_end == -1:
                        logging.warning("No end of headers found. Skipping frame.")
                        continue

                    headers = frame_data[:headers_end]
                    jpeg_data = frame_data[headers_end + 4:]

                    # Optionally, parse headers if needed
                    # For now, assume jpeg_data is the image

                    if jpeg_data:
                        with frame_lock:
                            latest_frame = jpeg_data
                            logging.debug(f"Updated latest_frame with size {len(latest_frame)} bytes.")
                    else:
                        logging.warning("Empty frame data received.")

    except FileNotFoundError as e:
        logging.error(f"Named pipe not found: {e}")
    except Exception as e:
        logging.error(f"Error in frame_reader: {e}")
    finally:
        logging.info("Frame reader thread terminated.")

def generate_frames():
    """
    Generator function to yield the latest frame to the client.
    """
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
                    b'Content-Type: image/jpeg\r\n\r\n'
                    + frame +
                    b'\r\n'
                )
            except GeneratorExit:
                logging.info("Client disconnected from video_feed.")
                break
            except Exception as e:
                logging.error(f"Error while yielding frame: {e}")
        else:
            logging.debug("No frame available to yield. Sleeping for 0.1 seconds.")
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
