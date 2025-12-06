import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime

from .base import BaseStage
from ..core.models import JobObject, StageName
from ..core.factory import ProviderFactory

logger = logging.getLogger("Amanu.Refine")

class RefineStage(BaseStage):
    stage_name = StageName.REFINE

    def validate_prerequisites(self, job_dir: Path, job: JobObject) -> None:
        """
        Validate prerequisites for refine stage.
        """
        # Check for standard mode input (transcript)
        raw_transcript_file = None
        if job.raw_transcript_file:
            raw_transcript_file = job_dir / job.raw_transcript_file
        else:
            raw_transcript_file = job_dir / "transcripts" / "raw_transcript.json"
        
        # Check for direct mode input (ingest result)
        ingest_result = job.ingest_result
        
        has_transcript = raw_transcript_file and raw_transcript_file.exists()
        has_ingest = ingest_result is not None
        
        if not has_transcript and not has_ingest:
            raise ValueError(
                f"Cannot run 'refine' stage: no input data found.\n"
                f"Either run 'scribe' stage first (transcript mode) or ensure 'ingest' stage completed (direct mode).\n"
                f"Missing files:\n"
                f"  - Transcript: {raw_transcript_file}\n"
                f"  - Ingest result: {'Present' if has_ingest else 'Missing'}"
            )
        
        # Additional check for direct mode
        if has_ingest and not has_transcript:
            # Direct mode - check language configuration
            meta = self.manager.load_meta(job_dir)
            if job.configuration.language == 'auto' and not meta.audio.language:
                logger.warning(
                    f"Language not specified for direct audio analysis. "
                    f"Consider setting language in configuration or running 'scribe' stage first."
                )

    def _normalize_array_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix nested {type: array, items: [...]} structures returned by AI.
        Some LLMs interpret the JSON Schema structure literally and return
        data in that format instead of plain arrays.
        """
        for key, value in list(data.items()):
            if isinstance(value, dict):
                # Check for {type: "array", items: [...]} pattern
                if value.get("type") == "array" and "items" in value:
                    data[key] = value.get("items", [])
                    logger.debug(f"Normalized nested array field '{key}'")
                # Also handle variant with nested items
                elif "items" in value and isinstance(value.get("items"), list):
                    data[key] = value.get("items", [])
                    logger.debug(f"Normalized nested items field '{key}'")
        return data

    def execute(self, job_dir: Path, job: JobObject, **kwargs) -> Dict[str, Any]:
        """
        Refine transcript and generate structured data (Enriched Context).
        Supports two modes:
        1. Standard: Input is raw_transcript.json (Text)
        2. Direct: Input is ingest.json (Audio URI) - "Direct Analysis"
        """

        
        # Determine Input Mode
        # Check JobObject first
        raw_transcript_file = None
        if job.raw_transcript_file:
            raw_transcript_file = job_dir / job.raw_transcript_file
        else:
            # Fallback
            raw_transcript_file = job_dir / "transcripts" / "raw_transcript.json"
            
        ingest_result = job.ingest_result
        
        input_data = None
        mode = "unknown"
        
        if raw_transcript_file and raw_transcript_file.exists():
            logger.info("Mode: Standard (Text Analysis)")
            mode = "standard"
            with open(raw_transcript_file, "r") as f:
                input_data = json.load(f)
        elif ingest_result:
            logger.info("Mode: Direct Analysis (Audio Processing)")
            mode = "direct"
            input_data = ingest_result
            
            if not input_data:
                raise FileNotFoundError("No input found. Run Scribe (for Standard) or Ingest (for Direct).")

        # Generate Enriched Context
        provider_name = job.configuration.refine.provider
        logger.info(f"Using refinement provider: {provider_name}")
        
        provider_config = self.manager.providers.get(provider_name)
        provider = ProviderFactory.create_refinement_provider(provider_name, job.configuration, provider_config)
        
        # Get detected language from meta
        meta = self.manager.load_meta(job_dir)
        detected_language = meta.audio.language
        if detected_language:
            logger.info(f"Using detected language context: {detected_language}")
            
        # Load templates to find custom fields
        from ..core.templates import load_template, parse_template
        
        custom_schema_fields = {}
        
        for artifact_config in job.configuration.output.artifacts:
            plugin_name = artifact_config.plugin
            template_name = artifact_config.template
            
            content, _ = load_template(plugin_name, template_name)
            if content:
                metadata, _ = parse_template(content)
                if "custom_fields" in metadata:
                    logger.info(f"Found custom fields in template '{template_name}': {list(metadata['custom_fields'].keys())}")
                    custom_schema_fields.update(metadata["custom_fields"])
        
        # Add original file creation date to custom_schema_fields if it exists
        # meta already loaded above
        original_file_creation_date = meta.original_file_creation_date
        
        if original_file_creation_date:
            # We add it as a potential field, even if not explicitly requested by a template.
            # This ensures it's available for AI to consider and for templates to use.
            custom_schema_fields["file_date"] = {
                "description": "The creation date of the original file, or the earliest date found in its metadata.",
                "structure": "string" # Will be formatted as YYYY-MM-DD HH:MM
            }
            logger.info(f"Added 'file_date' to custom schema from original file creation date: {original_file_creation_date.strftime('%Y-%m-%d %H:%M')}")

        try:
            # Pass detected_language and custom_schema to refine
            result = provider.refine(
                input_data,
                mode,
                language=detected_language,
                custom_schema=custom_schema_fields,
                job_dir=job_dir
            )
            result_data = result.get("result", {})
            usage = result.get("usage")

            # Normalize array fields - fix AI returning {type: array, items: [...]} instead of plain arrays
            result_data = self._normalize_array_fields(result_data)

            # If file_date was requested and AI didn't provide it or returned "Unknown", use the one from JobObject
            if "file_date" in custom_schema_fields and original_file_creation_date:
                if "file_date" not in result_data or result_data.get("file_date") == "Unknown":
                    result_data["file_date"] = original_file_creation_date.strftime("%Y-%m-%d %H:%M")
                    logger.info(f"Injected 'file_date' from JobObject into result_data: {result_data['file_date']}")

        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            raise

        # Save Enriched Context
        context_file = job_dir / "transcripts" / "enriched_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(context_file, "w") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
            
        # Update Job Object
        job.enriched_context_file = str(context_file.relative_to(job_dir))
            
        if usage:
            # Handle dictionary usage (OpenRouter, etc.)
            if isinstance(usage, dict):
                input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or usage.get("prompt_token_count") or 0
                output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or usage.get("candidates_token_count") or 0
                provider_cost = usage.get("cost_usd", 0.0)
            # Handle object usage (Gemini)
            else:
                input_tokens = getattr(usage, "prompt_token_count", 0)
                output_tokens = getattr(usage, "candidates_token_count", 0)
                provider_cost = getattr(usage, "cost_usd", 0.0)

            job.processing.total_tokens.input += input_tokens
            job.processing.total_tokens.output += output_tokens
        else:
            input_tokens = 0
            output_tokens = 0
            provider_cost = 0.0
        
        job.processing.request_count += 1
        job.processing.steps.append({
            "stage": "refine",
            "step": "analysis",
            "mode": mode,
            "provider": provider_name,
            "timestamp": datetime.now().isoformat(),
            "model": job.configuration.refine.model,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens
            }
        })
        
        # Calculate cost
        cost = 0.0
        
        if provider_cost > 0:
            cost = provider_cost
            logger.info(f"Using provider-reported cost: ${cost:.6f}")
        else:
            # Calculate cost - get pricing from provider model spec
            pricing = None
            model_name = job.configuration.refine.model
            
            if hasattr(provider_config, 'models') and provider_config.models:
                for model_spec in provider_config.models:
                    if model_spec.name == model_name:
                        pricing = model_spec.cost_per_1M_tokens_usd
                        break
            
            if pricing:
                 cost = (input_tokens / 1_000_000 * pricing.input) + \
                        (output_tokens / 1_000_000 * pricing.output)
            else:
                 cost = 0.0
                 logger.warning(f"No pricing info for model {model_name}, cost set to 0.0")
             
        job.processing.total_cost_usd += cost
        
        return {
            "enriched_context_file": str(context_file),
            "mode": mode,
            "provider": provider_name,
            "model": job.configuration.refine.model,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens
            },
            "cost_usd": cost
        }
