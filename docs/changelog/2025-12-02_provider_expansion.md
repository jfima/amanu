# Changelog - 2025-12-02

## Provider Expansion & Template System Enhancement

### 🚀 New Features

#### Multi-Provider Support
- **WhisperX Provider**: Added local GPU-accelerated transcription support with speaker diarization
  - Implemented `WhisperXProvider` with CUDA/cuDNN support for WSL2 environments
  - Added `whisperx_wrapper.py` for seamless integration with whisperx CLI
  - Configurable device selection (CPU/CUDA), compute type, and batch size
  - Optional speaker diarization with HuggingFace token support
  - Automatic VAD/alignment disabling for PyTorch 2.6+ compatibility
  
- **Z.AI Provider**: Integrated Zhipu AI for both transcription and refinement
  - Implemented `ZaiProvider` for audio transcription using GLM models
  - Implemented `ZaiRefinementProvider` with dual-mode support:
    - Native ZhipuAI chat API
    - Claude-compatible endpoint for enhanced flexibility
  - Automatic fallback mechanism between API modes
  - Support for custom schema fields in refinement

#### Template System Overhaul
- **Dynamic Custom Fields**: New `templates.py` module for advanced template processing
  - YAML Front Matter support in templates for metadata and custom field definitions
  - Automatic aggregation of custom fields from multiple templates
  - Dynamic schema generation for AI refinement stage
  - Optimized API usage by requesting only necessary data

- **Enhanced Templates**: Updated all template files with custom field support
  - Markdown templates: `concise`, `default`, `detailed`, `story`, `summary`, `stats` (new)
  - PDF templates: `classic`, `creative`, `modern`, `report`
  - TXT templates: `default`, `script`, `timestamped`
  - All templates now support custom field extraction via Front Matter

### ⚙️ Core System Improvements

#### Pipeline Architecture
- **Enhanced Error Handling**: Improved error propagation and status tracking across all stages
  - Better job state management in `JobManager`
  - Comprehensive error logging with context
  - Graceful degradation for missing dependencies

- **Stage Refactoring**: Updated all pipeline stages for better modularity
  - `IngestStage`: Enhanced format conversion and validation
  - `ScribeStage`: Multi-provider support with automatic provider selection
  - `RefineStage`: Custom schema integration and dynamic field extraction
  - `GenerateStage`: Template metadata parsing and custom field rendering
  - `ShelveStage`: Improved output handling and validation

#### Configuration Management
- **Extended Models**: Added new configuration models for providers
  - `WhisperXConfig`: Comprehensive WhisperX settings
  - `ZaiConfig`: Z.AI API configuration with optional base URL
  - Enhanced `ModelSpec` for cost tracking across providers

- **Provider Factory**: Updated `ProviderFactory` to support new providers
  - Dynamic provider instantiation based on configuration
  - Validation of provider-specific requirements
  - Better error messages for missing dependencies

### 🔧 CLI Enhancements
- **Improved Commands**: Enhanced all CLI commands with better feedback
  - Added progress indicators for long-running operations
  - Better error messages with actionable suggestions
  - Enhanced wizard for multi-provider setup

### 📝 Documentation Updates
- **New Documentation**:
  - `docs/INDEX.md`: Comprehensive documentation index
  - `docs/architecture_decisions.md`: Design decisions and rationale
  - `docs/audio-processing-stratagies-gemini.md`: Gemini-specific strategies
  - `docs/pipeline_dependencies.md`: Pipeline stage dependencies
  - `docs/template_system_design.md`: Template system architecture
  - `docs/providers/`: Provider-specific documentation (directory)

- **Updated Documentation**:
  - `README.md`: Updated with new provider information
  - `docs/architecture_report.md`: Reflected new architecture changes
  - `docs/configuration.md`: Added new provider configurations
  - `docs/features.md`: Documented new features
  - `docs/usage_guide.md`: Updated usage examples

### 🐛 Bug Fixes
- Fixed `.gitignore` to properly exclude temporary files and credentials
- Removed Windows Zone.Identifier files from repository
- Fixed cost calculation for providers without explicit pricing models
- Improved JSON parsing in WhisperX output handling

### 🔄 Breaking Changes
None - all changes are backward compatible with existing configurations.

### 📦 Dependencies
- Added `zhipuai` for Z.AI provider support
- WhisperX requires separate installation (optional dependency)
- Enhanced CUDA/cuDNN support for GPU acceleration

### 📊 Statistics
- **36 files changed**: 1,422 insertions(+), 410 deletions(-)
- **3 new providers**: WhisperX, Z.AI (transcription + refinement)
- **13 templates updated**: All templates now support custom fields
- **5 new documentation files**: Comprehensive architecture and design docs

---

**Migration Notes**: 
- Existing configurations continue to work without changes
- To use new providers, update `config.yaml` with provider-specific settings
- Templates with custom fields require Front Matter syntax (see `docs/template_system_design.md`)
