import time
import sys
import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from utils import load_config, setup_logging
from processor import AudioProcessor

logger = setup_logging()

class AudioHandler(FileSystemEventHandler):
    def __init__(self, processor):
        self.processor = processor

    def on_created(self, event):
        if event.is_directory:
            return
        
        filename = event.src_path
        if filename.lower().endswith('.mp3'):
            # Convert to absolute path
            filepath = os.path.abspath(filename)
            logger.info(f"New file detected: {filepath}")
            # Small delay to ensure file write is complete
            time.sleep(2) 
            self.processor.process_file(filepath)

def main():
    logger.info("Starting AI Audio Processor...")
    
    config = load_config()
    processor = AudioProcessor(config)
    
    input_dir = config['paths']['input']
    
    event_handler = AudioHandler(processor)
    observer = Observer()
    observer.schedule(event_handler, input_dir, recursive=False)
    observer.start()
    
    logger.info(f"Monitoring {input_dir} for .mp3 files...")
    logger.info("Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Stopping...")
    
    observer.join()

if __name__ == "__main__":
    main()
