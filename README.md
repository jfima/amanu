# Amanu: Your AI Amanuensis

Transform your voice notes into structured documents with AI. Simple, powerful, and built for everyone.

![Andrew Taylor Still with his amanuensis, Annie Morris, who is at a typewriter](./amanuensis.png)

*Andrew Taylor Still with his amanuensis Annie Morris at the typewriter. You speak, Amanu writes.*

---

## 🚀 Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Configure

Run the interactive setup wizard:

```bash
amanu setup
```

The wizard will guide you through:
- 🔑 Getting your Google Gemini API key
- 🤖 Choosing the right AI model for your needs
- 🌍 Setting your language preferences
- 📁 Configuring output formats

### 3. Process Your First File

```bash
amanu run your-audio.mp3
```

That's it! Find your transcripts in `scribe-out/`.

---

## 🏗️ How It Works

Amanu processes your audio in **5 distinct stages**. This modular architecture allows you to pause, retry, or customize each step independently.

### The Pipeline

1.  **Ingest**: Prepares your audio.
    *   Converts to optimized format (OGG/Opus) to save bandwidth.
    *   **Gemini Cache**: Large files are uploaded to Gemini's cache once, allowing multiple operations without re-uploading.
2.  **Scribe**: Transcribes audio to text.
    *   **Verbatim**: Produces a word-for-word transcript with timestamps and speaker IDs.
    *   **Flexible**: You can skip this stage (`--skip-transcript`) if you only need a summary.
3.  **Refine**: Analyzes the content.
    *   Extracts summaries, action items, and key insights.
    *   Uses the raw transcript or direct audio analysis.
4.  **Generate**: Creates output files.
    *   Uses plugins to create Markdown, PDF, SRT, or custom formats.
5.  **Shelve**: Organizes the results.
    *   Moves finished files to your library (`scribe-out/`), organized by date or topic.

### 🧠 Smart Features

*   **Multi-Provider Support**: Choose from multiple AI providers:
    *   **Gemini**: Google's powerful multimodal AI with caching for long files
    *   **OpenRouter**: Access to 100+ models from various providers
    *   **Whisper/WhisperX**: Local, private transcription on your machine
    *   **Claude**: Anthropic's advanced language model
    *   **Z.AI**: Additional cloud provider option
*   **Gemini Caching**: For long recordings, Amanu uploads the file to Gemini's high-speed cache. This means you can ask for a summary, then a transcript, then a rewrite—all without waiting for the file to upload again.
*   **Local Whisper Support**: Want privacy or free transcription? Amanu supports **Whisper.cpp** and **WhisperX**. They run entirely on your machine.
    *   *Note: Requires `whisper-cli` or WhisperX installed.*
    *   [See Setup Guide](./docs/usage_guide.md) for instructions.

---

## 📖 Documentation

**📑 [Documentation Index](./docs/INDEX.md)** - Complete guide to all documentation

### Quick Start Guides
- [Windows 11 Setup](./docs/getting-started-windows.md) - Complete walkthrough for Windows users
- [macOS Setup](./docs/getting-started-macos.md) - Complete walkthrough for Mac users

### User Guides
- [Core Features](./docs/features.md) - What Amanu can do
- [Configuration Guide](./docs/configuration.md) - Customize your setup
- [Usage Guide](./docs/usage_guide.md) - Multi-provider support
- [OpenRouter Quick Start](./docs/openrouter_quickstart.md) - Using OpenRouter provider
- [Template System](./docs/template_system_design.md) - Custom field architecture

### Developer Docs
- [Architecture Report](./docs/architecture_report.md) - System design
- [Adding New Providers](./docs/adding_new_providers.md) - Create custom providers
- [Partial Pipeline Execution](./docs/partial_pipeline_execution.md) - Stage-by-stage control

---

## ✨ Key Features

- **🎙️ Multi-Format Support**: MP3, WAV, MP4, M4A, and more
- **📝 Rich Outputs**: Markdown, PDF, SRT subtitles
- **🗣️ Speaker Detection**: Automatic speaker identification
- **🌐 Multi-Language**: Auto-detect or force specific languages
- **💰 Cost Tracking**: Know exactly what you're spending
- **⚡ Watch Mode**: Auto-process files in a folder

---

## 💡 Common Use Cases

### Meeting Minutes
```bash
amanu run meeting.mp3
```
Get: Summary, action items, and full transcript

### Interview Transcription
```bash
amanu run interview.wav --compression-mode optimized
```
Get: Speaker-separated transcript with timestamps

### Lecture Notes
```bash
amanu run lecture.m4a --skip-transcript
```
Get: Summary and key points (lower cost)

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

### Cost Reports
```bash
amanu report --days 30       # Usage for last 30 days
```

---

## 🎨 Customization

Edit `config.yaml` or use `amanu setup` to configure:

- **Models**: Choose between speed (2.0 Flash) and quality (2.5 Pro)
- **Languages**: Auto-detect or force specific language
- **Output Formats**: Markdown, PDF, SRT, or custom templates
- **Organization**: Timeline (by date) or Zettelkasten (flat)

---

## 💰 Pricing

Amanu uses Google Gemini API:

| Model | Cost | Best For |
|-------|------|----------|
| Gemini 2.0 Flash | $0.10/1M tokens | Fast, everyday use |
| Gemini 2.5 Flash | $0.30/1M tokens | Balanced quality |
| Gemini 2.5 Pro | $1.25/1M tokens | Professional work |

**Example**: 1-hour audio ≈ $0.01-0.05

---

## 🤝 Contributing

Contributions welcome! See our [Contributing Guide](./CONTRIBUTING.md).

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

---

## 🙏 Built With

- [Google Gemini](https://ai.google.dev/) - AI transcription
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal UI
- [FFmpeg](https://ffmpeg.org/) - Audio processing
