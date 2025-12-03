# Adding New Providers to Amanu

This guide explains how to add a new AI provider to Amanu. Thanks to the dynamic provider discovery system, adding a provider requires **no changes to `wizard.py`** - just create the provider files with proper metadata.

## Quick Start

To add a new provider named "NewProvider":

1. Create provider directory structure
2. Implement the provider class
3. Add metadata to `defaults.yaml`
4. Test with `amanu setup`

That's it! The wizard automatically discovers and integrates your provider.

## Step-by-Step Guide

### Step 1: Create Directory Structure

```bash
cd amanu/providers/
mkdir newprovider
cd newprovider
touch __init__.py provider.py defaults.yaml
```

Your structure should look like:
```
amanu/providers/newprovider/
├── __init__.py
├── provider.py
└── defaults.yaml
```

### Step 2: Implement Provider Class

**File: `provider.py`**

```python
from typing import Dict, Any, Optional
from ..base import BaseProvider

class NewProviderProvider(BaseProvider):
    """Provider for NewProvider AI service."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('NEWPROVIDER_API_KEY')
        # Initialize your provider-specific client
        
    def transcribe(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """Transcribe audio to text."""
        # Implement transcription
        pass
        
    def refine(self, text: str, **kwargs) -> str:
        """Refine/clean up text."""
        # Implement refinement
        pass
```

**File: `__init__.py`**

```python
from .provider import NewProviderProvider

__all__ = ['NewProviderProvider']
```

### Step 3: Add Metadata to defaults.yaml

**File: `defaults.yaml`**

```yaml
# NewProvider Configuration
# Description of what this provider does

metadata:
  # Display information
  display_name: "NewProvider"
  description: "Brief description of NewProvider's capabilities"
  
  # Provider characteristics
  type: "cloud"              # Options: cloud | local | hybrid
  cost_indicator: "$$"       # Options: Free | $ | $$ | $$$
  speed_indicator: "fast"    # Options: fast | medium | slow
  
  # Capabilities (what this provider can do)
  capabilities:
    - transcription          # Include if provider can transcribe
    - refinement            # Include if provider can refine text
  
  # API configuration
  api_key:
    required: true           # Set to false if no API key needed
    env_var: "NEWPROVIDER_API_KEY"
    display_name: "NewProvider API Key"
  
  # Documentation links (optional but recommended)
  docs_url: "https://newprovider.com/docs"
  pricing_url: "https://newprovider.com/pricing"

# Models available from this provider
models:
  - name: newprovider-model-v1
    type: general
    context_window:
      input_tokens: 128000
      output_tokens: 4096
    cost_per_1M_tokens_usd:
      input: 1.0
      output: 2.0
  
  - name: newprovider-fast
    type: fast
    context_window:
      input_tokens: 64000
      output_tokens: 4096
    cost_per_1M_tokens_usd:
      input: 0.5
      output: 1.0
```

### Step 4: Test Your Provider

1. **Run setup wizard:**
   ```bash
   amanu setup
   ```

2. **Verify your provider appears:**
   - In API Keys section (if `api_key.required: true`)
   - In Transcription section (if `capabilities: transcription`)
   - In Refinement section (if `capabilities: refinement`)

3. **Test functionality:**
   ```bash
   # Create test config using your provider
   amanu transcribe input.wav --provider newprovider
   ```

## Metadata Field Reference

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `display_name` | string | Human-readable name | "NewProvider" |
| `description` | string | Brief description | "Fast AI transcription service" |
| `type` | string | Provider type | "cloud", "local", "hybrid" |
| `capabilities` | list | What provider can do | ["transcription", "refinement"] |

### Optional Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `cost_indicator` | string | Relative cost | "?" |
| `speed_indicator` | string | Relative speed | "?" |
| `api_key.required` | boolean | Needs API key? | false |
| `api_key.env_var` | string | Environment variable name | "{PROVIDER}_API_KEY" |
| `api_key.display_name` | string | UI display name | "{Provider} API Key" |
| `docs_url` | string | Documentation URL | "" |
| `pricing_url` | string | Pricing info URL | "" |

### Capabilities

Declare which capabilities your provider supports:

| Capability | When to Use | Example Providers |
|------------|-------------|-------------------|
| `transcription` | Provider can convert audio to text | Gemini, WhisperX, OpenRouter |
| `refinement` | Provider can clean/improve text | Gemini, Claude, OpenRouter |
| `translation` | Provider can translate text | *(future)* |
| `summarization` | Provider can summarize text | *(future)* |

## Examples

### Example 1: Cloud Transcription Provider

