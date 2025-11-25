import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from .manager import JobManager
from .models import JobMeta, StageStatus

logger = logging.getLogger("Amanu.Reporting")

class CostReporter:
    def __init__(self, job_manager: JobManager):
        self.manager = job_manager

    def generate_summary(self, days: int = 30) -> Dict[str, Any]:
        """Generate a cost and usage summary for the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        jobs = self.manager.list_jobs(include_history=True)
        
        summary = {
            "period_days": days,
            "total_jobs": 0,
            "total_cost_usd": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_time_seconds": 0.0,
            "jobs_by_status": {},
            "jobs_by_model": {}
        }
        
        for job_state in jobs:
            # Filter by date
            if job_state.created_at < cutoff_date:
                continue
                
            try:
                # Use location if available, otherwise fallback to ID (which checks work_dir)
                load_arg = job_state.location if job_state.location else job_state.job_id
                meta = self.manager.load_meta(load_arg)
                stats = meta.processing
                
                summary["total_jobs"] += 1
                summary["total_cost_usd"] += stats.total_cost_usd
                summary["total_input_tokens"] += stats.total_tokens.input
                summary["total_output_tokens"] += stats.total_tokens.output
                summary["total_time_seconds"] += stats.total_time_seconds
                
                # Status count
                status = job_state.current_stage
                summary["jobs_by_status"][status] = summary["jobs_by_status"].get(status, 0) + 1
                
                # Model count (Transcribe model as primary)
                model = meta.configuration.transcribe.name
                summary["jobs_by_model"][model] = summary["jobs_by_model"].get(model, 0) + 1
                
            except Exception as e:
                logger.warning(f"Could not load meta for job {job_state.job_id}: {e}")
                
        return summary

    def print_report(self, days: int = 30):
        """Print a formatted report to stdout."""
        summary = self.generate_summary(days)
        
        print(f"\n{'='*50}")
        print(f"Amanu Cost & Usage Report (Last {days} days)")
        print(f"{'='*50}")
        
        print(f"Total Jobs:        {summary['total_jobs']}")
        print(f"Total Cost:        ${summary['total_cost_usd']:.4f}")
        print(f"Total Tokens:      {summary['total_input_tokens'] + summary['total_output_tokens']:,}")
        print(f"  - Input:         {summary['total_input_tokens']:,}")
        print(f"  - Output:        {summary['total_output_tokens']:,}")
        
        avg_cost = summary['total_cost_usd'] / summary['total_jobs'] if summary['total_jobs'] > 0 else 0
        print(f"Avg Cost/Job:      ${avg_cost:.4f}")
        
        print(f"\nJobs by Status:")
        for status, count in summary['jobs_by_status'].items():
            print(f"  - {status:<15} {count}")
            
        print(f"\nJobs by Model:")
        for model, count in summary['jobs_by_model'].items():
            print(f"  - {model:<15} {count}")
            
        print(f"{'='*50}\n")
