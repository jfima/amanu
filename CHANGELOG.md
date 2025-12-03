# Changelog

All notable changes to Amanu will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2025-12-03

### 🚀 Major Provider System Refactor

This release introduces a complete overhaul of the provider system with dynamic discovery, multi-provider support, and improved configuration management.

### Added
- **Dynamic Provider Discovery**: Providers are now automatically discovered from metadata
  - No wizard.py changes needed when adding new providers
  - Metadata-driven provider configuration
  - See [Adding New Providers](./docs/adding_new_providers.md) guide
- **OpenRouter Provider**: Full integration with OpenRouter.ai
  - Support for 100+ models from various providers
  - Transcription via multimodal chat and Whisper models
  - Text refinement capabilities
  - Accurate cost tracking via generation API
  - See [OpenRouter Quick Start](./docs/openrouter_quickstart.md)
- **Provider Restructuring**: Each provider now has its own directory
  - `amanu/providers/base.py` - Base provider classes
  - `amanu/providers/gemini/` - Gemini provider
  - `amanu/providers/openrouter/` - OpenRouter provider
  - `amanu/providers/whisper/` - Whisper.cpp provider
  - `amanu/providers/whisperx/` - WhisperX provider
  - `amanu/providers/claude/` - Claude provider
  - `amanu/providers/zai/` - Z.AI provider
- **Provider Metadata System**: Each provider includes `defaults.yaml` with:
  - Display name, description, and capabilities
  - Cost and speed indicators
  - API key requirements
  - Supported models with pricing
- **Enhanced Setup Wizard**: Improved interactive configuration
  - Dynamic provider discovery and selection
  - Rich table displays for providers and models
  - Automatic API key validation
  - Model recommendations based on use case
- **Improved Reporting**: Refactored reporting system
  - `work/` directory as source of truth for job history
  - `results/` directory is now user-managed
  - Better cost tracking and statistics
  - Debug mode preserves all artifacts
- **Configuration Improvements**:
  - API keys moved to `.env` file
  - Provider-specific settings in `defaults.yaml`
  - Cleaner, simplified `config.yaml`
  - Example configuration with detailed comments

### Changed
- **Provider Architecture**: Complete restructure from flat files to modular directories
  - Old: `amanu/providers/gemini.py`
  - New: `amanu/providers/gemini/provider.py`
- **Configuration Management**:
  - API keys no longer in `config.yaml` (use `.env` instead)
  - Provider defaults moved from `config.yaml` to provider-specific `defaults.yaml`
  - Eliminated configuration duplication
- **Factory Pattern**: Updated `core/factory.py` for lazy loading
  - Providers loaded on-demand
  - Better error handling
  - Support for multiple provider types per provider
- **Reporting Logic**: Refactored job finalization
  - Debug mode: All files preserved in `work/`
  - Production mode: Heavy files pruned, metadata retained
  - Consistent job state tracking

### Fixed
- **OpenRouter Refine Error**: Fixed `AttributeError` with usage object
  - Correctly handle dictionary-based usage data
  - Proper token count and cost tracking
- **WhisperX SecretStr Error**: Fixed `TypeError` with HF token
  - Proper handling of `SecretStr` objects
  - Safe logging without exposing secrets
- **Setup Wizard Paths**: Fixed `PermissionError` outside project root
  - Config and logs now in `~/.config/amanu/`
  - User-writable locations for pip installations

### Documentation
- **New Guides**:
  - [Adding New Providers](./docs/adding_new_providers.md) - Complete provider development guide
  - [OpenRouter Quick Start](./docs/openrouter_quickstart.md) - Getting started with OpenRouter
  - [OpenRouter Implementation](./docs/openrouter_implementation.md) - Technical details
  - [Dynamic Provider Discovery](./docs/dynamic_provider_discovery_plan.md) - Architecture documentation
- **Updated Documentation**:
  - [README.md](./README.md) - Added multi-provider information
  - [INDEX.md](./docs/INDEX.md) - Added provider documentation section
  - [Configuration Guide](./docs/configuration.md) - Updated for new config structure
- **Detailed Changelogs**:
  - [2025-12-03 OpenRouter Provider](./docs/changelog/2025-12-03_openrouter_provider.md)
  - [2025-12-03 Dynamic Provider Discovery](./docs/changelog/2025-12-03_dynamic_provider_discovery.md)
  - [2025-12-03 Config Refactor](./docs/changelog/2025-12-03_config_refactor.md)
  - [2025-12-03 Reporting Refactor](./docs/changelog/2025-12-03_reporting_refactor.md)
  - [2025-12-02 Provider Expansion](./docs/changelog/2025-12-02_provider_expansion.md)

### Migration Guide (v1.5.0 → v1.6.0)

#### Environment Variables
Create a `.env` file in your project root:
```bash
# Copy from example
cp .env.example .env

# Add your API keys
GEMINI_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here  # If using OpenRouter
```

#### Configuration Changes
Update your `config.yaml`:
```yaml
# OLD (v1.5.0)
providers:
  gemini:
    api_key: "your_key"
    model: "gemini-2.0-flash-001"

# NEW (v1.6.0)
transcribe:
  provider: gemini
  model: gemini-2.0-flash-001

refine:
  provider: gemini
  model: gemini-2.5-flash-001

# API keys now in .env file
```

#### Provider Selection
Use the setup wizard to configure providers:
```bash
amanu setup
```

Or manually edit `config.yaml` to choose providers:
- `gemini` - Google Gemini (default)
- `openrouter` - OpenRouter.ai (100+ models)
- `whisper` - Local Whisper.cpp
- `whisperx` - Local WhisperX
- `claude` - Anthropic Claude
- `zai` - Z.AI

---

## [1.5.0] - 2025-11-27

### 🏗️ Architecture Refactor

This release addresses structural concerns by separating AI providers from output plugins and improving system robustness.

### Changed
- **File Structure**: Moved AI providers from `amanu/plugins/` to `amanu/providers/`.
  - `amanu/providers/gemini.py`
  - `amanu/providers/claude.py`
  - `amanu/providers/whisper.py`
- **Plugins**: `amanu/plugins/` now strictly contains output formatters (Markdown, PDF, SRT).
- **Factory**: Updated `ProviderFactory` to load providers from the new location.

### Added
- **Global Error Logging**: Implemented a global exception handler (`sys.excepthook`) to ensure all crashes and unhandled exceptions are written to `logs/app.log`, preventing silent failures.

---

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
