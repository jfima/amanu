from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from ..core.manager import JobManager
from ..core.models import JobObject, StageName, StageStatus

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
            
            # Load current job object
            job_dir = self.manager._get_job_dir(job_id)
            job = self.manager.load_job_object(job_dir)
            
            # Validate prerequisites before execution
            self.validate_prerequisites(job_dir, job)
            
            # Execute stage logic
            # The execute method now modifies the job object directly or returns data to be merged
            result = self.execute(job_dir, job, **kwargs)
            
            # Save updated job object
            # Note: execute() might have modified job.audio, job.processing, etc.
            # We also merge any returned result into the job object if needed,
            # but ideally execute() should update the job object directly.
            # However, for backward compatibility with my own design, let's assume execute returns a dict
            # that we might want to log or store.
            # But in the new architecture, we want to update specific fields in JobObject.
            
            # Let's enforce that execute() updates the passed 'job' object.
            self.manager.save_job_object(job_dir, job)
            
            self.manager.update_stage_status(job_id, self.stage_name, StageStatus.COMPLETED)
            logger.info(f"Stage {self.stage_name.value} completed for job {job_id}")
            
        except Exception as e:
            logger.error(f"Stage {self.stage_name.value} failed for job {job_id}: {e}")
            # Log traceback if debug is enabled for the job
            # We need to reload job to check debug flag safely or use cached config
            try:
                job_dir = self.manager._get_job_dir(job_id)
                job = self.manager.load_job_object(job_dir)
                if job.configuration.debug:
                    import traceback
                    logger.debug("""%s""", traceback.format_exc())
            except:
                pass
                
            self.manager.update_stage_status(job_id, self.stage_name, StageStatus.FAILED, error=str(e))
            raise

    @abstractmethod
    def validate_prerequisites(self, job_dir: Path, job: JobObject) -> None:
        """
        Validate prerequisites for this stage.
        Raise ValueError if prerequisites are not met.
        """
        pass

    @abstractmethod
    def execute(self, job_dir: Path, job: JobObject, **kwargs) -> Dict[str, Any]:
        """
        Implement stage logic here.
        Should update the 'job' object directly with results.
        Returns a dictionary (optional) for logging or legacy reasons.
        """
        pass

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
        
    def run_all_stages(self, job_id: str, skip_transcript: bool = False, start_at: Optional[StageName] = None, stop_after: Optional[StageName] = None) -> None:
        """Run all stages in sequence, optionally starting at and/or stopping after a specific stage."""
        from .ingest import IngestStage
        from .scribe import ScribeStage
        from .refine import RefineStage
        from .generate import GenerateStage
        from .shelve import ShelveStage
        
        logger.info(f"Starting pipeline for job {job_id} (Skip Transcript: {skip_transcript}, Start At: {start_at.value if start_at else 'None'}, Stop After: {stop_after.value if stop_after else 'None'})")

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
                # If start_at is defined, skip stages until we reach it
                if start_at and stage_order.index(current_stage_name) < stage_order.index(start_at):
                    logger.info(f"Skipping stage {current_stage_name.value} (waiting for start_at: {start_at.value})")
                    continue

                # Reload state in each iteration to get the latest status updates
                # Try loading JobObject first
                job_dir = self.job_manager._get_job_dir(job_id)
                if (job_dir / "_stages" / "_job.json").exists():
                    job = self.job_manager.load_job_object(job_dir)
                    current_stage_status = job.stages[current_stage_name].status
                else:
                    # Fallback
                    job_state = self.job_manager.load_state(job_id)
                    current_stage_status = job_state.stages[current_stage_name].status

                if current_stage_status == StageStatus.COMPLETED:
                    logger.info(f"Stage {current_stage_name.value} already completed. Skipping.")
                    # Check if we should stop after this already-completed stage
                    if stop_after and current_stage_name == stop_after:
                        logger.info(f"Stopped after {stop_after.value} as requested")
                        logger.info(f"Job {job_id} remains in work directory (not finalized)")
                        return
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
                # Pass results_dir to ShelveStage if it's the current stage
                if current_stage_name == StageName.SHELVE:
                    stage_instance.run(job_id, results_dir=self.results_dir)
                else:
                    stage_instance.run(job_id)
                
                # Check if we should stop after this stage
                if stop_after and current_stage_name == stop_after:
                    logger.info(f"Stopped after {stop_after.value} as requested")
                    logger.info(f"Job {job_id} remains in work directory (not finalized)")
                    return
                    
            except Exception as e:
                import traceback
                logger.error(f"Pipeline failed at stage {current_stage_name.value}: {e}\n{traceback.format_exc()}")
                raise

        # 6. Finalize (only if we didn't stop early)
        # Update total time
        from datetime import datetime
        job = self.job_manager.load_job_object(job_id)
        job.processing.total_time_seconds = (datetime.now() - job.created_at).total_seconds()
        job_dir = self.job_manager._get_job_dir(job_id)
        self.job_manager.save_job_object(job_dir, job)
        
        result_path = self.job_manager.finalize_job(job_id, self.results_dir)
        logger.info(f"Pipeline completed! Results at: {result_path}")
