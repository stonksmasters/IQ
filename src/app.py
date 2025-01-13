# src/app.py

import eventlet
eventlet.monkey_patch()  # Must be the first import to ensure proper monkey patching

from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import threading
import time
import logging
import signal
import subprocess

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

# GStreamer pipeline command to output MJPEG frames via stdout
gst_pipeline_cmd = (
    "gst-launch-1.0 -v libcamerasrc ! "
    "queue ! "
    "videoconvert ! "
    "jpegenc ! "
    "multipartmux boundary=frame ! "
    "fdsink fd=1"
)

def generate_frames():
    """
    Generator function to capture video frames using GStreamer subprocess.
    """
    logging.info("Starting GStreamer subprocess for video capture.")
    proc = subprocess.Popen(
        gst_pipeline_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    
    boundary = b'--frame\r\n'
    try:
        while True:
            # Read lines until boundary
            line = proc.stdout.readline()
            if not line:
                break
            if boundary in line:
                # Read headers
                content_type = proc.stdout.readline()
                empty_line = proc.stdout.readline()
                
                # Read JPEG frame
                # GStreamer doesn't send content-length, so read until boundary
                frame = bytearray()
                while True:
                    byte = proc.stdout.read(1)
                    if not byte:
                        break
                    frame += byte
                    if frame.endswith(b'\r\n--frame\r\n'):
                        frame = frame[:-len(b'\r\n--frame\r\n')]
                        break
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + bytes(frame) + b'\r\n')
    except Exception as e:
        logging.error(f"Error in generate_frames: {e}")
    finally:
        proc.kill()
        logging.info("GStreamer subprocess terminated.")

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
