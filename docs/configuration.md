# Configuration Guide

## Overview

Amanu uses a modular configuration system that separates concerns:

1. **`config.yaml`** - Main configuration file (user-specific settings)
2. **`.env`** - API keys and secrets (never commit to git!)
3. **`amanu/providers/{provider}/defaults.yaml`** - Provider defaults (shipped with code)

## Quick Start

1. **Copy example files:**
   ```bash
   cp config.example.yaml config.yaml
   cp .env.example .env
   ```

2. **Add your API keys to `.env`:**
   ```bash
   GEMINI_API_KEY=your_actual_key_here
   HF_TOKEN=your_huggingface_token_here
   ```

3. **Customize `config.yaml`** as needed

## Configuration Structure

### Main Config (`config.yaml`)

The main config file contains:

- **Stage configuration**: Which provider/model to use for each stage
- **Processing settings**: Language, compression, output formats
- **Paths**: Input/output directories
- **Cleanup rules**: Retention policies
- **Provider overrides**: Override defaults when needed

### Environment Variables (`.env`)

Store all sensitive data here:

- `GEMINI_API_KEY` - Google Gemini API key
- `CLAUDE_API_KEY` - Anthropic Claude API key
- `ZAI_API_KEY` - Zhipu AI API key
- `HF_TOKEN` - HuggingFace token (for WhisperX diarization)

### Provider Defaults (`amanu/providers/{provider}/defaults.yaml`)

Each provider has a defaults file that defines:

- Available models and their specifications
- Default settings (device, batch size, etc.)
- Cost information
- Context window sizes

**These files are part of the codebase and should not be modified by users.**

## How It Works

1. **Loading Order:**
   - Load provider defaults from `amanu/providers/{provider}/defaults.yaml`
   - Merge with user settings from `config.yaml`
   - Override with environment variables from `.env`

2. **No Duplication:**
   - Model definitions live only in provider defaults
   - API keys live only in `.env`
   - User config only contains choices and overrides

3. **Example:**

   **Provider defaults** (`amanu/providers/gemini/defaults.yaml`):
   ```yaml
   models:
     - name: gemini-2.0-flash
       context_window: {input_tokens: 1048576, output_tokens: 8192}
       cost_per_1M_tokens_usd: {input: 0.075, output: 0.30}
   ```

   **User config** (`config.yaml`):
   ```yaml
   transcribe:
     provider: gemini
     model: gemini-2.0-flash  # Just reference the model name
   ```

   **Environment** (`.env`):
   ```bash
   GEMINI_API_KEY=your_actual_key
   ```

## Provider Overrides

If you need to override provider defaults, add them to `config.yaml`:

```yaml
providers:
  whisperx:
    language: Russian  # Override auto-detection
    batch_size: 32     # Override default batch size
```

Only specify what you want to change. Everything else comes from defaults.

## Available Providers

### Transcription Providers

- **whisperx** - Local GPU transcription with diarization
- **whisper** - Local CPU transcription (whisper.cpp)
- **gemini** - Google Gemini API transcription
- **claude** - Anthropic Claude API transcription
- **zai** - Zhipu AI API transcription

### Refinement Providers

- **gemini** - Google Gemini API
- **claude** - Anthropic Claude API
- **zai** - Zhipu AI API

## Best Practices

1. **Never commit `.env`** - Add it to `.gitignore`
2. **Don't modify provider defaults** - Use overrides in `config.yaml` instead
3. **Use relative paths** - Makes config portable across systems
4. **Document custom settings** - Add comments explaining why you override defaults

## Migration from Old Config

If you have an old config with embedded model definitions and API keys:

1. **Extract API keys** to `.env`
2. **Remove model definitions** (they're in provider defaults now)
3. **Keep only**:
   - Stage provider/model choices
   - Processing settings
   - Paths
   - Any custom provider overrides

See `config.example.yaml` for the new structure.
