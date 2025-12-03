# Dynamic Provider Discovery - December 3, 2025

## Overview

Refactored the setup wizard (`amanu setup`) to use dynamic provider discovery instead of hardcoded provider lists. This makes adding new providers seamless - simply create a provider directory with a `defaults.yaml` file containing metadata, and the wizard automatically discovers and integrates it.

## Motivation

**Previous Issues:**
- Adding new providers (like OpenRouter) required modifying multiple locations in `wizard.py`
- Provider metadata (description, cost, speed) was hardcoded in Python code
- No clear capability declaration (which providers support transcription vs refinement)
- Maintenance burden: every new provider meant editing hardcoded lists

**Solution:**
- Moved all provider metadata into `defaults.yaml` files
- Implemented capability-based filtering
- Wizard now discovers providers from filesystem
- Zero code changes needed to add new providers

## Changes

### 1. Enhanced Provider Metadata Schema

All provider `defaults.yaml` files now include a `metadata` section:

```yaml
metadata:
  # Display information
  display_name: "OpenRouter"
  description: "Access 200+ AI models through unified API"
  
  # Provider characteristics
  type: "cloud"              # cloud | local | hybrid
  cost_indicator: "$$"       # $ | $$ | $$$ | Free
  speed_indicator: "fast"    # fast | medium | slow
  
  # Capabilities
  capabilities:
    - transcription
    - refinement
  
  # API configuration
  api_key:
    required: true
    env_var: "OPENROUTER_API_KEY"
    display_name: "OpenRouter API Key"
  
  # Documentation links
  docs_url: "https://openrouter.ai/docs"
  pricing_url: "https://openrouter.ai/pricing"
```

**Updated Files:**
- [`amanu/providers/openrouter/defaults.yaml`](amanu/providers/openrouter/defaults.yaml)
- [`amanu/providers/gemini/defaults.yaml`](amanu/providers/gemini/defaults.yaml)
- [`amanu/providers/whisperx/defaults.yaml`](amanu/providers/whisperx/defaults.yaml)
- [`amanu/providers/zai/defaults.yaml`](amanu/providers/zai/defaults.yaml)
- [`amanu/providers/claude/defaults.yaml`](amanu/providers/claude/defaults.yaml)
- [`amanu/providers/whisper/defaults.yaml`](amanu/providers/whisper/defaults.yaml)

### 2. ProviderManager Enhancements

**New Methods in [`wizard.py`](amanu/wizard.py):**

```python
class ProviderManager:
    def get_all_providers(self) -> List[str]:
        """Return list of all available provider names"""
        
    def get_providers_by_capability(self, capability: str) -> List[str]:
        """Filter providers that support a specific capability"""
        
    def get_metadata(self, provider_name: str) -> Dict[str, Any]:
        """Get provider metadata from defaults.yaml"""
        
    def requires_api_key(self, provider_name: str) -> bool:
        """Check if provider requires API key"""
        
    def get_api_key_info(self, provider_name: str) -> Dict[str, str]:
        """Get API key configuration for provider"""
```

**Removed:**
- `get_provider_info()` - hardcoded metadata replaced by dynamic `get_metadata()`

### 3. Wizard Refactoring

#### API Keys Setup
**Before:** Hardcoded list `["gemini", "zai"]`

**After:** Dynamic discovery
```python
all_providers = self.provider_manager.get_all_providers()
providers_needing_keys = [
    p for p in all_providers 
    if self.provider_manager.requires_api_key(p)
]
```

#### Transcription Setup
**Before:** Hardcoded list `["gemini", "whisperx", "zai"]`

**After:** Capability-based filtering
```python
available_providers = self.provider_manager.get_providers_by_capability('transcription')
```

#### Refinement Setup
**Before:** Hardcoded list `["gemini", "zai"]`

**After:** Capability-based filtering
```python
available_providers = self.provider_manager.get_providers_by_capability('refinement')
```

#### Dashboard Display
**Before:** Hardcoded status checks for Gemini and Zai only

