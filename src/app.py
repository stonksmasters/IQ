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

from flipper import fetch_flipper_data  # Ensures this function exists in flipper.py
from shared import signals_data, signals_lock, selected_signal
from config import config

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Named pipe path
named_pipe_path = 'named_pipes/video_pipe'

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

def generate_frames():
    """
    Generator function to read MJPEG frames from the named pipe.
    Each frame in the pipe is separated by '--frame\\r\\n', followed by HTTP-like headers,
    and ends with an empty line. The actual JPEG data continues until the next boundary.
    """
    logging.info(f"Opening named pipe {named_pipe_path} for reading.")
    client_count = 0  # Track number of connected clients
    try:
        with open(named_pipe_path, 'rb') as pipe:
            logging.info("Named pipe opened successfully for reading.")

            while True:
                boundary_line = pipe.readline()
                if not boundary_line:
                    logging.warning("No data from named pipe. Waiting...")
                    time.sleep(1)
                    continue

                boundary = b'--frame\r\n'
                if boundary_line.startswith(boundary):
                    logging.debug("Boundary line detected. Reading headers.")

                    # Read headers
                    headers = []
                    while True:
                        header_line = pipe.readline()
                        if not header_line:
                            logging.warning("EOF or no more data in pipe while reading headers.")
                            break
                        if header_line == b'\r\n':
                            break
                        headers.append(header_line.strip())
                        logging.debug(f"Header: {header_line.strip()}")

                    # Read JPEG frame data
                    logging.debug("Reading frame data from named pipe.")
                    frame = bytearray()
                    while True:
                        byte = pipe.read(1)
                        if not byte:
                            logging.warning("EOF encountered while reading frame data.")
                            break
                        frame += byte
                        if frame.endswith(b'\r\n--frame\r\n'):
                            frame = frame[:-len(b'\r\n--frame\r\n')]
                            break

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
                            client_count -= 1
                            logging.info(f"Client disconnected. Active clients: {client_count}")
                            break
                        except Exception as e:
                            logging.error(f"Error while yielding frame to client: {e}")
                else:
                    logging.warning(f"Unexpected data in named pipe: {boundary_line.strip()}")
    except FileNotFoundError as e:
        logging.error(f"Named pipe not found: {e}")
    except Exception as e:
        logging.error(f"Error reading from named pipe: {e}")
    finally:
        logging.info("Named pipe generator closed.")

@app.route('/video_feed')
def video_feed():
    """
    Route to provide MJPEG video feed.
    Logs every client connection and disconnection.
    """
    global client_count
    client_count += 1
    logging.info(f"New client connected. Active clients: {client_count}")

    try:
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    finally:
        client_count -= 1
        logging.info(f"Client disconnected. Active clients: {client_count}")

@app.route('/')
def index():
    """Main page with HTML/JS to display the video stream and signals."""
    return render_template('index.html')


@app.route('/add_signal', methods=['POST'])
def add_signal():
    """
    Simple REST endpoint for external devices/computers to post signals
    that will show up on the Pi's HUD. Example JSON:
      {
        "type": "wifi",
        "name": "OfficeNetwork",
        "rssi": -50
      }
    """
    data = request.get_json()
    if not data or 'type' not in data or 'name' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    signal_type = data['type'].lower()
    signal_name = data['name']
    signal_rssi = data.get('rssi', -60)  # default RSSI if not provided

    with signals_lock:
        if signal_type not in signals_data:
            signals_data[signal_type] = []
        signals_data[signal_type].append({
            'name': signal_name,
            'rssi': signal_rssi,
            'type': signal_type
        })

    return jsonify({'status': 'success'}), 200

def emit_signals():
    """
    Background thread: continuously emits the signals_data to all connected
    SocketIO clients, so they can update their HUD overlays in real-time.
    """
    while True:
        with signals_lock:
            all_signals = []
            for signal_type, data_list in signals_data.items():
                for item in data_list:
                    all_signals.append({**item, "type": signal_type})

        # Send to all connected SocketIO clients
        socketio.emit('update_signals', {'signals': all_signals})
        socketio.sleep(config.get('signal_update_interval', 5))

# Prepare the named pipe before reading
create_named_pipe(named_pipe_path)

# Start the background signals thread
signals_thread = threading.Thread(target=emit_signals, daemon=True)
signals_thread.start()

def handle_shutdown(sig, frame):
    """Gracefully shut down SocketIO on SIGINT/SIGTERM."""
    logging.info("Received shutdown signal, stopping SocketIO...")
    socketio.stop()

# Register signal handlers for clean exit
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
