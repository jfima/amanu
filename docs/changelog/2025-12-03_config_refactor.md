# Configuration Refactoring Summary

## What Changed

### ✅ Simplified `config.yaml`
- **Removed**: API keys (moved to `.env`)
- **Removed**: Model definitions (moved to provider `defaults.yaml`)
- **Removed**: Provider-specific settings (using defaults)
- **Kept**: Stage configuration, processing settings, paths, cleanup rules
- **Added**: Comprehensive English comments

### ✅ Enhanced `.env` and `.env.example`
- Added detailed comments with links to get API keys
- Clear structure separating AI providers from additional tokens
- Security reminder about not committing to git

### ✅ Improved Provider Defaults
Updated all provider `defaults.yaml` files with English comments:
- `amanu/providers/gemini/defaults.yaml` - Already had good comments
- `amanu/providers/whisperx/defaults.yaml` - Added setup instructions
- `amanu/providers/whisper/defaults.yaml` - Added download instructions
- `amanu/providers/claude/defaults.yaml` - Added model descriptions
- `amanu/providers/zai/defaults.yaml` - Added documentation links

### ✅ Updated `config.example.yaml`
- Complete rewrite with detailed English comments
- Examples for all available options
- Clear explanation of each setting
- Commented-out examples for optional features

### ✅ Created Documentation
- `docs/configuration.md` - Comprehensive guide explaining:
  - How the modular config system works
  - Loading order and precedence
  - Best practices
  - Migration guide from old config

## Benefits

1. **No Duplication**: Each piece of information lives in exactly one place
2. **Clearer Separation**: Config vs Secrets vs Defaults
3. **Easier Maintenance**: Update model info in one place (provider defaults)
4. **Better Security**: API keys only in `.env`, never in config
5. **User-Friendly**: Simpler config with helpful comments
6. **Portable**: Provider defaults ship with code, user config is minimal

## File Structure

```
amanu/
├── config.yaml                          # User config (minimal, no secrets)
├── config.example.yaml                  # Example with all options documented
├── .env                                 # API keys (gitignored)
├── .env.example                         # Template for .env
├── docs/
│   └── configuration.md                 # Configuration guide
└── amanu/providers/
    ├── gemini/defaults.yaml            # Gemini models & defaults
    ├── claude/defaults.yaml            # Claude models & defaults
    ├── zai/defaults.yaml               # Z.AI models & defaults
    ├── whisper/defaults.yaml           # Whisper.cpp defaults
    └── whisperx/defaults.yaml          # WhisperX defaults
```

## Migration Guide

If you have an existing `config.yaml`:

1. **Extract API keys to `.env`**:
   ```bash
   # From config.yaml providers section, move to .env:
   GEMINI_API_KEY=your_key
   CLAUDE_API_KEY=your_key
   ZAI_API_KEY=your_key
   HF_TOKEN=your_token
   ```

2. **Remove model definitions**: They're now in `amanu/providers/{provider}/defaults.yaml`

3. **Simplify provider sections**: Only keep overrides you actually need

4. **Keep**: Stage config, processing settings, paths, cleanup settings

See `config.example.yaml` for the new structure.

## Testing

The configuration loading code in `amanu/core/config.py` already supports this structure:
- Loads provider defaults from `defaults.yaml`
- Merges with user config
- Reads API keys from environment variables

No code changes were needed - the system was already designed for this!
