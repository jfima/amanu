import logging
import json
import os
import subprocess
from typing import Dict, Any, List
from pathlib import Path

from ..core.providers import TranscriptionProvider, IngestSpecs
from ..core.models import JobConfiguration, WhisperXConfig

logger = logging.getLogger("Amanu.Plugin.WhisperX")

class WhisperXProvider(TranscriptionProvider):
    def __init__(self, config: JobConfiguration, provider_config: WhisperXConfig):
        super().__init__(config, provider_config)
        self.wx_config = provider_config
        
        # Verify whisperx availability
        try:
            subprocess.run(
                [self.wx_config.python_executable, "-m", "whisperx", "--version"], 
                capture_output=True, 
                check=True
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(
                f"whisperx not found or not working using '{self.wx_config.python_executable}'.\n"
                "Please ensure it is installed: pip install whisperx"
            )

    @classmethod
    def get_ingest_specs(cls) -> IngestSpecs:
        return IngestSpecs(
            target_format="mp3", # WhisperX handles mp3 fine
            requires_upload=False,
            upload_target="none"
        )

    def transcribe(self, ingest_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        local_file_path = ingest_result.get("local_file_path")
        if not local_file_path:
            raise ValueError("No local file path found in Ingest result for WhisperX.")
            
        model_name = self.config.transcribe.model
        
        # Find model spec in the list
        model_spec = next((m for m in self.wx_config.models if m.name == model_name), None)
        
        if not model_spec:
            # If not explicitly defined, we can try to use the name directly if it's a valid HF model
            logger.warning(f"Model '{model_name}' not found in WhisperX provider settings. Using as direct model name.")
            # Create a dummy spec for cost calculation if needed, or just proceed
            
        logger.info(f"Transcribing {local_file_path} using WhisperX model {model_name}...")
        
        # Determine language - prefer provider-specific language over global config
        language = self.wx_config.language if self.wx_config.language else self.config.language
        if language == "auto":
             language = None # WhisperX auto-detects if not specified
        
        # Run transcription
        try:
            segments = self._run_whisperx(local_file_path, model_name, language)
        except Exception as e:
            logger.error(f"WhisperX transcription failed: {e}")
            raise

        # Calculate tokens (approximate)
        output_tokens = sum(len(s.get('text', '').split()) * 1.3 for s in segments) if segments else 0
        input_tokens = output_tokens # Rough approximation

        # Calculate cost
        cost = 0.0
        if model_spec:
            input_cost_rate = model_spec.cost_per_1M_tokens_usd.input
            output_cost_rate = model_spec.cost_per_1M_tokens_usd.output
            cost = (input_tokens / 1_000_000 * input_cost_rate) + (output_tokens / 1_000_000 * output_cost_rate)

        return {
            "segments": segments,
            "tokens": {"input": int(input_tokens), "output": int(output_tokens)},
            "cost_usd": cost,
            "analysis": {"language": language or "auto"} 
        }

    def _run_whisperx(self, audio_path: str, model_name: str, language: str = None) -> List[Dict[str, Any]]:
        abs_audio_path = os.path.abspath(audio_path)
        output_dir = os.path.dirname(abs_audio_path)
        
        # Path to our wrapper script
        wrapper_script = Path(__file__).parent / "whisperx_wrapper.py"
        
        cmd = [
            self.wx_config.python_executable,
            str(wrapper_script),
            abs_audio_path,
            "--model", model_name,
            "--output_dir", output_dir,
            "--output_format", "json",
            "--device", self.wx_config.device,
            "--compute_type", self.wx_config.compute_type,
            "--batch_size", str(self.wx_config.batch_size)
        ]
        
        # Completely disable VAD/alignment if diarization is off (to avoid PyTorch 2.6 compatibility issues)
        if not self.wx_config.enable_diarization:
            cmd.append("--no_align")
        
        # Add diarization if enabled
        if self.wx_config.enable_diarization:
            cmd.append("--diarize")
            
        # Add HF token if provided
        if self.wx_config.hf_token:
            cmd.extend(["--hf_token", self.wx_config.hf_token])
        
        if language:
            cmd.extend(["--language", language])
            
        logger.info(f"Running command: {' '.join(cmd)}")
        
        try:
            # Add paths for both cuDNN (system) and CUDA drivers (WSL2)
            env = os.environ.copy()
            current_ld_path = env.get('LD_LIBRARY_PATH', '')
            # /usr/lib/wsl/lib is critical for WSL2 CUDA support
            env['LD_LIBRARY_PATH'] = f"/usr/lib/wsl/lib:/usr/lib/x86_64-linux-gnu:{current_ld_path}"
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
            
            # The tool creates a file named <audio_filename>.json
            # Note: whisperx might change the filename slightly, usually it's just name.json
            base_name = os.path.splitext(os.path.basename(abs_audio_path))[0]
            json_output_path = os.path.join(output_dir, f"{base_name}.json")
            
            if not os.path.exists(json_output_path):
                raise RuntimeError(f"JSON output file not found at {json_output_path}")
                
            # Parse results
            with open(json_output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Clean up
            # os.remove(json_output_path) # Keep it for debugging for now? Or maybe remove.
            
            results = []
            for segment in data.get('segments', []):
                results.append({
                    "speaker_id": segment.get("speaker", "Unknown"),
                    "start_time": round(segment['start'], 3),
                    "end_time": round(segment['end'], 3),
                    "text": segment['text'].strip(),
                    "confidence": 1.0 # WhisperX doesn't always give per-segment confidence in simple json
                })
                
            return results
            
        except subprocess.CalledProcessError as e:
            error_msg = f"WhisperX execution failed with exit code {e.returncode}"
            if e.stderr:
                error_msg += f"\nSTDERR: {e.stderr}"
            if e.stdout:
                error_msg += f"\nSTDOUT: {e.stdout}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
