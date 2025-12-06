from typing import Optional, List
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from ..base import ProviderConfig

class OllamaConfig(ProviderConfig, BaseSettings):
    """Configuration for Ollama provider."""
    
    # Retry configuration
    retry_max: int = Field(default=3, description="Max retry attempts for generation")
    retry_delay_seconds: int = Field(default=2, description="Delay between retries in seconds")

    # Ollama server configuration
    base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL"
    )
    
    timeout: int = Field(
        default=600,
        description="Request timeout in seconds"
    )
    
    auto_pull_models: bool = Field(
        default=True,
        description="Automatically pull models if not available"
    )
    
    # Model configuration
    transcription_model: Optional[str] = Field(
        default="whisper-large-v3-turbo",
        description="Default model for transcription"
    )
    
    refinement_model: Optional[str] = Field(
        default="gpt-oss:20b",
        description="Default model for refinement"
    )
    
    # API configuration (not required for local Ollama)
    api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key (not required for local Ollama)"
    )
    
    # Advanced settings
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests"
    )
    
    retry_delay: int = Field(
        default=5,
        description="Delay between retries in seconds"
    )
    
    # GPU settings
    use_gpu: bool = Field(
        default=True,
        description="Use GPU acceleration if available"
    )
    
    gpu_memory_limit: Optional[int] = Field(
        default=None,
        description="GPU memory limit in MB (None for unlimited)"
    )
    
    # Model quantization preferences
    preferred_quantization: str = Field(
        default="q4_0",
        description="Preferred model quantization (q4_0, q5_1, q8_0, etc.)"
    )
    
    class Config:
        env_prefix = "OLLAMA_"
        case_sensitive = False
        extra = "ignore"

# Model specifications for dynamic loading
class ModelSpec:
    """Model specification for Ollama models."""
    
    def __init__(self, name: str, model_type: str, **kwargs):
        self.name = name
        self.type = model_type
        self.context_window = kwargs.get('context_window', {'input_tokens': 0, 'output_tokens': 0})
        self.cost_per_1M_tokens_usd = kwargs.get('cost_per_1M_tokens_usd', {'input': 0.0, 'output': 0.0})
        self.description = kwargs.get('description', '')
        self.display_name = kwargs.get('display_name', name)

# Alias for Config loader
Config = OllamaConfig

__all__ = ['OllamaConfig', 'ModelSpec', 'Config']