```yaml
metadata:
  display_name: "DeepSpeech Cloud"
  description: "Cloud-based speech recognition with high accuracy"
  type: "cloud"
  cost_indicator: "$$"
  speed_indicator: "fast"
  capabilities:
    - transcription
  api_key:
    required: true
    env_var: "DEEPSPEECH_API_KEY"
    display_name: "DeepSpeech API Key"
  docs_url: "https://deepspeech.example.com/docs"

models:
  - name: deepspeech-v1
    context_window: {input_tokens: 0, output_tokens: 0}
    cost_per_1M_tokens_usd: {input: 0.006, output: 0.0}
```

### Example 2: Local Refinement Provider

```yaml
metadata:
  display_name: "LocalLLM"
  description: "Run LLM locally for text refinement"
  type: "local"
  cost_indicator: "Free"
  speed_indicator: "medium"
  capabilities:
    - refinement
  api_key:
    required: false
  docs_url: "https://github.com/example/localllm"

models:
  - name: llama-3-8b
    context_window: {input_tokens: 8192, output_tokens: 2048}
    cost_per_1M_tokens_usd: {input: 0.0, output: 0.0}
```

### Example 3: Multi-Capability Provider

```yaml
metadata:
  display_name: "UnifiedAI"
  description: "All-in-one AI service for transcription and refinement"
  type: "cloud"
  cost_indicator: "$"
  speed_indicator: "fast"
  capabilities:
    - transcription
    - refinement
  api_key:
    required: true
    env_var: "UNIFIEDAI_API_KEY"
    display_name: "UnifiedAI API Key"

models:
  - name: unified-v1
    type: multimodal
    context_window: {input_tokens: 128000, output_tokens: 4096}
    cost_per_1M_tokens_usd: {input: 0.5, output: 1.0}
```

## Provider Implementation Tips

### 1. Transcription Providers

Must implement:
```python
def transcribe(self, audio_path: str, **kwargs) -> Dict[str, Any]:
    """
    Returns:
        {
            "text": "transcribed text",
            "segments": [...],  # Optional: timestamped segments
            "language": "en",   # Optional: detected language
        }
    """
```

### 2. Refinement Providers

Must implement:
```python
def refine(self, text: str, **kwargs) -> str:
    """
    Returns:
        Cleaned/refined text string
    """
```

### 3. Error Handling

```python
from ..base import ProviderError

def transcribe(self, audio_path: str, **kwargs) -> Dict[str, Any]:
    try:
        # Your implementation
        pass
    except Exception as e:
        raise ProviderError(f"Transcription failed: {e}")
```

### 4. Configuration

Access config in your provider:
```python
def __init__(self, config: Dict[str, Any]):
    super().__init__(config)
    self.model = config.get('model', 'default-model')
    self.api_key = config.get('api_key') or os.getenv('YOUR_API_KEY')
```

## Testing Checklist

Before submitting your provider:

- [ ] Provider appears in `amanu setup` wizard
- [ ] Metadata displays correctly in tables
- [ ] API key prompt works (if required)
- [ ] Model selection works
- [ ] Transcription works (if applicable)
- [ ] Refinement works (if applicable)
- [ ] Error messages are clear
- [ ] Documentation is complete
- [ ] Example usage is provided

## Common Patterns

### API Key from Environment

```python
import os

class YourProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('YOUR_API_KEY')
        if not self.api_key:
            raise ProviderError("API key required")
```

### Model Selection

```python
def __init__(self, config: Dict[str, Any]):
    super().__init__(config)
    self.model = config.get('model', 'default-model-v1')
```

### Rate Limiting

```python
import time
from functools import wraps

def rate_limited(max_per_second):
    min_interval = 1.0 / float(max_per_second)
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator
```

## Troubleshooting

### Provider Not Appearing in Wizard

1. Check `defaults.yaml` is in correct location
2. Verify YAML syntax is valid: `python -m yaml amanu/providers/yourprovider/defaults.yaml`
3. Ensure `metadata` section exists
4. Check provider directory name matches

### API Key Not Prompted

1. Verify `api_key.required: true` in metadata
2. Check `env_var` matches your actual environment variable
3. Ensure wizard is reading updated defaults.yaml

### Models Not Showing

1. Verify `models` section exists in defaults.yaml
2. Check model structure matches schema
3. Ensure at least one model is defined

## See Also

- [Configuration Guide](configuration.md)
- [Dynamic Provider Discovery Plan](dynamic_provider_discovery_plan.md)
- [OpenRouter Implementation](openrouter_implementation.md)
- [Provider Base Class](../amanu/providers/base.py)

## Contributing

When contributing a new provider:

1. Follow this guide
2. Add tests in `tests/`
3. Update documentation
4. Submit pull request with:
   - Provider implementation
   - defaults.yaml with metadata
   - Usage examples
   - Test results

---

**Need Help?** Open an issue on GitHub with the "provider" tag.