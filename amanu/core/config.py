import os
import yaml
import importlib
from pathlib import Path
from typing import Dict, Any, Type, Optional
from dotenv import load_dotenv

from .models import (
    ConfigContext, JobConfiguration, PathsConfig, CleanupConfig,
    StageConfig, ScribeConfig, OutputConfig, ShelveConfig,
    ZettelkastenConfig, ArtifactConfig
)
from amanu.providers.base import ProviderConfig

# Load environment variables from .env file
load_dotenv()

DEFAULT_CONFIG_FILENAME = "config.yaml"

def load_yaml(path: Path) -> Dict[str, Any]:
    if path.exists():
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}

def _merge_dicts(base: Dict, update: Dict):
    """Recursively merge update dict into base dict."""
    for k, v in update.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            _merge_dicts(base[k], v)
        else:
            base[k] = v

def load_provider_config(provider_name: str, user_provider_config: Dict[str, Any]) -> Any:
    """
    Dynamically load a provider's configuration.
    
    Args:
        provider_name: The name of the provider (e.g., 'gemini').
        user_provider_config: The provider configuration from the user's config.yaml.
        
    Returns:
        Validated Pydantic model for the provider configuration.
    """
    try:
        # Import the provider module
        module = importlib.import_module(f"amanu.providers.{provider_name}")
        
        # Expecting a 'Config' class in the module or __init__.py
        if hasattr(module, "Config"):
            config_model = getattr(module, "Config")
        else:
            # Fallback: try to find a class ending in Config
            config_model = None
            if hasattr(module, "__dict__"):
                for name, obj in module.__dict__.items():
                    if name.endswith("Config") and isinstance(obj, type) and issubclass(obj, ProviderConfig):
                        config_model = obj
                        break
            
            if not config_model:
                # If no specific config model, return dict (or generic model)
                return user_provider_config

        # Load default config from the provider's directory
        provider_dir = Path(module.__file__).parent
        default_config_path = provider_dir / "defaults.yaml"
        provider_config = load_yaml(default_config_path)
        
        # Merge user config into default config
        _merge_dicts(provider_config, user_provider_config)
        
        # Validate with Pydantic model
        return config_model(**provider_config)

    except ImportError:
        # Provider not found or not installed
        # print(f"Warning: Provider '{provider_name}' not found.")
        return user_provider_config
    except Exception as e:
        print(f"Error loading provider '{provider_name}': {e}")
        return user_provider_config

def load_config(config_path: str = None) -> ConfigContext:
    """Load configuration from file and env vars."""
    
    # 1. Determine config path
    if config_path:
        user_config_path = Path(config_path)
    else:
        # Search order: current dir -> user home
        cwd_config = Path(DEFAULT_CONFIG_FILENAME)
        home_config = Path.home() / ".config" / "amanu" / DEFAULT_CONFIG_FILENAME
        
        if cwd_config.exists():
            user_config_path = cwd_config
        elif home_config.exists():
            user_config_path = home_config
        else:
            # Fallback to package default if exists, or empty
            user_config_path = Path(__file__).parent.parent.parent / DEFAULT_CONFIG_FILENAME

    # 2. Load user config
    user_config = load_yaml(user_config_path)
    
    # 3. Parse Core Sections
    
    # Paths
    paths_conf = user_config.get("paths", {})
    paths = PathsConfig(**paths_conf)
    
    # Cleanup
    cleanup_conf = user_config.get("cleanup", {})
    cleanup = CleanupConfig(**cleanup_conf)
    
    # Processing / Job Defaults
    processing_conf = user_config.get("processing", {})
    
    # Extract stage configs
    transcribe_conf = user_config.get("transcribe", {})
    if not transcribe_conf:
        # Fallback for legacy
        transcribe_conf = {"provider": "gemini", "model": "gemini-2.0-flash"}
        
    refine_conf = user_config.get("refine", {})
    if not refine_conf:
        refine_conf = {"provider": "gemini", "model": "gemini-2.0-flash"}

    # Output config
    output_conf_dict = processing_conf.get("output", {})
    output_config = OutputConfig(**output_conf_dict)
    
    # Shelve config
    shelve_conf_dict = user_config.get("shelve", {})
    if not shelve_conf_dict:
         shelve_conf_dict = processing_conf.get("shelve", {})
    shelve_config = ShelveConfig(**shelve_conf_dict)

    # Scribe config
    scribe_conf_dict = processing_conf.get("scribe", {})
    scribe_config = ScribeConfig(**scribe_conf_dict)

    defaults = JobConfiguration(
        language=processing_conf.get("language", "auto"),
        compression_mode=processing_conf.get("compression_mode", "compressed"),
        shelve=shelve_config,
        output=output_config,
        debug=user_config.get("debug", False),
        scribe=scribe_config,
        transcribe=StageConfig(**transcribe_conf),
        refine=StageConfig(**refine_conf)
    )

    # 4. Dynamic Provider Loading
    providers_config = {}
    user_providers_section = user_config.get("providers", {})
    
    # Identify active providers from stages + explicit providers section
    active_providers = set(user_providers_section.keys())
    if defaults.transcribe.provider:
        active_providers.add(defaults.transcribe.provider)
    if defaults.refine.provider:
        active_providers.add(defaults.refine.provider)
    
    for provider_name in active_providers:
        if not provider_name: continue
        
        provider_conf_dict = user_providers_section.get(provider_name, {})
        loaded_conf = load_provider_config(provider_name, provider_conf_dict)
        providers_config[provider_name] = loaded_conf
        
    # 5. Return Context
    return ConfigContext(
        defaults=defaults,
        providers=providers_config,
        paths=paths,
        cleanup=cleanup
    )
