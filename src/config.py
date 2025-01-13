#/src/config.py

import yaml
import logging

def load_config(config_path='config/config.yaml'):
    """
    Load configuration from a YAML file.
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logging.info("Configuration loaded successfully.")
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file {config_path} not found.")
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML configuration: {e}")
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {e}")
    return {}

# Load the configuration at module import
config = load_config()
