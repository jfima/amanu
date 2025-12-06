"""File system watcher for monitoring input directory."""

import time
import logging
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from .core.manager import JobManager
from .core.config import ConfigContext
from .pipeline.base import Pipeline

logger = logging.getLogger("Amanu.Watcher")

class AudioFileHandler(FileSystemEventHandler):
    """Handles file system events for audio files."""
    
    def __init__(self, job_manager: JobManager, config: ConfigContext, pipeline: Pipeline):
        self.job_manager = job_manager
        self.config = config
        self.pipeline = pipeline
        self.processing_files = set()
        
    def on_created(self, event: FileCreatedEvent):
        """Handle file creation events."""
        if event.is_directory:
            return
            
        filepath = Path(event.src_path).resolve()
        
        # Supported extensions
        supported_exts = {'.mp3', '.wav', '.ogg', '.m4a', '.mp4', '.mov', '.mkv', '.webm'}
        if filepath.suffix.lower() not in supported_exts:
            return
            
        # Avoid duplicate processing
        if filepath in self.processing_files:
            logger.debug(f"Already processing {filepath.name}, skipping")
            return
            
        self.processing_files.add(filepath)
        
        try:
            # Small delay to ensure file write is complete
            time.sleep(2)
            
            # Verify file still exists and is stable
            if not filepath.exists():
                logger.warning(f"File {filepath.name} disappeared before processing")
                return
                
            logger.info(f"New file detected: {filepath.name}")
            
            # Create job
            job = self.job_manager.create_job(filepath, self.config.defaults)
            logger.info(f"Created job: {job.job_id}")
            
            # Delete source file from input (original is now in work/)
            try:
                filepath.unlink()
                logger.info(f"Removed {filepath.name} from input directory")
            except Exception as e:
                logger.error(f"Failed to remove {filepath.name} from input: {e}")
            
            # Run pipeline
            try:
                self.pipeline.run_all_stages(job.job_id)
                logger.info(f"Successfully completed job: {job.job_id}")
            except Exception as e:
                logger.error(f"Pipeline failed for job {job.job_id}: {e}")
                # Job stays in work/ with failed status
                
        finally:
            if filepath in self.processing_files:
                self.processing_files.remove(filepath)


class FileWatcher:
    """Watches input directory for new audio files."""
    
    def __init__(self, config: ConfigContext):
        # Setup logging based on config.debug
        from .utils import setup_logging
        setup_logging(debug=config.defaults.debug)
        
        self.config = config
        self.input_dir = Path(config.paths.input)
        self.job_manager = JobManager(work_dir=Path(config.paths.work))
        self.pipeline = Pipeline(
            job_manager=self.job_manager,
            results_dir=Path(config.paths.results)
        )
        
    def start(self):
        """Start watching the input directory."""
        # Create input directory if it doesn't exist
        self.input_dir.mkdir(parents=True, exist_ok=True)
        
        # Auto-cleanup old jobs if enabled
        if self.config.cleanup.auto_cleanup_enabled:
            logger.info("Running auto-cleanup of old jobs...")
            from .core.models import StageStatus
            
            # Cleanup failed jobs
            removed = self.job_manager.cleanup_old_jobs(
                retention_days=self.config.cleanup.failed_jobs_retention_days,
                status_filter=StageStatus.FAILED
            )
            if removed > 0:
                logger.info(f"Cleaned up {removed} old failed job(s)")
            
            # Cleanup completed jobs
            removed = self.job_manager.cleanup_old_jobs(
                retention_days=self.config.cleanup.completed_jobs_retention_days,
                status_filter=StageStatus.COMPLETED
            )
            if removed > 0:
                logger.info(f"Cleaned up {removed} old completed job(s)")
        
        # Setup file watcher
        event_handler = AudioFileHandler(
            job_manager=self.job_manager,
            config=self.config,
            pipeline=self.pipeline
        )
        
        observer = Observer()
        observer.schedule(event_handler, str(self.input_dir), recursive=False)
        observer.start()
        
        logger.info(f"📥 Watching for files in: {self.input_dir}")
        logger.info(f"🔧 Work directory: {self.config.paths.work}")
        logger.info(f"✅ Results directory: {self.config.paths.results}")
        logger.info("Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            logger.info("Stopping file watcher...")
        
        observer.join()
