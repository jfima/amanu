import yaml
import logging
import os
import sys

def load_config(config_path=None):
    """
    Loads configuration with hierarchy:
    1. Path provided via argument (if any)
    2. Environment variable AMANU_CONFIG
    3. Local file (./amanu.yaml or ./config.yaml)
    4. User config (~/.config/amanu/config.yaml)
    5. Defaults
    """
    # Default configuration
    config = {
        "paths": {
            "input": "./input",
            "results": "./results",
            "quarantine": "./quarantine"
        },
        "gemini": {
            "api_key": None,
            "model": "gemini-2.0-flash"
        },
        "audio": {
            "format": "ogg",
            "bitrate": "24k"
        },
        "pricing": {
            "input_per_1m": 0.075,
            "output_per_1m": 0.30
        }
    }

    # Determine config file to load
    files_to_check = []
    
    if config_path:
        files_to_check.append(config_path)
    
    if os.environ.get("AMANU_CONFIG"):
        files_to_check.append(os.environ.get("AMANU_CONFIG"))
        
    files_to_check.extend([
        "./amanu.yaml",
        "./config.yaml",
        os.path.expanduser("~/.config/amanu/config.yaml")
    ])

    loaded_file = None
    for f in files_to_check:
        if os.path.exists(f):
            try:
                with open(f, "r") as stream:
                    file_config = yaml.safe_load(stream)
                    if file_config:
                        # Deep merge (simple version)
                        for section, values in file_config.items():
                            if section in config and isinstance(values, dict):
                                config[section].update(values)
                            else:
                                config[section] = values
                        loaded_file = f
                        break # Stop after finding the first valid config
            except Exception as e:
                print(f"Warning: Failed to load config from {f}: {e}")

    # Environment Variable Overrides
    if os.environ.get("GEMINI_API_KEY"):
        config['gemini']['api_key'] = os.environ.get("GEMINI_API_KEY")

    return config

from logging.handlers import TimedRotatingFileHandler

def setup_logging(log_dir="logs"):
    """Configures logging to console and rotating file."""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    logger = logging.getLogger("Amanu")
    logger.setLevel(logging.INFO)
    
    # Avoid adding handlers multiple times
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(console_handler)
        
        # File Handler (Rotating)
        file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(file_handler)
        
    return logger

def get_cost_estimate(input_tokens, output_tokens, input_rate=0.075, output_rate=0.30):
    """
    Estimates cost for Gemini.
    Pricing rates are per 1M tokens.
    """
    input_cost = (input_tokens / 1_000_000) * input_rate
    output_cost = (output_tokens / 1_000_000) * output_rate
    total_cost = input_cost + output_cost

    return f"${total_cost:.6f}"
