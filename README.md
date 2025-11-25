# Amanu: The Digital Amanuensis

**Amanu** (short for Amanuensis) is your trusted AI scribe. It automatically processes voice media files (MP3, WAV, MP4) into structured, clean markdown transcripts using Google Gemini.

In the spirit of the great amanuenses of history, it sits ready to capture your spoken words and commit them to the page. But unlike its human predecessors, this scribe never tires, never misses a word, and types at the speed of light.

Feed it your voice notes, interviews, or ramblings, and watch as it weaves them into structured documents in multiple formats: **Markdown**, **PDF**, and **SRT subtitles**.

![Andrew Taylor Still with his amanuensis, Annie Morris, who is at a typewriter](./amanuensis.png)

*Andrew Taylor Still, founder of osteopathy, with his amanuensis Annie Morris at the typewriter. A fitting metaphor: you speak, it crafts.*

---

## 🧠 How It Works

Amanu operates as a **5-stage pipeline**, treating your audio processing as a multi-stage "job" with full state management.

### The Pipeline

```
Audio File → INGEST → SCRIBE → REFINE → GENERATE → SHELVE → Results
```

1. **INGEST** (Preparation)
   - Analyzes audio metadata (duration, format, bitrate)
   - Compresses to OGG Opus (24kbps) for optimal API efficiency
   - Uploads to Gemini with smart caching (5+ min files)

2. **SCRIBE** (Transcription)
   - Identifies speakers and assigns consistent names
   - Generates time-aligned transcript with JSONL streaming
   - Retry logic for API rate limits (429 errors)

3. **REFINE** (Intelligence Extraction)
   - Extracts structured data: summary, keywords, action items, quotes
   - Two modes: **Standard** (high quality) or **Direct** (low cost, skips transcript)
   - Outputs pure JSON data (no formatting)

4. **GENERATE** (Multi-Format Output)
   - Plugin-based architecture for extensibility
   - Applies Jinja2 templates to create user artifacts
   - Supports: Markdown, PDF, SRT subtitles

5. **SHELVE** (Organization)
   - Timeline mode: `YYYY/MM/DD/job_id/`
   - Zettelkasten mode: ID-based naming with tag routing
   - Configurable storage strategies

---

## 🚀 Key Features

### Core Capabilities
- ✅ **Multi-Format Output**: Markdown, PDF, SRT subtitles
- ✅ **Large File Handling**: Process hours of audio in a single pass (2M token context)
- ✅ **Context Caching**: Reduce latency and cost for long files
- ✅ **Speaker Identification**: Automatic speaker detection and naming
- ✅ **Job Management**: Track, retry, and resume failed jobs
- ✅ **Watch Mode**: Auto-process files dropped in a folder
- ✅ **Cost Tracking**: Detailed token usage and pricing reports

### Advanced Features
- ✅ **Direct Analysis Mode**: Skip transcription for cost savings (`--skip-transcript`)
- ✅ **Configurable Compression**: Original, compressed, or optimized modes
- ✅ **Template System**: Jinja2-based customizable output templates
- ✅ **Plugin Architecture**: Easily add new output formats
- ✅ **Retry Logic**: Automatic retry for API errors with configurable delays

---

## 🛠 Installation

### Requirements
- **Python**: ≥3.10
- **FFmpeg**: For audio processing
- **ReportLab**: For PDF generation (optional: `pip install reportlab`)

### Setup

```bash
# Clone and install
git clone https://github.com/jfima/amanu
cd amanu
pip install -e .

# Configure
cp config.example.yaml config.yaml
```

Edit `config.yaml`:
```yaml
gemini:
  api_key: "YOUR_GEMINI_API_KEY"
  transcribe_model: "gemini-2.0-flash"
  refine_model: "gemini-2.0-flash"

processing:
  language: "en"
  compression_mode: "compressed"
  debug: true
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
      - plugin: srt
        template: standard
```

---

## ⚡ Usage

### Quick Start
```bash
# Process a single file
amanu run interview.mp3

# With options
amanu run meeting.wav --compression-mode optimized --shelve-mode zettelkasten

# Direct Analysis (skip transcript, lower cost)
amanu run lecture.m4a --skip-transcript
```

### Watch Mode (Magic Folder)
```bash
amanu watch
```
Drop files in `input/`, get results in `scribe-out/YYYY/MM/DD/`.

### Manual Pipeline Control
```bash
# Run individual stages
amanu ingest audio.mp3          # Prepare audio
amanu scribe [job_id]           # Transcribe
amanu refine [job_id]           # Extract intelligence
amanu shelve [job_id]           # Organize results

# Job management
amanu jobs list                 # List all jobs
amanu jobs show <job_id>        # Inspect job details
amanu jobs retry <job_id>       # Retry failed job
amanu jobs cleanup --older-than 7  # Clean old jobs

# Cost reporting
amanu report --days 30          # Last 30 days usage
```

---

## 📁 Output Structure

```
scribe-out/
└── 2025/
    └── 11/
        └── 26/
            └── 25-1126-143022_interview/
                ├── transcript.md          # Full transcript
                ├── summary.md             # Executive summary
                ├── report.pdf             # PDF report
                ├── standard.srt           # Subtitles
                ├── media/
                │   ├── original.mp3
                │   └── compressed.ogg
                ├── transcripts/
                │   ├── raw_transcript.json
                │   └── enriched_context.json
                ├── _stages/               # Debug logs (if enabled)
                │   ├── ingest.json
                │   ├── scribe.json
                │   ├── refine.json
                │   ├── generate.json
                │   └── shelve.json
                ├── state.json
                └── meta.json
```

---

## 🎨 Customization

### Templates
Create custom Jinja2 templates in `amanu/templates/{plugin}/`:

```jinja2
# templates/markdown/custom.j2
# {{ summary }}

## Key Points
{% for item in key_takeaways %}
- {{ item }}
{% endfor %}

## Full Text
{{ clean_text }}
```

Update `config.yaml`:
```yaml
output:
  artifacts:
    - plugin: markdown
      template: custom
      filename: "my_output"
```

### Plugins
Extend with custom output formats by implementing `BasePlugin`:

```python
from amanu.plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "myformat"
    
    def generate(self, context, template_content, output_path, **kwargs):
        # Your custom logic
        return output_path
```

---

## 💰 Cost Estimation

Amanu tracks costs in real-time:

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|-------|---------------------|----------------------|
| gemini-2.0-flash | $0.10 | $0.40 |
| gemini-2.5-flash | $0.30 | $2.50 |

**Example**: 1-hour audio (~15K tokens) ≈ $0.01-0.05 depending on mode and model.

Check `_stages/scribe.json` for detailed breakdowns.

---

## 🗺 Roadmap

- [ ] **Additional Plugins**: DOCX, HTML, LaTeX
- [ ] **Multi-API Support**: OpenAI Whisper, Anthropic Claude
- [ ] **Advanced Templates**: Blog posts, video scripts, meeting minutes
- [ ] **Web UI**: Browser-based interface
- [ ] **Batch Processing**: Process multiple files in parallel

---

## 📚 Documentation

- [Architecture Report](./docs/architecture_report.md) - Detailed system design
- [Plugin Development](./docs/plugins.md) - Create custom output formats
- [Template Guide](./docs/templates.md) - Customize output formatting

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

Built with:
- [Google Gemini](https://ai.google.dev/) - AI transcription and analysis
- [ReportLab](https://www.reportlab.com/) - PDF generation
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine
- [FFmpeg](https://ffmpeg.org/) - Audio processing
