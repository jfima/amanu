# Changelog: OpenRouter Provider Implementation
**Date**: 2025-12-03

## Summary
Implemented a new provider for amanu that integrates with OpenRouter.ai, enabling access to a wide variety of AI models for both transcription and refinement tasks with automatic cost tracking.

## New Features

### OpenRouter Provider
- **Transcription Support**: 
  - Multimodal chat models (e.g., `mistralai/voxtral-small-24b-2507`, `google/gemini-2.0-flash-lite-001`)
  - Whisper ASR models (e.g., `openai/whisper-large-v3`)
  - Automatic detection of model type and appropriate API endpoint
  - JSONL response parsing with speaker identification

- **Refinement Support**:
  - Text-based refinement using various LLMs
  - Custom schema support for template-driven field extraction
  - Comprehensive default schema for backward compatibility

- **Cost Tracking**:
  - Automatic cost retrieval from OpenRouter's generation API
  - Accurate billing information for all operations
  - Token usage logging for transparency

### Configuration
- Added `openrouter` provider configuration section
- Support for custom site URL and app name (for OpenRouter tracking)
- Environment variable support for API key (`OPENROUTER_API_KEY`)

### Documentation
- **Implementation Guide**: Comprehensive technical documentation (`docs/openrouter_implementation.md`)
- **Quick Start Guide**: User-friendly setup and usage guide (`docs/openrouter_quickstart.md`)
- Model recommendations for different use cases
- Troubleshooting section

### Testing
- Created comprehensive test suite (`tests/verify_openrouter.py`)
- Tests for configuration loading, provider initialization, and JSONL parsing
- All tests passing ✓

## Files Modified

### Core Files
- `amanu/core/factory.py`: Added OpenRouter provider registration
- `config.yaml`: Added OpenRouter provider configuration
- `pyproject.toml`: Added `openai` and `requests` dependencies

### New Files
- `amanu/providers/openrouter/__init__.py`: Provider configuration
- `amanu/providers/openrouter/provider.py`: Provider implementation
- `amanu/providers/openrouter/defaults.yaml`: Default model configurations
- `tests/verify_openrouter.py`: Test suite
- `docs/openrouter_implementation.md`: Technical documentation
- `docs/openrouter_quickstart.md`: User guide

## Dependencies Added
- `openai>=1.0.0`: OpenAI Python client (OpenRouter-compatible)
- `requests`: For direct API calls to OpenRouter's generation endpoint

## Usage Example

### Setup
```bash
# Add to .env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx

# Update config.yaml
transcribe:
  provider: openrouter
  model: mistralai/voxtral-small-24b-2507

refine:
  provider: openrouter
  model: google/gemini-2.0-flash-lite-001
```

### Run
```bash
amanu run input/audio.mp3 .
```

## Technical Details

### Architecture
- Follows existing provider pattern for consistency
- Supports both Whisper-style and multimodal chat-style transcription
- Uses OpenAI-compatible API endpoints
- Implements lazy loading in factory

### Audio Handling
- Multimodal models: Base64-encoded audio in chat messages
- Whisper models: Binary file upload to transcriptions endpoint
- Target format: MP3 (from ingest stage)

### Cost Tracking Flow
1. API call returns generation ID
2. Provider queries `/api/v1/generation?id={id}`
3. Actual cost retrieved and logged
4. Cost included in job metadata

## Benefits
- **Access to Multiple Models**: Single provider for many different AI models
- **Cost Optimization**: Easy switching between models based on budget
- **Accurate Billing**: Real-time cost tracking from OpenRouter
- **Flexibility**: Support for both transcription and refinement
- **Free Tier**: Access to free models when available

## Future Enhancements (Optional)
- Free model discovery CLI command
- Model pricing cache
- Streaming transcription support
- Rate limit handling
- Model capability validation

## Testing Status
✓ All tests passing
✓ Configuration loading verified
✓ Provider initialization verified
✓ JSONL parsing verified

## Migration Notes
No breaking changes. Existing providers continue to work as before. OpenRouter is an additional option.

## References
- OpenRouter API: https://openrouter.ai/docs
- OpenRouter Models: https://openrouter.ai/models
- Implementation Plan: See original user request
