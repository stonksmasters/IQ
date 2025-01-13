# src/main.py

import logging
import time
import subprocess
from app import app, socketio

def main():
    logging.info("Starting the application with SocketIO...")
    try:
        # Function to launch Chromium in kiosk mode after a short delay
        def launch_kiosk():
            logging.info("Kiosk launcher thread started. Waiting for server to initialize...")
            time.sleep(5)  # Wait longer to ensure the server is up
            logging.info("Launching Chromium in kiosk mode...")
            try:
                subprocess.Popen([
                    "chromium-browser",
                    "--noerrdialogs",
                    "--disable-infobars",
                    "--kiosk",
                    "--incognito",  # Optional: opens in incognito mode
                    "http://localhost:5000"
                ])
                logging.info("Chromium launched successfully in kiosk mode.")
            except Exception as e:
                logging.error(f"Failed to launch Chromium: {e}")

        # Start the kiosk launcher in a separate daemon thread
        from threading import Thread
        kiosk_thread = Thread(target=launch_kiosk, daemon=True)
        kiosk_thread.start()

        # Run the SocketIO server (blocking call)
        logging.info("Running SocketIO server...")
        socketio.run(app, host='0.0.0.0', port=5000)

    except Exception as e:
        logging.error(f"Application failed to start: {e}")

if __name__ == '__main__':
    main()
