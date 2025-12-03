# Changelog - 2025-12-02: Provider Architecture Refactor

## 🏗️ Architecture Overhaul

### Modular Provider System
- **Dynamic Loading**: Providers are now loaded dynamically from the `amanu/providers/` directory.
- **Isolated Configuration**: Each provider has its own directory with `provider.py`, `__init__.py`, and `defaults.yaml`.
- **Pydantic Models**: Configuration validation is now powered by Pydantic, ensuring type safety and better error messages.

### 🔒 Security & Configuration
- **Secrets Management**: Moved API keys to `.env` file (supported by `python-dotenv`).
- **Gitignore**: `config.yaml` and `.env` are now ignored by default to prevent accidental commits of sensitive data.
- **Backward Compatibility**: The system still supports the old `config.yaml` structure, but migrating to the new format is recommended.

### 📂 Directory Structure
New provider structure:
```
amanu/providers/
├── base.py
├── gemini/
│   ├── provider.py
│   ├── defaults.yaml
│   └── __init__.py
├── whisperx/
│   ├── provider.py
│   ├── defaults.yaml
│   └── __init__.py
└── ...
```

### 📦 Dependencies
- Added `pydantic`, `pydantic-settings`, `python-dotenv`.

### 🔄 Migration Guide
1. Create a `.env` file in the project root (copy from `.env.example`).
2. Move your API keys from `config.yaml` to `.env`.
3. (Optional) Update `config.yaml` to remove keys and use the new structure (though old structure works).
