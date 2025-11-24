# Amanu: AI-Powered Amanuensis

**Amanu** (short for Amanuensis) is your trusted AI scribe. It automatically processes voice notes (MP3) into structured, clean markdown transcripts using Google Gemini 2.0 Flash.

![Andrew Taylor Still with his amanuensis, Annie Morris, who is at a typewriter](./amanuensis.png)

*Andrew Taylor Still, founder of osteopathy, with his amanuensis Annie Morris at the typewriter. The recursive irony: he's drawing his scribe while she records his words — a fitting metaphor for this AI transcription tool.*

## Features
- **Unified Pipeline**: Robust state-based processing (Scout -> Prep -> Scribe -> Refine -> Shelve).
- **Automatic Transcription**: Converts audio to text with high accuracy using Gemini 2.0 Flash.
- **Structured Output**: Generates `raw.json` (time-aligned) and `clean.md` (polished read).
- **Smart Summaries**: Includes a TL;DR section for quick insights.
- **Job Management**: Full control over jobs with retry, cleanup, and status tracking.
- **Dual Modes**:
    - `amanu watch`: Runs as a daemon, monitoring `scribe-in/` for new files.
    - `amanu run`: Processes specific files manually.

## Prerequisites

1.  **Python 3.9+**: [Download Python](https://www.python.org/downloads/)
2.  **FFmpeg**: Required for audio processing.
    - **Ubuntu/Debian**: `sudo apt install ffmpeg`
    - **macOS**: `brew install ffmpeg`
3.  **Gemini API Key**: Get one from [Google AI Studio](https://aistudio.google.com/api-keys).

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/jfima/amanu
    cd amanu
    ```

2.  **Install the package**:
    ```bash
    pip install -e .
    ```

3.  **Configuration**:
    - Copy the example config:
      ```bash
      cp config.example.yaml config.yaml
      ```
    - Open `config.yaml` and configure:
      ```yaml
      gemini:
        api_key: "YOUR_KEY_HERE"
      
      processing:
        debug: true  # Enable DEBUG logging (false for INFO only)
        template: "default"  # or "summary"
        language: "auto"  # or specific language like "russian", "english"
        compression_mode: "compressed"  # original, compressed, or optimized
      ```

## Quick Start

1.  **Prepare**: You have a voice note named `meeting.mp3`.
2.  **Action**: Drop the file into the `scribe-in/` folder.
3.  **Run Watcher**:
    ```bash
    amanu watch
    ```
4.  **Result**: Amanu picks up the file, processes it in `scribe-work/`, and saves the final results in `scribe-out/`.

## CLI Commands

### Global Options
- `-v, --verbose`: Enable verbose (DEBUG) logging, overrides `debug` setting in config.yaml

### Manual Run
Process a specific file immediately:
```bash
amanu run input/interview.mp3
```

Options:
- `--template <name>`: Use a specific template (e.g., `summary`, `default`)
- `--compression-mode <mode>`: Choose compression strategy:
  - `original`: No compression (use original file)
  - `compressed`: Convert to OGG format (default)
  - `optimized`: OGG + silence removal for cost optimization
- `--dry-run`: Simulate execution without API calls or file changes

Examples:
```bash
# Use summary template with optimized compression
amanu run meeting.mp3 --template summary --compression-mode optimized

# Dry run to see what would happen
amanu run interview.mp3 --dry-run

# Enable debug logging
amanu run -v notes.mp3
```

### Pipeline Stages
Run individual stages for fine-grained control:

```bash
# Start a new job (scout stage)
amanu scout audio.mp3 --model gemini-2.5-flash --compression-mode compressed

# Prepare audio (compress/chunk)
amanu prep <JOB_ID>

# Transcribe
amanu scribe <JOB_ID>

# Refine transcript
amanu refine <JOB_ID>

# Categorize and shelve
amanu shelve <JOB_ID>
```

### Watch Mode
Monitor a directory for new files and process automatically:
```bash
amanu watch
```
Files dropped into `scribe-in/` are automatically processed and moved to `scribe-out/`.

### Job Management
Amanu tracks every job in `scribe-work/`. You can manage them with:

- **List Jobs**:
  ```bash
  amanu jobs list
  amanu jobs list --status failed
  amanu jobs list --status completed
  ```

- **Show Details**:
  ```bash
  amanu jobs show <JOB_ID>
  ```

- **Retry Failed Job**:
  ```bash
  amanu jobs retry <JOB_ID>
  # Or retry from a specific stage
  amanu jobs retry <JOB_ID> --from-stage scribe
  ```

- **Cleanup Old Jobs**:
  ```bash
  amanu jobs cleanup --older-than 7 --status failed
  amanu jobs cleanup --older-than 1 --status completed
  ```

- **Finalize Job** (move to results):
  ```bash
  amanu jobs finalize <JOB_ID>
  ```

- **Delete Job**:
  ```bash
  amanu jobs delete <JOB_ID>
  ```

## Output Structure

Results are organized by date in `scribe-out/`:
`scribe-out/YYYY/MM/DD/<JOB_ID>/`

Inside each folder:
- **`transcripts/clean.md`**: The human-readable document with summary and polished text.
- **`transcripts/raw.json`**: Verbatim transcript with timestamps and speaker IDs.
- **`_stages/`**: detailed JSON logs for each pipeline stage (scout, prep, scribe, etc.), including cost and token usage.

## License
MIT
