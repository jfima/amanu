import argparse
import sys
import logging
from .utils import load_config, setup_logging
from .scribe import Scribe

def main():
    # Parent parser for shared arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--config", help="Path to configuration file.")
    parent_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    parent_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress output (errors only).")
    parent_parser.add_argument("--dry-run", action="store_true", help="Simulate processing without making API calls.")
    parent_parser.add_argument("--template", default="default", help="Output template name (default: 'default').")

    # Main parser
    parser = argparse.ArgumentParser(description="Amanu - AI-powered amanuensis for your voice notes.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Run in daemon mode, watching for new files.", parents=[parent_parser])
    watch_parser.add_argument("path", nargs="?", help="Input directory to watch (overrides config).")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run once, processing all existing files and exiting.", parents=[parent_parser])
    run_parser.add_argument("path", nargs="?", help="Input directory or file to process (overrides config).")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR
        
    logger = setup_logging()
    logger.setLevel(log_level)
    # Also set handler levels if needed, but logger level is usually enough if handlers inherit

    # Load config
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Initialize Scribe
    scribe = Scribe(config, dry_run=args.dry_run, template_name=args.template)

    if args.command == "watch":
        logger.info("Starting Amanu in WATCH mode...")
        scribe.watch(input_path=args.path)
    elif args.command == "run":
        logger.info("Starting Amanu in RUN mode...")
        scribe.process_all(input_path=args.path)
    else:
        # Default to help if no command provided
        parser.print_help()

if __name__ == "__main__":
    main()
