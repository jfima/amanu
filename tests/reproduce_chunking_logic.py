import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from amanu.pipeline.scout import ScoutStage
from amanu.core.models import JobMeta, JobConfiguration, ModelSpec, ModelContextWindow

def test_chunking_logic():
    print("Testing chunking logic...")
    
    # Setup Mock
    mock_manager = MagicMock()
    scout = ScoutStage(mock_manager)
    
    # Case 1: Large file (1h 40m = 6000s) with Gemini 2.0 Flash (8k output limit)
    print("\nCase 1: 1h 40m file with Gemini 2.0 Flash")
    input_tokens = 200000 # Well within 1M limit
    input_limit = 1048576
    output_limit = 8192
    duration = 6000.0
    
    decision = scout._decide_chunking(input_tokens, input_limit, output_limit, duration)
    
    print(f"Decision: {decision['needs_chunking']}")
    print(f"Reason: {decision['reason']}")
    
    if decision['needs_chunking'] and "Estimated output" in decision['reason']:
        print("PASS: Correctly decided to chunk based on output limit.")
    else:
        print("FAIL: Should have decided to chunk based on output limit.")

    # Case 2: Short file (5m = 300s) with Gemini 2.0 Flash
    print("\nCase 2: 5m file with Gemini 2.0 Flash")
    input_tokens = 10000
    duration = 300.0
    
    decision = scout._decide_chunking(input_tokens, input_limit, output_limit, duration)
    
    print(f"Decision: {decision['needs_chunking']}")
    print(f"Reason: {decision['reason']}")
    
    if not decision['needs_chunking']:
        print("PASS: Correctly decided NOT to chunk.")
    else:
        print("FAIL: Should NOT have chunked.")

if __name__ == "__main__":
    test_chunking_logic()
