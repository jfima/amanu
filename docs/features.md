# Amanu Features Guide

Everything Amanu can do for you.

---

## 🎙️ Audio Processing

### Supported Formats
- **Audio**: MP3, WAV, OGG, M4A, FLAC
- **Video**: MP4, MOV, MKV, WEBM (extracts audio)

### Smart Compression
Amanu automatically optimizes your audio for the AI:

| Mode | Description | When to Use |
|------|-------------|-------------|
| `original` | No compression | High-quality source, small files |
| `compressed` | OGG Opus 24kbps | Default, good balance |
| `optimized` | Compressed + silence removal | Long recordings with pauses |

```bash
amanu run audio.mp3 --compression-mode optimized
```

---

## 🗣️ Speaker Detection

Amanu automatically:
- Identifies different speakers
- Assigns consistent names (Speaker 1, Speaker 2, etc.)
- Maintains speaker identity throughout the transcript

**Example Output:**
```markdown
**Speaker 1**: Hello, thanks for joining today's meeting.
**Speaker 2**: Happy to be here! Let's dive in.
**Speaker 1**: Great. First item on the agenda...
```

---

## 📝 Output Formats

### Markdown
Clean, readable transcripts with:
- Speaker labels
- Timestamps (optional)
- Formatting preserved

### PDF
Professional reports with:
- Title page
- Table of contents
- Formatted sections
- Custom styling

### SRT Subtitles
Standard subtitle format for:
- Video editing
- Accessibility
- Translation workflows

**Configure in `config.yaml`:**
```yaml
output:
  artifacts:
    - plugin: markdown
      template: default
    - plugin: pdf
      template: report
    - plugin: srt
      template: standard
```

---

## 🌐 Multi-Language Support

### Auto-Detection
Amanu can automatically detect the language of your audio:

```bash
amanu setup  # Choose "Auto" for language
```

### Supported Languages
- 🇬🇧 English
- 🇷🇺 Russian
- 🇩🇪 German
- 🇫🇷 French
- 🇯🇵 Japanese
- 🇨🇳 Chinese
- And many more!

### Force Specific Language
```yaml
processing:
  language: "ru"  # Force Russian
```

---

## 💰 Cost Optimization

### Direct Analysis Mode
Skip the full transcript to save money:

```bash
amanu run lecture.mp3 --skip-transcript
```

**What you get:**
- ✅ Summary
- ✅ Key points
- ✅ Action items
- ❌ Full transcript

**Savings:** ~70% reduction in tokens

### Model Selection

| Model | Speed | Quality | Cost | Best For |
|-------|-------|---------|------|----------|
| 2.0 Flash | ⚡⚡⚡ | ⭐⭐ | 💰 | Daily use, quick notes |
| 2.5 Flash | ⚡⚡ | ⭐⭐⭐ | 💰💰 | Important meetings |
| 2.5 Pro | ⚡ | ⭐⭐⭐⭐ | 💰💰💰 | Professional work |

### Cost Tracking
```bash
amanu report --days 30
```

**Example Output:**
```
Cost Report (Last 30 days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Jobs: 15
Total Cost: $2.34
Average per Job: $0.16

Breakdown by Model:
  gemini-2.0-flash: $1.89 (12 jobs)
  gemini-2.5-flash: $0.45 (3 jobs)
```

---

## ⚡ Watch Mode

Auto-process files dropped into a folder:

```bash
amanu watch
```

**How it works:**
1. Drop audio files into `scribe-in/`
2. Amanu detects them automatically
3. Processing starts immediately
4. Results appear in `scribe-out/`

**Perfect for:**
- Batch processing recordings
- Automated workflows
- Integration with recording software

---

## 🔄 Job Management

### List Jobs
```bash
amanu jobs list
amanu jobs list --status failed
```

### Inspect Job Details
```bash
amanu jobs show <job_id>
```

**Shows:**
- Original file info
- Processing stages
- Token usage
- Errors (if any)

### Retry Failed Jobs
```bash
amanu jobs retry <job_id>
amanu jobs retry <job_id> --from-stage scribe
```

### Cleanup Old Jobs
```bash
amanu jobs cleanup --older-than 7 --status failed
```

---

## 📊 Advanced Features

### Context Caching
For files longer than 5 minutes, Amanu uses Google's caching feature:
- ✅ Faster processing
- ✅ Lower costs
- ✅ Handles very long files (hours)

### Retry Logic
Automatic retry for API errors:
- Rate limits (429 errors)
- Temporary failures
- Configurable delays

```yaml
processing:
  scribe:
    retry_max: 3
    retry_delay_seconds: 5
```

### Debug Mode
Enable detailed logging:

```yaml
processing:
  debug: true
```

**Creates `_stages/` folder with:**
- Full API requests/responses
- Timing information
- Token counts
- Error details

---

## 📁 Organization Modes

### Timeline Mode (Default)
```
scribe-out/
└── 2025/
    └── 11/
        └── 26/
            └── job_id/
```

**Best for:** Chronological organization, journals, meetings

### Zettelkasten Mode
```
scribe-out/
└── 202511260930 Meeting Notes.md
└── 202511261445 Interview.md
```

**Best for:** Knowledge management, atomic notes

```yaml
shelve:
  strategy: "zettelkasten"
  zettelkasten:
    id_format: "%Y%m%d%H%M"
    filename_pattern: "{id} {slug}.md"
```

---

## 🎨 Customization

### Templates
Create custom output formats using Jinja2:

```jinja2
# templates/markdown/brief.j2
# {{ title }}

{{ summary }}

## Key Points
{% for point in key_takeaways %}
- {{ point }}
{% endfor %}
```

### Plugins
Extend Amanu with custom output formats:
- DOCX documents
- HTML pages
- LaTeX papers
- Custom JSON structures

See [Customization Guide](./customization.md) for details.

---

## 💡 Use Case Examples

### Meeting Minutes
```bash
amanu run meeting.mp3
```
**Get:** Full transcript + summary + action items

### Interview Transcription
```bash
amanu run interview.wav --compression-mode optimized
```
**Get:** Speaker-separated, time-stamped transcript

### Lecture Notes
```bash
amanu run lecture.m4a --skip-transcript
```
**Get:** Summary + key concepts (fast & cheap)

### Podcast Subtitles
```bash
amanu run podcast.mp3
```
**Get:** SRT file for video editing

### Voice Journal
```bash
amanu watch  # Drop daily notes into folder
```
**Get:** Organized by date in `scribe-out/`

---

## 🔍 What's Next?

- [Configuration Guide](./configuration.md) - Deep dive into settings
- [Customization Guide](./customization.md) - Templates and plugins
- [Architecture](./architecture_report.md) - How it works under the hood
