import logging
import json
import os
import subprocess
from typing import Dict, Any, List
from pathlib import Path

from ..core.providers import TranscriptionProvider, IngestSpecs
from ..core.models import JobConfiguration, WhisperConfig

logger = logging.getLogger("Amanu.Plugin.Whisper")

class WhisperProvider(TranscriptionProvider):
    def __init__(self, config: JobConfiguration, provider_config: WhisperConfig):
        super().__init__(config, provider_config)
        self.whisper_config = provider_config
        
        # Verify whisper-cli availability and determine whisper home directory
        try:
            result = subprocess.run(
                ["which", "whisper-cli"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            whisper_cli_path = Path(result.stdout.strip())
            
            # Auto-detect whisper home if not configured
            if self.whisper_config.whisper_home:
                self.whisper_home = Path(self.whisper_config.whisper_home)
            else:
                # Assume whisper-cli is in whisper.cpp directory or its subdirectory
                self.whisper_home = whisper_cli_path.parent
                
            logger.info(f"Using Whisper installation at: {self.whisper_home}")
            
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "whisper-cli not found in PATH.\n"
                "Please install whisper.cpp and ensure whisper-cli is accessible:\n"
                "  1. Clone: git clone https://github.com/ggerganov/whisper.cpp\n"
                "  2. Build: cd whisper.cpp && make\n"
                "  3. Add to PATH or create symlink in /usr/local/bin/\n"
                "See: https://github.com/ggerganov/whisper.cpp"
            )

    @classmethod
    def get_ingest_specs(cls) -> IngestSpecs:
        return IngestSpecs(
            target_format="wav",
            requires_upload=False,
            upload_target="none"
        )

    def transcribe(self, ingest_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        local_file_path = ingest_result.get("local_file_path")
        if not local_file_path:
            raise ValueError("No local file path found in Ingest result for Whisper.")
            
        model_name = self.config.transcribe.model
        
        # Find model spec in the list
        model_spec = next((m for m in self.whisper_config.models if m.name == model_name), None)
        
        if not model_spec:
            raise ValueError(f"Model '{model_name}' not found in Whisper provider settings.")
            
        # Resolve model path relative to whisper_home
        model_path = self.whisper_home / model_spec.path
            
        if not model_path.exists():
            raise FileNotFoundError(
                f"Whisper model file not found at {model_path}\n"
                f"  Model: {model_name}\n"
                f"  Whisper home: {self.whisper_home}\n"
                f"  Relative path: {model_spec.path}\n"
                f"Please download the model or check your configuration."
            )

        logger.info(f"Transcribing {local_file_path} using Whisper model {model_name}...")
        
        # Determine language
        language = self.config.language
        if language == "auto":
             # Whisper CLI uses 'auto' for detection
             language = "auto" 
        
        # Run transcription
        try:
            segments = self._run_whisper_cli(local_file_path, str(model_path), language)
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise

        # Calculate tokens
        # Whisper CLI returns tokens for each segment. We sum them up for output tokens.
        # For input tokens, we use the user's heuristic that input ~ output for audio context.
        output_tokens = sum(len(s.get('tokens', [])) for s in segments) if segments else 0
        
        # If segments don't have tokens (e.g. some other cli version), we might need a fallback, 
        # but _run_whisper_cli parses 'tokens' field so it should be fine.
        input_tokens = output_tokens

        # Calculate cost
        input_cost_rate = model_spec.cost_per_1M_tokens_usd.input
        output_cost_rate = model_spec.cost_per_1M_tokens_usd.output
        
        cost = (input_tokens / 1_000_000 * input_cost_rate) + (output_tokens / 1_000_000 * output_cost_rate)

        return {
            "segments": segments,
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost_usd": cost,
            "analysis": {"language": language} # Basic analysis
        }

    def _run_whisper_cli(self, audio_path: str, model_path: str, language: str) -> List[Dict[str, Any]]:
        abs_audio_path = os.path.abspath(audio_path)
        
        cmd = [
            "whisper-cli",
            "-m", model_path,
            "-f", abs_audio_path,
            "-l", language,
            "-ojf",        # Output full JSON
            "--no-prints"  # Suppress console output
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            
            # The tool creates a file named <audio_filename>.json
            json_output_path = f"{abs_audio_path}.json"
            
            if not os.path.exists(json_output_path):
                raise RuntimeError("JSON output file was not created by whisper-cli.")
                
            # Parse results
            with open(json_output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Clean up
            os.remove(json_output_path)
            
            results = []
            for segment in data.get('transcription', []):
                # Calculate confidence
                tokens = segment.get('tokens', [])
                confidence = 0.0
                if tokens:
                    probs = [t.get('p', 0) for t in tokens]
                    confidence = sum(probs) / len(probs)

                # Convert offsets (ms) to seconds
                start = segment['offsets']['from'] / 1000.0
                end = segment['offsets']['to'] / 1000.0
                
                results.append({
                    "speaker_id": "Unknown", # Diarization not supported in this CLI mode
                    "start_time": round(start, 3),
                    "end_time": round(end, 3),
                    "text": segment['text'].strip(),
                    "confidence": round(confidence, 2),
                    "tokens": tokens
                })
                
            return results
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Whisper CLI execution failed: {e.stderr.decode()}")
            raise
