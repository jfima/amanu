import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

import google.generativeai as genai
from google.generativeai import caching
from google.api_core import exceptions

from ...core.providers import TranscriptionProvider, IngestSpecs, RefinementProvider
from ...core.models import JobConfiguration
from ...core.logger import APILogger
from . import GeminiConfig
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger("Amanu.Plugin.Gemini")

class GeminiProvider(TranscriptionProvider):
    def __init__(self, config: JobConfiguration, provider_config: GeminiConfig):
        super().__init__(config, provider_config)
        self.gemini_config = provider_config
        
        if not self.gemini_config or not self.gemini_config.api_key:
             # Try env var or fail
             import os
             api_key = os.environ.get("GEMINI_API_KEY")
             if not api_key:
                 raise ValueError("Gemini API Key not found in config or environment.")
             genai.configure(api_key=api_key)
        else:
             genai.configure(api_key=self.gemini_config.api_key.get_secret_value())

    @classmethod
    def get_ingest_specs(cls) -> IngestSpecs:
        return IngestSpecs(
            target_format="ogg",
            requires_upload=True,
            upload_target="gemini_cache"
        )

    def transcribe(self, ingest_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        job_dir = kwargs.get("job_dir")
        api_logger = APILogger(job_dir) if job_dir else None
        
        gemini_data = ingest_result.get("gemini", {})
        cache_name = gemini_data.get("cache_name")
        file_name = gemini_data.get("file_name")
        
        model_name = self.config.transcribe.model
        
        # Initialize model
        if cache_name:
            logger.info(f"Using cached content: {cache_name}")
            try:
                cache = caching.CachedContent.get(cache_name)
                model = genai.GenerativeModel.from_cached_content(cached_content=cache)
                chat = model.start_chat(history=[])
            except Exception as e:
                logger.error(f"Failed to load cache {cache_name}: {e}")
                raise
        elif file_name:
            logger.info(f"Using direct file input (no cache): {file_name}")
            try:
                model = genai.GenerativeModel(model_name)
                file_obj = genai.get_file(file_name)
                chat = model.start_chat(history=[{
                    "role": "user",
                    "parts": [file_obj]
                }])
            except Exception as e:
                logger.error(f"Failed to load file {file_name}: {e}")
                raise
        else:
            raise ValueError("No valid cache or file found in Ingest result for Gemini.")

        # 1. Speaker Identification & Transcription (Merged)
        logger.info("Step 1: Transcribing with merged speaker ID and compact JSONL...")
        
        # We no longer do a separate speaker ID step.
        detected_language = "auto" # Will be detected in the main loop
        analysis = {}


        # 2. Transcription Loop
        logger.info("Step 2: Transcribing with JSONL streaming...")
        
        merged_transcript = []
        total_input_tokens = 0 # usage_metadata.prompt_token_count if usage_metadata else 0
        total_output_tokens = 0 # usage_metadata.candidates_token_count if usage_metadata else 0
        
        language_instruction = ""
        if self.config.language != "auto":
             language_instruction = f"Transcribe in {self.config.language}."

        prompt = f"""
I have uploaded an audio file. Analyze it completely and transcribe the entire conversation.
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
        
        is_complete = False
        turn_count = 0
        max_turns = 50
        
        while not is_complete and turn_count < max_turns:
            turn_count += 1
            if turn_count > 1:
                time.sleep(self.config.scribe.retry_delay_seconds)
            
            # Prepare generation config
            generation_config = {"response_mime_type": "application/json"}
            
            # Find model config to get max output tokens
            if self.gemini_config and self.gemini_config.models:
                for m in self.gemini_config.models:
                    if m.name == model_name:
                        generation_config["max_output_tokens"] = m.context_window.output_tokens
                        break

            try:
                logger.info(f"--- SENDING PROMPT (Turn {turn_count}) ---\n{prompt}\n------------------------------------------")
                response = self._send_with_retry(chat, prompt, timeout=self.config.scribe.timeout, generation_config=generation_config, api_logger=api_logger)
                turn_text = ""
                for chunk in response:
                    if chunk.parts: turn_text += chunk.text
                
                logger.info(f"--- RECEIVED RESPONSE (Turn {turn_count}) ---\n{turn_text}\n---------------------------------------------")

                # Debug logging
                if not turn_text.strip():
                    logger.warning(f"Turn {turn_count}: Received empty response from model.")

                lines, is_truncated, found_end_token, turn_analysis = self._parse_jsonl(turn_text)
                
                if turn_analysis:
                    analysis.update(turn_analysis)
                    if "language" in turn_analysis:
                        detected_language = turn_analysis["language"]
                        logger.info(f"Detected language: {detected_language}")
                
                # Only warn if we got text but couldn't parse ANY lines AND it's not just truncation
                if not lines and turn_text.strip() and not is_truncated:
                    logger.warning(f"Turn {turn_count}: Failed to parse any JSON lines from response. Raw text:\n{turn_text[:500]}")

                merged_transcript.extend(lines)
                
                # Checkpoint save
                if job_dir:
                    try:
                        transcripts_dir = Path(job_dir) / "transcripts"
                        transcripts_dir.mkdir(parents=True, exist_ok=True)
                        partial_file = transcripts_dir / "raw_transcript_partial.json"
                        with open(partial_file, "w") as f:
                            json.dump(merged_transcript, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        logger.warning(f"Failed to save partial transcript: {e}")

                logger.info(f"Turn {turn_count}: Parsed {len(lines)} segments. Truncated: {is_truncated}, End token: {found_end_token}")
                
                # Log content for short turns or first few segments for debugging
                if len(lines) <= 3:
                    for i, line in enumerate(lines):
                        logger.info(f"  Segment {i+1}: [{line.get('speaker_id')}] {line.get('text')[:100]}...")
                elif len(lines) > 0:
                     # Log first segment just in case
                     logger.debug(f"  First segment: [{lines[0].get('speaker_id')}] {lines[0].get('text')[:100]}...")

                if hasattr(response, 'usage_metadata'):
                     usage = response.usage_metadata
                     total_input_tokens += usage.prompt_token_count
                     total_output_tokens += usage.candidates_token_count
                
                # Loop detection: Check if timestamps reset significantly
                if lines and merged_transcript:
                    # Get end time of the last segment BEFORE this turn
                    last_segment_end = merged_transcript[-len(lines)-1].get("end_time", 0.0) if len(merged_transcript) > len(lines) else 0.0
                    
                    # Get start time of the first segment of THIS turn
                    current_start = lines[0].get("start_time", 0.0)
                    
                    # If current start is significantly less than last end (e.g. < 50%), it's likely a restart
                    # We use a loose threshold because timestamps can be messy
                    if last_segment_end > 1.0 and current_start < last_segment_end * 0.5:
                        logger.warning(f"Detected potential loop/restart (Time reset: {last_segment_end} -> {current_start}). Stopping transcription.")
                        is_complete = True
                        # Remove the duplicate lines we just added
                        merged_transcript = merged_transcript[:-len(lines)]
                        break

                if found_end_token:
                     is_complete = True
                elif is_truncated:
                     prompt = """Continue transcription from where you stopped.
IMPORTANT: Start with a COMPLETE JSON object on a new line.
Do not try to continue the truncated line - start fresh with the next segment.
Output strictly JSONL format."""
                elif len(lines) == 0:
                     # If we got no lines and no end token, but text was generated, it might be a refusal or error.
                     # But if we just continue, we might loop.
                     # Let's try to continue once more, but if it happens again, we should probably stop?
                     # For now, existing logic was "is_complete = True" if len(lines) == 0.
                     # Let's keep that behavior for empty responses that aren't truncated.
                     is_complete = True

                else:
                     prompt = """You stopped without outputting [END].
If you have finished the entire audio, output [END] immediately.
If there is more audio, continue transcription from the last timestamp.
Do NOT restart from the beginning.
Output strictly JSONL format."""
                     
            except Exception as e:
                logger.error(f"Error in turn {turn_count}: {e}")
                # Re-raise to stop the pipeline, as partial results are already saved to disk
                raise

        # Calculate cost (simplified lookup)
        # TODO: Get pricing from config based on model name
        cost = 0.0 

        return {
            "segments": merged_transcript,
            "tokens": {"input": total_input_tokens, "output": total_output_tokens},
            "cost_usd": cost,
            "analysis": analysis
        }

    def _send_with_retry(self, chat, prompt: str, timeout: int = 600, generation_config: Optional[Dict] = None, api_logger: Optional[APILogger] = None):
        max_retries = self.config.scribe.retry_max
        delay = self.config.scribe.retry_delay_seconds
        
        for attempt in range(max_retries + 1):
            try:
                response = chat.send_message(prompt, stream=True, request_options={'timeout': timeout}, generation_config=generation_config)
                
                # Consume stream to get text and usage for logging
                # Note: Consuming the stream here means we can't consume it again outside?
                # Actually, response is an iterator. If we iterate it here, we exhaust it.
                # But we return 'response' which is the iterator.
                # Wait, if I iterate here to log, I can't return it for the caller to iterate.
                # I should gather the response parts here, log, and then return a new iterator or the gathered parts.
                # Or, simpler: Just log the request here, and log the response in the caller after consumption.
                # But the caller consumes it chunk by chunk.
                # Let's log the REQUEST here. The caller logs the RESPONSE text.
                
                if api_logger:
                    api_logger.log("gemini", "chat.send_message", prompt, "STREAM_RESPONSE")
                    
                return response
                
            except exceptions.ResourceExhausted:
                if attempt < max_retries:
                    logger.warning(f"Resource exhausted (429). Retrying in {delay}s (Attempt {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                else:
                    logger.error(f"Resource exhausted (429) after {max_retries} retries.")
                    if api_logger:
                         api_logger.log("gemini", "chat.send_message", prompt, None, error="ResourceExhausted")
                    raise
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                if api_logger:
                     api_logger.log("gemini", "chat.send_message", prompt, None, error=str(e))
                raise

    def _parse_jsonl(self, text: str):
        lines = []
        is_truncated = False
        found_end_token = False
        analysis = {}
        
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith("```"): continue
            try:
                obj = json.loads(line)
                
                # Check for [END] token
                if isinstance(obj, str) and obj == "[END]":
                    found_end_token = True
                    continue
                if isinstance(obj, dict) and (obj.get("speaker_id") == "[END]" or obj.get("text") == "[END]"):
                    found_end_token = True
                    continue
                    
                # Check for metadata object (dict with "speakers" or "language")
                if isinstance(obj, dict):
                    if "speakers" in obj or "language" in obj:
                        analysis = obj
                        continue
                    # Fallback for old format or if model outputs dicts despite instructions
                    lines.append(obj)
                    continue

                # Check for compact array format: [start, end, speaker, text]
                if isinstance(obj, list) and len(obj) >= 4:
                    segment = {
                        "start_time": obj[0],
                        "end_time": obj[1],
                        "speaker_id": obj[2],
                        "text": obj[3]
                    }
                    lines.append(segment)
                else:
                    logger.debug(f"Skipping unrecognized JSON structure: {line[:100]}")

            except json.JSONDecodeError as e:
                # Check for [END] token first
                if "[END]" in line:
                    found_end_token = True
                # Check if line looks like truncated JSON
                elif line.startswith("[") or line.startswith("{"):
                    is_truncated = True
                    logger.debug(f"Detected truncated JSON line (will continue): {line[:100]}...")
                else:
                    # Log non-JSON content that's not truncation or end token
                    logger.debug(f"Skipping non-JSON line: {line[:100]}")
                    
        return lines, is_truncated, found_end_token, analysis

class GeminiRefinementProvider(RefinementProvider):
    def __init__(self, config: JobConfiguration, provider_config: GeminiConfig):
        super().__init__(config, provider_config)
        self.gemini_config = provider_config
        
        if not self.gemini_config or not self.gemini_config.api_key:
             import os
             api_key = os.environ.get("GEMINI_API_KEY")
             if not api_key:
                 raise ValueError("Gemini API Key not found.")
             genai.configure(api_key=api_key)
        else:
             genai.configure(api_key=self.gemini_config.api_key.get_secret_value())

    def refine(self, input_data: Any, mode: str, language: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        model_name = self.config.refine.model
        custom_schema = kwargs.get("custom_schema")
        job_dir = kwargs.get("job_dir")
        api_logger = APILogger(job_dir) if job_dir else None
        
        if mode == "standard":
            return self._process_text(input_data, model_name, language, custom_schema, api_logger)
        else:
            return self._process_audio(input_data, model_name, language, custom_schema, api_logger)

    def _process_text(self, transcript: list, model_name: str, language: Optional[str] = None, custom_schema: Dict = None, api_logger: Optional[APILogger] = None):
        # Optimize transcript for prompt: use compact list of lists [Speaker, Text]
        # Timestamps are generally not needed for high-level refinement/summary
        optimized_transcript = []
        for segment in transcript:
            speaker = segment.get("speaker_id", "Unknown")
            text = segment.get("text", "")
            optimized_transcript.append([speaker, text])
            
        transcript_text = json.dumps(optimized_transcript, ensure_ascii=False)
        
        # Determine target language
        # Priority: 1. Config (if not auto) 2. Detected Language (passed arg) 3. "Detect from transcript"
        if self.config.language != 'auto':
            target_language = self.config.language
        elif language:
            target_language = language
        else:
            target_language = 'Detect from transcript'
        
        # Base Schema - Minimal default if no custom schema provided
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
                    { "assignee": "string or null", "task": "string" }
                ],
                "quotes": [
                    { "speaker": "string", "text": "string" }
                ],
                "keywords": ["string"],
                "participants": ["string (real names)"],
                "topics": ["string"],
                "sentiment": "positive|neutral|negative",
                "language": "string (detected language code)"
             }

        schema_str = json.dumps(output_schema, indent=2)

        prompt = f"""
You are a professional editor and analyst.
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
        return self._generate_content(model_name, prompt, api_logger)

    def _process_audio(self, ingest_data: Dict, model_name: str, language: Optional[str] = None, custom_schema: Dict = None, api_logger: Optional[APILogger] = None):
        gemini_data = ingest_data.get("gemini", {})
        cache_name = gemini_data.get("cache_name")
        file_name = gemini_data.get("file_name")
        
        model = genai.GenerativeModel(model_name)
        
        if cache_name:
            logger.info(f"Using cached audio: {cache_name}")
            cache = caching.CachedContent.get(cache_name)
            model = genai.GenerativeModel.from_cached_content(cached_content=cache)
        elif file_name:
            logger.info(f"Using direct audio file: {file_name}")
            file_obj = genai.get_file(file_name)
        else:
            raise ValueError("No audio source found in Ingest data.")

        # Determine target language
        if self.config.language != 'auto':
            target_language = self.config.language
        elif language:
            target_language = language
        else:
            # Default language when not specified
            target_language = 'en'
            logger.warning(f"Language not specified, using default: {target_language}")
        
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
             # Fallback to default schema if no custom fields defined
             output_schema = {
                "summary": "string (concise summary)",
                "key_takeaways": ["string"],
                "action_items": [
                    { "assignee": "string or null", "task": "string" }
                ],
                "quotes": [
                    { "speaker": "string", "text": "string" }
                ],
                "keywords": ["string"],
                "participants": ["string (real names)"],
                "topics": ["string"],
                "sentiment": "positive|neutral|negative",
                "language": "string (detected language code)"
             }

        schema_str = json.dumps(output_schema, indent=2)

        prompt = f"""
You are a professional analyst. Listen to the audio and extract structured intelligence.

INSTRUCTIONS:
1. **Analysis**:
   - Extract the data as requested in the OUTPUT SCHEMA.

2. **Language**: All output MUST be in {target_language}.
{custom_instructions}
OUTPUT SCHEMA (JSON):
{schema_str}
"""
        if cache_name:
             return self._generate_content_with_model(model, prompt, api_logger)
        else:
             return self._generate_content_with_model(model, [file_obj, prompt], api_logger)

    def _generate_content(self, model_name: str, prompt: Any, api_logger: Optional[APILogger] = None):
        model = genai.GenerativeModel(model_name)
        return self._generate_content_with_model(model, prompt, api_logger)

    def _generate_content_with_model(self, model, prompt, api_logger: Optional[APILogger] = None):
        # Log prompt
        log_prompt = prompt
        if isinstance(prompt, list):
             log_prompt = [p for p in prompt if isinstance(p, str)]
        
        logger.info(f"--- SENDING REFINEMENT PROMPT ---\n{log_prompt}\n---------------------------------")

        generation_config = {
            "temperature": 0.3,
            "response_mime_type": "application/json"
        }
        
        try:
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            
            if api_logger:
                api_logger.log("gemini", "generate_content", log_prompt, response.text)
                
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            if api_logger:
                 api_logger.log("gemini", "generate_content", log_prompt, None, error=str(e))
            raise

        try:
            logger.info(f"--- RECEIVED REFINEMENT RESPONSE ---\n{response.text}\n------------------------------------")
        except Exception as e:
            logger.warning(f"Could not log response text (maybe blocked?): {e}")

        # Parse response to dict
        try:
             result_data = json.loads(response.text)
             if isinstance(result_data, list):
                 result_data = result_data[0] if result_data else {}
        except json.JSONDecodeError as e:
            # Log the error details
            logger.error(f"Failed to parse JSON response from Gemini model")
            logger.error(f"Response text (first 500 chars): {response.text[:500]}")
            logger.debug(f"Full response: {response.text}")
            logger.debug(f"JSON decode error: {e}")
            
            # Raise a proper exception so it's recorded in _job.json
            raise ValueError(
                f"Gemini model returned invalid JSON response. "
                f"JSON parse error: {e}. "
                f"Response preview: {response.text[:200]}..."
            )

        return {
            "result": result_data,
            "usage": response.usage_metadata
        }
