import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseStage
from ..core.models import JobObject, StageName
from ..core.factory import ProviderFactory

logger = logging.getLogger("Amanu.Scribe")

class ScribeStage(BaseStage):
    stage_name = StageName.SCRIBE

    def validate_prerequisites(self, job_dir: Path, job: JobObject) -> None:
        """
        Validate prerequisites for scribe stage.
        """
        # Check that ingest stage completed successfully
        ingest_result = job.ingest_result
        if not ingest_result:
            raise ValueError(
                f"Cannot run 'scribe' stage: ingest result not found.\n"
                f"Please run 'ingest' stage first."
            )

    def execute(self, job_dir: Path, job: JobObject, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio using the configured provider.
        """
        # Load ingest result from JobObject
        ingest_result = job.ingest_result
        if not ingest_result:
            raise RuntimeError("Ingest result not found in JobObject.")
        
        # Initialize Provider
        provider_name = job.configuration.transcribe.provider
        logger.info(f"Using transcription provider: {provider_name}")
        
        provider_config = self.manager.providers.get(provider_name)
        if not provider_config:
            logger.warning(f"No configuration found for provider {provider_name}. Using defaults/empty.")

        provider = ProviderFactory.create(provider_name, job.configuration, provider_config)
        
        # Execute Transcription
        try:
            result = provider.transcribe(ingest_result, job_dir=job_dir)
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

        # Update Job Object and Meta
        analysis = result.get("analysis", {})
        if "language" in analysis:
            meta = self.manager.load_meta(job_dir)
            meta.audio.language = analysis["language"]
            self.manager.save_meta(job_dir, meta)
            
        job.raw_transcript_file = str(raw_file.relative_to(job_dir))
            
        job.processing.request_count += 1
        job.processing.total_tokens.input += result.get("tokens", {}).get("input", 0)
        job.processing.total_tokens.output += result.get("tokens", {}).get("output", 0)
        job.processing.total_cost_usd += result.get("cost_usd", 0.0)
        
        job.processing.steps.append({
            "stage": "scribe",
            "provider": provider_name,
            "timestamp": datetime.now().isoformat(),
            "segments_count": len(merged_transcript),
            "cost_usd": result.get("cost_usd", 0.0)
        })

        return {
            "started_at": datetime.now().isoformat(),
            "provider": provider_name,
            "model": job.configuration.transcribe.model,
            "segments_count": len(merged_transcript),
            "cost_usd": result.get("cost_usd", 0.0)
        }
