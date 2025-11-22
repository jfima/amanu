# Amanu: AI-Powered Amanuensis

**Amanu** (short for Amanuensis) is your trusted AI scribe. It automatically processes voice notes (MP3) into structured, clean markdown transcripts using Google Gemini 2.0 Flash.

## Features
- **Automatic Transcription**: Converts audio to text with high accuracy.
- **Structured Output**: Generates a `transcript_raw.json` (time-aligned) and `transcript_clean.md` (polished read).
- **Smart Summaries**: Includes a TL;DR section for quick insights.
- **Dual Modes**:
    - `amanu watch`: Runs as a daemon, monitoring a folder for new files.
    - `amanu run`: Processes all existing files in the folder and exits.

## Prerequisites

Before installing, ensure you have the following:

1.  **Python 3.9+**: [Download Python](https://www.python.org/downloads/)
2.  **FFmpeg**: Required for audio compression.
    - **Ubuntu/Debian**: `sudo apt install ffmpeg`
    - **macOS**: `brew install ffmpeg`
    - **Windows**: [Download FFmpeg](https://ffmpeg.org/download.html) and add it to your PATH.
3.  **Gemini API Key**: Get one from [Google AI Studio](https://aistudio.google.com/).

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd amanu
    ```

2.  **Install the package**:
    ```bash
    pip install -e .
    ```
    *This installs the `amanu` command globally in your current environment.*

3.  **Configuration**:
    - Copy the example config:
      ```bash
      cp config.example.yaml config.yaml
      ```
    - Open `config.yaml` and paste your API key:
      ```yaml
      gemini:
        api_key: "YOUR_KEY_HERE"
      ```

## Quick Start Use Case

1.  **Prepare**: You have a voice note named `meeting_notes.mp3`.
2.  **Action**: Drop the file into the `input/` folder.
3.  **Run**:
    ```bash
    amanu run
    ```
    *(Or keep `amanu watch` running in the background)*
4.  **Result**: Amanu processes the file and saves the results in `results/`.

## Advanced Usage

### 1. Templates
Control the format of the `transcript_clean.md` output using the `--template` argument.

-   **Default**: Detailed structured note.
    ```bash
    amanu run
    ```
-   **Summary**: Concise executive summary.
    ```bash
    amanu run --template summary
    ```
-   **Custom**: Create your own `.md` file in `amanu/templates/` or `~/.config/amanu/templates/` and reference it by name.
    ```bash
    amanu run --template my-custom-template
    ```

### 2. Flexible Inputs
You don't need to rely on the config folder. You can process specific files or directories directly:
```bash
amanu run ./my-folder
amanu run interview.mp3
```

### 3. Dry Run
Simulate processing without making API calls or spending money. Useful for testing configuration.
```bash
amanu run --dry-run
```

### 4. Configuration Hierarchy
Amanu loads configuration in the following order (highest priority first):
1.  **Command Line Arguments** (e.g., `--template`, `path`)
2.  **Environment Variables** (`AMANU_CONFIG`, `GEMINI_API_KEY`)
3.  **Local Config** (`./config.yaml`)
4.  **User Config** (`~/.config/amanu/config.yaml`)
5.  **Defaults**

## Output Structure

For every processed file, Amanu creates a dedicated folder organized by date:
`results/YYYY/MM/DD/<timestamp>-<filename>/`

Inside this folder, you will find:

### 1. `transcript_clean.md` (The Document)
This is the human-readable version. It contains:
-   **TL;DR**: A 3-bullet summary of the key points.
-   **Polished Transcript**: The text is cleaned of filler words ("um", "ah") and formatted into paragraphs with bolded speaker names. Perfect for reading or sharing.

### 2. `transcript_raw.json` (The Data)
This is the machine-readable version. It contains the verbatim transcript with precise timestamps.
```json
[
  {"time": "00:00", "speaker": "Speaker A", "text": "Hello..."},
  {"time": "00:05", "speaker": "Speaker B", "text": "Hi there..."}
]
```
Useful for subtitles, search, or clicking to seek in a player.

### 3. `meta.json` (The Stats)
Contains processing metadata:
-   Processing duration.
-   Token usage (Input/Output).
-   Estimated cost.
-   File checksums.

### 4. `compressed.ogg`
The optimized audio file that was sent to the AI.

## License
MIT
