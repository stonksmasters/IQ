from app import app, socketio
import subprocess, time, logging
from threading import Thread

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

def main():
    logging.info("Starting Flask-SocketIO server...")
    # Start kiosk in background
    t = Thread(target=launch_kiosk, daemon=True)
    t.start()
    socketio.run(app, host="0.0.0.0", port=5000)

if __name__ == '__main__':
    main()
