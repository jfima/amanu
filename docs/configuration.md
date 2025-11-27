# Configuration Guide

Complete reference for `config.yaml` and the setup wizard.

---

## 🎯 Quick Setup

The easiest way to configure Amanu:

```bash
amanu setup
```

The interactive wizard handles everything. But if you want to understand what's happening under the hood, read on!

---

## 📁 Configuration File Locations

Amanu looks for `config.yaml` in this order:

1. `./config.yaml` (current directory)
2. `~/.config/amanu/config.yaml` (user config)

**Tip:** Use local `config.yaml` for project-specific settings.

---

## 🔑 API Configuration

### Gemini API Key

```yaml
gemini:
  api_key: "YOUR_API_KEY_HERE"
  transcribe_model: "gemini-2.0-flash"
  refine_model: "gemini-2.0-flash"
```

**Get your key:** [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

**Environment variable:** You can also set `GEMINI_API_KEY` instead of putting it in the config.

### Available Models

```yaml
gemini_models:
  - name: "gemini-2.0-flash"
    context_window:
      input_tokens: 1048576
      output_tokens: 8192
    cost_per_1M_tokens_usd:
      input: 0.10
      output: 0.40
  
  - name: "gemini-2.5-flash"
    context_window:
      input_tokens: 1048576
      output_tokens: 65536
    cost_per_1M_tokens_usd:
      input: 0.30
      output: 2.50
  
  - name: "gemini-2.5-pro"
    context_window:
      input_tokens: 1048576
      output_tokens: 65536
    cost_per_1M_tokens_usd:
      input: 1.25
      output: 10.0
```

---

## 🌐 Processing Options

### Language

```yaml
processing:
  language: "auto"  # Auto-detect language
  # Or force specific language:
  # language: "en"  # English
  # language: "ru"  # Russian
  # language: "de"  # German
```

**Supported codes:** `en`, `ru`, `de`, `fr`, `ja`, `zh`, and more

### Compression Mode

```yaml
processing:
  compression_mode: "compressed"
```

**Options:**
- `original` - No compression (use original file)
- `compressed` - OGG Opus 24kbps (recommended)
- `optimized` - Compressed + silence removal

### Debug Mode

```yaml
processing:
  debug: false  # Set to true for detailed logs
```

When enabled, creates `_stages/` folder with:
- API requests/responses
- Timing information
- Token usage details

---

## 📝 Output Configuration

### Artifacts

Define what files to generate:

```yaml
processing:
  output:
    artifacts:
      # Markdown transcript
      - plugin: markdown
        template: default
        filename: "transcript"
      
      # Summary
      - plugin: markdown
        template: summary
        filename: "summary"
      
      # PDF report
      - plugin: pdf
        template: report
      
      # SRT subtitles
      - plugin: srt
        template: standard
```

**Available plugins:**
- `markdown` - Markdown files
- `pdf` - PDF documents (requires `reportlab`)
- `srt` - SRT subtitle files

**Available templates:**
- Markdown: `default`, `summary`, `brief`
- PDF: `report`, `minimal`
- SRT: `standard`

---

## 📁 Path Configuration

```yaml
paths:
  input: "./scribe-in"      # Watch mode input
  work: "./scribe-work"     # Temporary processing
  results: "./scribe-out"   # Final outputs
```

**Relative paths** are relative to where you run `amanu`.

**Absolute paths** work too:
```yaml
paths:
  input: "/Users/you/Dropbox/voice-notes"
  results: "/Users/you/Documents/transcripts"
```

---

## 🗂️ Organization (Shelve)

### Timeline Mode (Default)

```yaml
shelve:
  enabled: true
  strategy: "timeline"
```

**Output structure:**
```
scribe-out/
└── 2025/
    └── 11/
        └── 26/
            └── 25-1126-143022_meeting/
                ├── transcript.md
                ├── summary.md
                └── ...
```

### Zettelkasten Mode

```yaml
shelve:
  enabled: true
  strategy: "zettelkasten"
  zettelkasten:
    id_format: "%Y%m%d%H%M"
    filename_pattern: "{id} {slug}.md"
```

**Output structure:**
```
scribe-out/
├── 202511261430 Meeting Notes.md
├── 202511261445 Interview.md
└── ...
```

**ID format codes:**
- `%Y` - Year (2025)
- `%m` - Month (11)
- `%d` - Day (26)
- `%H` - Hour (14)
- `%M` - Minute (30)

---

## 🔄 Retry Configuration

```yaml
processing:
  scribe:
    retry_max: 3              # Max retry attempts
    retry_delay_seconds: 5    # Delay between retries
```

**When retries happen:**
- API rate limits (429 errors)
- Temporary network issues
- Service unavailable errors

---

## 🧹 Cleanup Configuration

```yaml
cleanup:
  failed_jobs_retention_days: 7
  completed_jobs_retention_days: 1
  auto_cleanup_enabled: true
```

**What gets cleaned:**
- Failed jobs older than N days
- Completed jobs older than N days
- Only from `work/` directory (results are safe!)

**Manual cleanup:**
```bash
amanu jobs cleanup --older-than 7 --status failed
```

---

## 📋 Complete Example

```yaml
# API Configuration
gemini:
  api_key: "AIzaSy..."
  transcribe_model: "gemini-2.0-flash"
  refine_model: "gemini-2.0-flash"

# Processing Options
processing:
  language: "auto"
  compression_mode: "compressed"
  debug: false
  
  # Retry settings
  scribe:
    retry_max: 3
    retry_delay_seconds: 5
  
  # Output formats
  output:
    artifacts:
      - plugin: markdown
        template: default
        filename: "transcript"
      - plugin: markdown
        template: summary
        filename: "summary"
      - plugin: pdf
        template: report

# Paths
paths:
  input: "./scribe-in"
  work: "./scribe-work"
  results: "./scribe-out"

# Organization
shelve:
  enabled: true
  strategy: "timeline"

# Cleanup
cleanup:
  failed_jobs_retention_days: 7
  completed_jobs_retention_days: 1
  auto_cleanup_enabled: true

# Model definitions (usually don't need to change)
gemini_models:
  - name: "gemini-2.0-flash"
    context_window:
      input_tokens: 1048576
      output_tokens: 8192
    cost_per_1M_tokens_usd:
      input: 0.10
      output: 0.40
```

---

## 🎨 Advanced: Per-Job Overrides

Override settings for specific jobs:

```bash
# Use different model
amanu run audio.mp3 --model gemini-2.5-pro

# Different compression
amanu run audio.mp3 --compression-mode optimized

# Different organization
amanu run audio.mp3 --shelve-mode zettelkasten
```

---

## 🔍 Configuration Validation

Amanu validates your config on startup. Common errors:

### "API key not found"
- Set `gemini.api_key` in config
- Or set `GEMINI_API_KEY` environment variable

### "Model not found"
- Check model name matches one in `gemini_models`
- Default models are always available

### "Invalid path"
- Use forward slashes even on Windows: `C:/Users/...`
- Or use double backslashes: `C:\\Users\\...`

---

## 💡 Tips

### Keep API Key Secure
Don't commit `config.yaml` with your API key to git!

Add to `.gitignore`:
```
config.yaml
```

Use `config.example.yaml` as a template for others.

### Multiple Configurations
Create different configs for different use cases:

```bash
# Work meetings
amanu run meeting.mp3 --config work-config.yaml

# Personal notes
amanu run note.mp3 --config personal-config.yaml
```

### Environment Variables
Override any setting:
```bash
export GEMINI_API_KEY="your-key"
export AMANU_LANGUAGE="ru"
amanu run audio.mp3
```

---

## 🔍 What's Next?

- [Features Guide](./features.md) - What Amanu can do
- [Customization Guide](./customization.md) - Templates and plugins
- [Troubleshooting](./troubleshooting.md) - Common issues
