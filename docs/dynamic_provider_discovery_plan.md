# Dynamic Provider Discovery - Implementation Plan

## Overview
Refactor the setup wizard to dynamically discover providers from the filesystem instead of using hardcoded lists. This will allow adding new providers (like OpenRouter) without modifying `wizard.py`.

## Current Problems

### 1. Hardcoded Provider Lists
**Location:** [`wizard.py:270`](amanu/wizard.py:270), [`wizard.py:297`](amanu/wizard.py:297), [`wizard.py:353`](amanu/wizard.py:353)

```python
# API Keys - hardcoded
providers = ["gemini", "zai"]

# Transcription - hardcoded  
available_providers = ["gemini", "whisperx", "zai"]

# Refinement - hardcoded
available_providers = ["gemini", "zai"]
```

**Issue:** OpenRouter and future providers are excluded.

### 2. Hardcoded Provider Metadata
**Location:** [`wizard.py:124-132`](amanu/wizard.py:124-132)

```python
def get_provider_info(self, provider_name: str) -> Dict[str, Any]:
    info = {
        "gemini": {...},
        "zai": {...},
        "whisperx": {...},
        # OpenRouter missing!
    }
```

**Issue:** Metadata lives in code instead of provider configuration files.

### 3. No Capability Declaration
Providers don't declare what they can do (transcription, refinement, both).

---

## Solution Architecture

### Enhanced defaults.yaml Schema

Each provider's `defaults.yaml` will include a `metadata` section:

```yaml
# Provider metadata for wizard UI and capability discovery
metadata:
  # Display information
  display_name: "OpenRouter"
  description: "Access 200+ models through a unified API"
  
  # Provider characteristics
  type: "cloud"              # cloud | local | hybrid
  cost_indicator: "$$"       # $ | $$ | $$$ | Free
  speed_indicator: "fast"    # fast | medium | slow
  
  # Capabilities (what this provider can do)
  capabilities:
    - transcription          # Can transcribe audio
    - refinement            # Can refine/clean text
    - translation           # Future: can translate
    - summarization         # Future: can summarize
  
  # API configuration
  api_key:
    required: true
    env_var: "OPENROUTER_API_KEY"
    display_name: "OpenRouter API Key"
    
  # Optional: links for documentation
  docs_url: "https://openrouter.ai/docs"
  pricing_url: "https://openrouter.ai/pricing"

# Models section (existing)
models:
  - name: google/gemini-2.0-flash-001
    type: multimodal
    # ...
```

### ProviderManager Enhancements

**Current:** [`wizard.py:97-132`](amanu/wizard.py:97-132)

**New Methods:**
```python
class ProviderManager:
    def get_all_providers(self) -> List[str]:
        """Return list of all available provider names"""
        return list(self.providers.keys())
    
    def get_providers_by_capability(self, capability: str) -> List[str]:
        """Filter providers that support a specific capability"""
        return [
            name for name, data in self.providers.items()
            if capability in data.get('metadata', {}).get('capabilities', [])
        ]
    
    def get_metadata(self, provider_name: str) -> Dict[str, Any]:
        """Get provider metadata (replaces get_provider_info)"""
        return self.providers.get(provider_name, {}).get('metadata', {})
    
    def requires_api_key(self, provider_name: str) -> bool:
        """Check if provider requires API key"""
        metadata = self.get_metadata(provider_name)
        return metadata.get('api_key', {}).get('required', False)
    
    def get_api_key_info(self, provider_name: str) -> Dict[str, str]:
        """Get API key configuration for provider"""
        metadata = self.get_metadata(provider_name)
        return metadata.get('api_key', {})
```

### Wizard Refactoring

#### 1. API Keys Setup
**Before:** Hardcoded `["gemini", "zai"]`

**After:** Dynamic discovery
```python
def _setup_api_keys(self):
    console.print(Panel("[bold]Step 1: API Keys[/bold]", style="cyan"))
    
    # Discover all providers that need API keys
    all_providers = self.provider_manager.get_all_providers()
    providers_needing_keys = [
        p for p in all_providers 
        if self.provider_manager.requires_api_key(p)
    ]
    
    for provider in sorted(providers_needing_keys):
        key_info = self.provider_manager.get_api_key_info(provider)
        key_name = key_info['env_var']
        display_name = key_info.get('display_name', provider.capitalize())
        # ... rest of logic
```

#### 2. Transcription Setup
**Before:** Hardcoded `["gemini", "whisperx", "zai"]`

**After:** Filter by capability
```python
def _setup_transcription(self):
    # Get providers that support transcription
    available_providers = self.provider_manager.get_providers_by_capability('transcription')
    
    # Build table dynamically
    table = Table(title="Available Transcription Providers", box=box.ROUNDED)
    choices = []
    
    for provider in sorted(available_providers):
        metadata = self.provider_manager.get_metadata(provider)
        table.add_row(
            metadata.get('display_name', provider),
            metadata.get('type', 'Unknown'),
            metadata.get('cost_indicator', '?'),
            metadata.get('speed_indicator', '?'),
            metadata.get('description', '')
        )
        choices.append(questionary.Choice(
            metadata.get('display_name', provider), 
            value=provider
        ))
    # ... continue
```

#### 3. Refinement Setup
**Before:** Hardcoded `["gemini", "zai"]`

**After:** Filter by capability
```python
def _setup_refinement(self):
    # Get providers that support refinement
    available_providers = self.provider_manager.get_providers_by_capability('refinement')
    # ... same dynamic pattern as transcription
```

