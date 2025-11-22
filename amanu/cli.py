import argparse
import sys
import logging
from .utils import load_config, setup_logging
from .scribe import Scribe

def main():
    parser = argparse.ArgumentParser(description="Amanu - AI-powered amanuensis for your voice notes.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Run in daemon mode, watching for new files.")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run once, processing all existing files and exiting.")

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()

    # Load config
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Initialize Scribe
    scribe = Scribe(config)

    if args.command == "watch":
        logger.info("Starting Amanu in WATCH mode...")
        scribe.watch()
    elif args.command == "run":
        logger.info("Starting Amanu in RUN mode...")
        scribe.process_all()
    else:
        # Default to help if no command provided
        parser.print_help()

if __name__ == "__main__":
    main()
