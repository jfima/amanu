from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class ProviderConfig(BaseModel):
    """Base configuration for all providers."""
    pass

class Provider(ABC):
    """
    Abstract base class for all providers.
    
    Attributes:
        name (str): The unique name of the provider (e.g., 'gemini', 'whisperx').
        config (ProviderConfig): The configuration object for this provider.
    """
    
    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of the provider."""
        pass
    
    @classmethod
    @abstractmethod
    def get_config_model(cls) -> type[ProviderConfig]:
        """Return the Pydantic model class used for this provider's configuration."""
        pass
