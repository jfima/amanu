import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .base import BaseStage
from ..core.models import JobMeta, StageName, AudioMeta

logger = logging.getLogger("Amanu.Scout")

class ScoutStage(BaseStage):
    stage_name = StageName.SCOUT

    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Analyze audio file and determine processing strategy.
        """
        # Find original file (extension may vary)
        media_dir = job_dir / "media"
        original_files = list(media_dir.glob("original.*"))
        if not original_files:
            raise FileNotFoundError(f"Original audio file not found in {media_dir}")
        original_file = original_files[0]

        # 1. Analyze Audio
        audio_meta = self._analyze_audio(original_file)
        meta.audio = audio_meta
        
        # 2. Estimate Tokens
        # Rough estimate: 1 second ~ 10 tokens (very conservative, usually less)
        # Gemini counts tokens differently, but this is for chunking decision
        estimated_tokens = int(audio_meta.duration_seconds * 10) if audio_meta.duration_seconds else 0
        
        # 3. Decide on Chunking
        # Lookup context window for selected model
        # 3. Decide on Chunking
        # Lookup context window for selected model
        context_window = meta.configuration.transcribe.context_window.input_tokens
        output_limit = meta.configuration.transcribe.context_window.output_tokens
        
        # Force cap output limit to 4096 due to observed truncation issues with gemini-2.0-flash
        # User requested to remove this cap and respect config.
        # if output_limit > 4096:
        #     logger.warning(f"Configured output limit {output_limit} > 4096. Capping at 4096 for safety.")
        #     output_limit = 4096
            
        logger.info(f"Using context window {context_window} (input) / {output_limit} (output) for model {meta.configuration.transcribe.name}")
        
        chunking_decision = self._decide_chunking(estimated_tokens, context_window, output_limit, audio_meta.duration_seconds)
        
        # 4. Update Meta
        meta.processing.total_tokens.input = estimated_tokens # Initial estimate
        
        return {
            "started_at": datetime.now().isoformat(),
            "audio_analysis": audio_meta.model_dump(),
            "chunking_decision": chunking_decision
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
            result_dur = subprocess.run(cmd_duration, capture_output=True, text=True)
            duration = float(result_dur.stdout.strip()) if result_dur.stdout.strip() else 0.0

            # Get format and bitrate
            cmd_info = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=format_name,bit_rate,size',
                '-of', 'json',
                str(filepath)
            ]
            result_info = subprocess.run(cmd_info, capture_output=True, text=True)
            import json
            info = json.loads(result_info.stdout)
            fmt = info['format']
            
            return AudioMeta(
                duration_seconds=duration,
                format=fmt.get('format_name'),
                bitrate=int(fmt.get('bit_rate', 0)),
                file_size_bytes=int(fmt.get('size', 0))
            )
        except Exception as e:
            logger.warning(f"Failed to analyze audio: {e}")
            return AudioMeta(duration_seconds=0.0)

    def _decide_chunking(self, estimated_input_tokens: int, input_limit: int, output_limit: int, duration_seconds: float) -> Dict[str, Any]:
        """Decide if chunking is needed based on token estimate and output limits."""
        
        # 1. Check Input Limit
        # Safety margin: use 90% of context window
        input_safe_limit = input_limit * 0.9
        
        # If input exceeds limit, we MUST physically split the file
        if estimated_input_tokens > input_safe_limit:
            logger.info(f"Input tokens {estimated_input_tokens} > limit {input_safe_limit}. Using physical splitting.")
            
            # Physical splitting strategy (Legacy)
            target_tokens = input_safe_limit * 0.5
            chunk_duration = int(target_tokens / 10) # 10 tokens/sec heuristic
            
            return {
                "needs_chunking": True,
                "reason": f"Input tokens {estimated_input_tokens} > limit {input_safe_limit}",
                "strategy": {
                    "method": "physical_split",
                    "chunk_duration_seconds": chunk_duration,
                    "overlap_seconds": 60,
                    "estimated_chunks": (estimated_input_tokens // target_tokens) + 1
                }
            }
            
        # 2. Check Output Limit (Adaptive Chunking with Caching)
        # Heuristic: ~15 tokens per second for dense speech (very conservative)
        estimated_output_tokens = int(duration_seconds * 15)
        output_safe_limit = output_limit * 0.9
        
        if estimated_output_tokens > output_safe_limit:
            logger.info(f"Output tokens {estimated_output_tokens} > limit {output_safe_limit}. Using caching with logical chunking.")
            
            # Calculate max safe duration for output
            # duration = output_safe_limit / 15 (tokens/sec)
            max_duration_output = output_safe_limit / 15
            
            # Apply safety factor
            chunk_duration = int(max_duration_output * 0.9)
            
            # Generate logical chunks
            chunks = []
            current_time = 0.0
            chunk_idx = 1
            
            while current_time < duration_seconds:
                start = current_time
                end = min(start + chunk_duration, duration_seconds)
                
                chunks.append({
                    "id": f"chunk_{chunk_idx:03d}",
                    "start_time": self._format_duration(start),
                    "end_time": self._format_duration(end),
                    "start_seconds": start,
                    "end_seconds": end
                })
                
                current_time = end
                chunk_idx += 1
                
                if current_time >= duration_seconds - 1.0:
                    break

            return {
                "needs_chunking": True,
                "reason": f"Estimated output {estimated_output_tokens} > limit {output_safe_limit}",
                "strategy": {
                    "method": "caching",
                    "logical_chunks": chunks
                }
            }

        # Fits within both limits
        return {
            "needs_chunking": False,
            "reason": f"Fits within limits. Input: {estimated_input_tokens}/{input_safe_limit}, Output: {estimated_output_tokens}/{output_safe_limit}",
            "strategy": None
        }

    def _format_duration(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS.mmm"""
        if seconds is None:
            return "00:00:00"
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"
