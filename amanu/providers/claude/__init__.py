"""Claude provider configuration and models."""
from typing import List, Optional
from pydantic import Field, SecretStr
from amanu.providers.base import ProviderConfig
from amanu.core.models import ModelSpec

class ClaudeConfig(ProviderConfig):
    """Configuration for Claude provider."""
    api_key: Optional[SecretStr] = Field(default=None, description="Claude API key")
    models: List[ModelSpec] = Field(default_factory=list)

# Alias for dynamic loading
Config = ClaudeConfig
