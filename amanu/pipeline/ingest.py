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
from ..core.models import JobObject, StageName, AudioMeta
from ..core.factory import ProviderFactory

logger = logging.getLogger("Amanu.Ingest")

class IngestStage(BaseStage):
    stage_name = StageName.INGEST

    def validate_prerequisites(self, job_dir: Path, job: JobObject) -> None:
        """
        Validate prerequisites for ingest stage.
        """
        # Check that source file exists
        media_dir = job_dir / "media"
        original_files = list(media_dir.glob("original.*"))
        if not original_files:
            raise FileNotFoundError(f"No source file found in {media_dir}")
        
        # Check that file is not empty
        original_file = original_files[0]
        if original_file.stat().st_size == 0:
            raise ValueError(f"Source file is empty: {original_file}")

    def execute(self, job_dir: Path, job: JobObject, **kwargs) -> Dict[str, Any]:
        """
        Analyze, Compress, and Upload audio.
        Combines previous Scout and Prep stages.
        """


        # 1. Locate Original File
        media_dir = job_dir / "media"
        original_files = list(media_dir.glob("original.*"))
        if not original_files:
            raise FileNotFoundError(f"No original file found in {media_dir}")
        original_file = original_files[0]

        # 2. Analyze Audio (Scout Logic)
        logger.info(f"Analyzing {original_file.name}...")
        audio_meta = self._analyze_audio(original_file)
        job.audio = audio_meta
        
        # Estimate tokens (conservative 15 tokens/sec for output limit check)
        estimated_output_tokens = int(audio_meta.duration_seconds * 15)
        
        # Determine Provider Requirements
        provider_name = job.configuration.transcribe.provider
        provider_cls = ProviderFactory.get_provider_class(provider_name)
        specs = provider_cls.get_ingest_specs()
        
        logger.info(f"Ingest for provider: {provider_name} (Format: {specs.target_format}, Upload: {specs.requires_upload})")

        # 3. Convert/Optimize
        # Respect compression_mode setting:
        # - 'original': Use original file as-is, no conversion
        # - 'compressed' or 'optimized': Convert to provider's target format
        
        target_ext = f".{specs.target_format}"
        
        # If user explicitly wants original, skip conversion entirely
        if job.configuration.compression_mode == 'original':
            needs_conversion = False
        else:
            # Otherwise, convert if format doesn't match OR compression is requested
            needs_conversion = (original_file.suffix.lower() != target_ext) or \
                               (job.configuration.compression_mode in ['compressed', 'optimized'])
        
        prepared_file = original_file
        if needs_conversion:
            logger.info(f"Converting to {specs.target_format}...")
            prepared_file = job_dir / "media" / f"prepared{target_ext}"
            self._convert_file(original_file, prepared_file, specs.target_format)
            compression_method = f"converted_{specs.target_format}"
        else:
            logger.info("Using original file...")
            compression_method = "original"

        # 4. Upload (if required)
        gemini_data = {}
        if specs.requires_upload and specs.upload_target == "gemini_cache":
            # Gemini Logic
            # Ensure Gemini is configured
            gemini_config = self.manager.providers.get("gemini")
            if gemini_config and gemini_config.api_key:
                genai.configure(api_key=gemini_config.api_key)
            else:
                # Try env var
                import os
                api_key = os.environ.get("GEMINI_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                else:
                    logger.warning("Gemini API Key not found. Upload might fail.")

            use_cache = audio_meta.duration_seconds > 300 # 5 minutes
            
            cache_name = None
            file_uri = None
            file_name = None
            
            if use_cache:
                logger.info("Uploading and creating Context Cache...")
                try:
                    cache_name, file_name, file_uri = self._create_cache(prepared_file, job.configuration.transcribe.model)
                except Exception as e:
                    logger.warning(f"Cache creation failed ({e}). Falling back to direct upload.")
                    use_cache = False
            
            if not use_cache:
                logger.info("Uploading for Direct Processing...")
                file_obj = self._upload_direct(prepared_file)
                file_name = file_obj.name
                file_uri = file_obj.uri
                
            gemini_data = {
                "file_name": file_name,
                "file_uri": file_uri,
                "cache_name": cache_name,
                "using_cache": bool(cache_name)
            }

        # 5. Result
        result_data = {
            "started_at": datetime.datetime.now().isoformat(),
            "audio_meta": audio_meta.model_dump(),
            "compression": {
                "method": compression_method,
                "file": str(prepared_file.relative_to(job_dir))
            },
            "local_file_path": str(prepared_file), # Generic path for local providers
            "gemini": gemini_data
        }
        
        # Update Job Object
        job.ingest_result = result_data
        
        return result_data

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

    def _convert_file(self, input_path: Path, output_path: Path, format: str) -> None:
        """Convert audio to target format."""
        cmd = ['ffmpeg', '-y', '-v', 'error', '-i', str(input_path)]
        
        if format == "ogg":
            cmd.extend([
                '-vn', '-map_metadata', '-1', '-ac', '1', 
                '-c:a', 'libopus', '-b:a', '24k', '-application', 'voip'
            ])
        elif format == "wav":
            cmd.extend([
                '-vn', '-map_metadata', '-1', '-ac', '1',
                '-ar', '16000', '-c:a', 'pcm_s16le'
            ])
        elif format == "mp3":
             cmd.extend([
                '-vn', '-map_metadata', '-1', '-ac', '1',
                '-c:a', 'libmp3lame', '-q:a', '4' 
            ])
        
        cmd.append(str(output_path))
        subprocess.run(cmd, check=True)

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



    def _upload_direct(self, file_path: Path):
        """Upload file for direct use (no cache)."""
        file = genai.upload_file(file_path)
        
        while file.state.name == "PROCESSING":
            time.sleep(1)
            file = genai.get_file(file.name)
            
        if file.state.name == "FAILED":
            raise ValueError(f"File upload failed: {file.state.name}")
            
        return file
