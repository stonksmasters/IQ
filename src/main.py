# src/main.py

import logging
import time
import subprocess
from app import app, socketio

def main():
    logging.info("Starting the application with SocketIO...")
    try:
        # Run the Flask-SocketIO server in a separate thread
        # socketio.run(...) is blocking, so we do it in a child process OR
        # we run the kiosk in a non-blocking way
        #
        # We'll do a non-blocking approach: Start kiosk AFTER socketio is up.

        # Start the server (blocking call)
        # We'll do the kiosk launch after a brief delay (in a separate thread or so).
        # But for simplicity, we'll just do the kiosk launch as a subprocess call,
        # with a little delay. We'll do that after the server starts.

        # Approach: We'll run socketio.run(...) last, but spawn kiosk just before that
        # in a background subprocess. The simplest approach is to do it just after a small sleep.

        # Start kiosk in the background
        # Wait 2 seconds to let the Flask server initialize
        def launch_kiosk():
            time.sleep(2)
            logging.info("Launching Chromium in kiosk mode...")
            subprocess.Popen([
                "chromium-browser",
                "--noerrdialogs",
                "--disable-infobars",
                "--kiosk",
                "http://localhost:5000"
            ])
        
        # We can do kiosk launch in a separate thread so that we can proceed to run the server
        from threading import Thread
        kiosk_thread = Thread(target=launch_kiosk, daemon=True)
        kiosk_thread.start()

        # Now run the SocketIO server (blocking)
        socketio.run(app, host='0.0.0.0', port=5000)
    except Exception as e:
        logging.error(f"Application failed to start: {e}")

if __name__ == '__main__':
    main()
