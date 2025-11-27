import yaml
import os
from pathlib import Path
from typing import Dict, Any

from .models import (
    JobConfiguration, ModelPricing, PricingModel, ModelSpec, ModelContextWindow, ConfigContext,
    StageConfig, GeminiConfig, WhisperConfig, ClaudeConfig, WhisperModelSpec,
    ScribeConfig, OutputConfig, ArtifactConfig, ShelveConfig, ZettelkastenConfig,
    PathsConfig, CleanupConfig
)

DEFAULT_CONFIG = {
    "transcribe": {
        "provider": "gemini",
        "model": "gemini-2.0-flash"
    },
    "refine": {
        "provider": "gemini",
        "model": "gemini-2.0-flash"
    },
    "providers": {
        "gemini": {
            "api_key": "",
            "models": [
                {
                    "name": "gemini-2.0-flash",
                    "context_window": {"input_tokens": 1048576, "output_tokens": 8192},
                    "cost_per_1M_tokens_usd": {"input": 0.10, "output": 0.40}
                }
            ]
        },
        "whisper": {
            "models": []
        },
        "claude": {
            "api_key": "",
            "models": []
        }
    },
    "processing": {
        "language": "auto",
        "compression_mode": "compressed",
        "debug": False,
        "output": {
            "artifacts": []
        }
    },
    "paths": {
        "input": "./scribe-in",
        "work": "./scribe-work",
        "results": "./scribe-out"
    },
    "cleanup": {
        "failed_jobs_retention_days": 7,
        "completed_jobs_retention_days": 1,
        "auto_cleanup_enabled": True
    }
}