**After:** Dynamic API key status for all providers
```python
for provider in sorted(all_providers):
    if self.provider_manager.requires_api_key(provider):
        # Check and display status dynamically
```

## Benefits

### ✅ OpenRouter Integration
- OpenRouter now appears automatically in:
  - API Keys configuration
  - Transcription provider selection (for multimodal models)
  - Refinement provider selection (for text models)

### ✅ Zero-Code Provider Addition

To add a new provider, simply:

1. Create directory: `amanu/providers/newprovider/`
2. Add `defaults.yaml` with metadata section
3. Done! Wizard automatically discovers it

### ✅ Maintainability
- Single source of truth: all provider info in `defaults.yaml`
- No more hardcoded lists in Python code
- Consistent metadata structure across providers

### ✅ Flexibility
- Providers can declare multiple capabilities
- Easy to add new capabilities (translation, summarization, etc.)
- Graceful degradation: missing metadata fields use sensible defaults

## Backward Compatibility

✅ **Fully backward compatible**
- Existing providers work with new metadata
- Falls back to defaults if metadata missing
- No changes required to existing `config.yaml` files
- No breaking changes to provider APIs

## Current Provider Support

After this update, the following providers are available in `amanu setup`:

| Provider | Transcription | Refinement | Type | Cost |
|----------|---------------|------------|------|------|
| Gemini | ✅ | ✅ | Cloud | $$ |
| OpenRouter | ✅ | ✅ | Cloud | $$ |
| Zai | ✅ | ✅ | Cloud | $ |
| Claude | ❌ | ✅ | Cloud | $$$ |
| WhisperX | ✅ | ❌ | Local | Free |
| Whisper | ✅ | ❌ | Local | Free |

## Testing

Verified that:
- ✅ All six providers appear correctly in wizard
- ✅ OpenRouter shows in both transcription and refinement
- ✅ API key prompts work for all providers requiring keys
- ✅ Provider metadata displays correctly in tables
- ✅ Model selection works for all providers
- ✅ Dashboard shows correct API key status

## Migration Notes

**No action required for users:**
- Existing installations continue working
- Setup wizard automatically uses new discovery system
- All provider metadata loaded from updated defaults.yaml files

## Future Enhancements

This refactoring enables:
- Easy addition of translation providers
- Support for hybrid providers (local + cloud)
- Provider-specific wizard steps
- Dynamic model filtering (e.g., by context window, cost)
- Provider health checks and availability status

## Files Modified

**Core Changes:**
- [`amanu/wizard.py`](amanu/wizard.py) - Refactored ProviderManager and wizard methods

**Provider Metadata:**
- [`amanu/providers/openrouter/defaults.yaml`](amanu/providers/openrouter/defaults.yaml)
- [`amanu/providers/gemini/defaults.yaml`](amanu/providers/gemini/defaults.yaml)
- [`amanu/providers/whisperx/defaults.yaml`](amanu/providers/whisperx/defaults.yaml)
- [`amanu/providers/zai/defaults.yaml`](amanu/providers/zai/defaults.yaml)
- [`amanu/providers/claude/defaults.yaml`](amanu/providers/claude/defaults.yaml)
- [`amanu/providers/whisper/defaults.yaml`](amanu/providers/whisper/defaults.yaml)

**Documentation:**
- [`docs/dynamic_provider_discovery_plan.md`](docs/dynamic_provider_discovery_plan.md) - Implementation plan
- [`docs/changelog/2025-12-03_dynamic_provider_discovery.md`](docs/changelog/2025-12-03_dynamic_provider_discovery.md) - This file

## Related Changes

- **December 3, 2025**: OpenRouter provider implementation (see [`docs/changelog/2025-12-03_openrouter_provider.md`](docs/changelog/2025-12-03_openrouter_provider.md))
- **December 2, 2025**: Provider expansion (see [`docs/changelog/2025-12-02_provider_expansion.md`](docs/changelog/2025-12-02_provider_expansion.md))

---

**Impact:** Low risk, high value
**Breaking Changes:** None
**Testing:** Manual verification completed
**Status:** ✅ Production ready