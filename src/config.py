# src/config.py

import yaml
import logging

def load_config():
    """Load configuration from config/config.yaml."""
    try:
        with open('config/config.yaml', 'r') as f:
            conf = yaml.safe_load(f)
            logging.info("Configuration loaded successfully.")
            return conf
    except FileNotFoundError:
        logging.error("config/config.yaml not found.")
        return {}
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML: {e}")
        return {}

config = load_config()