def load_config(config_path: str = None) -> ConfigContext:
    """Load configuration from file and env vars."""
    config = DEFAULT_CONFIG.copy()
    
    # 1. Load from file
    paths_to_check = [
        Path("config.yaml"),
        Path.home() / ".config" / "amanu" / "config.yaml"
    ]
    if config_path:
        paths_to_check.insert(0, Path(config_path))
        
    for path in paths_to_check:
        if path.exists():
            with open(path, "r") as f:
                user_config = yaml.safe_load(f)
                _merge_dicts(config, user_config)
            break
            
    # 2. Env vars override
    if os.environ.get("GEMINI_API_KEY"):
        # Ensure providers.gemini exists
        if "providers" not in config:
            config["providers"] = {}
        if "gemini" not in config["providers"]:
            config["providers"]["gemini"] = {}
        config["providers"]["gemini"]["api_key"] = os.environ["GEMINI_API_KEY"]
    elif config.get("providers", {}).get("gemini", {}).get("api_key"):
        # Export to env so other modules can use it
        os.environ["GEMINI_API_KEY"] = config["providers"]["gemini"]["api_key"]
        
    # 4. Parse Providers
    providers = {}
    
    # Gemini - try new format first, then fall back to legacy
    gemini_conf = config.get("providers", {}).get("gemini", {})
    gemini_models_list = []
    
    # New format: providers.gemini.models
    if gemini_conf.get("models"):
        for m in gemini_conf["models"]:
            gemini_models_list.append(ModelSpec(
                name=m["name"],
                context_window=ModelContextWindow(**m["context_window"]),
                cost_per_1M_tokens_usd=PricingModel(
                    input=m["cost_per_1M_tokens_usd"]["input"],
                    output=m["cost_per_1M_tokens_usd"]["output"]
                )
            ))
    # Legacy format: top-level gemini_models
    elif "gemini_models" in config:
        for m in config["gemini_models"]:
            gemini_models_list.append(ModelSpec(
                name=m["name"],
                context_window=ModelContextWindow(**m["context_window"]),
                cost_per_1M_tokens_usd=PricingModel(
                    input=m["cost_per_1M_tokens_usd"]["input"],
                    output=m["cost_per_1M_tokens_usd"]["output"]
                )
            ))
    
    # Get API key from providers.gemini.api_key or legacy gemini.api_key
    gemini_api_key = gemini_conf.get("api_key") or config.get("gemini", {}).get("api_key")
    
    providers["gemini"] = GeminiConfig(
        api_key=gemini_api_key,
        models=gemini_models_list
    )

    # Whisper
    whisper_conf = config.get("providers", {}).get("whisper", {})
    whisper_models_raw = whisper_conf.get("models", [])
    whisper_models_list = []
    
    if isinstance(whisper_models_raw, dict):
        # Legacy format: name -> path
        for name, path in whisper_models_raw.items():
            whisper_models_list.append(WhisperModelSpec(
                name=name,
                path=path,
                context_window=ModelContextWindow(input_tokens=0, output_tokens=0),
                cost_per_1M_tokens_usd=PricingModel(input=0.0, output=0.0)
            ))
    elif isinstance(whisper_models_raw, list):
        # New format
        for m in whisper_models_raw:
             whisper_models_list.append(WhisperModelSpec(
                name=m["name"],
                path=m["path"],
                context_window=ModelContextWindow(**m["context_window"]),
                cost_per_1M_tokens_usd=PricingModel(**m["cost_per_1M_tokens_usd"])
            ))
            
    providers["whisper"] = WhisperConfig(
        whisper_home=whisper_conf.get("whisper_home"),
        models=whisper_models_list
    )

    # Claude
    claude_conf = config.get("providers", {}).get("claude", {})
    claude_models_list = []
    
    if claude_conf.get("models"):
        for m in claude_conf["models"]:
            claude_models_list.append(ModelSpec(
                name=m["name"],
                context_window=ModelContextWindow(**m["context_window"]),
                cost_per_1M_tokens_usd=PricingModel(**m["cost_per_1M_tokens_usd"])
            ))
    
    providers["claude"] = ClaudeConfig(
        api_key=claude_conf.get("api_key"),
        models=claude_models_list
    )

    # 5. Parse Stages (Transcribe / Refine)
    # Backward compatibility: if top-level transcribe/refine missing, use gemini legacy
    
    transcribe_conf = config.get("transcribe", {})
    if not transcribe_conf.get("provider"):
        # Fallback to legacy gemini config
        transcribe_conf = {
            "provider": "gemini",
            "model": config["gemini"].get("transcribe_model", "gemini-2.0-flash")
        }
        
    refine_conf = config.get("refine", {})
    if not refine_conf.get("provider"):
         # Fallback to legacy gemini config
        refine_conf = {
            "provider": "gemini",
            "model": config["gemini"].get("refine_model", "gemini-2.0-flash")
        }

    transcribe_stage = StageConfig(**transcribe_conf)
    refine_stage = StageConfig(**refine_conf)

    # Load scribe config
    scribe_config_dict = config["processing"].get("scribe", {})
    scribe_config = ScribeConfig(
        retry_max=scribe_config_dict.get("retry_max", 3),
        retry_delay_seconds=scribe_config_dict.get("retry_delay_seconds", 5)
    )

    # Load output config
    output_config_dict = config["processing"].get("output", {})
    artifacts = []
    for artifact_dict in output_config_dict.get("artifacts", []):
        artifacts.append(ArtifactConfig(**artifact_dict))
    output_config = OutputConfig(artifacts=artifacts)

    # Load shelve config
    shelve_config_dict = config.get("shelve", {}) # Top level or inside processing? Spec says 'shelve' at root level in yaml example section 4.1
    # But usually config is structured. Spec section 4.1 shows:
    # shelve:
    #   enabled: true
    # ...
    # Let's check DEFAULT_CONFIG if I added it? No I didn't add it to DEFAULT_CONFIG yet.
    
    # If users put it in 'shelve' top-level, we should read from config['shelve'].
    # If they put it in 'processing', we should read from there.
    # Let's support root level 'shelve' as per spec 4.1.
    
    shelve_dict = config.get("shelve", {})
    zettelkasten_dict = shelve_dict.get("zettelkasten", {})
    zettelkasten_config = ZettelkastenConfig(**zettelkasten_dict)
    
    shelve_config = ShelveConfig(
        enabled=shelve_dict.get("enabled", True),
        root_path=shelve_dict.get("root_path"),
        strategy=shelve_dict.get("strategy", "timeline"),
        zettelkasten=zettelkasten_config
    )
    
    defaults = JobConfiguration(
        # template=config["processing"]["template"], # Deprecated
        language=config["processing"]["language"],
        compression_mode=config["processing"].get("compression_mode", "compressed"),
        shelve=shelve_config,
        output=output_config,
        debug=config["processing"].get("debug", False),
        scribe=scribe_config,
        transcribe=transcribe_stage,
        refine=refine_stage
    )

    # Load paths config
    paths_config = PathsConfig(**config.get("paths", {}))
    cleanup_config = CleanupConfig(**config.get("cleanup", {}))

    return ConfigContext(
        defaults=defaults,
        available_models=gemini_models_list, # Legacy support
        providers=providers,
        paths=paths_config,
        cleanup=cleanup_config
    )

def _merge_dicts(base: Dict, update: Dict):
    for k, v in update.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            _merge_dicts(base[k], v)
        else:
            base[k] = v
