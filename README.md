# Amanu: Your Digital Amanuensis

![Andrew Taylor Still with his amanuensis, Annie Morris, who is at a typewriter](./amanuensis.png)

*Andrew Taylor Still with his amanuensis Annie Morris at the typewriter. You speak, Amanu writes.*

---

## 📜 Philosophy

**Amanu** is your digital amanuensis—a scribe hired to capture the thoughts of a great person.

In ancient times, scholars and leaders employed amanuenses to transcribe their spoken words into written form. These scribes didn't just write down words—they prepared materials, captured speech verbatim, refined and enriched the text with details, and carefully archived the finished work.

Amanu brings this timeless practice into the AI age. It's not just a transcription tool—it's a complete pipeline that transforms your voice into polished, structured documents.

### Built for "Big Data" Audio
Amanu is specifically engineered to handle **massive audio files** (talks, lectures, day-long recordings) that break other tools. It features robust resumption, caching, and state management, so you never lose progress on a 3-hour transcription.

---

## ✨ Key Features

- **🔒 Fully Local & Free**: Use **WhisperX** (transcription) + **Ollama** (refinement) for a completely offline, $0 cost privacy-focused stack.
- **🎙️ Extreme Compatibility**: Handles MP3, WAV, MP4, M4A, and massive files with ease.
- **🏗️ Robust Pipeline**: specialized stages for ingestion, transcription, refinement, and generation.
- **🤖 Multi-Provider**: Switch seamlessy between **Gemini**, **OpenRouter**, **Claude**, **WhisperX**, and **Ollama**.
- **📊 Detailed Reporting**: Track every token and cent with `amanu report`.
- **🔌 Automation Ready**: Designed with future **n8n** integration in mind for automated workflows.

---

## 🚀 Installation & Setup

### Prerequisites
- **Python 3.10+**
- **FFmpeg** (Required for audio processing)
  - Ubuntu: `sudo apt install ffmpeg`
  - MacOS: `brew install ffmpeg`
  - Windows: `winget install ffmpeg`
- **Git**

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jfima/amanu.git
   cd amanu
   ```

2. **Create a virtual environment** (Recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # on Windows: .venv\Scripts\activate
   ```

3. **Install Amanu**:
   ```bash
   pip install -e .
   ```

4. **Verify Installation**:
   ```bash
   amanu --version
   ```

---

## ⚙️ Configuration

Amanu includes an **interactive setup wizard** that guides you through configuration, API keys, and model selection.

### 1. Run the Wizard
```bash
amanu setup
```

The wizard will help you:
- 🔑 **Configure Providers**: Enter API keys (stored safely in `.env`) or set up local models.
- 🤖 **Select Models**: Choose the best models for Transcription and Refinement to fit your budget and quality needs.
- 🌍 **Set Defaults**: Configure language and output preferences.

### 2. The "Fully Local" Stack (Optional)
To use Amanu without any API costs or data leaving your machine:
1.  **Install WhisperX** (see `amanu/providers/whisperx/README.md` if needed).
2.  **Pull an Ollama Model**: `ollama pull llama3` (or any other model).
3.  Run `amanu setup` and select **WhisperX** for transcription and **Ollama** for refinement.

---

## 🏗️ Architecture

Amanu processes audio through a robust **5-stage pipeline**:

### 1. **Ingest**
- Converts audio to optimized formats (OGG/Opus).
- Uploads large files to provider caches (e.g., Gemini Cache).
- Prepares job metadata and safeguards original files.

### 2. **Scribe**
- Produces word-for-word transcription with timestamps.
- **WhisperX** / **Gemini** / **Whisper.cpp**  supported.
- Automatic speaker identification.

### 3. **Refine**
- Analyzing the text for meaning and structure.
- Extracts summaries, action items, and key insights using LLMs.
- Outputs pure data (JSON) for the next stage.

### 4. **Generate**
- Applies templates to the refined data to create user-facing artifacts.
- Outputs **Markdown** reports, **PDF** documents, **SRT** subtitles, and more.

### 5. **Shelve**
- Organizes finished documents into your library.
- Supports Timeline (date-based) or Zettelkasten (flat) sorting.

---

## 🔌 Providers

Amanu is built on a modular "Provider" system. Providers are automatically discovered from the `amanu/providers/` directory.

| Provider | Type | Description | Cost |
|----------|------|-------------|------|
| **Gemini** | Cloud | Excellent multimodal capabilities, huge context window. | $$ |
| **OpenRouter** | Cloud | Access to 100+ top-tier models (GPT-4, Claude 3, etc.). | Varies |
| **WhisperX** | Local | State-of-the-art local transcription with alignment. | **Free** |
| **Ollama** | Local | Run powerful LLMs locally for refinement. | **Free** |
| **Claude** | Cloud | Anthropic's models, great for complex reasoning. | $$$ |

---

## 🛠️ Usage

### Basic Run
Process a file through the full pipeline:
```bash
amanu run interview.mp3
```

### Direct Analysis (Skip Transcription)
If you already have a transcript or text file:
```bash
amanu run meeting_notes.txt --skip-transcript
```

### Reporting
See exactly what you're spending:
```bash
amanu report --days 30
```

---

## 📖 Documentation

- **📑 [Documentation Index](./docs/INDEX.md)**
- **[Installation Guide](./docs/install_guide.md)**
- **[Configuration Guide](./docs/configuration.md)**
- **[Adding New Providers](./docs/adding_new_providers.md)**

---

## 🤝 Contributing
Contributions are welcome! See our [Contributing Guide](./CONTRIBUTING.md).

## 📄 License
MIT License - see [LICENSE](./LICENSE) for details.
