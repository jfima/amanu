import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

import google.generativeai as genai
from google.generativeai import caching
from google.api_core import exceptions

from ..core.providers import TranscriptionProvider, IngestSpecs, RefinementProvider
from ..core.models import JobConfiguration, GeminiConfig
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
             genai.configure(api_key=self.gemini_config.api_key)

    @classmethod
    def get_ingest_specs(cls) -> IngestSpecs:
        return IngestSpecs(
            target_format="ogg",
            requires_upload=True,
            upload_target="gemini_cache"
        )

    def transcribe(self, ingest_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
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

        # 1. Speaker Identification
        logger.info("Step 1: Identifying speakers...")
        speaker_prompt = """I have uploaded an audio file. Analyze it completely.
            IMPORTANT: 
            1. Identify all speakers and try to determine their real names from the conversation.
            2. Detect the primary language of the conversation.
            Output your analysis as a JSON object with this structure:
            {
                "speakers": ["Speaker Name 1", "Speaker Name 2"],
                "language": "Language Name" (e.g. "English", "Russian", "Spanish")
            }
            Reply ONLY with the JSON object."""
            
        response_1 = self._send_with_retry(chat, speaker_prompt)
        
        response_text = ""
        for chunk in response_1:
            response_text += chunk.text
            
        usage_metadata = response_1.usage_metadata if hasattr(response_1, 'usage_metadata') else None
        
        try:
            json_text = response_text.strip()
            if json_text.startswith("```json"): json_text = json_text[7:]
            if json_text.endswith("```"): json_text = json_text[:-3]
            analysis = json.loads(json_text.strip())
            detected_language = analysis.get("language", "English")
            logger.info(f"Detected language: {detected_language}")
        except Exception as e:
            logger.warning(f"Failed to parse analysis: {e}. Defaulting to English.")
            detected_language = "English"
            analysis = {}

        # 2. Transcription Loop
        logger.info("Step 2: Transcribing with JSONL streaming...")
        
        merged_transcript = []
        total_input_tokens = usage_metadata.prompt_token_count if usage_metadata else 0
        total_output_tokens = usage_metadata.candidates_token_count if usage_metadata else 0
        
        language_instruction = f"Transcribe in {detected_language}."
        if self.config.language != "auto":
             language_instruction = f"Transcribe in {self.config.language}."

        prompt = f"""
Excellent. Now transcribe the entire conversation from the beginning.
{language_instruction}
Format the output as JSONL (JSON Lines), where each line is a valid JSON object.
Use this schema for each line:
{{ 
  "speaker_id": (string - use the real name if identified, otherwise "Speaker A", "Speaker B"), 
  "start_time": (float, seconds), 
  "end_time": (float, seconds), 
  "text": (string, combined sentence or paragraph for the speaker), 
  "confidence": (float, 0.0-1.0)
}}
Instructions:
1. Use the real names you identified for speaker_id.
2. CRITICAL: Combine ALL consecutive speech from the same speaker into ONE segment.
3. Ensure valid JSON on each line.
4. Start generating now.
5. When you have transcribed the entire audio, output the token [END] on a new line.
"""
        
        is_complete = False
        turn_count = 0
        max_turns = 50
        
        while not is_complete and turn_count < max_turns:
            turn_count += 1
            if turn_count > 1:
                time.sleep(self.config.scribe.retry_delay_seconds)
            
            try:
                response = self._send_with_retry(chat, prompt)
                turn_text = ""
                for chunk in response:
                    if chunk.parts: turn_text += chunk.text
                
                lines, is_truncated, found_end_token = self._parse_jsonl(turn_text)
                merged_transcript.extend(lines)
                
                if hasattr(response, 'usage_metadata'):
                     usage = response.usage_metadata
                     total_input_tokens += usage.prompt_token_count
                     total_output_tokens += usage.candidates_token_count
                
                if is_truncated:
                     prompt = "Continue from where you left off. Output strictly JSONL."
                elif found_end_token or len(lines) == 0:
                     is_complete = True
                else:
                     prompt = "Continue. Output strictly JSONL. Do not repeat the last segment."
                     
            except Exception as e:
                logger.error(f"Error in turn {turn_count}: {e}")
                break

        # Calculate cost (simplified lookup)
        # TODO: Get pricing from config based on model name
        cost = 0.0 

        return {
            "segments": merged_transcript,
            "tokens": {"input": total_input_tokens, "output": total_output_tokens},
            "cost_usd": cost,
            "analysis": analysis
        }

    def _send_with_retry(self, chat, prompt: str):
        max_retries = self.config.scribe.retry_max
        delay = self.config.scribe.retry_delay_seconds
        
        for attempt in range(max_retries + 1):
            try:
                return chat.send_message(prompt, stream=True)
            except exceptions.ResourceExhausted:
                if attempt < max_retries:
                    time.sleep(delay)
                else:
                    raise
            except Exception:
                raise

    def _parse_jsonl(self, text: str):
        lines = []
        is_truncated = False
        found_end_token = False
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith("```"): continue
            try:
                lines.append(json.loads(line))
            except json.JSONDecodeError:
                if line.startswith("{"): is_truncated = True
                elif "[END]" in line: found_end_token = True
        return lines, is_truncated, found_end_token

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
             genai.configure(api_key=self.gemini_config.api_key)

    def refine(self, input_data: Any, mode: str, **kwargs) -> Dict[str, Any]:
        model_name = self.config.refine.model
        
        if mode == "standard":
            return self._process_text(input_data, model_name)
        else:
            return self._process_audio(input_data, model_name)

    def _process_text(self, transcript: list, model_name: str):
        # Optimize transcript for prompt: remove heavy metadata like token details
        optimized_transcript = []
        for segment in transcript:
            optimized_transcript.append({
                "speaker_id": segment.get("speaker_id", "Unknown"),
                "start_time": segment.get("start_time"),
                "text": segment.get("text", "")
            })
            
        transcript_text = json.dumps(optimized_transcript, indent=2, ensure_ascii=False)
        target_language = self.config.language if self.config.language != 'auto' else 'Detect from transcript'
        
        prompt = f"""
You are a professional editor and analyst.
Transform the raw transcript into structured data and extract key intelligence.

INPUT TRANSCRIPT:
{transcript_text}

INSTRUCTIONS:
1. **Clean Text (Literary Editing)**: 
   - Convert the spoken transcript into readable, written-style text.
   - Remove filler words, stuttering, and repetitions.
   - Improve grammar and sentence structure while preserving the original meaning and tone.
   - Output as plain text (NO Markdown formatting - that will be applied later).
   - If it's a dialogue, keep it as a script but polished. If it's a monologue/speech, turn it into flowing text.

2. **Analysis**:
   - **Summary**: A concise executive summary.
   - **Key Takeaways**: 3-5 most important points (bullet points).
   - **Action Items**: Tasks, assignments, or next steps mentioned (who, what, when).
   - **Quotes**: 3-5 most memorable or significant verbatim quotes.
   - **Keywords & Entities**: Extract relevant tags.

3. **Language**: All output MUST be in {target_language}.

OUTPUT SCHEMA (JSON):
{{
  "clean_text": "string (plain text, no markdown)",
  "summary": "string (concise executive summary)",
  "key_takeaways": ["string"],
  "action_items": [
    {{ "assignee": "string or null", "task": "string" }}
  ],
  "quotes": [
    {{ "speaker": "string", "text": "string" }}
  ],
  "keywords": ["string"],
  "participants": ["string (real names)"],
  "topics": ["string"],
  "sentiment": "positive|neutral|negative",
  "language": "string (detected language code)"
}}
"""
        return self._generate_content(model_name, prompt)

    def _process_audio(self, ingest_data: Dict, model_name: str):
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

        target_language = self.config.language if self.config.language != 'auto' else 'Detect from audio'
        
        prompt = f"""
You are a professional analyst. Listen to the audio and extract structured intelligence.

INSTRUCTIONS:
1. **Analysis**:
   - **Summary**: A detailed summary of the conversation.
   - **Key Takeaways**: 3-5 most important points.
   - **Action Items**: Tasks or next steps mentioned.
   - **Quotes**: Key quotes verbatim.
   
2. **Clean Text (Overview)**: 
   - Since this is direct analysis, provide a high-level structured overview or a polished summary of key segments.
   - Output as plain text (NO Markdown - formatting will be applied later).

3. **Language**: All output MUST be in {target_language}.

OUTPUT SCHEMA (JSON):
{{
  "clean_text": "string (plain text overview)",
  "summary": "string (concise summary)",
  "key_takeaways": ["string"],
  "action_items": [
    {{ "assignee": "string or null", "task": "string" }}
  ],
  "quotes": [
    {{ "speaker": "string", "text": "string" }}
  ],
  "keywords": ["string"],
  "participants": ["string (real names)"],
  "topics": ["string"],
  "sentiment": "positive|neutral|negative",
  "language": "string (detected language code)"
}}
"""
        if cache_name:
             return self._generate_content_with_model(model, prompt)
        else:
             return self._generate_content_with_model(model, [file_obj, prompt])

    def _generate_content(self, model_name: str, prompt: Any):
        model = genai.GenerativeModel(model_name)
        return self._generate_content_with_model(model, prompt)

    def _generate_content_with_model(self, model, prompt):
        generation_config = {
            "temperature": 0.3,
            "response_mime_type": "application/json"
        }
        
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
        
        # Parse response to dict
        try:
             result_data = json.loads(response.text)
             if isinstance(result_data, list):
                 result_data = result_data[0] if result_data else {}
        except Exception:
             result_data = {}

        return {
            "result": result_data,
            "usage": response.usage_metadata
        }
