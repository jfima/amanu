import yaml
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from logging.handlers import TimedRotatingFileHandler
from rich.logging import RichHandler
from amanu.core.console import console as console_manager

def setup_logging(log_dir: Optional[str] = None, debug: bool = False, output_mode: str = "standard") -> logging.Logger:
    """Configures logging to console and rotating file.
    
    Args:
        log_dir: Directory for log files. If None, uses ~/.local/state/amanu/logs
        debug: If True, set logging level to DEBUG, otherwise INFO
        output_mode: 'standard', 'verbose', 'silent'. 'silent' suppresses console output.
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

    # Silence noisy 3rd party loggers
    noisy_loggers = [
        "urllib3", "requests", "httpx", "httpcore", "multipart", 
        "watchdog", "asyncio", "charset_normalizer"
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    logger = logging.getLogger("Amanu")
    
    # Determine levels
    if output_mode == "silent":
        console_level = logging.CRITICAL
        file_level = logging.DEBUG  # Always log details to file
    elif debug:
        console_level = logging.DEBUG
        file_level = logging.DEBUG
    else:
        # In standard mode, we want INFO logs, BUT we likely want them formatted nicely.
        console_level = logging.INFO
        file_level = logging.INFO

    # Set logger to lowest level to capture everything for handlers
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    
    # Avoid adding handlers multiple times
    if not logger.handlers:
        # Console Handler (Rich)
        if output_mode != "silent":
            # Use RichHandler for beautiful output
            # shared console instance ensures theme consistency
            console_handler = RichHandler(
                console=console_manager.console, 
                rich_tracebacks=True, 
                markup=True,
                show_time=True,
                show_path=False
            )
            console_handler.setLevel(console_level)
            # RichHandler has its own formatter schema, no need for standard setFormatter usually
            logger.addHandler(console_handler)
        
        # File Handler (Rotating)
        try:
            file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
            file_handler.setLevel(file_level)
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
            logger.addHandler(file_handler)
        except Exception as e:
            # We can't log this normally as handlers aren't set up
            if output_mode != "silent":
                print(f"Warning: Could not create log file at {log_file}: {e}")
                print("Logging to console only.")

    else:
        # Update existing handlers if they exist
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, TimedRotatingFileHandler):
                 # This captures both StreamHandler and RichHandler (subclass of StreamHandler)
                 if output_mode == "silent":
                     handler.setLevel(logging.CRITICAL)
                 else:
                     handler.setLevel(console_level)
            elif isinstance(handler, TimedRotatingFileHandler):
                handler.setLevel(file_level)
        
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
