from typing import Type, Dict, Any
from .providers import TranscriptionProvider
from .models import JobConfiguration

class ProviderFactory:
    _registry: Dict[str, Type[TranscriptionProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: Type[TranscriptionProvider]):
        cls._registry[name] = provider_cls

    @classmethod
    def get_provider_class(cls, name: str) -> Type[TranscriptionProvider]:
        if name not in cls._registry:
            # Lazy load standard plugins
            if name == "gemini":
                from ..providers.gemini.provider import GeminiProvider
                cls.register("gemini", GeminiProvider)
            elif name == "whisper":
                from ..providers.whisper.provider import WhisperProvider
                cls.register("whisper", WhisperProvider)
            elif name == "whisperx":
                from ..providers.whisperx.provider import WhisperXProvider
                cls.register("whisperx", WhisperXProvider)
            elif name == "claude":
                from ..providers.claude.provider import ClaudeProvider
                cls.register("claude", ClaudeProvider)
            elif name == "zai":
                from ..providers.zai.provider import ZaiProvider
                cls.register("zai", ZaiProvider)
            elif name == "openrouter":
                from ..providers.openrouter.provider import OpenRouterTranscriptionProvider
                cls.register("openrouter", OpenRouterTranscriptionProvider)
            else:
                raise ValueError(f"Unknown provider: {name}")
        
        return cls._registry[name]

    @classmethod
    def create(cls, name: str, config: JobConfiguration, provider_config: Any) -> TranscriptionProvider:
        provider_cls = cls.get_provider_class(name)
        return provider_cls(config, provider_config)

    @classmethod
    def get_refinement_provider_class(cls, name: str) -> Type[Any]:
        # Currently supported providers for refinement
        if name == "gemini":
            from ..providers.gemini.provider import GeminiRefinementProvider
            return GeminiRefinementProvider
        elif name == "zai":
            from ..providers.zai.provider import ZaiRefinementProvider
            return ZaiRefinementProvider
        elif name == "openrouter":
            from ..providers.openrouter.provider import OpenRouterRefinementProvider
            return OpenRouterRefinementProvider
        elif name == "claude":
             # TODO: Implement ClaudeRefinementProvider
             raise NotImplementedError("Claude refinement not yet implemented.")
        else:
            raise ValueError(f"Unknown refinement provider: {name}")

    @classmethod
    def create_refinement_provider(cls, name: str, config: JobConfiguration, provider_config: Any) -> Any:
        provider_cls = cls.get_refinement_provider_class(name)
        return provider_cls(config, provider_config)
