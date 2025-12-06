import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from amanu.core.models import JobMeta, JobObject, JobConfiguration, StageConfig, ProcessingStats
from amanu.core.manager import JobManager
from amanu.pipeline.scribe import ScribeStage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Test")

def create_mock_job_and_meta():
    stage_config = StageConfig(provider="gemini", model="gemini-1.5-flash")
    
    config = JobConfiguration(
        transcribe=stage_config,
        refine=stage_config,
        debug=True
    )
    
    job_id = "test_job"
    timestamp = datetime.now()
    
    job = JobObject(
        job_id=job_id,
        created_at=timestamp,
        updated_at=timestamp,
        configuration=config,
        current_stage="ingest",
        ingest_result={"gemini": {"cache_name": "test_cache"}} # Mock ingest result
    )
    
    meta = JobMeta(
        original_file="test.mp3",
        created_at=timestamp
    )
    
    return job, meta

def test_debug_flag():
    logger.info("Testing Debug Flag...")
    manager = JobManager(work_dir=Path("test_work"))
    
    # Create dummy job dir
    job_dir = manager.work_dir / "test_job"
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a dummy file that should be kept/pruned
    (job_dir / "transcripts").mkdir(exist_ok=True)
    (job_dir / "transcripts" / "test.txt").write_text("transcript data")
    
    job, meta = create_mock_job_and_meta()
    
    # Test 1: Debug = True (Should keep files)
    job.configuration.debug = True
    
    with patch.object(manager, 'load_job_object', return_value=job):
        with patch.object(manager, 'load_meta', return_value=meta): 
            with patch.object(manager, '_get_job_dir', return_value=job_dir):
                results_dir = Path("test_results")
                if results_dir.exists():
                    shutil.rmtree(results_dir)
                    
                manager.finalize_job("test_job", results_dir)
                
                # Results structure: results/YYYY/MM/DD/test_job
                date_path = meta.created_at.strftime("%Y/%m/%d")
                result_job_dir = results_dir / date_path / "test_job"
                
                # In finalize, we COPY to results. The original work dir is what gets pruned or not.
                # Actually manager.finalize_job copies then prunes WORK dir.
                # We should check if files still exist in JOB DIR (Work dir)
                
                # Check WORK dir preservation
                if (job_dir / "transcripts" / "test.txt").exists():
                    logger.info("PASS: work files preserved when debug=True")
                else:
                    logger.error("FAIL: work files NOT preserved when debug=True")

    # Test 2: Debug = False (Should prune files)
    job.configuration.debug = False
    
    # Re-create file because it might have been moved/deleted? 
    # finalize_job does copytree then prune.
    (job_dir / "transcripts").mkdir(exist_ok=True)
    (job_dir / "transcripts" / "test.txt").write_text("transcript data")
    
    with patch.object(manager, 'load_job_object', return_value=job):
        with patch.object(manager, 'load_meta', return_value=meta):
             with patch.object(manager, '_get_job_dir', return_value=job_dir):
                if results_dir.exists():
                    shutil.rmtree(results_dir)
                    
                manager.finalize_job("test_job", results_dir)
                
                # Check WORK dir pruning. 
                # Transcripts folder should be deleted or empty? 
                # Manager logic: "delete: media, transcripts, artifacts"
                if not (job_dir / "transcripts").exists():
                     logger.info("PASS: work files pruned when debug=False")
                else:
                     logger.error("FAIL: work files NOT pruned when debug=False")

    # Cleanup
    if job_dir.exists():
        shutil.rmtree(job_dir)
    if results_dir.exists():
        shutil.rmtree(results_dir)
    if manager.work_dir.exists():
        shutil.rmtree(manager.work_dir)

def test_stats_collection():
    logger.info("Testing Stats Collection...")
    
    # Mock Manager
    manager = MagicMock()
    # Mock provider config
    manager.providers = {}
    
    stage = ScribeStage(manager)
    
    job, meta = create_mock_job_and_meta()
    job_dir = Path("test_job_dir")
    
    # We need to mock ProviderFactory to return a mock provider
    with patch("amanu.pipeline.scribe.ProviderFactory") as MockFactory:
        mock_provider = MagicMock()
        MockFactory.create.return_value = mock_provider
        
        # Setup mock result
        mock_result = {
            "segments": [{"text": "Hello", "start": 0.0, "end": 1.0}],
            "tokens": {"input": 100, "output": 50},
            "cost_usd": 0.05,
            "analysis": {"language": "en"}
        }
        mock_provider.transcribe.return_value = mock_result
        
        # Mock file operations to prevent writing to disk
        with patch("builtins.open", MagicMock()):
            with patch("pathlib.Path.mkdir", MagicMock()):
                with patch("json.dump", MagicMock()):
                    
                    # Run execute
                    try:
                        result = stage.execute(job_dir, job)
                    except Exception as e:
                        logger.error(f"Execution failed: {e}")
                        return

                    # Check stats on JOB object
                    if job.processing.request_count == 1:
                        logger.info(f"PASS: request_count incremented")
                    else:
                        logger.error(f"FAIL: request_count mismatch: {job.processing.request_count}")
                        
                    if job.processing.total_tokens.input == 100:
                        logger.info(f"PASS: input tokens updated")
                    else:
                        logger.error(f"FAIL: input tokens mismatch")
                        
                    steps = job.processing.steps
                    if len(steps) == 1 and steps[0]["stage"] == "scribe":
                         logger.info(f"PASS: step recorded")
                    else:
                         logger.error(f"FAIL: step not recorded correctly")

if __name__ == "__main__":
    test_debug_flag()
    test_stats_collection()
