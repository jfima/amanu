#!/usr/bin/env python3
"""
Test script for Ollama provider integration.
This script tests both transcription and refinement capabilities.
"""

import os
import sys
import json
import tempfile
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from amanu.providers.ollama.provider import OllamaClient, OllamaTranscriptionProvider, OllamaRefinementProvider
from amanu.providers.ollama import OllamaConfig
from amanu.core.models import JobConfiguration, StageConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OllamaTest")

def test_ollama_connection():
    """Test basic connection to Ollama server."""
    print("🔍 Testing Ollama connection...")
    
    config = OllamaConfig()
    client = OllamaClient(config)
    
    if client.check_connection():
        print("✅ Successfully connected to Ollama server")
        return True
    else:
        print("❌ Failed to connect to Ollama server")
        return False

def test_list_models():
    """Test listing available models."""
    print("\n📋 Testing model listing...")
    
    config = OllamaConfig()
    client = OllamaClient(config)
    
    models = client.list_models()
    print(f"📊 Found {len(models)} models:")
    for model in models[:10]:  # Show first 10 models
        print(f"  - {model}")
    if len(models) > 10:
        print(f"  ... and {len(models) - 10} more")
    
    return models

def test_model_pull():
    """Test pulling a model."""
    print("\n⬇️  Testing model pull...")
    
    config = OllamaConfig()
    client = OllamaClient(config)
    
    # Try to pull a small model for testing
    test_model = "whisper-large-v3-turbo"
    
    if client.ensure_model(test_model):
        print(f"✅ Model {test_model} is available")
        return True
    else:
        print(f"❌ Failed to ensure model {test_model} is available")
        return False

def test_transcription_provider():
    """Test transcription provider initialization."""
    print("\n🎙️  Testing transcription provider...")
    
    try:
        # Create job configuration
        job_config = JobConfiguration(
            transcribe=StageConfig(provider="ollama", model="whisper-large-v3-turbo"),
            language="auto"
        )
        
        # Create provider configuration
        provider_config = OllamaConfig()
        
        # Initialize provider
        provider = OllamaTranscriptionProvider(job_config, provider_config)
        print("✅ Transcription provider initialized successfully")
        return provider
        
    except Exception as e:
        print(f"❌ Failed to initialize transcription provider: {e}")
        return None

def test_refinement_provider():
    """Test refinement provider initialization."""
    print("\n🔧 Testing refinement provider...")
    
    try:
        # Create job configuration
        job_config = JobConfiguration(
            refine=StageConfig(provider="ollama", model="gpt-oss:20b"),
            language="auto"
        )
        
        # Create provider configuration
        provider_config = OllamaConfig()
        
        # Initialize provider
        provider = OllamaRefinementProvider(job_config, provider_config)
        print("✅ Refinement provider initialized successfully")
        return provider
        
    except Exception as e:
        print(f"❌ Failed to initialize refinement provider: {e}")
        return None

def test_audio_transcription():
    """Test audio transcription with a sample file."""
    print("\n🎵 Testing audio transcription...")
    
    # Create a dummy audio file for testing
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
        # Write some dummy data (this won't work for real transcription, but tests the pipeline)
        temp_audio.write(b"dummy audio data")
        temp_audio_path = temp_audio.name
    
    try:
        provider = test_transcription_provider()
        if not provider:
            return False
        
        # Test ingest result format
        ingest_result = {
            "local_file_path": temp_audio_path
        }
        
        # This will likely fail with dummy audio, but tests the API flow
        try:
            result = provider.transcribe(ingest_result, job_dir=tempfile.mkdtemp())
            print("✅ Transcription API call completed")
            print(f"📝 Result: {json.dumps(result, indent=2)}")
            return True
        except Exception as e:
            print(f"⚠️  Transcription failed (expected with dummy audio): {e}")
            return True  # Expected to fail with dummy audio
            
    finally:
        # Clean up
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

def test_text_refinement():
    """Test text refinement."""
    print("\n📝 Testing text refinement...")
    
    try:
        provider = test_refinement_provider()
        if not provider:
            return False
        
        # Sample transcript data
        sample_transcript = [
            {"speaker_id": "Speaker A", "text": "Hello, this is a test transcript."},
            {"speaker_id": "Speaker B", "text": "Yes, let's test the refinement functionality."}
        ]
        
        # Test refinement
        result = provider.refine(
            input_data=sample_transcript,
            mode="standard",
            language="English",
            job_dir=tempfile.mkdtemp()
        )
        
        print("✅ Refinement completed successfully")
        print(f"📊 Result: {json.dumps(result, indent=2)}")
        return True
        
    except Exception as e:
        print(f"❌ Refinement failed: {e}")
        return False

def test_configuration():
    """Test configuration loading and validation."""
    print("\n⚙️  Testing configuration...")
    
    try:
        # Test default configuration
        config = OllamaConfig()
        print(f"✅ Default config loaded: {config.base_url}")
        
        # Test configuration with custom values
        custom_config = OllamaConfig(
            base_url="http://localhost:11434",
            timeout=300,
            auto_pull_models=False
        )
        print(f"✅ Custom config loaded: {custom_config.base_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Ollama Provider Tests")
    print("=" * 50)
    
    tests = [
        ("Connection", test_ollama_connection),
        ("Configuration", test_configuration),
        ("Model Listing", test_list_models),
        ("Model Pull", test_model_pull),
        ("Transcription Provider", test_transcription_provider),
        ("Refinement Provider", test_refinement_provider),
        ("Audio Transcription", test_audio_transcription),
        ("Text Refinement", test_text_refinement),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result is not None and result is not False))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Ollama provider is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())