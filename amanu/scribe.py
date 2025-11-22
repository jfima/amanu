import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .utils import load_config, get_cost_estimate
from .prompts import get_system_prompt
from .constants import (
    GEMINI_PROCESSING_POLL_INTERVAL,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_CHANNELS,
    MP3_EXTENSION,
)
from .file_manager import FileManager
from .response_parser import ResponseParser
from .results_manager import ResultsManager
from .models import AudioFile, ProcessingMetrics

logger = logging.getLogger("Amanu")


class AudioHandler(FileSystemEventHandler):
    """Handles file system events for audio files."""
    
    def __init__(self, scribe: 'Scribe'):
        self.scribe = scribe

    def on_created(self, event):
        if event.is_directory:
            return
        
        filepath = Path(event.src_path).resolve()
        if filepath.suffix.lower() == MP3_EXTENSION:
            logger.info(f"New file detected: {filepath}")
            # Small delay to ensure file write is complete
            time.sleep(2)
            self.scribe.process_file(filepath)


class Scribe:
    """Main orchestrator for audio transcription processing."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        dry_run: bool = False,
        template_name: str = "default"
    ):
        self.config = config
        self.dry_run = dry_run
        self.template_name = template_name
        self.processing_files: Set[Path] = set()
        
        # Initialize managers
        self.file_manager = FileManager()
        self.results_manager = ResultsManager(Path(config['paths']['results']))
        self.response_parser = ResponseParser()
        
        # Setup Gemini
        self.setup_gemini()

    def setup_gemini(self) -> None:
        """Configure Gemini API client."""
        import os
        api_key = os.getenv("GEMINI_API_KEY") or self.config['gemini']['api_key']
        if not api_key or api_key == "YOUR_KEY_HERE":
            logger.warning("Gemini API Key not found in env or config. Please set it.")
        genai.configure(api_key=api_key)
        
        try:
            system_instruction = get_system_prompt(self.template_name)
        except FileNotFoundError as e:
            logger.error(f"Template error: {e}")
            logger.warning("Falling back to 'default' template.")
            system_instruction = get_system_prompt("default")

        self.model = genai.GenerativeModel(
            model_name=self.config['gemini']['model'],
            system_instruction=system_instruction
        )

    def watch(self, input_path: Optional[str] = None) -> None:
        """Start daemon to watch for new files."""
        input_dir = Path(input_path) if input_path else Path(self.config['paths']['input'])
        input_dir.mkdir(parents=True, exist_ok=True)
        
        event_handler = AudioHandler(self)
        observer = Observer()
        observer.schedule(event_handler, str(input_dir), recursive=False)
        observer.start()
        
        logger.info(f"Scribe is listening in {input_dir}...")
        if self.dry_run:
            logger.info("DRY RUN MODE: No API calls will be made.")
        logger.info("Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            logger.info("Stopping Scribe...")
        
        observer.join()

    def process_all(self, input_path: Optional[str] = None) -> None:
        """Process all existing files in the input directory."""
        input_dir = Path(input_path) if input_path else Path(self.config['paths']['input'])
        input_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Scanning {input_dir} for files...")
        if self.dry_run:
            logger.info("DRY RUN MODE: No API calls will be made.")

        files = list(input_dir.glob(f"*{MP3_EXTENSION}"))
        
        if not files:
            logger.info("No files found to process.")
            return

        for filepath in files:
            self.process_file(filepath)

    def process_file(self, filepath: Path) -> None:
        """Process a single audio file."""
        filepath = filepath.resolve()
        
        if filepath in self.processing_files:
            logger.info(f"Skipping {filepath.name} - already processing.")
            return
        
        self.processing_files.add(filepath)
        
        # Wait for file to be ready
        if not self.file_manager.wait_for_file(filepath):
            logger.error(f"File {filepath} not found or not ready after waiting.")
            self.processing_files.remove(filepath)
            return

        start_time = time.time()
        logger.info(f"Starting processing for: {filepath.name}")
        logger.info(f"Using template: {self.template_name}")

        if self.dry_run:
            logger.info(f"[DRY RUN] Would process {filepath.name}")
            logger.info(f"[DRY RUN] Would compress -> upload -> generate -> save")
            self.processing_files.remove(filepath)
            return

        try:
            # 1. Compress Audio
            compressed_path = self.compress_audio(filepath)
            
            # 2. Upload to Gemini
            gemini_file = self.upload_to_gemini(compressed_path)
            
            # 3. Generate Content
            response = self.generate_content(gemini_file)
            
            # 4. Save Results
            self.save_results(filepath, compressed_path, response, start_time)
            
            # 5. Cleanup
            self.cleanup(filepath, compressed_path, gemini_file)
            
            logger.info(f"Successfully processed: {filepath.name}")

        except Exception as e:
            logger.error(f"Failed to process {filepath.name}: {e}")
            self.handle_failure(filepath)
        finally:
            if filepath in self.processing_files:
                self.processing_files.remove(filepath)

    def compress_audio(self, input_path: Path) -> Path:
        """Compress audio file using FFmpeg."""
        logger.info("Compressing audio...")
        output_path = input_path.parent / f"{input_path.stem}_compressed.ogg"
        
        bitrate = self.config['audio']['bitrate']
        
        cmd = [
            'ffmpeg', '-y',  # Overwrite
            '-i', str(input_path),
            '-c:a', 'libopus',
            '-b:a', bitrate,
            '-ac', str(DEFAULT_CHANNELS),  # Mono
            '-ar', str(DEFAULT_SAMPLE_RATE),  # 16kHz
            '-vn',  # No video
            str(output_path)
        ]
        
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg compression failed: {e}")
            raise

    def upload_to_gemini(self, filepath: Path):
        """Upload file to Gemini and wait for processing."""
        logger.info("Uploading to Gemini...")
        file = genai.upload_file(str(filepath), mime_type="audio/ogg")
        
        # Wait for processing
        while file.state.name == "PROCESSING":
            time.sleep(GEMINI_PROCESSING_POLL_INTERVAL)
            file = genai.get_file(file.name)
            
        if file.state.name == "FAILED":
            raise ValueError("Gemini file processing failed.")
            
        return file

    def generate_content(self, file):
        """Generate transcription and summary using Gemini."""
        logger.info("Generating transcription and summary...")
        # Safety settings to avoid blocking legitimate content
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        response = self.model.generate_content(
            [file, "Transcribe and summarize this audio."],
            safety_settings=safety_settings
        )
        return response

    def save_results(
        self,
        original_path: Path,
        compressed_path: Path,
        response,
        start_time: float
    ) -> None:
        """Save all processing results."""
        logger.info("Saving results...")
        
        # Create output directory
        output_dir = self.results_manager.create_output_directory(original_path.name)
        
        # Get file metadata
        creation_date_str = self.file_manager.get_creation_time(original_path)
        
        # Save compressed audio
        self.results_manager.save_compressed_audio(compressed_path, output_dir)
        
        # Parse response
        raw_json_str, clean_markdown = self.response_parser.parse_response(response.text)
        
        # Save transcripts
        self.results_manager.save_transcripts(
            raw_json_str,
            clean_markdown,
            output_dir,
            creation_date_str
        )
        
        # Calculate metrics
        end_time = time.time()
        duration = end_time - start_time
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        input_rate = self.config.get('pricing', {}).get('input_per_1m', 0.075)
        output_rate = self.config.get('pricing', {}).get('output_per_1m', 0.30)
        cost = get_cost_estimate(input_tokens, output_tokens, input_rate, output_rate)
        
        # Get audio duration
        audio_duration = self.get_audio_duration(compressed_path)
        
        # Create audio file info
        audio_file = AudioFile(
            path=original_path,
            original_name=original_path.name,
            created_at=datetime.fromtimestamp(original_path.stat().st_ctime).isoformat(),
            size_bytes=original_path.stat().st_size,
            duration_seconds=audio_duration,
            checksum_sha256=self.file_manager.calculate_checksum(compressed_path)
        )
        
        # Create processing metrics
        metrics = ProcessingMetrics(
            timestamp_start=datetime.fromtimestamp(start_time).isoformat(),
            duration_seconds=round(duration, 2),
            model=self.config['gemini']['model'],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost
        )
        
        # Save metadata
        self.results_manager.save_metadata(output_dir, audio_file, metrics)
        
        # Log completion
        self.results_manager.log_completion(
            original_path.name,
            creation_date_str,
            duration,
            input_tokens,
            output_tokens,
            cost
        )

    def get_audio_duration(self, filepath: Path) -> float:
        """Get audio file duration using ffprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(filepath)
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            return 0.0

    def cleanup(self, original_path: Path, compressed_path: Path, gemini_file) -> None:
        """Clean up temporary files and move original to processed."""
        # Delete compressed temp file
        if compressed_path.exists():
            compressed_path.unlink()
        
        # Move original file to processed folder
        self.file_manager.move_to_processed(original_path)
        
        # Delete from Gemini
        try:
            genai.delete_file(gemini_file.name)
        except Exception as e:
            logger.warning(f"Failed to delete file from Gemini: {e}")

    def handle_failure(self, filepath: Path) -> None:
        """Handle processing failure by moving file to quarantine."""
        quarantine_dir = Path(self.config['paths']['quarantine'])
        self.file_manager.move_to_quarantine(filepath, quarantine_dir)
