# main.py

from app import app
import logging

if __name__ == "__main__":
    try:
        logging.info("Starting the application...")
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        logging.error(f"Application failed to start: {e}")