#### 4. Dashboard Summary
Update API keys status to be dynamic:
```python
def _display_dashboard(self):
    # API Keys Status - dynamically check all providers
    keys_status = []
    all_providers = self.provider_manager.get_all_providers()
    
    for provider in sorted(all_providers):
        if self.provider_manager.requires_api_key(provider):
            key_info = self.provider_manager.get_api_key_info(provider)
            env_var = key_info['env_var']
            display_name = key_info.get('display_name', provider.capitalize())
            
            if self.env_manager.get(env_var):
                keys_status.append(f"{display_name}: [green]OK[/green]")
            else:
                keys_status.append(f"{display_name}: [red]Missing[/red]")
    # ...
```

---

## Implementation Steps

### Phase 1: Schema Design & Provider Updates

1. **Design enhanced defaults.yaml schema** ✓ (see above)

2. **Update each provider's defaults.yaml:**
   - [`gemini/defaults.yaml`](amanu/providers/gemini/defaults.yaml) - Add metadata section
   - [`whisperx/defaults.yaml`](amanu/providers/whisperx/defaults.yaml) - Add metadata section
   - [`zai/defaults.yaml`](amanu/providers/zai/defaults.yaml) - Add metadata section
   - [`claude/defaults.yaml`](amanu/providers/claude/defaults.yaml) - Add metadata section
   - [`openrouter/defaults.yaml`](amanu/providers/openrouter/defaults.yaml) - Add metadata section
   - [`whisper/defaults.yaml`](amanu/providers/whisper/defaults.yaml) - Add metadata section

### Phase 2: ProviderManager Refactoring

3. **Update [`ProviderManager._load_providers()`](amanu/wizard.py:103-118):**
   - Load metadata section along with models
   - Validate metadata structure
   - Provide sensible defaults for missing fields

4. **Add new ProviderManager methods:**
   - `get_all_providers()`
   - `get_providers_by_capability(capability)`
   - `get_metadata(provider_name)`
   - `requires_api_key(provider_name)`
   - `get_api_key_info(provider_name)`

5. **Remove hardcoded [`get_provider_info()`](amanu/wizard.py:123-132):**
   - Delete this method entirely
   - Replace all calls with `get_metadata()`

### Phase 3: Wizard Updates

6. **Update [`_setup_api_keys()`](amanu/wizard.py:267-283):**
   - Use `get_all_providers()` + `requires_api_key()`
   - Get env_var from metadata
   - Sort providers alphabetically

7. **Update [`_setup_transcription()`](amanu/wizard.py:285-345):**
   - Use `get_providers_by_capability('transcription')`
   - Build table from metadata
   - Remove hardcoded list

8. **Update [`_setup_refinement()`](amanu/wizard.py:347-386):**
   - Use `get_providers_by_capability('refinement')`
   - Build table from metadata
   - Remove hardcoded list

9. **Update [`_display_dashboard()`](amanu/wizard.py:226-265):**
   - Dynamic API keys status check
   - Sort providers for consistent display

### Phase 4: Testing & Documentation

10. **Test with all providers:**
    - Verify OpenRouter appears in wizard
    - Test transcription selection (Gemini, WhisperX, Zai, OpenRouter)
    - Test refinement selection (Gemini, Zai, Claude, OpenRouter)
    - Verify API key prompts work correctly
    - Test without any .env file (fresh install)

11. **Create documentation:**
    - `docs/adding_new_providers.md` - Guide for adding providers
    - Update `docs/configuration.md` - Document new schema
    - Add examples for different provider types

---

## Example: Adding a New Provider

After this refactoring, adding a provider requires only:

### 1. Create provider directory structure
```
amanu/providers/newprovider/
├── __init__.py
├── provider.py
└── defaults.yaml
```

### 2. Create defaults.yaml with metadata
```yaml
metadata:
  display_name: "NewProvider"
  description: "Amazing new AI service"
  type: "cloud"
  cost_indicator: "$"
  speed_indicator: "fast"
  capabilities:
    - refinement
  api_key:
    required: true
    env_var: "NEWPROVIDER_API_KEY"
    display_name: "NewProvider API Key"

models:
  - name: new-model-v1
    # ...
```

### 3. Done!
The wizard will automatically:
- Discover the provider
- Show it in appropriate sections
- Prompt for API key if needed
- Display correct metadata

---

## Benefits

### ✅ Extensibility
- Add providers without touching `wizard.py`
- Self-documenting configuration

### ✅ Maintainability
- Single source of truth (defaults.yaml)
- No hardcoded lists to update
- Consistent metadata structure

### ✅ OpenRouter Support
- Immediately available after adding metadata
- Works for both transcription and refinement

### ✅ Future-Proof
- Easy to add new capabilities (translation, etc.)
- Supports hybrid providers (local + cloud)
- Can add provider-specific settings

---

## Migration Notes

### Backward Compatibility
- Existing providers work with minimal metadata
- Falls back to defaults if metadata missing
- No breaking changes to config.yaml format

### Risk Mitigation
- Test each provider individually
- Validate YAML loading with error handling
- Provide clear error messages for malformed metadata

---

## Next Steps

**Ready to implement?** The plan is structured to allow incremental progress:

1. Start with schema design and one provider (e.g., OpenRouter)
2. Update ProviderManager with new methods
3. Refactor wizard one section at a time
4. Test thoroughly before moving to next section

**Questions for you:**
- Should we add more metadata fields (e.g., `homepage_url`, `support_url`)?
- Do you want to validate metadata on load or fail gracefully?
- Should providers be able to declare custom wizard steps?