import logging
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import BaseStage
from ..core.models import JobMeta, StageName

logger = logging.getLogger("Amanu.Refine")

class RefineStage(BaseStage):
    stage_name = StageName.REFINE

    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Refine transcript and generate summary.
        """
        # Configure Gemini
        self._configure_gemini(meta.configuration.refine.name)
        
        # Load raw transcript
        raw_file = job_dir / "transcripts" / "raw.json"
        if not raw_file.exists():
            raise FileNotFoundError("Raw transcript not found. Run scribe first.")
            
        with open(raw_file, "r") as f:
            raw_transcript = json.load(f)
            
        # 2. Generate Content
        prompt = self._build_prompt(raw_transcript, meta.configuration.template, meta.configuration.language)
        response = self._generate_content(meta.configuration.refine.name, prompt)
        
        # Parse JSON response
        try:
            result_data = json.loads(response.text)
            if isinstance(result_data, list):
                logger.warning("Model returned a list instead of a dict. Using first item if available.")
                if result_data:
                    result_data = result_data[0]
                else:
                    result_data = {}
            
            clean_text = result_data.get("clean_transcript", "")
            analysis_data = {k: v for k, v in result_data.items() if k != "clean_transcript"}
        except json.JSONDecodeError:
            logger.error("Failed to parse Refine stage JSON response. Falling back to raw text.")
            clean_text = response.text
            analysis_data = {}

        # 3. Save Results
        clean_file = job_dir / "transcripts" / "clean.md"
        with open(clean_file, "w") as f:
            f.write(clean_text)
            
        analysis_file = job_dir / "transcripts" / "analysis.json"
        with open(analysis_file, "w") as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
        # 4. Update Meta
        usage = response.usage_metadata
        meta.processing.total_tokens.input += usage.prompt_token_count
        meta.processing.total_tokens.output += usage.candidates_token_count
        
        meta.processing.request_count += 1
        meta.processing.steps.append({
            "stage": "refine",
            "step": "refine_transcript",
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
            "clean_transcript_file": str(clean_file),
            "analysis_file": str(analysis_file),
            "model": meta.configuration.refine.name,
            "tokens": {
                "input": usage.prompt_token_count,
                "output": usage.candidates_token_count
            },
            "cost_usd": cost
        }



    def _build_prompt(self, transcript: list, template_name: str, language: str) -> str:
        transcript_text = json.dumps(transcript, indent=2, ensure_ascii=False)
        
        target_language = language if language != 'auto' else 'Detect from transcript'
        
        # Load template instructions
        template_instructions = self._load_template(template_name)
        
        return f"""
You are a professional editor. Analyze and clean up this transcript.

INPUT TRANSCRIPT:
{transcript_text}

INSTRUCTIONS:
1. Clean up the text: Remove filler words, fix grammar, group by speaker.
2. Analyze the content: Identify participants, categories, keywords, and write a summary.
3. IMPORTANT: All output (summary, categories, keywords, etc.) MUST be in the following language: {target_language}.
4. IMPORTANT: For "participants", list ONLY the speakers who actually spoke in the audio (those who appear as "speaker_id" in the transcript). Do NOT include names that were only mentioned in conversation.
5. Format the "clean_transcript" field according to these template instructions:

{template_instructions}

6. Output strictly valid JSON with this schema:
{{
  "clean_transcript": "markdown string of the cleaned transcript",
  "summary": "TL;DR summary (3-5 bullets)",
  "participants": ["list of speakers/roles - use real names from transcript, not 'Speaker A/B'"],
  "categories": ["list of categories"],
  "keywords": ["list of keywords"],
  "content_type": "meeting|interview|lecture|voice_note|other",
  "sentiment": "positive|neutral|negative",
  "language": "language code (e.g. en, ru, es)"
}}

Target Language: {target_language}
"""

    def _generate_content(self, model_name: str, prompt: str):
        model = genai.GenerativeModel(model_name)
        
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
        return response

    def _load_template(self, template_name: str) -> str:
        """Load template instructions from file."""
        from pathlib import Path
        
        # Try to load from amanu/templates/
        template_dir = Path(__file__).parent.parent / "templates"
        template_file = template_dir / f"{template_name}.md"
        
        if template_file.exists():
            with open(template_file, "r") as f:
                return f.read()
        else:
            logger.warning(f"Template {template_name}.md not found. Using default instructions.")
            return "Format as a clear, well-structured markdown document with headings and sections."
