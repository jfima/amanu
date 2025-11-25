import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime

import google.generativeai as genai
from google.generativeai import caching
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import BaseStage
from ..core.models import JobMeta, StageName

logger = logging.getLogger("Amanu.Refine")

class RefineStage(BaseStage):
    stage_name = StageName.REFINE

    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Refine transcript and generate structured data (Enriched Context).
        Supports two modes:
        1. Standard: Input is raw_transcript.json (Text)
        2. Direct: Input is ingest.json (Audio URI) - "Direct Analysis"
        """
        # Configure Gemini
        self._configure_gemini(meta.configuration.refine.name)
        
        # Determine Input Mode
        raw_transcript_file = job_dir / "transcripts" / "raw_transcript.json"
        ingest_file = job_dir / "_stages" / "ingest.json"
        
        input_data = None
        mode = "unknown"
        
        if raw_transcript_file.exists():
            logger.info("Mode: Standard (Text Analysis)")
            mode = "standard"
            with open(raw_transcript_file, "r") as f:
                input_data = json.load(f)
        elif ingest_file.exists():
            logger.info("Mode: Direct Analysis (Audio Processing)")
            mode = "direct"
            with open(ingest_file, "r") as f:
                input_data = json.load(f)
        else:
            raise FileNotFoundError("No input found. Run Scribe (for Standard) or Ingest (for Direct).")

        # Generate Enriched Context
        if mode == "standard":
            response = self._process_text(input_data, meta)
        else:
            response = self._process_audio(input_data, meta)
            
        # Parse Response
        try:
            result_data = json.loads(response.text)
            if isinstance(result_data, list):
                logger.warning("Model returned a list instead of a dict. Using first item.")
                result_data = result_data[0] if result_data else {}
        except json.JSONDecodeError:
            logger.error("Failed to parse Refine JSON response.")
            raise ValueError("Model failed to return valid JSON.")

        # Save Enriched Context
        context_file = job_dir / "transcripts" / "enriched_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(context_file, "w") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
            
        # Update Meta
        usage = response.usage_metadata
        meta.processing.total_tokens.input += usage.prompt_token_count
        meta.processing.total_tokens.output += usage.candidates_token_count
        
        meta.processing.request_count += 1
        meta.processing.steps.append({
            "stage": "refine",
            "step": "analysis",
            "mode": mode,
            "timestamp": datetime.now().isoformat(),
            "model": meta.configuration.refine.name,
            "tokens": {
                "input": usage.prompt_token_count,
                "output": usage.candidates_token_count
            }
        })
        
        # Calculate cost
        pricing = meta.configuration.refine.cost_per_1M_tokens_usd
        cost = (usage.prompt_token_count / 1_000_000 * pricing.input) + \
               (usage.candidates_token_count / 1_000_000 * pricing.output)
        meta.processing.total_cost_usd += cost
        
        return {
            "enriched_context_file": str(context_file),
            "mode": mode,
            "model": meta.configuration.refine.name,
            "tokens": {
                "input": usage.prompt_token_count,
                "output": usage.candidates_token_count
            },
            "cost_usd": cost
        }

    def _process_text(self, transcript: list, meta: JobMeta):
        """Process text transcript."""
        transcript_text = json.dumps(transcript, indent=2, ensure_ascii=False)
        target_language = meta.configuration.language if meta.configuration.language != 'auto' else 'Detect from transcript'
        
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
        return self._generate_content(meta.configuration.refine.name, prompt)

    def _process_audio(self, ingest_data: Dict, meta: JobMeta):
        """Process audio directly (Direct Analysis)."""
        gemini_data = ingest_data.get("gemini", {})
        cache_name = gemini_data.get("cache_name")
        file_name = gemini_data.get("file_name")
        
        model = genai.GenerativeModel(meta.configuration.refine.name)
        
        # Prepare content
        if cache_name:
            logger.info(f"Using cached audio: {cache_name}")
            cache = caching.CachedContent.get(cache_name)
            model = genai.GenerativeModel.from_cached_content(cached_content=cache)
            content_part = "Analyze the audio in the context."
        elif file_name:
            logger.info(f"Using direct audio file: {file_name}")
            file_obj = genai.get_file(file_name)
            content_part = [file_obj, "Analyze this audio."]
        else:
            raise ValueError("No audio source found in Ingest data.")

        target_language = meta.configuration.language if meta.configuration.language != 'auto' else 'Detect from audio'
        
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
        # For cache, we just send the prompt string. For file, we send list [file, prompt].
        # But wait, if we use from_cached_content, the model is already "primed".
        # So we just send the text prompt.
        
        if cache_name:
             return self._generate_content_with_model(model, prompt)
        else:
             # Direct file
             return self._generate_content_with_model(model, [file_obj, prompt])

    def _generate_content(self, model_name: str, prompt: Union[str, list]):
        model = genai.GenerativeModel(model_name)
        return self._generate_content_with_model(model, prompt)

    def _generate_content_with_model(self, model, prompt):
        generation_config = {
            "temperature": 0.3,
            "response_mime_type": "application/json"
        }
        
        return model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
