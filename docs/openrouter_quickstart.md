# OpenRouter Provider - Quick Start Guide

## Setup

### 1. Get an API Key
1. Visit [OpenRouter.ai](https://openrouter.ai/)
2. Sign up or log in
3. Go to [Keys](https://openrouter.ai/keys) and create a new API key
4. Copy your API key

### 2. Configure Environment
Add to your `.env` file:
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Update Config
Edit `config.yaml`:
```yaml
transcribe:
  provider: openrouter
  model: mistralai/voxtral-small-24b-2507

refine:
  provider: openrouter
  model: google/gemini-2.0-flash-lite-001

providers:
  openrouter:
    site_url: https://github.com/yourusername/amanu  # Optional
    app_name: amanu  # Optional
```

## Usage

### Transcribe Audio
```bash
amanu run input/audio.mp3 .
```

### Refine Existing Transcript
```bash
amanu refine .
```

## Recommended Models

### For Transcription (Cheap & Fast)
```yaml
model: google/gemini-2.0-flash-lite-001
# Cost: $0.0375 per 1M input tokens, $0.15 per 1M output tokens
```

### For Transcription (High Quality)
```yaml
model: mistralai/voxtral-small-24b-2507
# Cost: $0.40 per 1M tokens (input/output)
```

### For Refinement (Cheap)
```yaml
model: google/gemini-2.0-flash-lite-001
# Cost: $0.0375 per 1M input tokens, $0.15 per 1M output tokens
```

### For Refinement (High Quality)
```yaml
model: anthropic/claude-3.5-haiku
# Cost: $1.00 per 1M input tokens, $5.00 per 1M output tokens
```

## Finding Free Models

OpenRouter occasionally offers free models. To find them:

1. Visit [OpenRouter Models](https://openrouter.ai/models)
2. Look for models with "$0.00" pricing
3. Update your `config.yaml` with the model name

Example free models (availability varies):
- `google/gemini-2.0-flash-lite-001` (often free or very cheap)
- Various community models

## Cost Tracking

The provider automatically tracks costs for all operations:
- Costs are retrieved from OpenRouter's generation API
- Logged in the console during processing
- Saved in job metadata for reporting

View costs with:
```bash
amanu report
```

## Troubleshooting

### "API Key not found"
- Ensure `OPENROUTER_API_KEY` is set in `.env`
- Check that `.env` is in your project root
- Verify the key starts with `sk-or-v1-`

### "Model not found"
- Check model name spelling in `config.yaml`
- Visit [OpenRouter Models](https://openrouter.ai/models) to verify model availability
- Some models may be region-restricted

### "Insufficient credits"
- Add credits to your OpenRouter account
- Use free models (see "Finding Free Models" above)

## Advanced Configuration

### Custom Site URL and App Name
These help OpenRouter track your usage:
```yaml
providers:
  openrouter:
    site_url: https://myproject.com
    app_name: my-transcription-app
```

### Multiple Providers
You can mix providers:
```yaml
transcribe:
  provider: whisperx  # Local transcription
  model: large-v2

refine:
  provider: openrouter  # Cloud refinement
  model: google/gemini-2.0-flash-lite-001
```

## Support

- OpenRouter Docs: https://openrouter.ai/docs
- OpenRouter Discord: https://discord.gg/openrouter
- Amanu Issues: https://github.com/yourusername/amanu/issues
