import logging
import json
import time
import base64
import tempfile
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import requests
import yaml

from ...core.providers import TranscriptionProvider, IngestSpecs, RefinementProvider
from ...core.models import JobConfiguration
from ...core.logger import APILogger
from . import OllamaConfig

logger = logging.getLogger("Amanu.Plugin.Ollama")

class OllamaClient:
    """Helper class for Ollama API interactions."""
    
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.base_url = config.base_url.rstrip('/')
        self.timeout = config.timeout
        self.session = requests.Session()
        self.session.timeout = self.timeout
    
    def get_loaded_models(self) -> List[Dict[str, Any]]:
        """Get list of models currently loaded in memory via /api/ps."""
        try:
            response = self.session.get(f"{self.base_url}/api/ps", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
            return []
        except Exception as e:
            logger.debug(f"Failed to check loaded models: {e}")
            return []

    def check_connection(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            # Short timeout for connection check
            response = self.session.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code != 200:
                logger.error(f"Ollama server at {self.base_url} returned status {response.status_code}")
                return False
            return True
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to Ollama at {self.base_url}. Please ensure 'ollama serve' is running.")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Ollama server: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """Get list of available models."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            logger.info(f"Pulling model {model_name} from Ollama...")
            response = self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            status = data.get('status', '')
                            logger.info(f"Pulling {model_name}: {status}")
                        except json.JSONDecodeError:
                            continue
                logger.info(f"Successfully pulled model {model_name}")
                return True
            else:
                logger.error(f"Failed to pull model {model_name}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    def ensure_model(self, model_name: str) -> bool:
        """Ensure model is available. Raises error if not found."""
        models = self.list_models()
        
        # Normalize model names for comparison
        # "llama3" should match "llama3:latest"
        target_model = model_name
        if ":" not in target_model:
            target_model = f"{target_model}:latest"
            
        if model_name in models or target_model in models:
            return True
            
        # Model not found - fail fast with helpful instructions
        raise RuntimeError(
            f"Model '{model_name}' not found on Ollama server.\n"
            f"Please run the following command in your terminal to download it:\n"
            f"  ollama pull {model_name}"
        )
    
    def generate(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using Ollama API."""
        try:
            data = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            data.update(kwargs)
            
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Generate request failed: {response.text}")
                raise Exception(f"Generate request failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"Error in generate: {e}")
            raise
    
    def chat(self, model: str, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Chat with Ollama model."""
        try:
            data = {
                "model": model,
                "messages": messages,
                "stream": False
            }
            data.update(kwargs)
            
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Chat request failed: {response.text}")
                raise Exception(f"Chat request failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise


class OllamaTranscriptionProvider(TranscriptionProvider):
    """Transcription provider for Ollama using Whisper and multimodal models."""
    
    def __init__(self, config: JobConfiguration, provider_config: OllamaConfig):
        super().__init__(config, provider_config)
        self.ollama_config = provider_config
        self.client = OllamaClient(provider_config)
        
        # Check connection
        if not self.client.check_connection():
            raise RuntimeError(f"Cannot connect to Ollama server at {provider_config.base_url}")
    
    @classmethod
    def get_ingest_specs(cls) -> IngestSpecs:
        return IngestSpecs(
            target_format="mp3",
            requires_upload=False,
            upload_target="none"
        )
    
    def transcribe(self, ingest_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Transcribe audio using Ollama models."""
        job_dir = kwargs.get("job_dir")
        api_logger = APILogger(job_dir) if job_dir else None
        
        local_file_path = ingest_result.get("local_file_path")
        if not local_file_path:
            raise ValueError("No local file path found in Ingest result for Ollama.")
        
        model_name = self.config.transcribe.model or self.ollama_config.transcription_model
        logger.info(f"Transcribing {local_file_path} with Ollama model: {model_name}")
        
        # Ensure model is available
        if not self.client.ensure_model(model_name):
            raise RuntimeError(f"Failed to ensure model {model_name} is available")
        
        # Determine transcription approach based on model type
        if "whisper" in model_name.lower():
            return self._transcribe_with_whisper(local_file_path, model_name, api_logger, **kwargs)
        elif "llava" in model_name.lower() or "bakllava" in model_name.lower():
            return self._transcribe_with_multimodal(local_file_path, model_name, api_logger, **kwargs)
        else:
            # Fallback to text-based approach
            return self._transcribe_with_text_prompt(local_file_path, model_name, api_logger, **kwargs)
    
    def _transcribe_with_whisper(self, audio_path: str, model_name: str, api_logger: Optional[APILogger] = None, **kwargs) -> Dict[str, Any]:
        """
        Attempt to transcribe using 'Whisper' named models in Ollama.
        
        NOTE: Despite the 'whisper' name, these models in Ollama are typically
        text-only LLMs that cannot process audio. Ollama's API does not support
        native audio input. Redirect to error handler.
        """
        logger.warning(
            f"Model '{model_name}' contains 'whisper' in name, but Ollama API "
            f"does not support native audio input. Redirecting to error handler."
        )
        # Redirect to error handler with helpful message
        return self._transcribe_with_text_prompt(audio_path, model_name, api_logger, **kwargs)
    
    def _transcribe_with_multimodal(self, audio_path: str, model_name: str, api_logger: Optional[APILogger] = None, **kwargs) -> Dict[str, Any]:
        """Transcribe using multimodal models via spectrogram conversion."""
        logger.info(f"Using multimodal model: {model_name}")
        
        try:
            # Convert audio to spectrogram
            spectrogram_path = self._audio_to_spectrogram(audio_path)
            
            # Read spectrogram as base64
            with open(spectrogram_path, "rb") as img_file:
                img_data = img_file.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # Create prompt for transcription
            language_instruction = ""
            if self.config.language != "auto":
                language_instruction = f"Transcribe in {self.config.language}."
            
            prompt = f"""This is a spectrogram of an audio file. Please analyze it and provide a transcription of the speech content.
{language_instruction}
Format your response as JSON:
{{
  "text": "the transcribed text",
  "segments": [
    {{"speaker": "Speaker A", "start": 0.0, "end": 10.0, "text": "first segment"}},
    {{"speaker": "Speaker B", "start": 10.0, "end": 20.0, "text": "second segment"}}
  ]
}}"""
            
            # Make request to Ollama
            if api_logger:
                api_logger.log("ollama", "generate", {"model": model_name, "prompt": prompt}, "PENDING")
            
            response = self.client.generate(
                model=model_name,
                prompt=prompt,
                images=[img_base64]
            )
            
            if api_logger:
                api_logger.log("ollama", "generate", {"model": model_name}, response)
            
            # Parse response
            response_text = response.get('response', '')
            
            try:
                # Try to parse JSON response
                result = json.loads(response_text)
                transcription_text = result.get('text', '')
                segments_data = result.get('segments', [])
                
                # Convert to expected format
                segments = []
                for seg in segments_data:
                    segments.append({
                        "speaker_id": seg.get('speaker', 'Speaker A'),
                        "start_time": seg.get('start', 0.0),
                        "end_time": seg.get('end', 0.0),
                        "text": seg.get('text', ''),
                        "confidence": 1.0
                    })
                
                if not segments and transcription_text:
                    # Fallback: single segment
                    segments = [{
                        "speaker_id": "Speaker A",
                        "start_time": 0.0,
                        "end_time": 0.0,
                        "text": transcription_text,
                        "confidence": 1.0
                    }]
                
            except json.JSONDecodeError:
                # Fallback: treat entire response as transcription
                segments = [{
                    "speaker_id": "Speaker A",
                    "start_time": 0.0,
                    "end_time": 0.0,
                    "text": response_text.strip(),
                    "confidence": 1.0
                }]
            
            # Clean up temporary spectrogram
            if os.path.exists(spectrogram_path):
                os.remove(spectrogram_path)
            
            return {
                "segments": segments,
                "tokens": {"input": 0, "output": len(response_text.split())},
                "cost_usd": 0.0,
                "analysis": {"language": self.config.language}
            }
            
        except Exception as e:
            if api_logger:
                api_logger.log("ollama", "generate", {"model": model_name}, None, error=str(e))
            logger.error(f"Multimodal transcription failed: {e}")
            raise
    
    def _transcribe_with_text_prompt(self, audio_path: str, model_name: str, api_logger: Optional[APILogger] = None, **kwargs) -> Dict[str, Any]:
        """
        Fallback for text-only models - raises an error with helpful guidance.
        
        Ollama does not currently support native audio input through its API.
        Models like 'karanchopda333/whisper' are text-only and cannot process audio files.
        """
        error_msg = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AUDIO TRANSCRIPTION NOT SUPPORTED                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ The model '{model_name}' cannot process audio files.                          
║                                                                               
║ Ollama currently does NOT support native audio input through its API.         
║ Text-only models (even those named 'whisper') cannot transcribe audio.        
║                                                                               
║ RECOMMENDED ALTERNATIVES:                                                     
║                                                                               
║ 1. Use WhisperX provider (local, free):                                       
║    transcribe:                                                                
║      provider: whisperx                                                       
║      model: large-v3                                                          
║                                                                               
║ 2. Use Gemini provider (cloud, paid):                                         
║    transcribe:                                                                
║      provider: gemini                                                         
║      model: gemini-2.0-flash                                                  
║                                                                               
║ 3. Use OpenRouter with Voxtral (cloud, paid):                                 
║    transcribe:                                                                
║      provider: openrouter                                                     
║      model: mistralai/voxtral-small-24b-2507                                  
║                                                                               
║ Run 'amanu setup' to configure a different provider.                          
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        logger.error(error_msg)
        raise RuntimeError(
            f"Model '{model_name}' does not support audio transcription. "
            f"Ollama API does not support native audio input. "
            f"Please use a different provider (whisperx, gemini, or openrouter)."
        )
    
    def _audio_to_spectrogram(self, audio_path: str) -> str:
        """Convert audio file to spectrogram image."""
        try:
            import librosa
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Load audio file
            y, sr = librosa.load(audio_path)
            
            # Create spectrogram
            plt.figure(figsize=(12, 8))
            S = librosa.feature.melspectrogram(y=y, sr=sr)
            S_db = librosa.power_to_db(S, ref=np.max)
            
            # Display and save
            librosa.display.specshow(S_db, sr=sr, x_axis='time', y_axis='mel')
            plt.axis('off')
            plt.tight_layout()
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            plt.savefig(temp_file.name, bbox_inches='tight', pad_inches=0, dpi=150)
            plt.close()
            
            return temp_file.name
            
        except ImportError as e:
            logger.error(f"Required libraries for spectrogram conversion not available: {e}")
            raise RuntimeError("Install librosa and matplotlib for multimodal transcription")
        except Exception as e:
            logger.error(f"Failed to convert audio to spectrogram: {e}")
            raise


class OllamaRefinementProvider(RefinementProvider):
    """Refinement provider for Ollama using text models."""
    
    def __init__(self, config: JobConfiguration, provider_config: OllamaConfig):
        super().__init__(config, provider_config)
        self.ollama_config = provider_config
        self.client = OllamaClient(provider_config)
        
        # Check connection
        if not self.client.check_connection():
            raise RuntimeError(f"Cannot connect to Ollama server at {provider_config.base_url}")
    
    def refine(self, input_data: Any, mode: str, language: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Refine and analyze transcribed text."""
        job_dir = kwargs.get("job_dir")
        api_logger = APILogger(job_dir) if job_dir else None
        
        model_name = self.config.refine.model or self.ollama_config.refinement_model
        custom_schema = kwargs.get("custom_schema", {})
        
        # Ensure model is available
        if not self.client.ensure_model(model_name):
            raise RuntimeError(f"Failed to ensure model {model_name} is available")
        
        # Check loaded models to debug VRAM state
        loaded_models = self.client.get_loaded_models()
        loaded_names = [m.get('name') for m in loaded_models]
        logger.info(f"Ollama loaded models: {loaded_names}")
        
        # Extract text content
        if mode == "standard":
            # Text mode - input is transcript data
            if isinstance(input_data, list):
                # Optimize transcript: use compact list of lists [Speaker, Text]
                optimized_transcript = []
                for segment in input_data:
                    speaker = segment.get("speaker_id", "Unknown")
                    text = segment.get("text", "")
                    optimized_transcript.append([speaker, text])
                transcript_text = json.dumps(optimized_transcript, ensure_ascii=False)
            else:
                transcript_text = str(input_data)
        else:
            # Direct mode - not supported for text-only refinement
            raise ValueError("Ollama refinement provider only supports 'standard' mode (text input)")
        
        # Determine target language
        if self.config.language != 'auto':
            target_language = self.config.language
        elif language:
            target_language = language
        else:
            target_language = 'Detect from transcript'
        
        # Build output schema
        output_schema = {}
        custom_instructions = ""
        
        if custom_schema:
            custom_instructions = "\n3. **Custom Analysis**:\n"
            for field, details in custom_schema.items():
                desc = details.get("description", "")
                structure = details.get("structure", f"string ({desc})")
                output_schema[field] = structure
                custom_instructions += f"   - **{field}**: {desc}\n"
        else:
            # Fallback to default schema
            output_schema = {
                "summary": "string (concise executive summary)",
                "key_takeaways": ["string"],
                "action_items": [
                    {"assignee": "string or null", "task": "string"}
                ],
                "quotes": [
                    {"speaker": "string", "text": "string"}
                ],
                "keywords": ["string"],
                "participants": ["string (real names)"],
                "topics": ["string"],
                "sentiment": "positive|neutral|negative",
                "language": "string (detected language code)"
            }
        
        schema_str = json.dumps(output_schema, indent=2)
        
        prompt = f"""You are a professional editor and analyst.
Transform the raw transcript into structured data and extract key intelligence.

INPUT TRANSCRIPT (Format: List of [Speaker, Text]):
{transcript_text}

INSTRUCTIONS:
1. **Analysis**:
   - Extract the data as requested in the OUTPUT SCHEMA.

2. **Language**: All output MUST be in {target_language}.
{custom_instructions}
OUTPUT SCHEMA (JSON):
{schema_str}

Please provide your analysis as valid JSON only, without any additional text or markdown formatting."""
        
        # Retry logic setup
        retry_max = getattr(self.ollama_config, 'retry_max', 3)
        retry_delay = getattr(self.ollama_config, 'retry_delay_seconds', 2)
        
        last_exception = None
        
        for attempt in range(retry_max):
            try:
                if attempt > 0:
                    wait_time = retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying Ollama generation (Attempt {attempt+1}/{retry_max}). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                
                logger.info(f"Refining with Ollama model: {model_name} (Attempt {attempt+1})")
                
                if api_logger:
                    api_logger.log("ollama", "generate", {"model": model_name, "prompt": prompt}, "PENDING")
                
                response = self.client.generate(
                    model=model_name,
                    prompt=prompt
                )
                
                if api_logger:
                    api_logger.log("ollama", "generate", {"model": model_name}, response)
                
                # Extract response
                response_text = response.get('response', '')
                
                # Parse JSON response
                # Handle markdown code blocks (```json ... ```)
                try:
                    # Strip markdown code blocks if present
                    text_to_parse = response_text.strip()
                    if text_to_parse.startswith("```"):
                        # Find the first newline after opening ```
                        first_newline = text_to_parse.find('\n')
                        if first_newline != -1:
                            # Find the closing ```
                            closing_marker = text_to_parse.rfind("```")
                            if closing_marker != -1 and closing_marker > first_newline:
                                # Extract content between markers
                                text_to_parse = text_to_parse[first_newline + 1:closing_marker].strip()
                    
                    result_data = json.loads(text_to_parse)
                    if isinstance(result_data, list):
                        result_data = result_data[0] if result_data else {}
                        
                    # Calculate tokens (rough estimation for local models)
                    input_tokens = len(prompt.split())
                    output_tokens = len(response_text.split())
                    
                    logger.info(f"Refinement complete: {input_tokens} input tokens, {output_tokens} output tokens")
                    
                    return {
                        "result": result_data,
                        "usage": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "cost_usd": 0.0  # Local models are free
                        }
                    }
                except json.JSONDecodeError as e:
                    # Log the error details
                    logger.warning(f"Failed to parse JSON response from model '{model_name}': {e}")
                    logger.debug(f"Response text preview: {response_text[:200]}")
                    
                    # Capture exception to raise if retries exhausted
                    last_exception = ValueError(
                        f"Model '{model_name}' returned invalid JSON response. "
                        f"JSON parse error: {e}. "
                        f"Response preview: {response_text[:200]}..."
                    )
                    # Continue to next retry
                    continue
                    
            except Exception as e:
                if api_logger:
                    api_logger.log("ollama", "generate", {"model": model_name}, None, error=str(e))
                logger.warning(f"Refinement attempt {attempt+1} failed: {e}")
                last_exception = e
        
        # If we get here, all retries failed
        logger.error(f"All {retry_max} retry attempts failed for Ollama refinement.")
        if last_exception:
            raise last_exception
        raise RuntimeError("Ollama refinement failed after multiple retries")