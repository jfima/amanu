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
from ..core.factory import ProviderFactory

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
        provider_name = meta.configuration.refine.provider
        logger.info(f"Using refinement provider: {provider_name}")
        
        provider_config = self.manager.providers.get(provider_name)
        provider = ProviderFactory.create_refinement_provider(provider_name, meta.configuration, provider_config)
        
        try:
            result = provider.refine(input_data, mode)
            result_data = result.get("result", {})
            usage = result.get("usage")
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            raise

        # Save Enriched Context
        context_file = job_dir / "transcripts" / "enriched_context.json"
        context_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(context_file, "w") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
            
        # Update Meta
        if usage:
            meta.processing.total_tokens.input += usage.prompt_token_count
            meta.processing.total_tokens.output += usage.candidates_token_count
            
            input_tokens = usage.prompt_token_count
            output_tokens = usage.candidates_token_count
        else:
            input_tokens = 0
            output_tokens = 0
        
        meta.processing.request_count += 1
        meta.processing.steps.append({
            "stage": "refine",
            "step": "analysis",
            "mode": mode,
            "provider": provider_name,
            "timestamp": datetime.now().isoformat(),
            "model": meta.configuration.refine.model,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens
            }
        })
        
        # Calculate cost - get pricing from provider model spec
        pricing = None
        model_name = meta.configuration.refine.model
        
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
             
        meta.processing.total_cost_usd += cost
        
        return {
            "enriched_context_file": str(context_file),
            "mode": mode,
            "provider": provider_name,
            "model": meta.configuration.refine.model,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens
            },
            "cost_usd": cost
        }
