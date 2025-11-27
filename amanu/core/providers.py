from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path

@dataclass
class IngestSpecs:
    """Specifications for how the Ingest stage should prepare audio."""
    target_format: str  # e.g., "ogg", "wav", "mp3"
    requires_upload: bool # True if provider needs remote upload (e.g. Gemini)
    upload_target: str = "none" # "gemini_cache", "blob", "none"

class TranscriptionProvider(ABC):
    """Abstract base class for transcription providers."""

    def __init__(self, config: Any, provider_config: Any):
        self.config = config
        self.provider_config = provider_config

    @classmethod
    @abstractmethod
    def get_ingest_specs(cls) -> IngestSpecs:
        """Return the ingestion specifications for this provider."""
        pass

    @abstractmethod
    def transcribe(self, ingest_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Perform transcription.
        
        Args:
            ingest_result: The dictionary output from the Ingest stage.
                           Contains keys like 'gemini' (uri/cache) or 'local_file_path'.
            **kwargs: Additional arguments (e.g., prompt, language).
            
        Returns:
            Dict containing:
            - segments: List[Dict] (speaker_id, start_time, end_time, text, confidence)
            - tokens: Dict (input, output)
            - cost_usd: float
        """
        pass

class RefinementProvider(ABC):
    """Abstract base class for refinement providers."""

    def __init__(self, config: Any, provider_config: Any):
        self.config = config
        self.provider_config = provider_config

    @abstractmethod
    def refine(self, input_data: Any, mode: str, **kwargs) -> Dict[str, Any]:
        """
        Perform refinement/analysis.
        
        Args:
            input_data: The input data (transcript dict or ingest dict).
            mode: "standard" (text) or "direct" (audio).
            **kwargs: Additional arguments.
            
        Returns:
            Dict containing the enriched context (summary, etc.) and usage stats.
        """
        pass
