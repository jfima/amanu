import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from .models import (
    JobState, JobMeta, StageName, StageStatus, 
    StageState, JobConfiguration
)

logger = logging.getLogger("Amanu.JobManager")

class JobManager:
    def __init__(self, work_dir: Path = Path("work")):
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def _get_job_dir(self, job_id: str) -> Path:
        # Support both full path and just job_id
        if "/" in job_id or "\\" in job_id:
             path = Path(job_id)
             if path.exists():
                 return path
        return self.work_dir / job_id

    def create_job(self, file_path: Path, config: JobConfiguration) -> JobMeta:
        """Commission a new job (SCOUT stage helper)."""
        timestamp = datetime.now().strftime("%d-%H%M%S")
        safe_filename = file_path.stem.replace(" ", "_")
        job_id = f"{timestamp}_{safe_filename}"
        job_dir = self.work_dir / job_id
        
        # Create directory structure
        (job_dir / "media").mkdir(parents=True)
        (job_dir / "transcripts").mkdir(parents=True)
        (job_dir / "_stages").mkdir(parents=True)

        # Copy original file
        dest_file = job_dir / "media" / f"original{file_path.suffix}"
        shutil.copy2(file_path, dest_file)

        now = datetime.now()

        # Initialize State
        state = JobState(
            job_id=job_id,
            original_file=file_path.name,
            created_at=now,
            updated_at=now,
            current_stage="commissioned"
        )
        self.save_state(job_dir, state)

        # Initialize Meta
        meta = JobMeta(
            job_id=job_id,
            original_file=file_path.name,
            created_at=now,
            updated_at=now,
            configuration=config
        )
        self.save_meta(job_dir, meta)

        return meta

    def load_state(self, job_id: str) -> JobState:
        job_dir = self._get_job_dir(job_id)
        state_file = job_dir / "state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"State file not found for job {job_id}")
        
        with open(state_file, "r") as f:
            data = json.load(f)
        return JobState(**data)

    def save_state(self, job_dir: Path, state: JobState) -> None:
        state.updated_at = datetime.now()
        with open(job_dir / "state.json", "w") as f:
            f.write(state.model_dump_json(indent=2))

    def load_meta(self, job_id: str) -> JobMeta:
        job_dir = self._get_job_dir(job_id)
        meta_file = job_dir / "meta.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"Meta file not found for job {job_id}")
        
        with open(meta_file, "r") as f:
            data = json.load(f)
        return JobMeta(**data)

    def save_meta(self, job_dir: Path, meta: JobMeta) -> None:
        meta.updated_at = datetime.now()
        with open(job_dir / "meta.json", "w") as f:
            f.write(meta.model_dump_json(indent=2))

    def update_stage_status(self, job_id: str, stage: StageName, status: StageStatus, error: Optional[str] = None) -> None:
        job_dir = self._get_job_dir(job_id)
        state = self.load_state(job_id)
        
        state.stages[stage].status = status
        if status == StageStatus.COMPLETED:
            state.stages[stage].timestamp = datetime.now()
            state.current_stage = stage.value
        elif status == StageStatus.FAILED:
            state.stages[stage].error = error
            state.errors.append({
                "stage": stage.value,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
        
        self.save_state(job_dir, state)

    def list_jobs(self) -> List[JobState]:
        jobs = []
        if not self.work_dir.exists():
            return []
            
        for job_dir in self.work_dir.iterdir():
            if job_dir.is_dir() and (job_dir / "state.json").exists():
                try:
                    jobs.append(self.load_state(job_dir.name))
                except Exception as e:
                    logger.error(f"Failed to load job {job_dir.name}: {e}")
        return sorted(jobs, key=lambda x: x.created_at, reverse=True)

    def get_ready_jobs(self, stage: StageName) -> List[JobState]:
        """Find jobs ready for a specific stage."""
        jobs = self.list_jobs()
        ready_jobs = []
        
        stage_order = [s.value for s in StageName]
        target_idx = stage_order.index(stage.value)
        
        for job in jobs:
            # Check if stage is already completed
            if job.stages[stage].status == StageStatus.COMPLETED:
                continue
                
            # Check if previous stages are completed
            is_ready = True
            for prev_stage in stage_order[:target_idx]:
                if job.stages[StageName(prev_stage)].status != StageStatus.COMPLETED:
                    is_ready = False
                    break
            
            if is_ready:
                ready_jobs.append(job)
                
        return ready_jobs

    def finalize_job(self, job_id: str, results_dir: Path) -> Path:
        job_dir = self._get_job_dir(job_id)
        meta = self.load_meta(job_id)
        
        # Create result path: results/YYYY/MM/DD/job_id
        date_path = meta.created_at.strftime("%Y/%m/%d")
        final_dest = results_dir / date_path / job_dir.name
        final_dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy everything except _stages and state.json (unless debug is on)
        if final_dest.exists():
            shutil.rmtree(final_dest)
        
        ignore_patterns = ["state.json"]
        if not meta.configuration.debug:
            ignore_patterns.append("_stages")
            
        shutil.copytree(job_dir, final_dest, ignore=shutil.ignore_patterns(*ignore_patterns))
        
        # Cleanup work dir
        shutil.rmtree(job_dir)
        
        return final_dest

    def cleanup_old_jobs(self, retention_days: int, status_filter: Optional[StageStatus] = None) -> int:
        """Clean up old jobs based on retention policy.
        
        Args:
            retention_days: Remove jobs older than this many days
            status_filter: Only remove jobs with this status (None = all)
            
        Returns:
            Number of jobs removed
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        removed_count = 0
        
        for job_dir in self.work_dir.iterdir():
            if not job_dir.is_dir():
                continue
                
            try:
                state = self.load_state(job_dir.name)
                
                # Check if job is old enough
                if state.updated_at > cutoff_date:
                    continue
                    
                # Check status filter
                if status_filter:
                    # Check if any stage has the target status
                    has_status = any(
                        stage_state.status == status_filter 
                        for stage_state in state.stages.values()
                    )
                    if not has_status:
                        continue
                
                # Remove job
                shutil.rmtree(job_dir)
                removed_count += 1
                logger.info(f"Cleaned up old job: {job_dir.name}")
                
            except Exception as e:
                logger.error(f"Failed to cleanup job {job_dir.name}: {e}")
                
        return removed_count

    def retry_job(self, job_id: str, from_stage: Optional[StageName] = None) -> None:
        """Retry a failed job from a specific stage.
        
        Args:
            job_id: Job ID to retry
            from_stage: Stage to retry from (None = retry from first failed stage)
        """
        state = self.load_state(job_id)
        
        # Find the stage to retry from
        if from_stage is None:
            # Find first failed stage
            stage_order = [s for s in StageName]
            for stage in stage_order:
                if state.stages[stage].status == StageStatus.FAILED:
                    from_stage = stage
                    break
                    
            if from_stage is None:
                raise ValueError(f"No failed stages found in job {job_id}")
        
        # Reset stages from the retry point onwards
        stage_order = [s for s in StageName]
        start_idx = stage_order.index(from_stage)
        
        for stage in stage_order[start_idx:]:
            state.stages[stage] = StageState(status=StageStatus.PENDING)
        
        state.current_stage = from_stage.value
        state.errors = []  # Clear errors
        
        job_dir = self._get_job_dir(job_id)
        self.save_state(job_dir, state)
        
        logger.info(f"Reset job {job_id} to retry from stage {from_stage.value}")
