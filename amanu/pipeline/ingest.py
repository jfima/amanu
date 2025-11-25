import subprocess
import logging
import json
import time
import datetime
from pathlib import Path
from typing import Dict, Any, List # Keep List if used, otherwise remove

import google.generativeai as genai
from google.generativeai import caching

from .base import BaseStage
from ..core.models import JobMeta, StageName, AudioMeta

logger = logging.getLogger("Amanu.Ingest")

class IngestStage(BaseStage):
    stage_name = StageName.INGEST

    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Analyze, Compress, and Upload audio.
        Combines previous Scout and Prep stages.
        """
        # Configure Gemini
        self._configure_gemini(meta.configuration.transcribe.name)

        # 1. Locate Original File
        media_dir = job_dir / "media"
        original_files = list(media_dir.glob("original.*"))
        if not original_files:
            raise FileNotFoundError(f"No original file found in {media_dir}")
        original_file = original_files[0]

        # 2. Analyze Audio (Scout Logic)
        logger.info(f"Analyzing {original_file.name}...")
        audio_meta = self._analyze_audio(original_file)
        meta.audio = audio_meta
        
        # Estimate tokens (conservative 15 tokens/sec for output limit check)
        estimated_output_tokens = int(audio_meta.duration_seconds * 15)
        
        # 3. Compress/Optimize (Prep Logic)
        strategy = self._get_compression_strategy(original_file, meta.configuration.compression_mode)
        
        if strategy['needs_conversion']:
            logger.info(f"Compressing to OGG (mode: {meta.configuration.compression_mode})...")
            compressed_file = job_dir / "media" / "compressed.ogg"
            self._compress_file(original_file, compressed_file)
            upload_file = compressed_file
            compression_method = "compressed"
        else:
            logger.info("Using original file (no compression needed)...")
            upload_file = original_file
            compression_method = "original"

        # 4. Upload to Gemini
        # Decision: Cache or Direct?
        # For now, we default to Cache for reliability with long files, 
        # unless file is very small (< 5 mins) where cache might be overkill/error-prone.
        
        use_cache = audio_meta.duration_seconds > 300 # 5 minutes
        
        cache_name = None
        file_uri = None
        file_name = None
        
        if use_cache:
            logger.info("Uploading and creating Context Cache...")
            try:
                cache_name, file_name, file_uri = self._create_cache(upload_file, meta.configuration.transcribe.name)
            except Exception as e:
                logger.warning(f"Cache creation failed ({e}). Falling back to direct upload.")
                use_cache = False
        
        if not use_cache:
            logger.info("Uploading for Direct Processing...")
            file_obj = self._upload_direct(upload_file)
            file_name = file_obj.name
            file_uri = file_obj.uri

        # 5. Result
        return {
            "started_at": datetime.datetime.now().isoformat(),
            "audio_meta": audio_meta.model_dump(),
            "compression": {
                "method": compression_method,
                "file": str(upload_file.relative_to(job_dir))
            },
            "gemini": {
                "file_name": file_name,
                "file_uri": file_uri,
                "cache_name": cache_name,
                "using_cache": bool(cache_name)
            }
        }

    def _analyze_audio(self, filepath: Path) -> AudioMeta:
        """Get audio details using ffprobe."""
        try:
            # Get duration
            cmd_duration = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(filepath)
            ]
            result_dur = subprocess.run(cmd_duration, capture_output=True, text=True, check=True)
            duration = float(result_dur.stdout.strip()) if result_dur.stdout.strip() else 0.0

            # Get format and bitrate
            cmd_info = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=format_name,bit_rate,size',
                '-of', 'json',
                str(filepath)
            ]
            result_info = subprocess.run(cmd_info, capture_output=True, text=True, check=True)
            info = json.loads(result_info.stdout)
            fmt = info['format']
            
            return AudioMeta(
                duration_seconds=duration,
                format=fmt.get('format_name'),
                bitrate=int(fmt.get('bit_rate', 0)),
                file_size_bytes=int(fmt.get('size', 0))
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFprobe command failed: {e.stderr}")
            raise
        except Exception as e:
            logger.warning(f"Failed to analyze audio: {e}")
            return AudioMeta(duration_seconds=0.0)

    def _get_compression_strategy(self, file_path: Path, mode: str) -> dict:
        """Determine compression strategy."""
        video_exts = {'.mp4', '.mov', '.mkv', '.webm'}
        is_video = file_path.suffix.lower() in video_exts
        
        return {
            'needs_conversion': is_video or mode in ['compressed', 'optimized'],
            'output_format': 'ogg'
        }

    def _create_cache(self, file_path: Path, model_name: str) -> tuple[str | None, str, str]:
        """Upload and create cache. Returns (cache_name, file_name, file_uri)."""
        file = genai.upload_file(file_path)
        
        # Wait for processing
        while file.state.name == "PROCESSING":
            time.sleep(2)
            file = genai.get_file(file.name)
            
        if file.state.name == "FAILED":
            raise ValueError(f"File upload failed: {file.state.name}")
            
        # Cache TTL: 1 hour
        ttl_seconds = 3600 
        
        try:
            cache = caching.CachedContent.create(
                model=model_name,
                display_name=f"amanu_cache_{file_path.name}",
                system_instruction="You are a professional transcriber. Transcribe the audio exactly as spoken.",
                contents=[file],
                ttl=datetime.timedelta(seconds=ttl_seconds),
            )
            return cache.name, file.name, file.uri
            
        except Exception as e:
            if "400" in str(e) and "too small" in str(e):
                logger.warning(f"Content too small for caching ({e}). Proceeding without cache.")
                return None, file.name, file.uri # Return file_uri here
            else:
                raise e

    def _compress_file(self, input_path: Path, output_path: Path, start_time: str | None = None, duration: str | None = None) -> None:
        """Convert to OGG Opus."""
        cmd = [
            'ffmpeg', '-y', '-v', 'error', 
            '-i', str(input_path),
            '-vn',                 # No video
            '-map_metadata', '-1', # Strip metadata
            '-ac', '1',            # Mono
            '-c:a', 'libopus',     # Opus codec
            '-b:a', '24k',         # Low bitrate
            '-application', 'voip',
            str(output_path)
        ]
        subprocess.run(cmd, check=True)

    def _upload_direct(self, file_path: Path):
        """Upload file for direct use (no cache)."""
        file = genai.upload_file(file_path)
        
        while file.state.name == "PROCESSING":
            time.sleep(1)
            file = genai.get_file(file.name)
            
        if file.state.name == "FAILED":
            raise ValueError(f"File upload failed: {file.state.name}")
            
        return file
