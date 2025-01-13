# src/app.py

import eventlet
eventlet.monkey_patch()  # Must be the first import to ensure proper monkey patching

from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import threading
import time
import logging
import signal
import os

from flipper import fetch_flipper_data  # Ensure flipper.py is in the correct path
from shared import signals_data, signals_lock, selected_signal  # Import shared data structures
from config import config  # Import configuration from config.py

# Initialize Flask app and SocketIO with eventlet
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Path to the named pipe
named_pipe_path = 'named_pipes/video_pipe'

def create_named_pipe(pipe_path):
    """
    Create a named pipe if it doesn't exist.
    """
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
    Generator function to read video frames from a named pipe.
    """
    named_pipe_path = 'named_pipes/video_pipe'
    logging.info(f"Opening named pipe {named_pipe_path} for reading.")
    try:
        with open(named_pipe_path, 'rb') as pipe:
            while True:
                # Read until boundary --frame\r\n
                boundary = b'--frame\r\n'
                line = pipe.readline()
                if not line:
                    logging.warning("No data received from named pipe. Waiting for data...")
                    time.sleep(1)
                    continue
                
                # If we find the boundary line, read header lines until an empty line
                if boundary in line:
                    while True:
                        header_line = pipe.readline()
                        if not header_line:
                            logging.warning("Reached EOF or no more data in the pipe.")
                            break
                        # An empty line (\r\n) signifies the end of headers.
                        if header_line == b'\r\n':
                            # Proceed to read the frame data.
                            break
                        else:
                            # You can log or skip any specific headers here:
                            # For example, skip Content-Length or Content-Type
                            logging.debug(f"Skipping header: {header_line.strip()}")
                    
                    # Now read the JPEG frame until we hit the next boundary
                    frame = bytearray()
                    while True:
                        byte = pipe.read(1)
                        if not byte:
                            # No more data, possibly EOF
                            break
                        frame += byte
                        
                        # The next boundary is \r\n--frame\r\n
                        if frame.endswith(b'\r\n--frame\r\n'):
                            # Remove that boundary from the frame
                            frame = frame[:-len(b'\r\n--frame\r\n')]
                            break
                    
                    # If we got a frame, yield it as part of the MJPEG stream
                    if frame:
                        yield (
                            b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n'
                            + frame +
                            b'\r\n'
                        )
    except Exception as e:
        logging.error(f"Error reading from named pipe: {e}")
    finally:
        logging.info("Named pipe closed.")

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def emit_signals():
    """
    Emit signal updates to all connected clients.
    """
    while True:
        with signals_lock:
            all_signals = []
            for signal_type, data_list in signals_data.items():
                for item in data_list:
                    all_signals.append({**item, "type": signal_type})

        # Emit the signals to all connected clients
        socketio.emit('update_signals', {'signals': all_signals})

        # Use socketio.sleep for non-blocking sleep in SocketIO context
        socketio.sleep(config.get('signal_update_interval', 5))  # Default to 5 seconds if not specified

# Initialize named pipe
create_named_pipe(named_pipe_path)

# Start emit_signals thread
signals_thread = threading.Thread(target=emit_signals)
signals_thread.daemon = True
signals_thread.start()

def handle_shutdown(signal_num, frame):
    """Handle application shutdown gracefully."""
    logging.info("Received shutdown signal.")
    # Perform any necessary cleanup here
    socketio.stop()

# Register shutdown handler
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

if __name__ == '__main__':
    try:
        logging.info("Starting the application with SocketIO...")
        socketio.run(app, host='0.0.0.0', port=5000)
    except Exception as e:
        logging.error(f"Application failed to start: {e}")
