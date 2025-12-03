"""OpenRouter provider configuration and models."""
from typing import List, Optional
from pydantic import Field, SecretStr
from amanu.providers.base import ProviderConfig
from amanu.core.models import ModelSpec

class OpenRouterConfig(ProviderConfig):
    """Configuration for OpenRouter provider."""
    api_key: Optional[SecretStr] = Field(default=None, description="OpenRouter API key")
    site_url: Optional[str] = Field(default=None, description="Your site URL for OpenRouter")
    app_name: Optional[str] = Field(default="amanu", description="Your app name for OpenRouter")
    models: List[ModelSpec] = Field(default_factory=list)

# Alias for dynamic loading
Config = OpenRouterConfig
