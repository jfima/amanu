import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .base import BaseStage
from ..core.models import JobMeta, StageName

import google.generativeai as genai
from google.generativeai import caching
import datetime
import time

logger = logging.getLogger("Amanu.Prep")

class PrepStage(BaseStage):
    stage_name = StageName.PREP

    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Compress audio and split into chunks if needed.
        """
        # Configure Gemini (required for caching)
        self._configure_gemini(meta.configuration.transcribe.name)

        # Find original file (extension may vary)
        media_dir = job_dir / "media"
        original_files = list(media_dir.glob("original.*"))
        if not original_files:
            raise FileNotFoundError(f"No original file found in {media_dir}")
        original_file = original_files[0]
        
        # Load scout result to get chunking strategy
        scout_result = self._load_scout_result(job_dir)
        chunking_strategy = scout_result.get("chunking_decision", {}).get("strategy")
        
        result = {
            "started_at": datetime.datetime.now().isoformat(),
            "compression": {},
            "chunks": []
        }

        if chunking_strategy and chunking_strategy.get("method") == "caching":
            logger.info("Using Caching strategy.")
            
            # 1. Handle Compression
            strategy = self._get_compression_strategy(original_file, meta.configuration.compression_mode)
            
            if strategy['needs_conversion']:
                logger.info(f"Converting to OGG (mode: {meta.configuration.compression_mode})...")
                compressed_file = job_dir / "media" / "compressed.ogg"
                self._compress_file(original_file, compressed_file, strategy['remove_silence'])
                upload_file = compressed_file
                result["compression"]["method"] = "compressed" if not strategy['remove_silence'] else "optimized"
                result["compression"]["file"] = str(compressed_file.relative_to(job_dir))
            else:
                logger.info("Using original file...")
                upload_file = original_file
                result["compression"]["method"] = "original"
                result["compression"]["file"] = str(original_file.relative_to(job_dir))

            # 2. Upload & Create Cache
            cache_name, file_name = self._create_cache(upload_file, meta.configuration.transcribe.name)
            result["cache_name"] = cache_name
            result["file_name"] = file_name
            
            # Pass through logical chunks from scout
            result["chunks"] = chunking_strategy.get("logical_chunks", [])
            
        elif chunking_strategy and chunking_strategy.get("method") == "physical_split":
            logger.info(f"Physical splitting strategy found: {chunking_strategy}")
            chunks = self._process_chunks(original_file, job_dir, chunking_strategy)
            result["chunks"] = chunks
            result["compression"]["method"] = "chunked"
            
        else:
            # Legacy/Fallback: Single file (no chunking needed)
            logger.info("No chunking needed. Compressing single file.")
            
            # Handle Compression
            strategy = self._get_compression_strategy(original_file, meta.configuration.compression_mode)
            
            if strategy['needs_conversion']:
                logger.info(f"Converting to OGG (mode: {meta.configuration.compression_mode})...")
                compressed_file = job_dir / "media" / "compressed.ogg"
                self._compress_file(original_file, compressed_file, strategy['remove_silence'])
                upload_file = compressed_file
                result["compression"]["method"] = "compressed" if not strategy['remove_silence'] else "optimized"
                result["compression"]["file"] = str(compressed_file.relative_to(job_dir))
            else:
                logger.info("Using original file...")
                upload_file = original_file
                result["compression"]["method"] = "original"
                result["compression"]["file"] = str(original_file.relative_to(job_dir))
            
            # Upload file directly (No Cache)
            logger.info(f"Uploading {upload_file.name} to Gemini (Direct)...")
            file_obj = genai.upload_file(upload_file)
            
            # Wait for processing
            while file_obj.state.name == "PROCESSING":
                time.sleep(1)
                file_obj = genai.get_file(file_obj.name)
                
            if file_obj.state.name == "FAILED":
                raise ValueError(f"File upload failed: {file_obj.state.name}")
                
            logger.info(f"File uploaded: {file_obj.uri}")
            
            result["cache_name"] = None
            result["file_name"] = file_obj.name
            
            # Add single chunk entry for uniform handling in Scribe
            result["chunks"] = [{
                "id": "chunk_001",
                "file": str(upload_file.relative_to(job_dir)),
                "start_time": "00:00:00",
                "end_time": self._format_duration(meta.audio.duration_seconds),
                "duration_seconds": meta.audio.duration_seconds
            }]

        return result

    def _create_cache(self, file_path: Path, model_name: str) -> tuple[Optional[str], str]:
        """Upload file and create Gemini cache."""
        logger.info(f"Uploading {file_path.name} to Gemini...")
        
        # 1. Upload File
        file = genai.upload_file(file_path)
        
        # Wait for processing
        while file.state.name == "PROCESSING":
            time.sleep(2)
            file = genai.get_file(file.name)
            
        if file.state.name == "FAILED":
            raise ValueError(f"File upload failed: {file.state.name}")
            
        logger.info(f"File uploaded: {file.uri}")
        
        # 2. Create Cache
        logger.info("Creating context cache...")
        
        # Cache TTL: 1 hour (sufficient for pipeline)
        ttl_seconds = 3600 
        
        try:
            cache = caching.CachedContent.create(
                model=model_name,
                display_name=f"amanu_cache_{file_path.name}",
                system_instruction="You are a professional transcriber. Transcribe the audio exactly as spoken.",
                contents=[file],
                ttl=datetime.timedelta(seconds=ttl_seconds),
            )
            logger.info(f"Cache created: {cache.name}")
            return cache.name, file.name
            
        except Exception as e:
            if "400" in str(e) and "too small" in str(e):
                logger.warning(f"Content too small for caching ({e}). Proceeding without cache.")
                return None, file.name
            else:
                raise e

    def _load_scout_result(self, job_dir: Path) -> Dict[str, Any]:
        import json
        scout_file = job_dir / "_stages" / "scout.json"
        if not scout_file.exists():
            raise FileNotFoundError("Scout stage result not found. Run scout first.")
        with open(scout_file, "r") as f:
            return json.load(f)

    def _get_compression_strategy(self, file_path: Path, mode: str) -> dict:
        """Determine compression strategy based on file type and mode."""
        video_exts = {'.mp4', '.mov', '.mkv', '.webm'}
        is_video = file_path.suffix.lower() in video_exts
        
        # Note: silence removal disabled due to API processing issues
        # 'optimized' mode now works the same as 'compressed'
        return {
            'needs_conversion': is_video or mode in ['compressed', 'optimized'],
            'remove_silence': False,  # Disabled - causes API issues
            'output_format': 'ogg' if (is_video or mode != 'original') else None
        }

    def _compress_file(self, input_path: Path, output_path: Path, remove_silence: bool = False, start_time: Optional[str] = None, duration: Optional[str] = None) -> None:
        """Convert to OGG format, optionally removing silence."""
        cmd = ['ffmpeg', '-y', '-v', 'error', '-i', str(input_path)]
        
        if start_time:
            cmd.extend(['-ss', start_time])
        if duration:
            cmd.extend(['-t', duration])
        
        # Silence removal disabled due to API processing issues
        # The feature caused fragmented audio that Gemini couldn't process correctly
        # Users still get cost savings through OGG compression
        # if remove_silence:
        #     cmd.extend([
        #         '-af',
        #         'silenceremove=stop_periods=-1:stop_duration=2:stop_threshold=-50dB'
        #     ])
            
        cmd.extend([
            '-vn',                 # No video
            '-map_metadata', '-1', # Strip metadata
            '-ac', '1',            # Mono
            '-c:a', 'libopus',     # Opus codec
            '-b:a', '24k',         # Low bitrate (sufficient for speech)
            '-application', 'voip',
            str(output_path)
        ])
        
        subprocess.run(cmd, check=True)

    def _process_chunks(self, input_path: Path, job_dir: Path, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks_dir = job_dir / "media" / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        
        chunk_duration = strategy["chunk_duration_seconds"]
        overlap = strategy["overlap_seconds"]
        
        # Get total duration from ffprobe again to be sure
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(input_path)]
        total_duration = float(subprocess.check_output(cmd).strip())
        
        chunks = []
        current_time = 0.0
        chunk_idx = 1
        
        while current_time < total_duration:
            # Calculate chunk parameters
            start = current_time
            # Last chunk might be shorter
            duration = min(chunk_duration, total_duration - start)
            
            # If this is not the first chunk, we need to account for overlap in the *previous* chunk's perspective?
            # No, the strategy says "overlap_seconds". 
            # Usually this means: Chunk N starts at T. Chunk N+1 starts at T + duration - overlap.
            # But here we want explicit control.
            
            # Let's follow the design:
            # Chunk 1: 0 to 3000
            # Chunk 2: 2940 to 5940 (starts at 3000 - 60)
            
            chunk_filename = f"chunk_{chunk_idx:03d}.ogg"
            output_path = chunks_dir / chunk_filename
            
            start_str = self._format_duration(start)
            duration_str = self._format_duration(duration)
            
            logger.info(f"Processing chunk {chunk_idx}: start={start_str}, duration={duration_str}")
            
            self._compress_file(input_path, output_path, start_time=start_str, duration=duration_str)
            
            chunk_info = {
                "id": f"chunk_{chunk_idx:03d}",
                "file": str(output_path.relative_to(job_dir)),
                "start_time": start_str,
                "end_time": self._format_duration(start + duration),
                "duration_seconds": duration
            }
            
            if chunk_idx > 1:
                chunk_info["overlap_with_previous"] = overlap
                
            chunks.append(chunk_info)
            
            # Next chunk starts before this one ends (overlap)
            current_time += (chunk_duration - overlap)
            chunk_idx += 1
            
            # Break if we've covered the whole file (small epsilon for float errors)
            if start + duration >= total_duration - 1.0:
                break
                
        return chunks

    def _format_duration(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS.mmm"""
        if seconds is None:
            return "00:00:00"
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"
