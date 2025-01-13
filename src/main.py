#/src/main.py

from app import app, socketio
import logging

if __name__ == "__main__":
    try:
        logging.info("Starting the application with SocketIO...")
        # Use socketio.run instead of app.run to enable WebSockets
        socketio.run(app, host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        logging.error(f"Application failed to start: {e}")
