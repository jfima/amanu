import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseStage
from ..core.models import JobMeta, StageName
from ..core.factory import ProviderFactory

logger = logging.getLogger("Amanu.Scribe")

class ScribeStage(BaseStage):
    stage_name = StageName.SCRIBE

    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio using the configured provider.
        """
        # Load ingest result
        ingest_result = self._load_ingest_result(job_dir)
        
        # Initialize Provider
        provider_name = meta.configuration.transcribe.provider
        logger.info(f"Using transcription provider: {provider_name}")
        
        provider_config = self.manager.providers.get(provider_name)
        if not provider_config:
            # Fallback or error?
            # If provider is gemini, we might have default env var fallback inside provider, 
            # but better to pass empty config if missing.
            # But wait, manager.providers is populated from ConfigContext.providers which has defaults.
            # So it should be there.
            logger.warning(f"No configuration found for provider {provider_name}. Using defaults/empty.")
            # We need to pass the correct type if possible, or let provider handle None/dict
            # The provider expects a specific Pydantic model.
            # But manager.providers stores Pydantic models (GeminiConfig etc).
            pass

        provider = ProviderFactory.create(provider_name, meta.configuration, provider_config)
        
        # Execute Transcription
        try:
            result = provider.transcribe(ingest_result)
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

        # Process Results
        merged_transcript = result.get("segments", [])
        
        # Save transcript
        transcripts_dir = job_dir / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        
        raw_file = transcripts_dir / "raw_transcript.json"
        with open(raw_file, "w") as f:
            json.dump(merged_transcript, f, indent=2, ensure_ascii=False)
            
        if not merged_transcript:
            raise RuntimeError("Transcription failed: No segments produced.")

        # Update Meta
        analysis = result.get("analysis", {})
        if "language" in analysis:
            meta.audio.language = analysis["language"]
            
        meta.processing.request_count += 1 # Abstract count
        meta.processing.total_tokens.input += result.get("tokens", {}).get("input", 0)
        meta.processing.total_tokens.output += result.get("tokens", {}).get("output", 0)
        meta.processing.total_cost_usd += result.get("cost_usd", 0.0)
        
        meta.processing.steps.append({
            "stage": "scribe",
            "provider": provider_name,
            "timestamp": datetime.now().isoformat(),
            "segments_count": len(merged_transcript),
            "cost_usd": result.get("cost_usd", 0.0)
        })

        return {
            "started_at": datetime.now().isoformat(),
            "provider": provider_name,
            "model": meta.configuration.transcribe.model,
            "segments_count": len(merged_transcript),
            "cost_usd": result.get("cost_usd", 0.0)
        }

    def _load_ingest_result(self, job_dir: Path) -> Dict[str, Any]:
        ingest_file = job_dir / "_stages" / "ingest.json"
        if not ingest_file.exists():
            raise FileNotFoundError("Ingest stage result not found. Run ingest first.")
        with open(ingest_file, "r") as f:
            return json.load(f)


