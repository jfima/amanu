import yaml
import os
from pathlib import Path
from typing import Dict, Any

from .models import JobConfiguration, ModelPricing, PricingModel, ModelSpec, ModelContextWindow, ConfigContext

DEFAULT_CONFIG = {
    "gemini": {
        "api_key": "",
        "transcribe_model": "gemini-2.0-flash",
        "refine_model": "gemini-2.0-flash",
    },
    "processing": {
        "context_window": 65000,
        "language": "auto"
    },
    "shelve": {
        "enabled": True,
        "strategy": "timeline",
        "zettelkasten": {
            "id_format": "%Y%m%d%H%M",
            "filename_pattern": "{id} {slug}.md"
        }
    },
    "pricing": {
        "transcribe_model": {"input": 0.075, "output": 0.30},
        "refine_model": {"input": 0.075, "output": 0.30}
    },
    "gemini_models": [
        {
            "name": "gemini-3-pro-preview",
            "context_window": {"input_tokens": 1048576, "output_tokens": 65536},
            "cost_per_1M_tokens_usd": {"input": 2.0, "output": 12.0}
        },
        {
            "name": "gemini-2.5-pro",
            "context_window": {"input_tokens": 1048576, "output_tokens": 65536},
            "cost_per_1M_tokens_usd": {"input": 1.25, "output": 10.0}
        },
        {
            "name": "gemini-2.5-flash",
            "context_window": {"input_tokens": 1048576, "output_tokens": 65536},
            "cost_per_1M_tokens_usd": {"input": 0.30, "output": 2.50}
        },
        {
            "name": "gemini-2.5-flash-lite",
            "context_window": {"input_tokens": 1048576, "output_tokens": 65536},
            "cost_per_1M_tokens_usd": {"input": 0.10, "output": 0.40}
        },
        {
            "name": "gemini-2.0-flash",
            "context_window": {"input_tokens": 1048576, "output_tokens": 8192},
            "cost_per_1M_tokens_usd": {"input": 0.10, "output": 0.40}
        }
    ]
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
        config["gemini"]["api_key"] = os.environ["GEMINI_API_KEY"]
    elif config["gemini"]["api_key"]:
        # Export to env so other modules can use it
        os.environ["GEMINI_API_KEY"] = config["gemini"]["api_key"]
        
    # 3. Create ConfigContext
    # Parse model specs
    model_specs = []
    if "gemini_models" in config:
        for m in config["gemini_models"]:
            model_specs.append(ModelSpec(
                name=m["name"],
                context_window=ModelContextWindow(**m["context_window"]),
                cost_per_1M_tokens_usd=PricingModel(
                    input=m["cost_per_1M_tokens_usd"]["input"],
                    output=m["cost_per_1M_tokens_usd"]["output"]
                )
            ))

    # Helper to find model by name
    def get_model(name: str) -> ModelSpec:
        for m in model_specs:
            if m.name == name:
                return m
        # Fallback if not found in list but specified (should ideally fail or warn)
        # For now creating a dummy spec with defaults if not found, or raise error
        # Let's raise error to be safe, or use the first one as fallback?
        # Better to raise error if config is inconsistent.
        # But for bootstrap, let's look for exact match.
        raise ValueError(f"Model {name} not found in gemini_models configuration.")

    try:
        transcribe_spec = get_model(config["gemini"]["transcribe_model"])
        refine_spec = get_model(config["gemini"]["refine_model"])
    except ValueError as e:
        # If default models are not in the list, this is a config error.
        # Fallback to first available or hardcoded for safety?
        if model_specs:
             transcribe_spec = model_specs[0]
             refine_spec = model_specs[0]
        else:
             raise ValueError("No models defined in gemini_models.")

    # Load scribe config
    from .models import ScribeConfig, OutputConfig, ArtifactConfig, ShelveConfig, ZettelkastenConfig
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
        transcribe=transcribe_spec,
        refine=refine_spec
    )

    # Load paths config
    from .models import PathsConfig, CleanupConfig
    paths_config = PathsConfig(**config.get("paths", {}))
    cleanup_config = CleanupConfig(**config.get("cleanup", {}))

    return ConfigContext(
        defaults=defaults,
        available_models=model_specs,
        paths=paths_config,
        cleanup=cleanup_config
    )

def _merge_dicts(base: Dict, update: Dict):
    for k, v in update.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            _merge_dicts(base[k], v)
        else:
            base[k] = v
