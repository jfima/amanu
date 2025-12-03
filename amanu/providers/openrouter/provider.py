import logging
import json
import base64
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import requests

from openai import OpenAI

from ...core.providers import TranscriptionProvider, IngestSpecs, RefinementProvider
from ...core.models import JobConfiguration
from . import OpenRouterConfig

logger = logging.getLogger("Amanu.Plugin.OpenRouter")

class OpenRouterTranscriptionProvider(TranscriptionProvider):
    """Transcription provider for OpenRouter using multimodal chat or Whisper API."""
    
    def __init__(self, config: JobConfiguration, provider_config: OpenRouterConfig):
        super().__init__(config, provider_config)
        self.openrouter_config = provider_config
        
        if not self.openrouter_config or not self.openrouter_config.api_key:
            import os
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OpenRouter API Key not found in config or environment.")
        else:
            api_key = self.openrouter_config.api_key.get_secret_value()
        
        # Initialize OpenAI client with OpenRouter base URL
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": self.openrouter_config.site_url or "https://github.com/yourusername/amanu",
                "X-Title": self.openrouter_config.app_name or "amanu"
            }
        )
    
    @classmethod
    def get_ingest_specs(cls) -> IngestSpecs:
        return IngestSpecs(
            target_format="mp3",
            requires_upload=False,
            upload_target="none"
        )
    
    def transcribe(self, ingest_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Transcribe audio using OpenRouter models."""
        local_file_path = ingest_result.get("local_file_path")
        if not local_file_path:
            raise ValueError("No local file path found in Ingest result for OpenRouter.")
        
        model_name = self.config.transcribe.model or "mistralai/voxtral-small-24b-2507"
        logger.info(f"Transcribing {local_file_path} with OpenRouter model: {model_name}")
        
        # Determine if this is a Whisper model or multimodal chat model
        if "whisper" in model_name.lower():
            return self._transcribe_with_whisper(local_file_path, model_name, **kwargs)
        else:
            return self._transcribe_with_chat(local_file_path, model_name, **kwargs)
    
    def _transcribe_with_whisper(self, audio_path: str, model_name: str, **kwargs) -> Dict[str, Any]:
        """Transcribe using Whisper-style audio transcriptions endpoint."""
        logger.info(f"Using Whisper API endpoint for {model_name}")
        
        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=model_name,
                    file=audio_file,
                    response_format="verbose_json"
                )
            
            # Extract segments from Whisper response
            segments = []
            if hasattr(response, 'segments') and response.segments:
                for seg in response.segments:
                    segments.append({
                        "speaker_id": "Speaker A",
                        "start_time": seg.get('start', 0.0),
                        "end_time": seg.get('end', 0.0),
                        "text": seg.get('text', ''),
                        "confidence": 1.0
                    })
            elif hasattr(response, 'text'):
                # Fallback: single segment with full text
                segments.append({
                    "speaker_id": "Speaker A",
                    "start_time": 0.0,
                    "end_time": 0.0,
                    "text": response.text,
                    "confidence": 1.0
                })
            
            # Get cost from generation endpoint
            generation_id = getattr(response, 'id', None)
            cost = self._get_generation_cost(generation_id) if generation_id else 0.0
            
            return {
                "segments": segments,
                "tokens": {"input": 0, "output": 0},
                "cost_usd": cost,
                "analysis": {"language": getattr(response, 'language', 'auto')}
            }
        
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise
    
    def _transcribe_with_chat(self, audio_path: str, model_name: str, **kwargs) -> Dict[str, Any]:
        """Transcribe using multimodal chat completions with audio input."""
        logger.info(f"Using Chat Completions API for multimodal model: {model_name}")
        
        # Read and encode audio file
        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Determine audio format from file extension
        audio_format = Path(audio_path).suffix.lstrip('.')
        
        # Build language instruction
        language_instruction = ""
        if self.config.language != "auto":
            language_instruction = f"Transcribe in {self.config.language}."
        
        # Construct prompt for transcription
        prompt = f"""I have uploaded an audio file. Analyze it completely and transcribe the entire conversation.
{language_instruction}

Output Format: JSONL (JSON Lines).
1. The FIRST line must be a metadata object:
   {{ "speakers": ["Name1", "Name2"], "language": "Language" }}
   
2. All subsequent lines must be compact JSON arrays representing segments:
   [start_time, end_time, "Speaker Name", "Text content"]

Schema details:
- start_time: float (seconds)
- end_time: float (seconds)
- Speaker Name: string (real name if identified, else "Speaker A")
- Text content: string (combined paragraph)

Instructions:
1. Identify speakers and use their real names.
2. CRITICAL: Combine ALL consecutive speech from the same speaker into ONE segment (paragraph). Do not split into single sentences.
3. Ensure valid JSON on each line.
4. When finished, output [END] on a new line.
"""
        
        # Make API call with audio in messages
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": audio_format
                            }
                        }
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.1
            )
            
            # Extract response text
            response_text = response.choices[0].message.content if response.choices else ""
            
            # Parse JSONL response
            segments, analysis = self._parse_jsonl_response(response_text)
            
            # Get usage and cost
            usage = response.usage if hasattr(response, 'usage') else None
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            
            # Get cost from generation endpoint
            generation_id = getattr(response, 'id', None)
            cost = self._get_generation_cost(generation_id) if generation_id else 0.0
            
            logger.info(f"Transcription complete: {len(segments)} segments, {input_tokens} input tokens, {output_tokens} output tokens, ${cost:.6f}")
            
            return {
                "segments": segments,
                "tokens": {"input": input_tokens, "output": output_tokens},
                "cost_usd": cost,
                "analysis": analysis
            }
        
        except Exception as e:
            logger.error(f"Chat-based transcription failed: {e}")
            raise
    
    def _parse_jsonl_response(self, text: str) -> tuple[List[Dict], Dict]:
        """Parse JSONL response from the model."""
        segments = []
        analysis = {}
        
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith("```"):
                continue
            
            try:
                obj = json.loads(line)
                
                # Check for [END] token
                if isinstance(obj, str) and obj == "[END]":
                    continue
                
                # Check for metadata object
                if isinstance(obj, dict):
                    if "speakers" in obj or "language" in obj:
                        analysis = obj
                        continue
                    # Fallback for dict format
                    segments.append(obj)
                    continue
                
                # Check for compact array format: [start, end, speaker, text]
                if isinstance(obj, list) and len(obj) >= 4:
                    segment = {
                        "start_time": obj[0],
                        "end_time": obj[1],
                        "speaker_id": obj[2],
                        "text": obj[3]
                    }
                    segments.append(segment)
            
            except json.JSONDecodeError:
                if "[END]" in line:
                    continue
                logger.debug(f"Skipping non-JSON line: {line[:100]}")
        
        return segments, analysis
    
    def _get_generation_cost(self, generation_id: str) -> float:
        """Fetch the actual cost of a generation from OpenRouter API."""
        if not generation_id:
            return 0.0
        
        try:
            api_key = self.openrouter_config.api_key.get_secret_value() if self.openrouter_config.api_key else None
            if not api_key:
                import os
                api_key = os.environ.get("OPENROUTER_API_KEY")
            
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            
            response = requests.get(
                f"https://openrouter.ai/api/v1/generation?id={generation_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                cost = data.get("data", {}).get("total_cost", 0.0)
                logger.info(f"Retrieved cost for generation {generation_id}: ${cost:.6f}")
                return cost
            else:
                logger.warning(f"Failed to retrieve cost for generation {generation_id}: {response.status_code}")
                return 0.0
        
        except Exception as e:
            logger.warning(f"Error retrieving generation cost: {e}")
            return 0.0


class OpenRouterRefinementProvider(RefinementProvider):
    """Refinement provider for OpenRouter using text models."""
    
    def __init__(self, config: JobConfiguration, provider_config: OpenRouterConfig):
        super().__init__(config, provider_config)
        self.openrouter_config = provider_config
        
        if not self.openrouter_config or not self.openrouter_config.api_key:
            import os
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OpenRouter API Key not found in config or environment.")
        else:
            api_key = self.openrouter_config.api_key.get_secret_value()
        
        # Initialize OpenAI client with OpenRouter base URL
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": self.openrouter_config.site_url or "https://github.com/yourusername/amanu",
                "X-Title": self.openrouter_config.app_name or "amanu"
            }
        )
    
    def refine(self, input_data: Any, mode: str, language: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Refine and analyze transcribed text."""
        model_name = self.config.refine.model or "google/gemini-2.0-flash-lite-001"
        custom_schema = kwargs.get("custom_schema", {})
        
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
            raise ValueError("OpenRouter refinement provider only supports 'standard' mode (text input)")
        
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
"""
        
        try:
            logger.info(f"Refining with OpenRouter model: {model_name}")
            
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Extract response
            response_text = response.choices[0].message.content if response.choices else "{}"
            
            # Parse JSON response
            try:
                result_data = json.loads(response_text)
                if isinstance(result_data, list):
                    result_data = result_data[0] if result_data else {}
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {response_text[:500]}")
                result_data = {}
            
            # Get usage and cost
            usage = response.usage if hasattr(response, 'usage') else None
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            
            # Get cost from generation endpoint
            generation_id = getattr(response, 'id', None)
            cost = self._get_generation_cost(generation_id) if generation_id else 0.0
            
            logger.info(f"Refinement complete: {input_tokens} input tokens, {output_tokens} output tokens, ${cost:.6f}")
            
            return {
                "result": result_data,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": cost
                }
            }
        
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            raise
    
    def _get_generation_cost(self, generation_id: str) -> float:
        """Fetch the actual cost of a generation from OpenRouter API."""
        if not generation_id:
            return 0.0
        
        try:
            api_key = self.openrouter_config.api_key.get_secret_value() if self.openrouter_config.api_key else None
            if not api_key:
                import os
                api_key = os.environ.get("OPENROUTER_API_KEY")
            
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            
            response = requests.get(
                f"https://openrouter.ai/api/v1/generation?id={generation_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                cost = data.get("data", {}).get("total_cost", 0.0)
                logger.info(f"Retrieved cost for generation {generation_id}: ${cost:.6f}")
                return cost
            else:
                logger.warning(f"Failed to retrieve cost for generation {generation_id}: {response.status_code}")
                return 0.0
        
        except Exception as e:
            logger.warning(f"Error retrieving generation cost: {e}")
            return 0.0
