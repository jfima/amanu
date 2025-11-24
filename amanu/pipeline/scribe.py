import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

import google.generativeai as genai
from google.generativeai import caching
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import BaseStage
from ..core.models import JobMeta, StageName

logger = logging.getLogger("Amanu.Scribe")

class ScribeStage(BaseStage):
    stage_name = StageName.SCRIBE

    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio using Gemini Chat Session with JSONL streaming.
        """
        # Configure Gemini
        self._configure_gemini(meta.configuration.transcribe.name)
        
        # Load prep result
        prep_result = self._load_prep_result(job_dir)
        cache_name = prep_result.get("cache_name")
        file_name = prep_result.get("file_name")
        
        transcripts_dir = job_dir / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        
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
                model = genai.GenerativeModel(meta.configuration.transcribe.name)
                file_obj = genai.get_file(file_name)
                chat = model.start_chat(history=[{
                    "role": "user",
                    "parts": [file_obj]
                }])
            except Exception as e:
                logger.error(f"Failed to load file {file_name}: {e}")
                raise
        else:
            logger.warning("No cache or file found. Falling back to legacy chunk processing is not fully supported in this refactor.")
            raise ValueError("Context Caching or File Input is required for this pipeline version.")
        
        # 1. Speaker Identification Turn
        logger.info("Step 1: Identifying speakers...")
        
        speaker_prompt = """I have uploaded an audio file. Analyze it completely.
            
            IMPORTANT: Identify all speakers and try to determine their real names from the conversation.
            If you can identify names, use them.
            If names are not mentioned, use generic labels (e.g., "Speaker A", "Speaker B").
            
            Remember their voices for the entire session. Reply 'Ready' when finished."""
        
        response_1 = self._send_with_retry(
            chat,
            speaker_prompt,
            max_retries=meta.configuration.scribe.retry_max,
            delay_seconds=meta.configuration.scribe.retry_delay_seconds
        )
        
        # Consume the stream
        response_text = ""
        for chunk in response_1:
            response_text += chunk.text
            
        logger.debug(f"Model response: {response_text.strip()}")
        
        meta.processing.request_count += 1
        
        # Get usage metadata from the response
        usage_metadata = response_1.usage_metadata if hasattr(response_1, 'usage_metadata') else None
        
        meta.processing.steps.append({
            "stage": "scribe",
            "step": "speaker_identification",
            "timestamp": datetime.now().isoformat(),
            "model": meta.configuration.transcribe.name,
            "tokens": {
                "input": usage_metadata.prompt_token_count if usage_metadata else 0,
                "output": usage_metadata.candidates_token_count if usage_metadata else 0
            }
        })
        
        # 2. Transcription Loop (JSONL Streaming)
        logger.info("Step 2: Transcribing with JSONL streaming...")
        
        merged_transcript = []
        total_input_tokens = 0
        total_output_tokens = 0
        
        # Initial prompt for transcription
        prompt = """
Excellent. Now transcribe the entire conversation from the beginning.
Format the output as JSONL (JSON Lines), where each line is a valid JSON object.

Use this schema for each line:
{ 
  "segment_id": (int, sequential counter), 
  "speaker_id": (string - use the real name if identified, otherwise "Speaker A", "Speaker B"), 
  "start_time": (float, seconds), 
  "end_time": (float, seconds), 
  "text": (string, combined sentence or paragraph for the speaker), 
  "confidence": (float, 0.0-1.0)
}

