# src/main.py

from app import app, socketio
import logging

def main():
    try:
        logging.info("Starting the application with SocketIO...")
        socketio.run(app, host='0.0.0.0', port=5000)
    except Exception as e:
        logging.error(f"Application failed to start: {e}")

if __name__ == '__main__':
    main()
