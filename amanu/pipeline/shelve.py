import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from .base import BaseStage
from ..core.models import JobMeta, StageName

logger = logging.getLogger("Amanu.Shelve")

class ShelveStage(BaseStage):
    stage_name = StageName.SHELVE

    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Categorize and tag the content using pre-computed analysis from Refine stage.
        """
        # Load analysis data
        analysis_file = job_dir / "transcripts" / "analysis.json"
        
        if analysis_file.exists():
            with open(analysis_file, "r") as f:
                try:
                    analysis_data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse analysis.json. Using defaults.")
                    analysis_data = {}
        else:
            logger.warning("Analysis file not found. Using defaults.")
            analysis_data = {}
            
        # Extract categories/tags
        categories = {
            "categories": analysis_data.get("categories", []),
            "keywords": analysis_data.get("keywords", []),
            "content_type": analysis_data.get("content_type", "unknown"),
            "sentiment": analysis_data.get("sentiment", "unknown"),
            "participants_count": len(analysis_data.get("participants", []))
        }
            
        # Update stats (No API usage here, just processing step)
        meta.processing.steps.append({
            "stage": "shelve",
            "step": "categorize_content",
            "timestamp": datetime.now().isoformat(),
            "source": "analysis.json"
        })
        
        return {
            "started_at": kwargs.get("started_at"),
            "categories": categories,
            "cost_usd": 0.0 # No cost for this stage now
        }
