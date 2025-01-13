import eventlet
eventlet.monkey_patch()  # Must be the first import

from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import logging
import time
import os
import threading
from flipper import fetch_flipper_data
from shared import signals_data, signals_lock, selected_signal
from config import config

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

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

# Global variable to track active clients
client_count = 0

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
    Handles unexpected data and skips to the next valid frame boundary.
    """
    logging.info(f"Opening named pipe {named_pipe_path} for reading.")
    boundary = b'--frame\r\n'
    try:
        with open(named_pipe_path, 'rb') as pipe:
            logging.info("Named pipe opened successfully for reading.")
            buffer = b''

            while True:
                chunk = pipe.read(4096)  # Read data in chunks
                if not chunk:
                    logging.warning("No data from named pipe. Waiting...")
                    time.sleep(1)
                    continue

                buffer += chunk
                while True:
                    # Look for the start of a frame boundary
                    start_index = buffer.find(boundary)
                    if start_index == -1:
                        # No boundary found; keep reading
                        break

                    # Look for the next boundary to extract the frame
                    end_index = buffer.find(boundary, start_index + len(boundary))
                    if end_index == -1:
                        # Incomplete frame; wait for more data
                        break

                    # Extract the frame data
                    frame_data = buffer[start_index + len(boundary):end_index]
                    buffer = buffer[end_index:]  # Remove processed data from buffer

                    # Ensure the frame data is valid
                    if frame_data.strip():
                        try:
                            logging.debug(f"Yielding frame of size {len(frame_data)} bytes.")
                            yield (
                                b'--frame\r\n'
                                b'Content-Type: image/jpeg\r\n\r\n'
                                + frame_data +
                                b'\r\n'
                            )
                        except Exception as e:
                            logging.error(f"Error while yielding frame: {e}")
                            continue
    except FileNotFoundError as e:
        logging.error(f"Named pipe not found: {e}")
    except Exception as e:
        logging.error(f"Error reading from named pipe: {e}")
    finally:
        logging.info("Named pipe generator closed.")

@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/add_signal', methods=['POST'])
def add_signal():
    """
    A simple REST endpoint to allow remote computers
    to add signals that appear on the Pi's HUD.
    """
    data = request.get_json()
    if not data or 'type' not in data or 'name' not in data:
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

    return jsonify({'status': 'success'}), 200

def emit_signals():
    """
    Continuously emit signal data to all connected clients for the HUD.
    """
    while True:
        with signals_lock:
            all_signals = []
            for signal_type, data_list in signals_data.items():
                for item in data_list:
                    all_signals.append({**item, "type": signal_type})

        socketio.emit('update_signals', {'signals': all_signals})
        socketio.sleep(config.get('signal_update_interval', 5))

# Prepare the named pipe
create_named_pipe(named_pipe_path)

# Start background thread to emit signals
signals_thread = threading.Thread(target=emit_signals, daemon=True)
signals_thread.start()

if __name__ == '__main__':
    logging.info("Starting SocketIO server...")
    socketio.run(app, host='0.0.0.0', port=5000)
