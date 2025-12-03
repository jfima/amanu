# OpenRouter Provider Implementation

## Overview
Successfully implemented a new provider for amanu that connects to OpenRouter.ai, supporting both transcription and refinement capabilities.

## Features Implemented

### 1. Transcription Support
- **Multimodal Chat Models**: Support for models like `mistralai/voxtral-small-24b-2507` and `google/gemini-2.0-flash-lite-001` using the Chat Completions API with audio input
- **Whisper Models**: Support for dedicated ASR models like `openai/whisper-large-v3` using the Audio Transcriptions API
- **Automatic Model Detection**: The provider automatically detects whether to use Whisper or Chat API based on the model name
- **JSONL Response Parsing**: Parses structured JSONL responses with speaker identification and timestamps

### 2. Refinement Support
- **Text Analysis**: Uses OpenRouter's text models for transcript refinement and analysis
- **Custom Schema Support**: Supports custom field extraction based on template requirements
- **Fallback Schema**: Provides comprehensive default schema when no custom fields are specified

### 3. Cost Tracking
- **Generation API Integration**: Retrieves actual costs from OpenRouter's `/api/v1/generation` endpoint
- **Accurate Billing**: Reports exact costs for both transcription and refinement operations
- **Token Usage Tracking**: Logs input/output tokens for all API calls

## Files Created

### Core Provider Files
1. **`amanu/providers/openrouter/__init__.py`**
   - Defines `OpenRouterConfig` with API key, site URL, and app name
   - Exports configuration for dynamic loading

2. **`amanu/providers/openrouter/provider.py`**
   - `OpenRouterTranscriptionProvider`: Handles audio transcription
   - `OpenRouterRefinementProvider`: Handles text refinement
   - Cost tracking methods for both providers

3. **`amanu/providers/openrouter/defaults.yaml`**
   - Curated list of recommended models for transcription and refinement
   - Includes pricing and context window information for each model

### Integration Files
4. **`amanu/core/factory.py`** (modified)
   - Added lazy loading for OpenRouter transcription provider
   - Added lazy loading for OpenRouter refinement provider

5. **`config.yaml`** (modified)
   - Added `openrouter` section to providers configuration

6. **`pyproject.toml`** (modified)
   - Added `openai>=1.0.0` dependency
   - Added `requests` dependency

### Testing
7. **`tests/verify_openrouter.py`**
   - Config loading tests
   - Provider initialization tests
   - Ingest specs validation
   - JSONL parsing tests
   - All tests passing ✓

## Configuration

### Environment Variables
Users need to set the following in their `.env` file:
```bash
OPENROUTER_API_KEY=your_api_key_here
```

### Config.yaml
```yaml
providers:
  openrouter:
    site_url: https://github.com/yourusername/amanu
    app_name: amanu

transcribe:
  provider: openrouter
  model: mistralai/voxtral-small-24b-2507

refine:
  provider: openrouter
  model: google/gemini-2.0-flash-lite-001
```

## Supported Models

### Transcription Models
- `mistralai/voxtral-small-24b-2507` - Multimodal audio transcription
- `google/gemini-2.0-flash-lite-001` - Fast, cheap multimodal
- `google/gemini-2.0-flash-001` - Balanced multimodal
- `openai/whisper-large-v3` - Dedicated ASR

### Refinement Models
- `google/gemini-2.0-flash-lite-001` - Fast, cheap text analysis
- `anthropic/claude-3.5-haiku` - High-quality analysis
- `meta-llama/llama-3.3-70b-instruct` - Open source option
- `qwen/qwen-2.5-72b-instruct` - Alternative option

## Usage Example

### Transcription
```bash
# Set up environment
export OPENROUTER_API_KEY="your_key"

# Update config.yaml to use openrouter provider
# Then run:
amanu run input/audio.mp3 .
```

### Refinement Only
```bash
amanu refine .
```

## Technical Details

### Audio Handling
- **Multimodal Models**: Audio is base64-encoded and sent in the chat messages with `input_audio` type
- **Whisper Models**: Audio is sent as binary file to the transcriptions endpoint
- **Format Support**: MP3 (target format from ingest stage)

### Cost Tracking Flow
1. API call returns a generation ID
2. Provider calls `GET /api/v1/generation?id={generation_id}`
3. Response contains actual cost in USD
4. Cost is logged and included in job metadata

### Error Handling
- Validates API key presence (config or environment)
- Graceful fallback for cost retrieval failures
- Comprehensive logging for debugging

## Testing Results
All tests passing:
- ✓ Config loading
- ✓ Ingest specs validation
- ✓ JSONL parsing
- ✓ Provider initialization (transcription & refinement)

## Next Steps (Optional Enhancements)

1. **Free Model Discovery**: Implement a CLI command to query OpenRouter's models API and filter for free/cheap models
2. **Model Caching**: Cache model pricing information to reduce API calls
3. **Streaming Support**: Add streaming transcription for real-time feedback
4. **Rate Limiting**: Implement rate limit handling for OpenRouter API
5. **Model Validation**: Add validation to ensure selected models support required features (audio input, etc.)

## Dependencies Added
- `openai>=1.0.0` - OpenAI Python client (compatible with OpenRouter)
- `requests` - For direct API calls to generation endpoint

## Notes
- OpenRouter uses OpenAI-compatible API endpoints, making integration straightforward
- The provider automatically handles both Whisper-style and multimodal chat-style transcription
- Cost tracking is accurate and retrieved directly from OpenRouter's billing API
- All provider code follows the existing amanu provider pattern for consistency
