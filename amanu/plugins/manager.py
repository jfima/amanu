import logging
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Type, Optional

from .base import BasePlugin

logger = logging.getLogger("Amanu.PluginManager")

class PluginManager:
    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._discover_plugins()

    def _discover_plugins(self):
        """
        Automatically discover and register plugins from the amanu.plugins package.
        """
        # Import the plugins package to find its path
        import amanu.plugins as plugins_pkg
        
        package_path = Path(plugins_pkg.__file__).parent
        
        for _, name, _ in pkgutil.iter_modules([str(package_path)]):
            if name == "base" or name == "manager":
                continue
                
            try:
                module = importlib.import_module(f"amanu.plugins.{name}")
                
                # Find classes that inherit from BasePlugin
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                        plugin_instance = attr()
                        self.register_plugin(plugin_instance)
                        logger.debug(f"Registered plugin: {plugin_instance.name}")
                        
            except Exception as e:
                logger.error(f"Failed to load plugin module {name}: {e}")

    def register_plugin(self, plugin: BasePlugin):
        """Register a plugin instance."""
        if plugin.name in self._plugins:
            logger.warning(f"Overwriting existing plugin: {plugin.name}")
        self._plugins[plugin.name] = plugin

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> Dict[str, str]:
        """List available plugins and their descriptions."""
        return {name: p.description for name, p in self._plugins.items()}
