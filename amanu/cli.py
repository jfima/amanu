import argparse
import sys
import logging
import time
from pathlib import Path
from typing import Optional, List

from .core.manager import JobManager
from .core.config import load_config
from .core.models import StageName, StageStatus
from .pipeline import ScoutStage, PrepStage, ScribeStage, RefineStage, ShelveStage

# Logger will be initialized after config is loaded
logger = None

def main() -> None:
    global logger
    
    parser = argparse.ArgumentParser(description="Amanu - AI-powered amanuensis.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Pipeline Stages
    scout_parser = subparsers.add_parser("scout", help="Hire amanuensis (Start job) [options: --model, --compression-mode]")
    scout_parser.add_argument("file", help="Input audio file")
    scout_parser.add_argument("--model", help="Transcribe model override")
    scout_parser.add_argument("--compression-mode", choices=["original", "compressed", "optimized"], help="Compression mode: original (no compression), compressed (OGG), optimized (OGG + silence removal)")
    
    prep_parser = subparsers.add_parser("prep", help="Prepare audio (Compress/Chunk)")
    prep_parser.add_argument("job", nargs="?", help="Job ID or path")
    
    scribe_parser = subparsers.add_parser("scribe", help="Transcribe audio")
    scribe_parser.add_argument("job", nargs="?", help="Job ID or path")
    
    refine_parser = subparsers.add_parser("refine", help="Refine transcript")
    refine_parser.add_argument("job", nargs="?", help="Job ID or path")
    
    shelve_parser = subparsers.add_parser("shelve", help="Categorize result")
    shelve_parser.add_argument("job", nargs="?", help="Job ID or path")

    # Orchestration
    run_parser = subparsers.add_parser("run", help="Run full pipeline [options: --template, --dry-run, --compression-mode]")
    run_parser.add_argument("file", help="Input audio file")
    run_parser.add_argument("--compression-mode", choices=["original", "compressed", "optimized"], help="Compression mode: original (no compression), compressed (OGG), optimized (OGG + silence removal)")
    run_parser.add_argument("--template", help="Override output template (e.g., 'summary', 'default')")
    run_parser.add_argument("--dry-run", action="store_true", help="Simulate run without API calls or file changes")
    
    watch_parser = subparsers.add_parser("watch", help="Watch input directory")
    
    # Jobs management
    jobs_parser = subparsers.add_parser("jobs", help="Manage jobs (list, show, retry, cleanup, finalize, delete)")
    jobs_subparsers = jobs_parser.add_subparsers(dest="jobs_command", help="Jobs commands")
    
    jobs_list_parser = jobs_subparsers.add_parser("list", help="List jobs")
    jobs_list_parser.add_argument("--status", choices=["failed", "completed", "all"], default="all", help="Filter by status")
    
    jobs_show_parser = jobs_subparsers.add_parser("show", help="Show job details")
    jobs_show_parser.add_argument("job_id", help="Job ID")
    
    jobs_retry_parser = jobs_subparsers.add_parser("retry", help="Retry failed job")
    jobs_retry_parser.add_argument("job_id", help="Job ID")
    jobs_retry_parser.add_argument("--from-stage", choices=[s.value for s in StageName], help="Stage to retry from")
    
    jobs_cleanup_parser = jobs_subparsers.add_parser("cleanup", help="Cleanup old jobs")
    jobs_cleanup_parser.add_argument("--older-than", type=int, default=7, help="Remove jobs older than N days")
    jobs_cleanup_parser.add_argument("--status", choices=["failed", "completed"], default="failed", help="Status to cleanup")

    jobs_finalize_parser = jobs_subparsers.add_parser("finalize", help="Finalize job (Move to results)")
    jobs_finalize_parser.add_argument("job_id", help="Job ID")

    jobs_delete_parser = jobs_subparsers.add_parser("delete", help="Delete job")
    jobs_delete_parser.add_argument("job_id", help="Job ID")

    args = parser.parse_args()

    # Load config first
    config_context = load_config()
    config = config_context.defaults
    
    # Setup logging based on config.debug or --verbose flag
    from .utils import setup_logging
    debug_mode = args.verbose or getattr(config_context.defaults, 'debug', False)
    logger = setup_logging(debug=debug_mode)

    manager = JobManager()

    try:
        if args.command == "scout":
            # Handle hiring
            file_path = Path(args.file)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                sys.exit(1)
            
            supported_exts = {'.mp3', '.wav', '.ogg', '.m4a', '.mp4', '.mov', '.mkv', '.webm'}
            if file_path.suffix.lower() not in supported_exts:
                logger.error(f"Unsupported file format: {file_path.suffix}. Supported: {', '.join(supported_exts)}")
                sys.exit(1)
                
            # Override config if needed
            if args.model:
                # Lookup model in available_models
                found = False
                for m in config_context.available_models:
                    if m.name == args.model:
                        config.transcribe = m
                        config.refine = m # Assuming same model for both if overridden, or we need separate args
                        found = True
                        break
                if not found:
                    logger.error(f"Model {args.model} not found in configuration.")
                    sys.exit(1)
            
            
            if args.compression_mode:
                config.compression_mode = args.compression_mode
                
            logger.info(f"Commissioning job for {file_path.name}...")
            meta = manager.create_job(file_path, config)
            logger.info(f"Job created: {meta.job_id}")
            
            # Run scout stage
            stage = ScoutStage(manager)
            stage.run(meta.job_id)
            
        elif args.command in ["prep", "scribe", "refine", "shelve"]:
            stage_name = StageName(args.command)
            job_id = _resolve_job(manager, args.job, stage_name)
            if not job_id:
                sys.exit(1)
                
            stage_map = {
                StageName.PREP: PrepStage,
                StageName.SCRIBE: ScribeStage,
                StageName.REFINE: RefineStage,
                StageName.SHELVE: ShelveStage
            }
            
            stage = stage_map[stage_name](manager)
            stage.run(job_id)

        elif args.command == "run":
            # Full pipeline
            file_path = Path(args.file)
            
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                sys.exit(1)
            
            supported_exts = {'.mp3', '.wav', '.ogg', '.m4a', '.mp4', '.mov', '.mkv', '.webm'}
            if file_path.suffix.lower() not in supported_exts:
                logger.error(f"Unsupported file format: {file_path.suffix}. Supported: {', '.join(supported_exts)}")
                sys.exit(1)

            logger.info(f"Running full pipeline for {file_path.name}...")
            
            if args.compression_mode:
                config.compression_mode = args.compression_mode
            
            if args.template:
                config.template = args.template
                logger.info(f"Using template: {config.template}")

            if args.dry_run:
                logger.info("DRY RUN MODE: Skipping actual execution.")
                logger.info(f"Configuration: Template={config.template}, Compression Mode={config.compression_mode}")
                logger.info("Would create job and run stages: Scout -> Prep -> Scribe -> Refine -> Shelve -> Finalize")
                return

            # 1. Scout
            meta = manager.create_job(file_path, config) # config is already defaults from context
            job_id = meta.job_id
            ScoutStage(manager).run(job_id)
            
            # 2. Prep
            PrepStage(manager).run(job_id)
            
            # 3. Scribe
            ScribeStage(manager).run(job_id)
            
            # 4. Refine
            RefineStage(manager).run(job_id)
            
            # 5. Shelve (Optional)
            try:
                ShelveStage(manager).run(job_id)
            except Exception as e:
                logger.warning(f"Shelve stage failed (non-critical): {e}")
                
            # 6. Finalize
            # Load meta BEFORE finalizing (moving) the job
            meta = manager.load_meta(job_id)
            result_path = manager.finalize_job(job_id, Path(config_context.paths.results))
            logger.info(f"Job completed! Results at: {result_path}")
            
            # Display Stats
            stats = meta.processing
            print(f"\n{'='*40}")
            print(f"Processing Summary for {job_id}")
            print(f"{'='*40}")
            print(f"Requests:      {stats.request_count}")
            print(f"Input Tokens:  {stats.total_tokens.input}")
            print(f"Output Tokens: {stats.total_tokens.output}")
            print(f"Total Cost:    ${stats.total_cost_usd:.4f}")
            print(f"{'='*40}\n")

        elif args.command == "watch":
            from .watcher import FileWatcher
            watcher = FileWatcher(config_context)
            watcher.start()

        elif args.command == "jobs":
            if args.jobs_command == "list":
                jobs = manager.list_jobs()
                
                # Filter by status
                if args.status == "failed":
                    jobs = [j for j in jobs if any(s.status == StageStatus.FAILED for s in j.stages.values())]
                elif args.status == "completed":
                    jobs = [j for j in jobs if all(s.status == StageStatus.COMPLETED for s in j.stages.values())]
                
                if not jobs:
                    print(f"No {args.status} jobs found.")
                else:
                    print(f"{'Job ID':<30} {'Stage':<10} {'Status':<15} {'Updated':<20}")
                    print("-" * 80)
                    for job in jobs:
                        # Determine overall status
                        has_failed = any(s.status == StageStatus.FAILED for s in job.stages.values())
                        status_str = "FAILED" if has_failed else job.current_stage
                        print(f"{job.job_id:<30} {job.current_stage:<10} {status_str:<15} {job.updated_at.strftime('%Y-%m-%d %H:%M')}")
            
            elif args.jobs_command == "show":
                try:
                    state = manager.load_state(args.job_id)
                    meta = manager.load_meta(args.job_id)
                    
                    print(f"\n{'='*60}")
                    print(f"Job: {state.job_id}")
                    print(f"Original File: {state.original_file}")
                    print(f"Created: {state.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"Updated: {state.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"Current Stage: {state.current_stage}")
                    print(f"\nConfiguration:")
                    print(f"  Template: {meta.configuration.template}")
                    print(f"  Language: {meta.configuration.language}")
                    print(f"  Transcribe Model: {meta.configuration.transcribe.name}")
                    print(f"  Refine Model: {meta.configuration.refine.name}")
                    print(f"\nStages:")
                    for stage, s_state in state.stages.items():
                        status_icon = "✓" if s_state.status == StageStatus.COMPLETED else "✗" if s_state.status == StageStatus.FAILED else "○"
                        print(f"  [{status_icon}] {stage.value:<10} {s_state.status.value}")
                        if s_state.error:
                            print(f"      Error: {s_state.error}")
                    
                    if state.errors:
                        print(f"\nErrors:")
                        for err in state.errors:
                            print(f"  - [{err['timestamp']}] {err['stage']}: {err['error']}")
                    print(f"{'='*60}\n")
                    
                except Exception as e:
                    logger.error(f"Failed to load job: {e}")
            
            elif args.jobs_command == "retry":
                try:
                    from_stage = StageName(args.from_stage) if args.from_stage else None
                    manager.retry_job(args.job_id, from_stage=from_stage)
                    logger.info(f"Job {args.job_id} reset for retry")
                    
                    # Optionally run the pipeline
                    from .pipeline.base import Pipeline
                    pipeline = Pipeline(manager, results_dir=Path(config_context.paths.results))
                    pipeline.run_all_stages(args.job_id)
                    logger.info(f"Job {args.job_id} completed successfully")
                    
                except Exception as e:
                    logger.error(f"Failed to retry job: {e}")
            
            elif args.jobs_command == "cleanup":
                try:
                    status_filter = StageStatus.FAILED if args.status == "failed" else StageStatus.COMPLETED
                    removed = manager.cleanup_old_jobs(args.older_than, status_filter=status_filter)
                    logger.info(f"Cleaned up {removed} old {args.status} job(s)")
                except Exception as e:
                    logger.error(f"Failed to cleanup jobs: {e}")
            
            elif args.jobs_command == "finalize":
                try:
                    result_path = manager.finalize_job(args.job_id, Path(config_context.paths.results))
                    logger.info(f"Finalized to: {result_path}")
                except Exception as e:
                    logger.error(f"Failed to finalize: {e}")

            elif args.jobs_command == "delete":
                try:
                    import shutil
                    job_dir = manager._get_job_dir(args.job_id)
                    if job_dir.exists():
                        shutil.rmtree(job_dir)
                        logger.info(f"Deleted job: {args.job_id}")
                    else:
                        logger.error(f"Job not found: {args.job_id}")
                except Exception as e:
                    logger.error(f"Failed to delete: {e}")

        else:
            parser.print_help()

    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def _resolve_job(manager: JobManager, job_arg: Optional[str], stage: StageName) -> Optional[str]:
    if job_arg:
        return job_arg
        
    # Smart detection
    ready_jobs = manager.get_ready_jobs(stage)
    
    if not ready_jobs:
        logger.error(f"No jobs ready for {stage.value} stage.")
        return None
        
    if len(ready_jobs) == 1:
        job = ready_jobs[0]
        logger.info(f"Auto-selected job: {job.job_id}")
        return job.job_id
        
    logger.error(f"Multiple jobs ready for {stage.value}. Please specify one:")
    for job in ready_jobs:
        print(f"  {job.job_id}")
    return None

if __name__ == "__main__":
    main()
