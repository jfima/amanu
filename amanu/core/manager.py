import json
import shutil
import logging
from pathlib import Path
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from .models import (
    JobMeta, StageName, StageStatus,
    StageState, JobConfiguration, JobObject
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

    def _get_file_creation_date(self, file_path: Path) -> Optional[datetime]:
        """
        Attempts to get the creation date of a file.
        Prioritizes st_birthtime (macOS/some Linux) then ctime (Windows/Linux metadata change).
        """
        try:
            stat_info = file_path.stat()
            if hasattr(stat_info, 'st_birthtime'):
                return datetime.fromtimestamp(stat_info.st_birthtime)
            else:
                # Fallback for systems without st_birthtime (e.g., some Linux)
                return datetime.fromtimestamp(stat_info.st_ctime)
        except Exception as e:
            logger.warning(f"Could not get creation date for {file_path}: {e}")
            return None

    def create_job(self, file_path: Path, config: JobConfiguration) -> JobObject:
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
        
        # Copy original file
        dest_file = job_dir / "media" / f"original{file_path.suffix}"
        shutil.copy2(file_path, dest_file)
        
        # Get original file creation date
        original_file_creation_date = self._get_file_creation_date(file_path)

        # Create Job Object (Dynamic State)
        job = JobObject(
            job_id=job_id,
            created_at=timestamp,
            updated_at=timestamp,
            configuration=config,
            current_stage=StageName.INGEST.value
        )
        self.save_job_object(job_dir, job)
        
        # Create Initial Meta (Static properties)
        meta = JobMeta(
            original_file=file_path.name,
            original_file_creation_date=original_file_creation_date,
            created_at=timestamp
        )
        self.save_meta(job_dir, meta)
        
        return job

    def save_job_object(self, job_dir: Path, job: JobObject) -> None:
        job.updated_at = datetime.now()
        with open(job_dir / "_job.json", "w") as f:
            f.write(job.model_dump_json(indent=2))

    def load_job_object(self, job_id_or_path: Any) -> JobObject:
        if isinstance(job_id_or_path, Path):
            job_dir = job_id_or_path
        else:
            job_dir = self._get_job_dir(job_id_or_path)
            
        job_file = job_dir / "_job.json"
        if not job_file.exists():
            raise FileNotFoundError(f"Job object not found for {job_id_or_path}")
            
        with open(job_file, "r") as f:
            data = json.load(f)
        return JobObject(**data)

    def save_meta(self, job_dir: Path, meta: JobMeta) -> None:
        with open(job_dir / "_meta.json", "w") as f:
            f.write(meta.model_dump_json(indent=2))

    def update_stage_status(self, job_id: str, stage: StageName, status: StageStatus, error: Optional[str] = None) -> None:
        job_dir = self._get_job_dir(job_id)
        job = self.load_job_object(job_dir)
        
        job.stages[stage].status = status
        job.stages[stage].timestamp = datetime.now()
        
        if error:
            job.stages[stage].error = error
            job.errors.append({
                "stage": stage.value,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
        
        if status == StageStatus.IN_PROGRESS:
            job.current_stage = stage.value
            
        self.save_job_object(job_dir, job)
    
    def list_jobs(self, include_history: bool = False) -> List[JobObject]:
        """List all jobs from work directory."""
        jobs = []
        
        if self.work_dir.exists():
            for job_dir in self.work_dir.iterdir():
                if not job_dir.is_dir(): 
                    continue
                
                if not (job_dir / "_job.json").exists():
                    continue
                    
                try:
                    job_obj = self.load_job_object(job_dir)
                    jobs.append(job_obj)
                except Exception as e:
                    logger.error(f"Failed to load job {job_dir.name}: {e}")
                    
        return sorted(jobs, key=lambda x: x.created_at, reverse=True)


    def load_meta(self, job_id_or_path: Any) -> JobMeta:
        """Load job meta from ID or Path."""
        if isinstance(job_id_or_path, Path):
            job_dir = job_id_or_path
        else:
            job_dir = self._get_job_dir(job_id_or_path)
            
        meta_file = job_dir / "_meta.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"Meta file not found for job {job_id_or_path}")
        
        with open(meta_file, "r") as f:
            data = json.load(f)
        return JobMeta(**data)

    def get_ready_jobs(self, stage: StageName) -> List[JobObject]:
        """Find jobs ready for a specific stage."""
        jobs = self.list_jobs()
        ready_jobs = []
        
        stage_order = [s.value for s in StageName]
        target_idx = stage_order.index(stage.value)
        
        for job in jobs:
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
        job = self.load_job_object(job_id)
        meta = self.load_meta(job_id)
        
               
        # Create result path based on shelve.strategy
        if job.configuration.shelve.strategy == "zettelkasten":
            final_dest = results_dir / "zettelkasten" / job_dir.name
        else:
            # Default: Timeline (YYYY/MM/DD)
            date_path = meta.created_at.strftime("%Y/%m/%d")
            final_dest = results_dir / date_path / job_dir.name
            
        final_dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy to results
        if final_dest.exists():
            shutil.rmtree(final_dest)
        
        # In results, we copy everything except potentially temp files if we wanted to be strict.
        # But usually results should have the full context.
        # We'll copy everything.
            
        shutil.copytree(job_dir, final_dest)
        
        # Cleanup work dir (Pruning)
        if not job.configuration.debug:
            logger.info(f"Pruning work directory {job_dir} (Debug=False)")
            # We want to keep: _job.json, _meta.json, api_calls.log
            # We want to delete: media, transcripts, artifacts, _stages (if it exists)
            
            # List of files/dirs to KEEP
            keep_files = ["_job.json", "_meta.json", "api_calls.log"]
            
            for item in job_dir.iterdir():
                if item.name not in keep_files:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            
        else:
            logger.info(f"Debug mode enabled: Preserving full work directory at {job_dir}")
        
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
                job = self.load_job_object(job_dir.name)
                
                # Check if job is old enough
                if job.updated_at > cutoff_date:
                    continue
                    
                # Check status filter
                if status_filter:
                    # Check if any stage has the target status
                    has_status = any(
                        stage_state.status == status_filter 
                        for stage_state in job.stages.values()
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
        """Retry a job from a specific stage."""
        job_dir = self._get_job_dir(job_id)
        job = self.load_job_object(job_dir)
        
        if from_stage is None:
            # Find first failed stage
            for stage in StageName:
                if job.stages[stage].status == StageStatus.FAILED:
                    from_stage = stage
                    break
            if from_stage is None:
                raise ValueError(f"No failed stages found in job {job_id}")
        
        # Reset this stage and all following stages to PENDING
        stage_order = list(StageName)
        start_idx = stage_order.index(from_stage)
        
        for stage in stage_order[start_idx:]:
            job.stages[stage] = StageState(status=StageStatus.PENDING)
        
        job.current_stage = from_stage.value
        job.errors = []
        self.save_job_object(job_dir, job)
        
        logger.info(f"Reset job {job_id} to retry from stage {from_stage.value}")
