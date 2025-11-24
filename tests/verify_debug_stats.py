import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from amanu.core.models import JobMeta, JobConfiguration, ModelSpec, ModelContextWindow, PricingModel, ProcessingStats
from amanu.core.manager import JobManager
from amanu.pipeline.scribe import ScribeStage
from amanu.pipeline.refine import RefineStage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Test")

def create_mock_meta():
    pricing = PricingModel(input=0.1, output=0.4)
    context = ModelContextWindow(input_tokens=1000, output_tokens=1000)
    model_spec = ModelSpec(name="test-model", context_window=context, cost_per_1M_tokens_usd=pricing)
    
    config = JobConfiguration(
        template="default",
        language="en",
        debug=True,
        transcribe=model_spec,
        refine=model_spec
    )
    
    return JobMeta(
        job_id="test_job",
        original_file="test.mp3",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        configuration=config
    )

def test_debug_flag():
    logger.info("Testing Debug Flag...")
    manager = JobManager(work_dir=Path("test_work"))
    
    # Create dummy job dir
    job_dir = manager.work_dir / "test_job"
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "_stages").mkdir(exist_ok=True)
    (job_dir / "_stages" / "test.txt").write_text("stage data")
    
    # Mock load_meta to return debug=True
    meta = create_mock_meta()
    meta.configuration.debug = True
    
    with patch.object(manager, 'load_meta', return_value=meta):
        with patch.object(manager, '_get_job_dir', return_value=job_dir):
            results_dir = Path("test_results")
            if results_dir.exists():
                shutil.rmtree(results_dir)
                
            manager.finalize_job("test_job", results_dir)
            
            # Check if _stages exists in results
            # Results structure: results/YYYY/MM/DD/test_job
            date_path = meta.created_at.strftime("%Y/%m/%d")
            result_job_dir = results_dir / date_path / "test_job"
            
            if (result_job_dir / "_stages").exists():
                logger.info("PASS: _stages preserved when debug=True")
            else:
                logger.error("FAIL: _stages NOT preserved when debug=True")

    # Cleanup
    if job_dir.exists():
        shutil.rmtree(job_dir)
    if results_dir.exists():
        shutil.rmtree(results_dir)

def test_stats_collection():
    logger.info("Testing Stats Collection...")
    
    # Mock ScribeStage
    manager = MagicMock()
    stage = ScribeStage(manager)
    
    meta = create_mock_meta()
    job_dir = Path("test_job_dir")
    
    # Mock internal methods to avoid real execution
    stage._configure_gemini = MagicMock()
    stage._load_prep_result = MagicMock(return_value={"cache_name": "test_cache"})
    
    # Mock genai
    with patch("amanu.pipeline.scribe.genai") as mock_genai:
        with patch("amanu.pipeline.scribe.caching") as mock_caching:
            # Setup mocks
            mock_model = MagicMock()
            mock_chat = MagicMock()
            mock_genai.GenerativeModel.from_cached_content.return_value = mock_model
            mock_model.start_chat.return_value = mock_chat
            
            # Mock responses
            response_1 = MagicMock()
            response_1.text = "Ready"
            response_1.usage_metadata.prompt_token_count = 10
            response_1.usage_metadata.candidates_token_count = 5
            
            response_2 = MagicMock()
            response_2.text = '{"text": "Hello"}'
            response_2.usage_metadata.prompt_token_count = 20
            response_2.usage_metadata.candidates_token_count = 10
            # Make response_2 iterable for the loop
            response_2.__iter__.return_value = [response_2]
            
            mock_chat.send_message.side_effect = [response_1, response_2]
            
            # Run execute (will fail at file operations but we check stats before that or mock file ops)
            # We need to mock file ops
            with patch("builtins.open", MagicMock()):
                with patch("pathlib.Path.mkdir", MagicMock()):
                    # We also need to mock _parse_jsonl to return something valid so it doesn't loop forever
                    stage._parse_jsonl = MagicMock(return_value=([{"text": "Hello", "end_time": 100.0}], False))
                    
                    # Set audio duration to match end time to stop loop
                    meta.audio.duration_seconds = 100.0
                    
                    try:
                        stage.execute(job_dir, meta)
                    except Exception as e:
                        # It might fail on something else, but let's check stats
                        logger.warning(f"Execution finished with: {e}")
                        pass
                    
                    # Check stats
                    if meta.processing.request_count >= 2:
                        logger.info(f"PASS: request_count = {meta.processing.request_count}")
                    else:
                        logger.error(f"FAIL: request_count = {meta.processing.request_count}")
                        
                    if len(meta.processing.steps) >= 2:
                        logger.info(f"PASS: steps recorded = {len(meta.processing.steps)}")
                        logger.info(f"Step 1: {meta.processing.steps[0]}")
                    else:
                        logger.error(f"FAIL: steps recorded = {len(meta.processing.steps)}")

if __name__ == "__main__":
    test_debug_flag()
    test_stats_collection()
