import yaml
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from logging.handlers import TimedRotatingFileHandler

def setup_logging(log_dir: Optional[str] = None, debug: bool = False) -> logging.Logger:
    """Configures logging to console and rotating file.
    
    Args:
        log_dir: Directory for log files. If None, uses ~/.local/state/amanu/logs
        debug: If True, set logging level to DEBUG, otherwise INFO
    """
    if log_dir is None:
        # Use XDG State Home or fallback to ~/.amanu/logs
        xdg_state = os.environ.get("XDG_STATE_HOME")
        if xdg_state:
            log_dir = str(Path(xdg_state) / "amanu" / "logs")
        else:
            log_dir = str(Path.home() / ".local" / "state" / "amanu" / "logs")

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    logger = logging.getLogger("Amanu")
    log_level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(log_level)
    
    # Avoid adding handlers multiple times
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(console_handler)
        
        # File Handler (Rotating)
        try:
            file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file at {log_file}: {e}")
            print("Logging to console only.")

    else:
        # Update existing handlers if they exist
        for handler in logger.handlers:
            handler.setLevel(log_level)
        
    return logger

def get_cost_estimate(input_tokens: int, output_tokens: int, input_rate: float = 0.075, output_rate: float = 0.30) -> str:
    """
    Estimates cost for Gemini.
    Pricing rates are per 1M tokens.
    """
    input_cost = (input_tokens / 1_000_000) * input_rate
    output_cost = (output_tokens / 1_000_000) * output_rate
    total_cost = input_cost + output_cost

    return f"${total_cost:.6f}"
