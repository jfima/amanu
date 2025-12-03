# Amanu Documentation Index

## 📚 Documentation Overview

This index helps you find the right documentation for your needs.

---

## 🚀 Getting Started

**New to Amanu?** Start here:

1. **[README](../README.md)** - Project overview and quick start
2. **Platform-Specific Guides:**
   - [Windows 11 Setup](./getting-started-windows.md) - Complete installation for Windows
   - [macOS Setup](./getting-started-macos.md) - Complete installation for macOS

---

## 📖 User Guides

### Core Functionality
- **[Features Guide](./features.md)** - Complete feature reference
  - Audio processing, speaker detection, output formats
  - Multi-language support, cost optimization
  - Watch mode, job management
  
- **[Configuration Guide](./configuration.md)** - Complete `config.yaml` reference
  - API keys, models, processing options
  - Output configuration, paths, organization modes
  - Retry logic, cleanup settings

- **[Usage Guide](./usage_guide.md)** - Multi-provider support
  - Gemini, Whisper, Claude providers
  - Stage-specific configuration
  - Adding custom providers

### Advanced Topics
- **[Template System Design](./template_system_design.md)** - Custom field architecture
  - How template Front Matter works
  - Field collection and merging
  - Creating custom templates

- **[Partial Pipeline Execution](./partial_pipeline_execution.md)** - Running specific stages
  - Stage-by-stage execution
  - Retrying failed jobs

---

## 🔌 Provider Documentation

### Using Providers
- **[Usage Guide](./usage_guide.md)** - Multi-provider support overview
  - Gemini, Whisper, Claude, OpenRouter providers
  - Stage-specific configuration

### OpenRouter Provider
- **[OpenRouter Quick Start](./openrouter_quickstart.md)** - Get started with OpenRouter
  - Setup and configuration
  - Recommended models
  - Cost tracking
  
- **[OpenRouter Implementation](./openrouter_implementation.md)** - Technical details
  - Features and capabilities
  - API integration
  - Testing results

### Developer Guides
- **[Adding New Providers](./adding_new_providers.md)** - Create your own provider
  - Step-by-step guide
  - Metadata configuration
  - Testing checklist
  
- **[Dynamic Provider Discovery](./dynamic_provider_discovery_plan.md)** - How provider discovery works
  - Architecture and design
  - Metadata system
  - Integration patterns

---

## 🏗️ Developer Documentation

### Architecture
- **[Architecture Report](./architecture_report.md)** - System design overview
  - Pipeline architecture
  - Provider abstraction
  - Data flow and directory structure

- **[Architecture Decisions](./architecture_decisions.md)** - Design rationale
  
- **[Folder Architecture](./folder-architecture.md)** - File organization

### Changelogs
- **[v1.4.0 Multi-Provider Refactor](./changelog/v1.4.0_multi_provider_refactor.md)**
- **[2025-12-03 OpenRouter Provider](./changelog/2025-12-03_openrouter_provider.md)**
- **[2025-12-03 Dynamic Provider Discovery](./changelog/2025-12-03_dynamic_provider_discovery.md)**
- **[2025-12-03 Config Refactor](./changelog/2025-12-03_config_refactor.md)**
- **[2025-12-03 Reporting Refactor](./changelog/2025-12-03_reporting_refactor.md)**
- **[2025-12-02 Provider Expansion](./changelog/2025-12-02_provider_expansion.md)**
- **[2025-12-02 Provider Refactor](./changelog/2025-12-02_provider_refactor.md)**

---

## 🗂️ Archive

Historical documents (may be outdated):
- [Plugin System Development Specification](../archive/plugin-system-development-specification.md)
- [Spec Review](../archive/spec_review.md)
- [Technical Specification](../archive/technical_specification.md)

---

## 🔍 Quick Links by Task

### "I want to install Amanu"
→ [Windows Setup](./getting-started-windows.md) or [macOS Setup](./getting-started-macos.md)

### "I want to understand what Amanu can do"
→ [Features Guide](./features.md)

### "I want to configure Amanu"
→ [Configuration Guide](./configuration.md)

### "I want to use OpenRouter"
→ [OpenRouter Quick Start](./openrouter_quickstart.md)

### "I want to create a new provider"
→ [Adding New Providers](./adding_new_providers.md)

### "I want to create custom templates"
→ [Template System Design](./template_system_design.md)

### "I want to use multiple AI providers"
→ [Usage Guide](./usage_guide.md)

### "I want to understand how Amanu works"
→ [Architecture Report](./architecture_report.md)

### "I want to run only specific pipeline stages"
→ [Partial Pipeline Execution](./partial_pipeline_execution.md)

---

## 📝 Documentation Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| README | ✅ Current | 2025-11 |
| Features Guide | ✅ Current | 2025-11 |
| Configuration Guide | ✅ Current | 2025-12 |
| Usage Guide | ✅ Current | 2025-11 |
| Template System Design | ✅ Current | 2025-11 |
| Architecture Report | ✅ Current | 2025-11 |
| OpenRouter Quick Start | ✅ Current | 2025-12 |
| OpenRouter Implementation | ✅ Current | 2025-12 |
| Adding New Providers | ✅ Current | 2025-12 |
| Dynamic Provider Discovery | ✅ Current | 2025-12 |
| Getting Started (Windows/macOS) | ⚠️ Review | - |
| Partial Pipeline Execution | ⚠️ Review | - |

---

**Need help?** See [README](../README.md) for support information.
