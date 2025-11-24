# Amanu: The AI Amanuensis

**Amanu** is an intelligent audio processing engine designed to turn **any media file** into **any content format**. 

It's not just a transcriber; it's an autonomous agent that listens, understands, and reconstructs your voice notes into structured, professional documents—whether that's a blog post, a video script, or a polished meeting summary.

![Andrew Taylor Still with his amanuensis, Annie Morris, who is at a typewriter](./amanuensis.png)

*Andrew Taylor Still, founder of osteopathy, with his amanuensis Annie Morris at the typewriter. A fitting metaphor for this tool: you speak, it crafts.*

## 🧠 How It Works

Amanu operates as a state-based pipeline, treating your audio processing as a multi-stage "job" rather than a simple script.

### The Pipeline
1.  **Scout**: Analyzes the input file. It checks duration, format, and complexity to decide the best strategy (e.g., "Should I split this?", "Is it too big for one pass?").
2.  **Prep**: Optimizes the media.
    *   **Compression**: Converts heavy WAV/MP3 files into highly efficient **OGG Opus (24k bitrate)**. This reduces file size by up to 10x without losing speech clarity, allowing hours of audio to fit into a single API call.
    *   **Smart Caching**: Instead of re-uploading the same file, Amanu uses **Gemini Context Caching**. It uploads the file once and creates a temporary "cache" in the cloud, making subsequent requests faster and cheaper.
3.  **Scribe**: The core transcription engine.
    *   **Speaker Identification**: First, it listens to the whole file to identify speakers and assign consistent names.
    *   **Streamed Transcription**: It transcribes in chunks using a robust JSONL streaming protocol, ensuring that even if the connection drops, progress is saved.
4.  **Refine**: Post-processing intelligence. It takes the raw transcript and applies a "Template" (e.g., Summary, Blog Post) to generate the final clean document.
5.  **Shelve**: Organizes the results into a structured `YYYY/MM/DD` folder hierarchy.

## 🚀 Key Features

- **Large File Handling**: By combining **OGG compression** with Gemini's **2-million token context window**, Amanu can process massive files (hours of audio) in a single pass without arbitrary splitting.
- **Context Caching**: Leverages Google's advanced caching to reduce latency and cost for repeated operations on the same audio.
- **Daemon Mode**: Run `amanu watch` to turn a folder into a magic portal. Drop a file in, get a markdown file out.
- **Resilient**: Built-in retry mechanisms for API limits (429 errors) and network glitches.

## 🗺 Roadmap

We are building the ultimate media-to-text engine. Coming soon:

- **Multi-Format Output**:
    - [ ] **SRT/VTT**: Ready-to-upload subtitles for YouTube/Premiere.
    - [ ] **DOCX**: Formatted Word documents for corporate use.
    - [ ] **PDF**: Polished reports.
- **Multi-API Support**:
    - [ ] **OpenAI Whisper**: For local or alternative cloud transcription.
    - [ ] **Anthropic Claude**: For advanced reasoning and summarization.
- **Content Templates**:
    - [ ] **Video Script**: Turn a rambling voice note into a structured YouTube script.
    - [ ] **Blog Post**: Convert a lecture into an SEO-optimized article.

## 🛠 Installation

1.  **Clone & Install**:
    ```bash
    git clone https://github.com/jfima/amanu
    cd amanu
    pip install -e .
    ```

2.  **Configuration**:
    ```bash
    cp config.example.yaml config.yaml
    ```
    Edit `config.yaml`:
    ```yaml
    gemini:
      api_key: "YOUR_KEY_HERE"
    
    processing:
      debug: true         # See exactly what's happening under the hood
      template: "default" # The blueprint for your output
    ```

## ⚡ Usage

### The "Magic Folder" (Watch Mode)
The easiest way to use Amanu. Just run this in the background:
```bash
amanu watch
```
Now, whenever you save a voice note to `scribe-in/`, Amanu wakes up, processes it, and delivers the result to `scribe-out/`.

### Manual Control
Process a specific file with custom settings:

```bash
# Standard run
amanu run interview.mp3

# Generate a summary using the optimized compression strategy
amanu run meeting.wav --template summary --compression-mode optimized

# See debug logs in real-time
amanu run -v lecture.m4a
```

### Job Management
Amanu keeps track of everything.
```bash
amanu jobs list              # See what's running or failed
amanu jobs show <JOB_ID>     # Inspect a specific job
amanu jobs retry <JOB_ID>    # Resume a failed job exactly where it left off
```

## Output Structure

Your data is organized for the long term:
```text
scribe-out/
  └── 2025/
      └── 11/
          └── 24/
              └── JOB_ID/
                  ├── transcripts/
                  │   ├── clean.md      # The polished, readable result
                  │   └── raw.json      # The precise, time-aligned data
                  └── _stages/          # Detailed logs of every decision made
```

## License
MIT
