# Amanu Multi-Provider Usage Guide

Amanu now supports multiple transcription and refinement providers, allowing you to mix and match services for optimal cost and performance.

## Supported Providers

| Provider | Transcription | Refinement | Key Features |
| :--- | :--- | :--- | :--- |
| **Gemini** | ✅ | ✅ | High speed, long context window, multimodal (audio/video). |
| **Whisper** | ✅ | ❌ | Runs locally (privacy, free), high accuracy. Requires `whisper-cli`. |
| **Claude** | ❌ (Coming Soon) | ❌ (Coming Soon) | High reasoning capability for refinement. |

## Configuration

The configuration is managed via `config.yaml`. You can specify the provider and model for both the `transcribe` and `refine` stages independently.

### 1. Stage Configuration

Define which provider to use for each stage:

```yaml
transcribe:
  provider: "whisper" # Use local Whisper for transcription
  model: "large-v3"

refine:
  provider: "gemini" # Use Gemini for refinement/summary
  model: "gemini-2.0-flash"
```

### 2. Provider Settings

Configure the specific settings for each provider in the `providers` block.

#### Gemini
Requires an API Key.

```yaml
providers:
  gemini:
    api_key: "YOUR_API_KEY" # Or use GEMINI_API_KEY env var
    models:
      - name: "gemini-2.0-flash"
        # ...
```

#### Whisper (Local)
Requires `whisper-cli` installed and models downloaded.

```yaml
providers:
  whisper:
    models:
      base: "/path/to/whisper.cpp/models/ggml-base.bin"
      large-v3: "/path/to/whisper.cpp/models/ggml-large-v3.bin"
```

**Note:** The `model` name specified in `transcribe.model` must match a key in `providers.whisper.models`.

#### Claude (Anthropic)
Requires an API Key.

```yaml
providers:
  claude:
    api_key: "YOUR_API_KEY" # Or use ANTHROPIC_API_KEY env var
    models:
      - name: "claude-3-5-sonnet-20241022"
        # ...
```

## Running the Pipeline

You can override the configuration at runtime using CLI arguments (if supported) or by editing `config.yaml`.

To run the full pipeline:
```bash
amanu run audio.mp3
```

To run specific stages:
```bash
amanu ingest audio.mp3
amanu scribe <job_id>
amanu refine <job_id>
```

## Adding New Providers

Amanu is designed to be extensible. To add a new provider:

1.  **Implement Provider Interface**: Create a new class in `amanu/providers/` inheriting from `TranscriptionProvider` (for Scribe) or `RefinementProvider` (for Refine).
2.  **Register in Factory**: Update `amanu/core/factory.py` to register your new provider.
3.  **Update Config**: Add configuration models in `amanu/core/models.py` and update `config.yaml`.

---

## Related Documentation

- **[Configuration Guide](./configuration.md)** - Complete `config.yaml` reference including provider configuration
- **[Features Guide](./features.md)** - Learn about Watch mode and job management
- **[Architecture Report](./architecture_report.md)** - Understanding the provider abstraction layer
- **[Documentation Index](./INDEX.md)** - Complete documentation overview
