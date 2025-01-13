# src/config.py

import yaml
import logging

def load_config():
    """Load configuration from config.yaml."""
    try:
        with open('config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            logging.info("Configuration loaded successfully.")
            return config
    except FileNotFoundError:
        logging.error("Configuration file config.yaml not found.")
        return {}
    except yaml.YAMLError as exc:
        logging.error(f"Error parsing config.yaml: {exc}")
        return {}

# Load configuration on module import
config = load_config()
