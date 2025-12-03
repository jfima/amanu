"""Whisper (whisper.cpp) provider configuration and models."""
from typing import List, Optional
from pydantic import Field
from amanu.providers.base import ProviderConfig
from amanu.core.models import ModelSpec

class WhisperModelSpec(ModelSpec):
    """Whisper model specification with path."""
    path: str = Field(description="Path to the model file")

class WhisperConfig(ProviderConfig):
    """Configuration for Whisper provider."""
    whisper_home: Optional[str] = Field(default=None, description="Path to whisper.cpp directory")
    models: List[WhisperModelSpec] = Field(default_factory=list)

# Alias for dynamic loading
Config = WhisperConfig
