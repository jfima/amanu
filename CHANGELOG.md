# Changelog

All notable changes to Amanu will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2025-11-26

### 🎉 Major Architecture Refactor

This release represents a complete architectural overhaul, transitioning from a 4-stage to a **5-stage pipeline** with a **plugin-based output system**.

### Added
- **GENERATE Stage**: New dedicated stage for multi-format artifact generation
- **Plugin System**: Extensible architecture for output formats
  - Markdown plugin (Jinja2-based)
  - PDF plugin (ReportLab-based)
  - SRT plugin (subtitle generation)
- **Template System**: Jinja2 templates for customizable output
  - `templates/markdown/default.j2` - Full transcript
  - `templates/markdown/summary.j2` - Executive summary
  - `templates/pdf/report.j2` - PDF reports
  - `templates/srt/standard.j2` - Subtitles
- **Multi-Format Output**: Generate multiple artifacts from single job
- **Direct Analysis Mode**: Skip transcription for cost savings (`--skip-transcript`)
- **SRT Subtitle Generation**: Time-aligned subtitles for video
- **PDF Report Generation**: Professional formatted reports
- **Job State Management**: Enhanced tracking with `state.json` and `meta.json`
- **Cost Reporting**: Detailed usage and pricing analytics (`amanu report`)
- **Retry Logic**: Configurable retry for API errors (429 rate limits)

### Changed
- **Pipeline Stages**: Renamed and restructured
  - `SCOUT` → `INGEST` (canonical name)
  - Removed `PREP` (merged into INGEST)
  - Added `GENERATE` (new stage)
- **REFINE Stage**: Now outputs **pure JSON data** (no Markdown formatting)
  - Markdown formatting moved to GENERATE stage
  - Cleaner separation of concerns
- **CLI Commands**: Simplified and clarified
  - Removed: `amanu scout`, `amanu prep`
  - Added: `amanu ingest` (canonical command)
  - All stage commands now match stage names
- **Configuration**: Enhanced `config.yaml` structure
  - New `output.artifacts` section for multi-format configuration
  - Plugin-based artifact specification
  - Removed deprecated `template` field
- **Output Structure**: Timeline mode now includes job_id
  - `YYYY/MM/DD/` → `YYYY/MM/DD/job_id/`
- **Python Requirement**: Minimum version increased to **3.10**
  - Enables modern type hint syntax (`Type | None`)

### Fixed
- **Template Loading**: Removed fallback to root `templates/` directory
  - Templates must now be in `templates/{plugin}/` subdirectories
- **SRT Validation**: Skip SRT generation in Direct Analysis mode
- **SCOUT Reference**: Fixed remaining `StageName.SCOUT` in `manager.py`
- **CLI Mapping**: Corrected stage name mappings
- **Shelve Structure**: Fixed timeline mode to create job-specific folders

### Removed
- **Legacy Files** (7 files):
  - `amanu/prompts.py` - Obsolete template system
  - `amanu/file_manager.py` - Unused utility
  - `amanu/models.py` - Superseded by `core/models.py`
  - `amanu/response_parser.py` - Unused parser
  - `amanu/results_manager.py` - Legacy result handler
  - `amanu/templates/summary.md` - Old template format
  - `amanu/pipeline/prep.py` - Merged into INGEST
- **Legacy Commands**: `scout`, `prep` (use `ingest` instead)
- **Deprecated Config**: Removed `template: "default"` comment

### Technical Details
- **LOC**: ~3,176 lines of Python code across 24 modules
- **Architecture**: Clean separation of concerns with plugin architecture
- **Type Safety**: Full Pydantic model validation
- **Extensibility**: Easy to add new output formats via plugins

### Migration Guide (v0.1.1 → v0.1.2)

#### Configuration Changes
Update your `config.yaml`:

```yaml
# OLD (v0.1.1)
processing:
  template: "default"

# NEW (v0.1.2)
processing:
  output:
    artifacts:
      - plugin: markdown
        template: default
        filename: "transcript"
      - plugin: markdown
        template: summary
        filename: "summary"
```

#### CLI Changes
Update your scripts:

```bash
# OLD
amanu scout file.mp3
amanu prep job_id

# NEW
amanu ingest file.mp3
amanu ingest file.mp3  # prep merged into ingest
```

#### Template Changes
If you have custom templates:
- Move from `templates/template.md` to `templates/markdown/template.j2`
- Update extension: `.md` → `.j2`
- Remove Markdown formatting from Refine prompts (now in templates)

---

## [0.1.1] - 2025-11-24

### Added
- Debug logging integration with `config.yaml`
- `.gitignore` for clean repository
- SRT file export option
- Silence removal optimization settings

### Fixed
- JSON encoding for non-ASCII characters
- API key validation with clear error messages
- Scribe output optimization (removed unnecessary chunk files)

---

## [0.1.0] - 2025-11-22

### Initial Release
- 4-stage pipeline (Scout, Prep, Scribe, Refine)
- Gemini API integration
- Context caching for long files
- OGG Opus compression
- Watch mode for auto-processing
- Job management system
- Timeline-based organization
