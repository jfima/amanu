import argparse
import sys
import os
import logging
import time
from pathlib import Path
from typing import Optional, List

from .core.manager import JobManager
from .core.config import load_config
from .core.models import StageName, StageStatus
from .pipeline import IngestStage, ScribeStage, RefineStage, ShelveStage

# Logger will be initialized after config is loaded
logger = None

def main() -> None:
    global logger
    
    parser = argparse.ArgumentParser(description="Amanu - AI-powered amanuensis.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup
    setup_parser = subparsers.add_parser("setup", help="Run interactive setup wizard")


    # Pipeline Stages
    ingest_parser = subparsers.add_parser("ingest", help="Prepare audio (Analyze/Compress/Upload) [options: --model, --compression-mode]")
    ingest_parser.add_argument("file", help="Input audio file")
    ingest_parser.add_argument("--model", help="Transcribe model override")
    ingest_parser.add_argument("--compression-mode", choices=["original", "compressed", "optimized"], help="Compression mode: original (no compression), compressed (OGG), optimized (OGG + silence removal)")
    
    scribe_parser = subparsers.add_parser("scribe", help="Transcribe audio")
    scribe_parser.add_argument("job", nargs="?", help="Job ID or path")
    scribe_parser.add_argument("--stop-after", choices=["ingest", "scribe", "refine", "generate", "shelve"], help="Stop pipeline after specified stage")
    
    refine_parser = subparsers.add_parser("refine", help="Refine transcript")
    refine_parser.add_argument("job", nargs="?", help="Job ID or path")
    refine_parser.add_argument("--stop-after", choices=["ingest", "scribe", "refine", "generate", "shelve"], help="Stop pipeline after specified stage")
    
    shelve_parser = subparsers.add_parser("shelve", help="Categorize result")
    shelve_parser.add_argument("job", nargs="?", help="Job ID or path")
    shelve_parser.add_argument("--stop-after", choices=["ingest", "scribe", "refine", "generate", "shelve"], help="Stop pipeline after specified stage")

    # Orchestration
    run_parser = subparsers.add_parser("run", help="Run full pipeline [options: --dry-run, --compression-mode]")
    run_parser.add_argument("file", help="Input audio file")
    run_parser.add_argument("--compression-mode", choices=["original", "compressed", "optimized"], help="Compression mode: original (no compression), compressed (OGG), optimized (OGG + silence removal)")
    run_parser.add_argument("--dry-run", action="store_true", help="Simulate run without API calls or file changes")
    run_parser.add_argument("--skip-transcript", action="store_true", help="Skip transcription (Direct Analysis mode)")
    run_parser.add_argument("--shelve-mode", choices=["timeline", "zettelkasten"], default="timeline", help="Shelve mode: timeline (YYYY/MM/DD) or zettelkasten (flat)")
    run_parser.add_argument("--stop-after", choices=["ingest", "scribe", "refine", "generate", "shelve"], help="Stop pipeline after specified stage (job remains in work directory)")    
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

    # Reporting
    report_parser = subparsers.add_parser("report", help="Generate cost & usage report")
    report_parser.add_argument("--days", type=int, default=30, help="Number of days to report (default: 30)")

    args = parser.parse_args()

    # Load config first
    config_context = load_config()
    config = config_context.defaults
    
    # Check for missing configuration (unless running setup or help)
    if args.command != "setup" and args.command is not None:
        # Check if API key is present either in env or config
        gemini_config = config_context.providers.get("gemini")
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key and gemini_config:
            api_key = gemini_config.api_key
        
        if not api_key:
            # Check if we have a valid config file at all
            config_path = Path.home() / ".config" / "amanu" / "config.yaml"
            if not config_path.exists() and not os.environ.get("GEMINI_API_KEY"):
                print("\n[!] Amanu is not configured yet.")
                print("    Please run 'amanu setup' to configure the system and API key.\n")
                # We don't exit here strictly, as some commands might not need it, 
                # but for most operations it's critical.
                # Let's warn but proceed, or exit?
                # Most commands need API key.
                if args.command in ["ingest", "scribe", "refine", "run"]:
                     print("Error: GEMINI_API_KEY is missing.")
                     sys.exit(1)

    
    # Setup logging based on config.debug or --verbose flag
    from .utils import setup_logging
    debug_mode = args.verbose or getattr(config_context.defaults, 'debug', False)
    logger = setup_logging(debug=debug_mode)

    # Global exception handler
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    manager = JobManager(
        work_dir=Path(config_context.paths.work),
        results_dir=Path(config_context.paths.results),
        providers=config_context.providers
    )

    try:
        if args.command == "setup":
            from .wizard import run_wizard
            run_wizard()
            return

        if args.command == "ingest":
            # Ingest stage: Analyze, Compress, Upload
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
                
            logger.info(f"Starting job for {file_path.name}...")
            meta = manager.create_job(file_path, config)
            logger.info(f"Job created: {meta.job_id}")
            
            # Run ingest stage
            stage = IngestStage(manager)
            stage.run(meta.job_id)
            
        elif args.command in ["scribe", "refine", "shelve"]:
            # Map command to stage
            command_to_stage = {
                "scribe": StageName.SCRIBE,
                "refine": StageName.REFINE,
                "shelve": StageName.SHELVE
            }
            stage_name = command_to_stage[args.command]
            job_id = _resolve_job(manager, args.job, stage_name)
            if not job_id:
                sys.exit(1)
                
            # Always reset stage status to ensure imperative execution
            manager.retry_job(job_id, from_stage=stage_name)
                
            # Determine stop_after
            # If --stop-after is provided, use it.
            # If not provided, default to stopping after the requested stage (e.g. 'amanu scribe' stops after scribe)
            # This maintains backward compatibility where 'amanu scribe' just ran scribe.
            stop_after = StageName(args.stop_after) if args.stop_after else stage_name
            
            from .pipeline.base import Pipeline
            pipeline = Pipeline(manager, results_dir=Path(config_context.paths.results))
            pipeline.run_all_stages(job_id, stop_after=stop_after)

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
            
            if args.shelve_mode:
                config.shelve.strategy = args.shelve_mode

            if args.dry_run:
                logger.info("DRY RUN MODE: Skipping actual execution.")
                logger.info(f"Configuration: Compression Mode={config.compression_mode}, Shelve Mode={config.shelve.strategy}")
                logger.info("Would create job and run stages: Scout -> Prep -> Scribe -> Refine -> Shelve -> Finalize")
                return

            # 1. Scout (Now Ingest)
            # Note: We are keeping the old stage names in comments for now, but logic is inside Pipeline.run_all_stages
            # Actually, Pipeline.run_all_stages runs everything. We don't need to call individual stages here if we use run_all_stages.
            # But wait, the original code called individual stages.
            # My new Pipeline.run_all_stages calls them all.
            # So I should replace the manual calls with the single pipeline call.
            
            # Instantiate pipeline
            from .pipeline.base import Pipeline
            pipeline = Pipeline(manager, results_dir=Path(config_context.paths.results))
            
            meta = manager.create_job(file_path, config)
            job_id = meta.job_id
            
            stop_after = StageName(args.stop_after) if args.stop_after else None
            pipeline.run_all_stages(job_id, skip_transcript=args.skip_transcript, stop_after=stop_after)
            return 0

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



        elif args.command == "report":
            from .core.reporting import CostReporter
            reporter = CostReporter(manager)
            reporter.print_report(days=args.days)

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
