"""
Test script for OpenRouter provider.
This script verifies that the OpenRouter provider can be loaded and configured correctly.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from amanu.providers.openrouter import OpenRouterConfig
from amanu.providers.openrouter.provider import OpenRouterTranscriptionProvider, OpenRouterRefinementProvider
from amanu.core.models import JobConfiguration, StageConfig
from pydantic import SecretStr

def test_config_loading():
    """Test that OpenRouter config can be loaded."""
    print("Testing OpenRouter config loading...")
    
    config = OpenRouterConfig(
        api_key=SecretStr("test_key"),
        site_url="https://github.com/test/amanu",
        app_name="amanu-test"
    )
    
    assert config.api_key.get_secret_value() == "test_key"
    assert config.site_url == "https://github.com/test/amanu"
    assert config.app_name == "amanu-test"
    
    print("✓ Config loading test passed")

def test_provider_initialization():
    """Test that providers can be initialized."""
    print("\nTesting provider initialization...")
    
    # Set environment variable for API key
    os.environ["OPENROUTER_API_KEY"] = "test_key_from_env"
    
    job_config = JobConfiguration(
        transcribe=StageConfig(
            provider="openrouter",
            model="mistralai/voxtral-small-24b-2507"
        ),
        refine=StageConfig(
            provider="openrouter",
            model="google/gemini-2.0-flash-lite-001"
        )
    )
    
    provider_config = OpenRouterConfig(
        site_url="https://github.com/test/amanu",
        app_name="amanu-test"
    )
    
    # Test transcription provider
    try:
        transcription_provider = OpenRouterTranscriptionProvider(job_config, provider_config)
        assert transcription_provider.client is not None
        print("✓ Transcription provider initialized")
    except Exception as e:
        print(f"✗ Transcription provider initialization failed: {e}")
        return False
    
    # Test refinement provider
    try:
        refinement_provider = OpenRouterRefinementProvider(job_config, provider_config)
        assert refinement_provider.client is not None
        print("✓ Refinement provider initialized")
    except Exception as e:
        print(f"✗ Refinement provider initialization failed: {e}")
        return False
    
    return True

def test_ingest_specs():
    """Test that ingest specs are correct."""
    print("\nTesting ingest specs...")
    
    specs = OpenRouterTranscriptionProvider.get_ingest_specs()
    
    assert specs.target_format == "mp3"
    assert specs.requires_upload == False
    assert specs.upload_target == "none"
    
    print("✓ Ingest specs test passed")

def test_jsonl_parsing():
    """Test JSONL response parsing."""
    print("\nTesting JSONL parsing...")
    
    os.environ["OPENROUTER_API_KEY"] = "test_key"
    
    job_config = JobConfiguration(
        transcribe=StageConfig(
            provider="openrouter",
            model="test-model"
        ),
        refine=StageConfig(
            provider="openrouter",
            model="test-model"
        )
    )
    
    provider_config = OpenRouterConfig()
    provider = OpenRouterTranscriptionProvider(job_config, provider_config)
    
    # Test with sample JSONL response
    sample_response = '''{"speakers": ["Alice", "Bob"], "language": "en"}
[0.0, 5.2, "Alice", "Hello, how are you?"]
[5.2, 10.5, "Bob", "I'm doing great, thanks!"]
[END]'''
    
    segments, analysis = provider._parse_jsonl_response(sample_response)
    
    assert len(segments) == 2
    assert segments[0]["speaker_id"] == "Alice"
    assert segments[0]["text"] == "Hello, how are you?"
    assert segments[1]["speaker_id"] == "Bob"
    assert analysis["language"] == "en"
    assert "Alice" in analysis["speakers"]
    
    print("✓ JSONL parsing test passed")

def main():
    """Run all tests."""
    print("=" * 60)
    print("OpenRouter Provider Tests")
    print("=" * 60)
    
    try:
        test_config_loading()
        test_ingest_specs()
        test_jsonl_parsing()
        
        if test_provider_initialization():
            print("\n" + "=" * 60)
            print("All tests passed! ✓")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("Some tests failed! ✗")
            print("=" * 60)
            return 1
    
    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
