"""Z.AI provider configuration and models."""
from typing import List, Optional
from pydantic import Field, SecretStr
from amanu.providers.base import ProviderConfig
from amanu.core.models import ModelSpec

class ZaiConfig(ProviderConfig):
    """Configuration for Z.AI provider."""
    api_key: Optional[SecretStr] = Field(default=None, description="Z.AI API key")
    base_url: Optional[str] = Field(default=None, description="Base URL for Z.AI API")
    models: List[ModelSpec] = Field(default_factory=list)

# Alias for dynamic loading
Config = ZaiConfig
