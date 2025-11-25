from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List # Keep List if used, otherwise remove
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
            # Log traceback if debug is enabled for the job
            if meta.configuration.debug:
                import traceback
                logger.debug("""%s""", traceback.format_exc())
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
            raise ValueError("GEMINI_API_KEY is missing. Please set it in config.yaml (gemini.api_key) or as an environment variable.")
            
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
            
            if "API key not valid" in error_msg or "400" in error_msg:
                clean_msg = "The provided Gemini API key is invalid. Please check your configuration."
            else:
                # Try to clean up gRPC errors
                if "[" in clean_msg:
                    clean_msg = clean_msg.split("[")[0].strip()
            
            raise ValueError(f"{clean_msg}")


class Pipeline:
    """Orchestrator for running all pipeline stages."""
    
    def __init__(self, job_manager: JobManager, results_dir: Path):
        self.job_manager = job_manager
        self.results_dir = results_dir
        
    def run_all_stages(self, job_id: str, skip_transcript: bool = False) -> None:
        """Run all stages in sequence."""
        from .ingest import IngestStage
        from .scribe import ScribeStage
        from .refine import RefineStage
        from .generate import GenerateStage
        from .shelve import ShelveStage
        
        logger.info(f"Starting pipeline for job {job_id} (Skip Transcript: {skip_transcript})")

        stage_order = [
            StageName.INGEST,
            StageName.SCRIBE,
            StageName.REFINE,
            StageName.GENERATE,
            StageName.SHELVE,
        ]
        
        # Map StageName to actual Stage classes
        stage_class_map = {
            StageName.INGEST: IngestStage,
            StageName.SCRIBE: ScribeStage,
            StageName.REFINE: RefineStage,
            StageName.GENERATE: GenerateStage,
            StageName.SHELVE: ShelveStage,
        }

        for current_stage_name in stage_order:
            try:
                # Reload state in each iteration to get the latest status updates
                job_state = self.job_manager.load_state(job_id)
                current_stage_status = job_state.stages[current_stage_name].status

                if current_stage_status == StageStatus.COMPLETED:
                    logger.info(f"Stage {current_stage_name.value} already completed. Skipping.")
                    continue

                if current_stage_name == StageName.SCRIBE and skip_transcript:
                    logger.info("Skipping Scribe stage (Direct Analysis Mode) as requested.")
                    self.job_manager.update_stage_status(job_id, StageName.SCRIBE, StageStatus.SKIPPED)
                    continue
                
                if current_stage_status == StageStatus.SKIPPED:
                     logger.info(f"Stage {current_stage_name.value} was previously skipped. Skipping.")
                     continue

                # If pending or failed, run the stage
                logger.info(f"Running stage {current_stage_name.value}...")
                stage_instance = stage_class_map[current_stage_name](self.job_manager)
                stage_instance.run(job_id)
            except Exception as e:
                import traceback
                logger.error(f"Pipeline failed at stage {current_stage_name.value}: {e}\n{traceback.format_exc()}")
                raise

        # 6. Finalize
        result_path = self.job_manager.finalize_job(job_id, self.results_dir)
        logger.info(f"Pipeline completed! Results at: {result_path}")
