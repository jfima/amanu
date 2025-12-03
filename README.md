# Amanu: Your Digital Amanuensis

![Andrew Taylor Still with his amanuensis, Annie Morris, who is at a typewriter](./amanuensis.png)

*Andrew Taylor Still with his amanuensis Annie Morris at the typewriter. You speak, Amanu writes.*

---

## 📜 Philosophy

**Amanu** is your digital amanuensis—a scribe hired to capture the thoughts of a great person.

In ancient times, scholars and leaders employed amanuenses to transcribe their spoken words into written form. These scribes didn't just write down words—they prepared materials, captured speech verbatim, refined and enriched the text with details, and carefully archived the finished work.

Amanu brings this timeless practice into the AI age. It's not just a transcription tool—it's a complete pipeline that transforms your voice into polished, structured documents.

---

## 🏗️ Architecture Philosophy

### Modular Provider System

Amanu is built on a **flexible provider architecture**. Each AI provider lives in its own directory under `amanu/providers/`:

```
amanu/providers/
├── gemini/          # Google's multimodal AI
├── openrouter/      # Access to 100+ models
├── whisper/         # Local Whisper.cpp
├── whisperx/        # Enhanced local transcription
├── claude/          # Anthropic's Claude
└── zai/             # Z.AI provider
```

**Key principles:**
- **Plug-and-play**: Add or remove providers by simply adding/deleting folders
- **Self-contained**: Each provider has its own `defaults.yaml` with model configurations
- **Discoverable**: Providers are automatically discovered and registered
- **Extensible**: Easy to add new providers following the base interface

### The Pipeline: Four Stages

Amanu processes audio through **four distinct stages**, each with a clear purpose:

#### 1. **Ingest** — Preparation
- Converts audio to optimized formats (OGG/Opus) to save bandwidth
- Uploads large files to provider caches (e.g., Gemini Cache)
- Prepares metadata and job tracking

#### 2. **Scribe** — Verbatim Transcription
- Produces word-for-word transcription with timestamps
- Identifies speakers automatically
- Can be skipped if you only need summaries

#### 3. **Refine** — Analysis & Enrichment
- Extracts summaries, action items, key insights
- Enriches content with structure and details
- Uses transcript or direct audio analysis

#### 4. **Shelve** — Archival
- Organizes finished documents into your library
- Supports timeline (by date) or Zettelkasten (flat) organization
- Generates multiple output formats (Markdown, PDF, SRT, TXT)

---

## 🚀 Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Configure with the Wizard

Amanu includes an **interactive setup wizard** that guides you through configuration:

```bash
amanu setup
```

The wizard helps you:
- 🔑 Configure API keys for your chosen providers
- 🤖 Select models for transcription and refinement
- 🌍 Set language preferences
- 📁 Choose output formats and organization modes

**Everything is configurable** through the wizard—no manual YAML editing required!

### 3. Process Your First File

```bash
amanu run your-audio.mp3
```

Find your results in `scribe-out/`.

---

## 🔌 Provider Philosophy

### Flexibility First

Amanu supports multiple AI providers, each with different strengths:

| Provider | Type | Best For | Cost |
|----------|------|----------|------|
| **Gemini** | Cloud | Large context, multimodal | $$ |
| **OpenRouter** | Cloud | Access to 100+ models | Varies |
| **Whisper** | Local | Privacy, free transcription | Free |
| **WhisperX** | Local | Enhanced local transcription | Free |
| **Claude** | Cloud | Advanced reasoning | $$$ |
| **Z.AI** | Cloud | Alternative cloud option | $$ |

### Easy Provider Management

**New providers** are added regularly. To use them:
1. Ensure the provider folder exists in `amanu/providers/`
2. Run `amanu setup` to configure API keys
3. Select the provider in your `config.yaml`

**Remove providers** you don't need by simply deleting their folders.

---

## 📊 Token Usage & Cost Tracking

Amanu tracks **every token** processed and provides detailed cost reports:

```bash
amanu report --days 30
```

This shows:
- 📈 Total tokens processed (input/output)
- 💰 Estimated costs per provider
- 📅 Usage breakdown by date
- 🎯 Cost per job

**Why this matters**: You always know exactly how much you're spending on AI processing.

---

## 🛠️ Advanced Usage

### Watch Mode (Auto-Process)
```bash
amanu watch
```
Drop files into `scribe-in/`, get results in `scribe-out/`

### Job Management
```bash
amanu jobs list              # See all jobs
amanu jobs show <job_id>     # Inspect details
amanu jobs retry <job_id>    # Retry failed jobs
```

### Stage-by-Stage Execution
```bash
amanu run audio.mp3 --stage ingest    # Only prepare
amanu run audio.mp3 --stage scribe    # Only transcribe
amanu run audio.mp3 --stage refine    # Only analyze
amanu run audio.mp3 --stage shelve    # Only archive
```

---

## 📖 Documentation

**📑 [Documentation Index](./docs/INDEX.md)** - Complete guide to all documentation

### Quick Start Guides
- [Windows 11 Setup](./docs/getting-started-windows.md)
- [macOS Setup](./docs/getting-started-macos.md)

### User Guides
- [Core Features](./docs/features.md)
- [Configuration Guide](./docs/configuration.md)
- [Usage Guide](./docs/usage_guide.md)
- [OpenRouter Quick Start](./docs/openrouter_quickstart.md)
- [Template System](./docs/template_system_design.md)

### Developer Docs
- [Architecture Report](./docs/architecture_report.md)
- [Adding New Providers](./docs/adding_new_providers.md)
- [Partial Pipeline Execution](./docs/partial_pipeline_execution.md)

---

## ✨ Key Features

- **🎙️ Multi-Format Support**: MP3, WAV, MP4, M4A, and more
- **📝 Rich Outputs**: Markdown, PDF, SRT subtitles, plain text
- **🗣️ Speaker Detection**: Automatic speaker identification
- **🌐 Multi-Language**: Auto-detect or force specific languages
- **💰 Cost Tracking**: Detailed token usage and cost reports
- **⚡ Watch Mode**: Auto-process files in a folder
- **🔧 Wizard Configuration**: Easy setup without manual editing
- **🔌 Modular Providers**: Add/remove providers as needed

---

## 💰 Pricing Examples

Costs vary by provider. Here's Gemini pricing:

| Model | Cost | Best For |
|-------|------|----------|
| Gemini 2.0 Flash Lite | $0.0375/1M input | Cheapest option |
| Gemini 2.5 Flash | $0.075/1M input | Balanced quality |
| Gemini 2.5 Pro | $1.25/1M input | Professional work |

**Example**: 1-hour audio ≈ $0.01-0.05 (depending on model)

Use `amanu report` to track your actual spending.

---

## 🤝 Contributing

Contributions welcome! See our [Contributing Guide](./CONTRIBUTING.md).

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

---

## 🙏 Built With

- [Google Gemini](https://ai.google.dev/) - Multimodal AI
- [OpenRouter](https://openrouter.ai/) - Multi-model access
- [Whisper](https://github.com/openai/whisper) - Local transcription
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal UI
- [FFmpeg](https://ffmpeg.org/) - Audio processing
