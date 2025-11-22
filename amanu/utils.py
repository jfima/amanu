import yaml
import logging
import os
import sys

def load_config(config_path="config.yaml"):
    """Loads the YAML configuration file."""
    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' not found.")
        sys.exit(1)
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

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
