# Pipeline & Plugin System Review

## Current State Analysis

### 1. Pipeline Architecture
The current pipeline consists of `Scribe` -> `Refine` -> `Shelve`.

*   **Scribe**: Handles transcription.
    *   *Pros*: Robust retry logic, speaker identification, JSONL streaming.
    *   *Cons*: Complex loop logic, output is strictly raw segments.
*   **Refine**: Handles cleaning AND analysis.
    *   *Pros*: Generates useful metadata.
    *   *Cons*: **Overloaded responsibility.** It performs text cleaning, summarization, and formatting (Markdown) all in one step. This makes it hard to reuse the "cleaning" logic for other formats (like PDF) without re-running the LLM or parsing the Markdown output.
*   **Shelve**: Placeholder.
    *   *Cons*: Does not actually organize files. Lacks flexibility.

### 2. User Concerns
*   **"Scribe and Refine are chaotic"**: Confirmed. `Refine` is doing too much. It mixes *content generation* (cleaning/summarizing) with *file formatting* (Markdown).
*   **"Shelve needs Zettelkasten"**: Confirmed. Current implementation is a stub.

## Proposed Improvements

I propose refactoring the pipeline into **4 distinct stages** to separate concerns and enable the plugin system effectively.

### New Pipeline Flow

1.  **Stage 1: SCRIBE (Transcription)**
    *   **Goal**: Accurate raw data.
    *   **Input**: Audio file.
    *   **Output**: `raw_transcript.json` (Segments with timestamps & speaker IDs).
    *   **Changes**: Minimal. Focus on robustness.

2.  **Stage 2: REFINE (Synthesis & Analysis)**
    *   **Goal**: Understanding and Structuring.
    *   **Input**: `raw_transcript.json`.
    *   **Output**: `enriched_context.json`.
    *   **Key Concept**: This stage performs the heavy cognitive lift **once**.
        *   Cleans the text (removes fillers, fixes grammar).
        *   Extracts metadata (Summary, Keywords, Entities, Sentiment).
        *   **Crucially**: It does *not* format the final file. It outputs pure data.

3.  **Stage 3: GENERATE (Projection)**
    *   **Goal**: Formatting and File Creation (The Plugin Layer).
    *   **Input**: `enriched_context.json` + `raw_transcript.json`.
    *   **Output**: Artifacts (Files).
    *   **Mechanism**:
        *   **Markdown Plugin**: Takes `clean_text` from context -> `transcript.md`.
        *   **PDF Plugin**: Takes `clean_text` + `summary` -> `report.pdf`.
        *   **SRT Plugin**: Takes `raw_transcript` -> `subs.srt`.
    *   **Benefit**: Multiple formats can be generated from a single "Refine" run without extra LLM costs for cleaning.

4.  **Stage 4: SHELVE (Organization)**
    *   **Goal**: Knowledge Management.
    *   **Input**: Generated Artifacts.
    *   **Output**: Files moved/linked to destination.
    *   **Features**:
        *   **Zettelkasten Support**: Rename files using ID-based patterns (e.g., `202411251430-my-note.md`).
        *   **Tag-based Routing**: Move files to folders based on tags found in `enriched_context.json`.

## 3. Artifact Naming & Plugin-Template Binding

You asked: *"How to organize storage... how to link pipeline, plugins, and templates? ...filename from template name?"*

This is the proposed solution:

### The Binding Logic
**`Plugin` + `Template` = `Artifact`**

*   **Plugin**: Defines **HOW** to write the file (Format).
    *   *Example*: `PDFPlugin` knows how to use `reportlab` to draw text on a page. It returns raw bytes.
    *   *Example*: `MarkdownPlugin` knows how to return a text string.
*   **Template**: Defines **WHAT** goes in the file (Content & Structure).
    *   *Example*: `templates/pdf/executive_report.j2` (Jinja2 template for PDF content).
    *   *Example*: `templates/markdown/meeting_notes.j2`.

### Naming Convention
By default, the **Output Filename** is derived from the **Template Name**.

| Plugin | Template Name | Default Output Filename |
| :--- | :--- | :--- |
| `markdown` | `meeting_notes` | `meeting_notes.md` |
| `pdf` | `executive_report` | `executive_report.pdf` |
| `srt` | `subtitles` | `subtitles.srt` |

### Configuration Example
Users can override this in `config.yaml` or CLI arguments.

```yaml
# config.yaml
output:
  # List of artifacts to generate
  artifacts:
    - plugin: markdown
      template: clean        # -> clean.md
    
    - plugin: pdf
      template: report       # -> report.pdf
      
    - plugin: markdown
      template: summary
      filename: "README"     # Override -> README.md
```

### Handling Binary vs Text
The `Generate` stage treats all outputs as **Bytes**.
1.  **Text Plugins (MD, JSON, SRT)**: Generate string -> Encode to UTF-8 bytes -> Return bytes.
2.  **Binary Plugins (PDF, DOCX)**: Generate binary object -> Serialize to bytes -> Return bytes.

The Pipeline (Stage 3) just receives a blob of bytes and a filename, so it doesn't care if it's text or binary.

## Specific Specification Updates

### 1. Update `Refine` vs `Generate`
The spec currently proposes replacing `Refine` with `Generate`. I suggest keeping `Refine` but narrowing its scope to "Analysis/Cleaning" and adding `Generate` as the "Formatting" stage.

### 2. Zettelkasten Configuration for `Shelve`
Add a configuration section for organization strategies.

```yaml
shelve:
  strategy: "zettelkasten" # or "flat", "date_tree"
  root_path: "~/Obsidian/Vault"
  
  zettelkasten:
    id_format: "%Y%m%d%H%M"
    filename_pattern: "{id}-{slug}.md"
    link_style: "wiki" # [[id]]
```

## Next Steps

1.  **Approve this architecture**: Do you agree with the 4-stage split?
2.  **Update Specification**: I will rewrite `plugin-system-development-specification.md` to reflect this cleaner architecture.
3.  **Refactor**: Begin implementation by splitting `Refine` logic.
