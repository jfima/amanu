from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
import logging

from ..core.manager import JobManager
from ..core.models import JobMeta, JobState, StageName, StageStatus

logger = logging.getLogger("Amanu.Pipeline")

class BaseStage(ABC):
    stage_name: StageName

    def __init__(self, manager: JobManager):
        self.manager = manager

    def run(self, job_id: str, **kwargs) -> None:
        """Execute the stage for a given job."""
        logger.info(f"Starting stage {self.stage_name.value} for job {job_id}")
        
        try:
            self.manager.update_stage_status(job_id, self.stage_name, StageStatus.IN_PROGRESS)
            
            # Load current state and meta
            job_dir = self.manager._get_job_dir(job_id)
            meta = self.manager.load_meta(job_id)
            
            # Execute stage logic
            result = self.execute(job_dir, meta, **kwargs)
            
            # Save stage result artifact
            self._save_stage_result(job_dir, result)
            
            # Update meta if needed (stage implementation should modify meta object)
            self.manager.save_meta(job_dir, meta)
            
            self.manager.update_stage_status(job_id, self.stage_name, StageStatus.COMPLETED)
            logger.info(f"Stage {self.stage_name.value} completed for job {job_id}")
            
        except Exception as e:
            logger.error(f"Stage {self.stage_name.value} failed for job {job_id}: {e}")
            self.manager.update_stage_status(job_id, self.stage_name, StageStatus.FAILED, error=str(e))
            raise

    @abstractmethod
    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Implement stage logic here.
        Returns a dictionary to be saved as _stages/{stage_name}.json
        """
        pass

    def _save_stage_result(self, job_dir: Path, result: Dict[str, Any]) -> None:
        stage_file = job_dir / "_stages" / f"{self.stage_name.value}.json"
        import json
        from datetime import datetime
        
        # Add common fields
        result["stage"] = self.stage_name.value
        if "completed_at" not in result:
            result["completed_at"] = datetime.now().isoformat()
            
        with open(stage_file, "w") as f:
            json.dump(result, f, indent=2, default=str, ensure_ascii=False)

    def _configure_gemini(self, model_name: str) -> None:
        """
        Configure Gemini API with validation.
        """
        import os
        import google.generativeai as genai
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
             from ..core.config import load_config
             load_config() 
             api_key = os.environ.get("GEMINI_API_KEY")
             
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment or config.yaml")
            
        try:
            genai.configure(api_key=api_key)
            # Lightweight call to verify key validity
            # We list models just to trigger auth check
            for _ in genai.list_models():
                break
        except Exception as e:
            logger.debug(f"Full Gemini API validation error: {e}")
            error_msg = str(e)
            clean_msg = error_msg
            
            if "API key not valid" in error_msg:
                clean_msg = "The provided Gemini API key is invalid."
            elif "400" in error_msg and "API key" in error_msg:
                 clean_msg = "The provided Gemini API key is invalid."
            else:
                # Try to clean up gRPC errors
                if "[" in clean_msg:
                    clean_msg = clean_msg.split("[")[0].strip()
            
            raise ValueError(f"{clean_msg} Please check your config.yaml or GEMINI_API_KEY environment variable.")

            raise ValueError(f"{clean_msg} Please check your config.yaml or GEMINI_API_KEY environment variable.")


class Pipeline:
    """Orchestrator for running all pipeline stages."""
    
    def __init__(self, job_manager: JobManager, results_dir: Path):
        self.job_manager = job_manager
        self.results_dir = results_dir
        
    def run_all_stages(self, job_id: str) -> None:
        """Run all stages in sequence."""
        from .scout import ScoutStage
        from .prep import PrepStage
        from .scribe import ScribeStage
        from .refine import RefineStage
        from .shelve import ShelveStage
        
        logger.info(f"Starting pipeline for job {job_id}")
        
        # 1. Scout
        ScoutStage(self.job_manager).run(job_id)
        
        # 2. Prep
        PrepStage(self.job_manager).run(job_id)
        
        # 3. Scribe
        ScribeStage(self.job_manager).run(job_id)
        
        # 4. Refine
        RefineStage(self.job_manager).run(job_id)
        
        # 5. Shelve (Optional)
        try:
            ShelveStage(self.job_manager).run(job_id)
        except Exception as e:
            logger.warning(f"Shelve stage failed (non-critical): {e}")
            
        # 6. Finalize
        result_path = self.job_manager.finalize_job(job_id, self.results_dir)
        logger.info(f"Pipeline completed! Results at: {result_path}")
