"""Results management for Amanu."""

import json
import uuid
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from .constants import (
    COMPRESSED_AUDIO_FILENAME,
    RAW_TRANSCRIPT_FILENAME,
    CLEAN_TRANSCRIPT_FILENAME,
    METADATA_FILENAME,
    RAW_TRANSCRIPT_ERROR_FILENAME,
)
from .models import ProcessingResult, AudioFile, ProcessingMetrics

logger = logging.getLogger("Amanu")


class ResultsManager:
    """Manages saving and organizing processing results."""
    
    def __init__(self, results_base_dir: Path):
        """
        Initialize ResultsManager.
        
        Args:
            results_base_dir: Base directory for saving results
        """
        self.results_base_dir = Path(results_base_dir)
    
    def create_output_directory(self, original_filename: str) -> Path:
        """
        Create timestamped output directory structure.
        
        Args:
            original_filename: Name of the original audio file
            
        Returns:
            Path to the created output directory
        """
        now = datetime.now()
        name_without_ext = Path(original_filename).stem
        
        timestamp = now.strftime("%H%M%S")
        folder_name = f"{timestamp}-{name_without_ext}"
        
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        
        target_dir = self.results_base_dir / year / month / day / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        return target_dir
    
    def save_compressed_audio(self, compressed_path: Path, output_dir: Path) -> None:
        """
        Copy compressed audio to output directory.
        
        Args:
            compressed_path: Path to compressed audio file
            output_dir: Output directory
        """
        destination = output_dir / COMPRESSED_AUDIO_FILENAME
        shutil.copy2(str(compressed_path), str(destination))
    
    def save_transcripts(
        self,
        raw_json_str: str,
        clean_markdown: str,
        output_dir: Path,
        creation_date_str: str,
    ) -> List[Dict[str, Any]]:
        """
        Save raw and clean transcripts.
        
        Args:
            raw_json_str: Raw JSON transcript string
            clean_markdown: Clean markdown transcript
            output_dir: Output directory
            creation_date_str: File creation date string
            
        Returns:
            Parsed raw transcript data (empty list if parsing fails)
        """
        # Save raw transcript (JSON)
        raw_data = []
        try:
            from .response_parser import ResponseParser
            raw_data = ResponseParser.parse_transcript_json(raw_json_str)
            
            raw_path = output_dir / RAW_TRANSCRIPT_FILENAME
            with open(raw_path, "w") as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse raw transcript JSON: {e}")
            # Save error file for debugging
            error_path = output_dir / RAW_TRANSCRIPT_ERROR_FILENAME
            with open(error_path, "w") as f:
                f.write(raw_json_str)
        
        # Save clean transcript (Markdown)
        now = datetime.now()
        meta_header = (
            f"**Original File Date:** {creation_date_str}\\n"
            f"**Processed Date:** {now.strftime('%Y-%m-%d %H:%M:%S')}\\n\\n"
        )
        final_clean_content = meta_header + clean_markdown
        
        clean_path = output_dir / CLEAN_TRANSCRIPT_FILENAME
        with open(clean_path, "w") as f:
            f.write(final_clean_content)
        
        return raw_data
    
    def save_metadata(
        self,
        output_dir: Path,
        audio_file: AudioFile,
        metrics: ProcessingMetrics,
        language: str = "auto",
        device_id: str = None,
        source: str = None,
    ) -> None:
        """
        Save processing metadata.
        
        Args:
            output_dir: Output directory
            audio_file: Audio file information
            metrics: Processing metrics
            language: Detected language
            device_id: Optional device ID
            source: Optional source information
        """
        meta = {
            "id": str(uuid.uuid4()),
            "file": {
                "original_name": audio_file.original_name,
                "created_at": audio_file.created_at,
                "size_bytes": audio_file.size_bytes,
                "checksum_sha256": audio_file.checksum_sha256,
                "duration_seconds": audio_file.duration_seconds,
            },
            "processing": {
                "timestamp_start": metrics.timestamp_start,
                "duration_seconds": metrics.duration_seconds,
                "model": metrics.model,
                "tokens": {
                    "input": metrics.input_tokens,
                    "output": metrics.output_tokens,
                },
                "cost_usd": metrics.cost_usd,
            },
            "content": {
                "language": language,
                "device_id": device_id,
                "source": source,
            },
        }
        
        meta_path = output_dir / METADATA_FILENAME
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    
    def log_completion(
        self,
        filename: str,
        creation_date_str: str,
        duration: float,
        input_tokens: int,
        output_tokens: int,
        cost: str,
    ) -> None:
        """
        Log completion statistics to console.
        
        Args:
            filename: Original filename
            creation_date_str: File creation date
            duration: Processing duration in seconds
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost: Estimated cost
        """
        logger.info("=" * 30)
        logger.info(f"DONE: {filename}")
        logger.info(f"Original Date: {creation_date_str}")
        logger.info(f"Time: {duration:.2f}s")
        logger.info(f"Tokens: {input_tokens} in / {output_tokens} out")
        logger.info(f"Cost: {cost}")
        logger.info("=" * 30)
