import logging
from typing import Dict, Any

from ..core.providers import TranscriptionProvider, IngestSpecs
from ..core.models import JobConfiguration, ClaudeConfig

logger = logging.getLogger("Amanu.Plugin.Claude")

class ClaudeProvider(TranscriptionProvider):
    def __init__(self, config: JobConfiguration, provider_config: ClaudeConfig):
        super().__init__(config, provider_config)
        self.claude_config = provider_config
        # Initialize Anthropic client here if needed

    @classmethod
    def get_ingest_specs(cls) -> IngestSpecs:
        return IngestSpecs(
            target_format="mp3",
            requires_upload=False, # Claude takes binary in request
            upload_target="none"
        )

    def transcribe(self, ingest_result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        logger.warning("Claude provider is not yet fully implemented.")
        raise NotImplementedError("Claude transcription is not yet implemented.")
