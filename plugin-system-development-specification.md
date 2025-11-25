# Amanu Plugin System & Pipeline Specification

## 1. Project Overview

**Objective:** Transform Amanu into a modular, extensible audio processing system. The goal is to decouple "intelligence" (AI processing) from "presentation" (file formatting) and "organization" (storage), enabling a flexible plugin ecosystem and advanced knowledge management features like Zettelkasten.

## 2. Pipeline Architecture

The system is refactored into **5 distinct, linear stages**. Each stage has a single responsibility and passes structured data to the next.

### Stage 1: INGEST (Preparation)
*   **Responsibility**: Prepare audio for AI processing.
*   **Actions**:
    1.  **Analyze**: Check duration, format, bitrate (`ffprobe`).
    2.  **Optimize**: Compress audio to OGG (Opus) to minimize upload size/time.
    3.  **Upload**: Send file to Gemini (Context Caching or Direct).
*   **Input**: Raw Audio File.
*   **Output**: `ingest.json` (File URI, Cache Name, Audio Metadata).
*   **Simplification**: Merges previous `Scout` and `Prep` stages to reduce file I/O and state management overhead.

### Stage 2: SCRIBE (Transcription)
*   **Responsibility**: Convert Audio to Raw Text.
*   **Actions**:
    1.  **Identify**: Detect speakers and assign IDs.
    2.  **Transcribe**: Generate verbatim transcript with timestamps.
*   **Input**: `ingest.json`.
*   **Output**: `raw_transcript.json` (List of segments: `{speaker, time, text}`).
*   **Key Feature**: Robust retry logic and JSONL streaming for reliability.

### Stage 3: REFINE (Synthesis)
*   **Responsibility**: Extract Intelligence from Text.
*   **Mechanism**: **API-Driven**.
    *   **Standard Mode**: Accepts `raw_transcript.json` (Text). High quality, grounded analysis.
    *   **Direct Mode**: Accepts `ingest.json` (Audio URI). Lower cost, faster, but higher risk of hallucinations (no text grounding).
*   **Actions**:
    1.  **Prompting**: Constructs a prompt containing the input (Text or Audio) and instructions.
    2.  **Processing**: The LLM (Gemini) processes the content.
    3.  **Output Parsing**: The LLM returns a JSON object.
*   **Input**: `raw_transcript.json` OR `ingest.json`.
*   **Output**: `enriched_context.json` (Pure data: `{clean_text, summary, keywords, ...}`).
*   **Crucial Change**: This stage **NO LONGER** generates Markdown files. It only generates *data*.

### Stage 4: GENERATE (Projection)
*   **Responsibility**: Create User Artifacts (The Plugin Layer).
*   **Actions**:
    1.  **Load Plugins**: Initialize requested formatters (Markdown, PDF, SRT).
    2.  **Render Templates**: Apply data from `enriched_context.json` to Jinja2 templates.
    3.  **Write Files**: Generate final output files.
*   **Input**: `enriched_context.json` + `raw_transcript.json`.
*   **Output**: List of generated files (Artifacts).

### Stage 5: SHELVE (Organization)
*   **Responsibility**: Store and Index Knowledge.
*   **Actions**:
    1.  **Rename**: Apply naming conventions (e.g., Zettelkasten ID).
    2.  **Route**: Move files to specific folders based on tags/categories.
    3.  **Link**: (Future) Update index files or graph databases.
*   **Input**: Generated Artifacts.
*   **Output**: Final stored files in User's Library.

---

## 3. Plugin System (The "Generate" Stage)

The `Generate` stage uses a plugin architecture to support unlimited output formats without bloating the core.

### 3.1 Concept: Binding
An output file is defined by the binding of a **Plugin** and a **Template**.

> **Artifact = Plugin (Format) + Template (Content)**

*   **Plugin**: Defines *HOW* to write the file (e.g., "Render PDF", "Write Text").
*   **Template**: Defines *WHAT* is in the file (e.g., "Executive Summary", "Full Transcript").

### 3.2 Directory Structure
```text
amanu/
├── plugins/
│   ├── markdown.py  # Core (Text generation)
│   ├── srt.py       # Core (Subtitle generation)
│   ├── pdf.py       # Optional (Requires reportlab)
│   └── docx.py      # Optional (Requires python-docx)
└── templates/
    ├── markdown/
    │   ├── clean.j2
    │   └── summary.j2
    ├── pdf/
    │   └── report.j2
    └── srt/
        └── standard.j2
```

### 3.3 Configuration
Users configure outputs in `config.yaml`.

```yaml
output:
  artifacts:
    # Default: Clean Transcript in Markdown
    - plugin: markdown
      template: clean
      # Result: clean.md (or {filename_from_template}.md)

    # Optional: PDF Report
    - plugin: pdf
      template: report
      # Result: report.pdf

    # Optional: Subtitles
    - plugin: srt
      template: standard
      # Result: standard.srt
```

