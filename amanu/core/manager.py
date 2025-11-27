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
    def __init__(self, work_dir: Path = Path("work"), results_dir: Path = Path("results"), providers: Dict[str, Any] = None):
        self.work_dir = work_dir
        self.results_dir = results_dir
        self.providers = providers or {}
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _get_job_dir(self, job_id: str) -> Path:
        # Support both full path and just job_id
        if "/" in job_id or "\\" in job_id:
             path = Path(job_id)
             if path.exists():
                 return path
        
        # Check work dir
        work_path = self.work_dir / job_id
        if work_path.exists():
            return work_path
            
        # Check results dir (search recursively? No, too slow. We need a better way or just fail)
        # For loading state/meta, we might need to search.
        # Let's try to find it in results if not in work.
        # This is expensive. For now, let's assume if it's not in work, we can't easily find it by ID alone
        # unless we index it. But for reporting, we iterate all.
        
        return work_path

    def create_job(self, file_path: Path, config: JobConfiguration) -> JobMeta:
        """Initialize a new job."""
        timestamp = datetime.now()
        job_id = f"{timestamp.strftime('%y-%m%d-%H%M%S')}_{file_path.stem}"
        # Sanitize job_id
        job_id = "".join([c if c.isalnum() or c in "-_" else "_" for c in job_id])
        
        job_dir = self.work_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup directories
        (job_dir / "media").mkdir()
        (job_dir / "transcripts").mkdir()
        (job_dir / "_stages").mkdir()
        
        # Copy original file
        dest_file = job_dir / "media" / f"original{file_path.suffix}"
        shutil.copy2(file_path, dest_file)
        
        # Create Initial State
        state = JobState(
            job_id=job_id,
            original_file=file_path.name,
            created_at=timestamp,
            updated_at=timestamp,
            current_stage=StageName.INGEST.value,
            location=job_dir
        )
        self.save_state(job_dir, state)
        
        # Create Initial Meta
        meta = JobMeta(
            job_id=job_id,
            original_file=file_path.name,
            created_at=timestamp,
            updated_at=timestamp,
            configuration=config
        )
        self.save_meta(job_dir, meta)
        
        return meta

    def save_state(self, job_dir: Path, state: JobState) -> None:
        state.updated_at = datetime.now()
        with open(job_dir / "state.json", "w") as f:
            f.write(state.model_dump_json(indent=2))

    def save_meta(self, job_dir: Path, meta: JobMeta) -> None:
        meta.updated_at = datetime.now()
        with open(job_dir / "meta.json", "w") as f:
            f.write(meta.model_dump_json(indent=2))

    def update_stage_status(self, job_id: str, stage: StageName, status: StageStatus, error: Optional[str] = None) -> None:
        job_dir = self._get_job_dir(job_id)
        state = self.load_state(job_dir)
        
        state.stages[stage].status = status
        state.stages[stage].timestamp = datetime.now()
        if error:
            state.stages[stage].error = error
            state.errors.append({
                "stage": stage.value,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            
        # Update current stage tracker if we are progressing
        if status == StageStatus.IN_PROGRESS:
            state.current_stage = stage.value
            
        self.save_state(job_dir, state)
    
    def list_jobs(self, include_history: bool = False) -> List[JobState]:
        jobs = []
        
        # 1. Active Jobs
        if self.work_dir.exists():
            for job_dir in self.work_dir.iterdir():
                if job_dir.is_dir() and (job_dir / "state.json").exists():
                    try:
                        state = self.load_state(job_dir)
                        state.location = job_dir
                        jobs.append(state)
                    except Exception as e:
                        logger.error(f"Failed to load job {job_dir.name}: {e}")
        
        # 2. Historical Jobs
        if include_history and self.results_dir.exists():
            for meta_file in self.results_dir.rglob("meta.json"):
                try:
                    job_dir = meta_file.parent
                    try:
                        state = self.load_state(job_dir)
                        state.location = job_dir
                        jobs.append(state)
                    except FileNotFoundError:
                        # Reconstruct state from meta if state.json is missing
                        meta = self.load_meta(job_dir)
                        state = JobState(
                            job_id=meta.job_id,
                            original_file=meta.original_file,
                            created_at=meta.created_at,
                            updated_at=meta.updated_at,
                            current_stage="completed",
                            location=job_dir
                        )
                        jobs.append(state)
                except Exception as e:
                    logger.error(f"Failed to load historical job {meta_file}: {e}")
                    
        return sorted(jobs, key=lambda x: x.created_at, reverse=True)

    def load_state(self, job_id_or_path: Any) -> JobState:
        """Load job state from ID or Path."""
        if isinstance(job_id_or_path, Path):
            job_dir = job_id_or_path
        else:
            job_dir = self._get_job_dir(job_id_or_path)
            
        state_file = job_dir / "state.json"
        if not state_file.exists():
            # Try to find in results if not found (simple search)
            # This is a bit hacky but helps if we only have ID
            pass 
            
        if not state_file.exists():
             raise FileNotFoundError(f"State file not found for job {job_id_or_path}")
        
        with open(state_file, "r") as f:
            data = json.load(f)
        return JobState(**data)

    def load_meta(self, job_id_or_path: Any) -> JobMeta:
        """Load job meta from ID or Path."""
        if isinstance(job_id_or_path, Path):
            job_dir = job_id_or_path
        else:
            job_dir = self._get_job_dir(job_id_or_path)
            
        meta_file = job_dir / "meta.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"Meta file not found for job {job_id_or_path}")
        
        with open(meta_file, "r") as f:
            data = json.load(f)
        return JobMeta(**data)

    def get_ready_jobs(self, stage: StageName) -> List[JobState]:
        """Find jobs ready for a specific stage."""
        jobs = self.list_jobs()
        ready_jobs = []
        
        stage_order = [s.value for s in StageName]
        target_idx = stage_order.index(stage.value)
        
        for job in jobs:
            # We no longer skip completed stages. 
            # If previous stages are done, it's ready for re-execution.
            pass
                
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
        
        # Create result path based on shelve.strategy
        if meta.configuration.shelve.strategy == "zettelkasten":
            # Flat structure: results/zettelkasten/job_id
            # Or maybe just results/job_id? Let's use a subfolder to be clean.
            # User asked for "Flat/Topic-based". 
            # Let's put them in a 'zettelkasten' folder to distinguish from timeline.
            final_dest = results_dir / "zettelkasten" / job_dir.name
        else:
            # Default: Timeline (YYYY/MM/DD)
            date_path = meta.created_at.strftime("%Y/%m/%d")
            final_dest = results_dir / date_path / job_dir.name
            
        final_dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy everything except _stages (unless debug is on)
        if final_dest.exists():
            shutil.rmtree(final_dest)
        
        ignore_patterns = []
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