Instructions:
1. Use the real names you identified for speaker_id. If no names were found, use "Speaker A", "Speaker B", etc.
2. CRITICAL: Combine ALL consecutive speech from the same speaker into ONE segment. Only create a new segment when the speaker changes.
3. Ensure valid JSON on each line.
4. Start generating now.
5. When you have transcribed the entire audio, output the token [END] on a new line.
"""
        
        is_complete = False
        turn_count = 0
        max_turns = 50 # Safety limit
        
        consecutive_low_yield_turns = 0
        error_occurred = None
        
        while not is_complete and turn_count < max_turns:
            turn_count += 1
            logger.info(f"Transcription Turn {turn_count}...")
            
            # Add delay between turns (except first turn)
            if turn_count > 1:
                delay = meta.configuration.scribe.retry_delay_seconds
                logger.info(f"Waiting {delay}s before Turn {turn_count}...")
                time.sleep(delay)
            
            try:
                # Retry logic for 429 errors
                response = self._send_with_retry(
                    chat, 
                    prompt, 
                    max_retries=meta.configuration.scribe.retry_max,
                    delay_seconds=meta.configuration.scribe.retry_delay_seconds
                )
                
                # Iterate through streamed chunks to handle potential timeouts/errors gracefully
                # and build the full text for this turn
                turn_text = ""
                for chunk in response:
                    try:
                        # Check if chunk has content before accessing text
                        if chunk.parts:
                            turn_text += chunk.text
                        elif chunk.candidates and chunk.candidates[0].finish_reason == 1: # STOP
                            # Normal completion, empty chunk
                            pass
                        else:
                            # Log other cases (e.g. SAFETY)
                            if hasattr(chunk, 'candidates') and chunk.candidates:
                                reason = chunk.candidates[0].finish_reason
                                if reason == 3: # SAFETY
                                    logger.error("Transcription blocked by safety filters.")
                                    is_complete = True
                                    break
                                else:
                                    logger.debug(f"Empty chunk with finish_reason: {reason}")
                    except Exception as e:
                        logger.warning(f"Chunk text access failed: {e}")
                    
                # Parse JSONL from this turn
                lines, is_truncated, found_end_token = self._parse_jsonl(turn_text)
                merged_transcript.extend(lines)
                
                # Update stats (approximate from last chunk usage if available, or accumulate)
                # Note: stream=True response usage_metadata might be tricky. 
                # We'll check the final chunk's usage if possible, or the aggregated response.
                # Actually, for chat, we can check chat.history or response.usage_metadata if available.
                if hasattr(response, 'usage_metadata'):
                     usage = response.usage_metadata
                     total_input_tokens += usage.prompt_token_count
                     total_output_tokens += usage.candidates_token_count
                
                meta.processing.request_count += 1
                meta.processing.steps.append({
                    "stage": "scribe",
                    "step": f"transcription_turn_{turn_count}",
                    "timestamp": datetime.now().isoformat(),
                    "segments_produced": len(lines),
                    "tokens": {
                        "input": usage.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                        "output": usage.candidates_token_count if hasattr(response, 'usage_metadata') else 0
                    }
                })
                
                logger.info(f"Turn {turn_count} produced {len(lines)} segments.")
                
                # Save intermediate result
                raw_file = transcripts_dir / "raw.json"
                with open(raw_file, "w") as f:
                    json.dump(merged_transcript, f, indent=2, ensure_ascii=False)
                
                # Check for completion
                if is_truncated:
                     # Model hit output limit, continue
                     prompt = "Continue from where you left off. Output strictly JSONL."
                elif found_end_token:
                     # Explicit completion signal found
                     logger.debug("Completion signal found. Stopping.")
                     is_complete = True
                elif len(lines) == 0:
                     # No data produced, assume complete
                     logger.info("No segments produced. Assuming transcription complete.")
                     is_complete = True
                else:
                     # Check if we've reached the end of audio
                     last_segment = lines[-1]
                     last_end_time = last_segment.get("end_time", 0)
                     
                     if last_end_time >= meta.audio.duration_seconds:
                         logger.info(f"Reached end of audio ({last_end_time:.2f}s / {meta.audio.duration_seconds:.2f}s). Stopping.")
                         is_complete = True
                     else:
                         # Check for low yield (potential stall)
                         if len(lines) < 3:
                             consecutive_low_yield_turns += 1
                             if consecutive_low_yield_turns >= 3:
                                 logger.warning("Multiple low-yield turns detected. Stopping to prevent infinite loop.")
                                 is_complete = True
                         else:
                             consecutive_low_yield_turns = 0
                         
                         # Additional safety: detect single-word loops
                         # If we are just generating "Угу" or "А" (short text) one by one, stop.
                         if len(lines) == 1 and len(lines[0].get("text", "")) < 5 and turn_count > 10:
                             logger.warning("Detected potential infinite loop of short segments. Stopping.")
                             is_complete = True
                         else:
                            prompt = "Continue. Output strictly JSONL. Do not repeat the last segment."
                    
            except Exception as e:
                logger.error(f"Error in turn {turn_count}: {e}")
                # Save what we have so far
                error_occurred = e
                break
        
        # Save merged transcript (even if partial)
        raw_file = transcripts_dir / "raw.json"
        with open(raw_file, "w") as f:
            json.dump(merged_transcript, f, indent=2, ensure_ascii=False)

        if error_occurred:
            raise RuntimeError(f"Transcription failed during turn {turn_count}: {error_occurred}")

        if not merged_transcript:
            raise RuntimeError("Transcription failed: No segments produced.")
            
        # Update meta stats
        meta.processing.total_tokens.input += total_input_tokens
        meta.processing.total_tokens.output += total_output_tokens
        
        # Calculate cost (approximate)
        pricing = meta.configuration.transcribe.cost_per_1M_tokens_usd
        cost = (total_input_tokens / 1_000_000 * pricing.input) + \
               (total_output_tokens / 1_000_000 * pricing.output)
        meta.processing.total_cost_usd += cost

        return {
            "started_at": datetime.now().isoformat(),
            "model": meta.configuration.transcribe.name,
            "segments_count": len(merged_transcript),
            "tokens": {
                "input": total_input_tokens,
                "output": total_output_tokens
            },
            "cost_usd": cost
        }

    def _load_prep_result(self, job_dir: Path) -> Dict[str, Any]:
        prep_file = job_dir / "_stages" / "prep.json"
        if not prep_file.exists():
            raise FileNotFoundError("Prep stage result not found. Run prep first.")
        with open(prep_file, "r") as f:
            return json.load(f)

    def _parse_jsonl(self, text: str) -> tuple[List[Dict[str, Any]], bool, bool]:
        """
        Parse a string containing JSONL lines.
        Returns (list of objects, is_truncated_bool, found_end_token_bool).
        """
        lines = []
        is_truncated = False
        found_end_token = False
        
        # Split by newline
        raw_lines = text.strip().split('\n')
        
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip markdown fences
            if line.startswith("```"):
                continue
                
            try:
                obj = json.loads(line)
                lines.append(obj)
            except json.JSONDecodeError:
                # If a line fails to parse, it might be the truncated last line
                # or just garbage/hallucination.
                # We treat it as truncation if it looks like the start of a JSON object
                if line.startswith("{"):
                    is_truncated = True
                    logger.warning(f"Truncated JSON line detected: {line[:50]}...")
                elif "[END]" in line or "transcribed" in line.lower():
                    # Expected completion tokens/messages
                    logger.debug(f"Completion signal detected: {line}")
                    found_end_token = True
                else:
                    logger.warning(f"Skipping invalid line: {line[:50]}...")
                    
        return lines, is_truncated, found_end_token

    def _send_with_retry(self, chat, prompt: str, max_retries: int, delay_seconds: int):
        """Send message with retry logic for 429 errors."""
        import time
        from google.api_core import exceptions
        
        for attempt in range(max_retries + 1):
            try:
                return chat.send_message(prompt, stream=True)
            except exceptions.ResourceExhausted as e:
                if attempt < max_retries:
                    logger.warning(f"429 Resource exhausted. Retrying in {delay_seconds}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay_seconds)
                else:
                    logger.error(f"429 Resource exhausted after {max_retries} retries. Giving up.")
                    raise
            except Exception as e:
                # Other errors - don't retry
                raise
