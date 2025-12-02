# Amanu Architecture Report

## 1. Overview

Amanu is a modular, AI-powered audio processing pipeline designed to transform raw audio recordings into structured, useful documents. It follows a "pipeline" architectural pattern, where data flows through a series of distinct stages, each responsible for a specific transformation.

The core design philosophy emphasizes:
*   **Modularity**: Stages are independent and can be retried or skipped.
*   **Extensibility**: New AI providers and output formats can be added via plugins.
*   **Robustness**: State is persisted at every step to prevent data loss.

## 2. System Architecture

### 2.1 The Pipeline

The application is structured around a 5-stage pipeline:

1.  **INGEST (`IngestStage`)**
    *   **Responsibility**: Prepares audio for processing.
    *   **Actions**:
        *   Analyzes input file (duration, format).
        *   Compresses audio to optimized OGG/Opus format (if configured).
        *   Uploads large files to Gemini Context Caching (if using Gemini).
    *   **Output**: `ingest.json` (contains file paths or cache URIs).

2.  **SCRIBE (`ScribeStage`)**
    *   **Responsibility**: Converts speech to text.
    *   **Actions**:
        *   Uses a `TranscriptionProvider` (Gemini, Whisper, Claude) to transcribe audio.
        *   Handles speaker identification and timestamping.
    *   **Output**: `raw_transcript.json` (verbatim transcript with metadata).

3.  **REFINE (`RefineStage`)**
    *   **Responsibility**: Extracts intelligence.
    *   **Actions**:
        *   Uses a `RefinementProvider` to analyze the transcript or audio.
        *   Generates summaries, action items, and key takeaways.
        *   Can perform "Direct Analysis" (skipping Scribe) for lower latency/cost.
    *   **Output**: `enriched_context.json` (structured data).

4.  **GENERATE (`GenerateStage`)**
    *   **Responsibility**: Creates user-facing artifacts.
    *   **Actions**:
        *   Uses output plugins to render data into files.
        *   Supports Markdown (via Jinja2), PDF, SRT, etc.
    *   **Output**: Final files in `transcripts/` folder (e.g., `meeting_notes.md`, `subs.srt`).

5.  **SHELVE (`ShelveStage`)**
    *   **Responsibility**: Finalizes the job.
    *   **Actions**:
        *   Moves the job from the working directory to the results library.
        *   Organizes files based on strategy (Timeline or Zettelkasten).
    *   **Output**: Archived job in `scribe-out/`.

### 2.2 Core Components

*   **`JobManager`**: Orchestrates the lifecycle of a job. It creates jobs, tracks their state (`state.json`), and manages the file system structure (`scribe-work/` vs `scribe-out/`).
*   **`ProviderFactory`**: A factory pattern implementation that dynamically loads AI providers based on configuration.
*   **`PluginManager`**: Discovers and loads output format plugins from `amanu/plugins/`.

## 3. Provider Abstraction

Amanu supports multiple AI backends through a unified interface located in `amanu/providers/`.

### 3.1 Transcription Providers
Must implement `TranscriptionProvider` interface:
*   `transcribe(ingest_result)`: Returns a list of segments with text, speakers, and timestamps.

**Implementations**:
*   **Gemini**: Uses Google's Gemini 1.5/2.0 models. Supports native audio caching.
*   **Whisper**: Uses local `whisper.cpp` via CLI. Privacy-focused and free.
*   **Claude**: (Experimental) Uses Anthropic's API.

### 3.2 Refinement Providers
Must implement `RefinementProvider` interface:
*   `refine(input_data, mode)`: Returns structured analysis (summary, actions, etc.).

**Implementations**:
*   **Gemini**: Uses Gemini's long-context window for deep analysis.

## 4. Data Flow

```mermaid
graph LR
    Input(Audio File) --> Ingest
    Ingest --> |ingest.json| Scribe
    Scribe --> |raw_transcript.json| Refine
    Refine --> |enriched_context.json| Generate
    Generate --> |Artifacts| Shelve
    Shelve --> Library(scribe-out/)
```

## 5. Directory Structure

```
amanu/
├── core/           # Core logic (Manager, Config, Models)
├── pipeline/       # Stage implementations
├── providers/      # AI Integrations (Gemini, Whisper)
├── plugins/        # Output formats (Markdown, PDF)
└── templates/      # Jinja2 templates for reports
```

## 6. Error Handling

*   **State Persistence**: If a stage fails, the job remains in `scribe-work/` with a `FAILED` status.
*   **Retry Mechanism**: Users can retry a job from any stage using `amanu jobs retry`.
*   **Global Logging**: All unhandled exceptions are caught and logged to `logs/app.log`.

---

## Related Documentation

- **[Template System Design](./template_system_design.md)** - Understanding how Generate and Refine stages work together
- **[Usage Guide](./usage_guide.md)** - Multi-provider architecture details
- **[Partial Pipeline Execution](./partial_pipeline_execution.md)** - Stage-by-stage control
- **[Folder Architecture](./folder-architecture.md)** - Directory structure details
- **[Documentation Index](./INDEX.md)** - Complete documentation overview
