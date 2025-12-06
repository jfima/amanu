"""WhisperX provider configuration and models."""
import os
from typing import List, Optional
from pydantic import Field, SecretStr, model_validator
from amanu.providers.base import ProviderConfig
from amanu.core.models import ModelSpec

class WhisperXModelSpec(ModelSpec):
    """WhisperX model specification."""
    pass

class WhisperXConfig(ProviderConfig):
    """Configuration for WhisperX provider."""
    python_executable: str = Field(default="python3", description="Python executable to use")
    device: str = Field(default="cuda", description="Device to use (cuda or cpu)")
    compute_type: str = Field(default="float16", description="Compute type (float16, int8, etc.)")
    batch_size: int = Field(default=16, description="Batch size for processing")
    language: Optional[str] = Field(default=None, description="Language for transcription")
    enable_diarization: bool = Field(default=False, description="Enable speaker diarization")
    hf_token: Optional[SecretStr] = Field(default=None, description="HuggingFace token for gated models")
    models: List[WhisperXModelSpec] = Field(default_factory=list)

    @model_validator(mode='after')
    def load_hf_token_from_env(self):
        """Load HF_TOKEN from environment if not provided."""
        if self.hf_token is None:
            # Ensure .env is loaded
            from dotenv import load_dotenv
            load_dotenv()
            env_token = os.environ.get("HF_TOKEN")
            if env_token:
                self.hf_token = SecretStr(env_token)
        return self

# Alias for dynamic loading
Config = WhisperXConfig

