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

def setup_logging():
    """Configures logging to console."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger("AIVoice")

def get_cost_estimate(input_tokens, output_tokens):
    """
    Estimates cost for Gemini 1.5 Flash (approximate pricing).
    Pricing (as of late 2024, check official docs for updates):
    - Input: ~$0.075 per 1M tokens
    - Output: ~$0.30 per 1M tokens
    """
    # Pricing constants (per 1M tokens)
    PRICE_INPUT_PER_1M = 0.075
    PRICE_OUTPUT_PER_1M = 0.30

    input_cost = (input_tokens / 1_000_000) * PRICE_INPUT_PER_1M
    output_cost = (output_tokens / 1_000_000) * PRICE_OUTPUT_PER_1M
    total_cost = input_cost + output_cost

    return f"${total_cost:.6f}"