### 3.4 Artifact Naming
By default, the output filename is derived from the **Template Name**.
*   Template `meeting_notes.j2` + Plugin `markdown` -> `meeting_notes.md`
*   Template `invoice.j2` + Plugin `pdf` -> `invoice.pdf`

Users can override this in config:
```yaml
- plugin: markdown
  template: summary
  filename: "README" # -> README.md
```

### 3.5 Pipeline Modes

Users can choose between quality and cost/speed.

| Mode | Flow | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Standard** (Default) | Ingest -> Scribe -> Refine | High accuracy, verifiable text (Grounding) | Higher cost (Output tokens) |
| **Direct Analysis** | Ingest -> Refine | Low cost, faster | No raw transcript, harder to verify facts |

**CLI Usage:**
```bash
# Standard (Full Transcript + Analysis)
amanu run meeting.mp3

# Direct Analysis (Summary only, skip transcript)
amanu run meeting.mp3 --skip-transcript
```

---

## 4. Knowledge Management (The "Shelve" Stage)

The `Shelve` stage is redesigned to support structured knowledge bases, specifically Zettelkasten.

### 4.1 Configuration
```yaml
shelve:
  enabled: true
  root_path: "~/Obsidian/Vault"
  
  # Strategies: "flat", "date_tree", "zettelkasten"
  strategy: "zettelkasten"

  zettelkasten:
    # ID Format (e.g., 202411251430)
    id_format: "%Y%m%d%H%M"
    
    # Filename Pattern
    # Available vars: {id}, {slug}, {date}, {title}
    filename_pattern: "{id} {slug}.md"
    
    # Sub-folder routing based on tags
    # If transcript has tag "meeting", move to "Meetings/"
    tag_routes:
      meeting: "Meetings"
      idea: "Ideas"
      journal: "Journal"
```

### 4.2 Logic
1.  **ID Generation**: Generate a unique ID based on the timestamp.
2.  **Slugification**: Convert the generated title/summary into a filename-safe slug.
3.  **Renaming**: Rename the artifact according to `filename_pattern`.
4.  **Routing**: Check `enriched_context.json` for tags. If a match is found in `tag_routes`, move the file there. Otherwise, move to `root_path/Inbox`.

---

## 6. Cost Tracking & Reporting

Transparency is a core requirement. Users must know exactly how much each job costs and have access to aggregate reports.

### 6.1 Data Collection
Every stage that interacts with an API must record usage in `JobMeta`.

*   **Ingest**: Tracks storage/cache creation costs.
*   **Scribe**: Tracks input/output tokens for transcription.
*   **Refine**: Tracks input/output tokens for analysis.

**Data Model (`JobMeta.processing`):**
```json
{
  "total_cost_usd": 0.15,
  "total_tokens": { "input": 15000, "output": 2000 },
  "steps": [
    { "stage": "scribe", "cost": 0.10, "tokens": ... },
    { "stage": "refine", "cost": 0.05, "tokens": ... }
  ]
}
```

### 6.2 Reporting CLI
A new command `amanu report` provides cost visibility.

```bash
# Show summary of all jobs
amanu report --summary

# Output:
# Total Jobs: 12
# Total Cost: $1.45
# Average Cost/Job: $0.12
# Total Audio Processed: 4h 20m

# Show detailed list
amanu report --list

# Output:
# ID            | Date       | Cost   | Status
# --------------------------------------------
# 20241125-001  | 2024-11-25 | $0.15  | Completed
# 20241125-002  | 2024-11-25 | $0.08  | Completed
```

---

## 7. Implementation Plan

### Phase 1: Core Refactoring (The 5 Stages)
1.  **Merge Scout/Prep**: Create `IngestStage`.
2.  **Refactor Scribe**: Ensure it outputs strict `raw_transcript.json`.
3.  **Refactor Refine**: Strip Markdown generation. Output `enriched_context.json`.
4.  **Create Generate**: Implement the basic plugin runner.

### Phase 2: Plugin Implementation
1.  **Markdown Plugin**: Port existing logic to Jinja2 templates.
2.  **SRT Plugin**: Implement simple subtitle generator.
3.  **PDF/DOCX Plugins**: Implement binary formatters (lazy-loaded dependencies).

### Phase 3: Shelve & Zettelkasten
1.  **Implement Renamer**: Logic for ID generation and patterns.
2.  **Implement Router**: Logic for tag-based file moving.

### Phase 4: CLI & Config
1.  Update `config.yaml` structure.
2.  Update CLI commands to support `--output` flags (e.g., `amanu run audio.mp3 --output pdf:report`).
