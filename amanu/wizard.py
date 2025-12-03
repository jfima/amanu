import os
import sys
import yaml
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
import questionary

# Initialize Rich Console
console = Console()

# --- Constants ---
PROJECT_ROOT = Path(__file__).parent.parent
PROVIDERS_DIR = PROJECT_ROOT / "amanu" / "providers"
TEMPLATES_DIR = PROJECT_ROOT / "amanu" / "templates"

# Determine Config Locations
# 1. Project-local (dev mode)
LOCAL_CONFIG = Path("config.yaml")
LOCAL_ENV = Path(".env")

# 2. User-global (installed mode)
USER_CONFIG_DIR = Path.home() / ".config" / "amanu"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.yaml"
# .env usually stays with the project or in a secure location, 
# but for CLI tools, it's often simpler to keep keys in env vars or a secure file.
# For now, we'll support a local .env or one in the config dir.
USER_ENV_FILE = USER_CONFIG_DIR / ".env"

ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"

# --- Helper Classes ---

class EnvManager:
    """Manages reading and writing to the .env file."""
    
    def __init__(self, env_path: Path):
        self.env_path = env_path
        self.values: Dict[str, str] = {}
        self._load()

    def _load(self):
        if not self.env_path.exists():
            return
        
        with open(self.env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    self.values[key.strip()] = val.strip().strip("'").strip('"')

    def get(self, key: str) -> Optional[str]:
        return self.values.get(key)

    def set(self, key: str, value: str):
        self.values[key] = value
        self._save_key(key, value)

    def _save_key(self, key: str, value: str):
        """Updates or appends a key to the .env file, preserving comments/structure where possible."""
        if not self.env_path.parent.exists():
            self.env_path.parent.mkdir(parents=True, exist_ok=True)
            
        if not self.env_path.exists():
            # Create from example if possible
            if ENV_EXAMPLE_FILE.exists():
                shutil.copy(ENV_EXAMPLE_FILE, self.env_path)
            else:
                self.env_path.touch()

        lines = self.env_path.read_text().splitlines()
        new_lines = []
        found = False
        
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            if new_lines and new_lines[-1] != "":
                new_lines.append("")
            new_lines.append(f"{key}={value}")
            
        self.env_path.write_text("\n".join(new_lines) + "\n")

class ProviderManager:
    """Manages provider metadata and configurations."""
    
    def __init__(self):
        self.providers = self._load_providers()

    def _load_providers(self) -> Dict[str, Any]:
        providers = {}
        if not PROVIDERS_DIR.exists():
            return providers

        for item in PROVIDERS_DIR.iterdir():
            if item.is_dir():
                defaults_path = item / "defaults.yaml"
                if defaults_path.exists():
                    try:
                        with open(defaults_path, "r") as f:
                            data = yaml.safe_load(f)
                            providers[item.name] = data
                    except Exception as e:
                        console.print(f"[red]Error loading defaults for {item.name}: {e}[/red]")
        return providers

    def get_all_providers(self) -> List[str]:
        """Return list of all available provider names."""
        return list(self.providers.keys())
    
    def get_providers_by_capability(self, capability: str) -> List[str]:
        """Filter providers that support a specific capability."""
        return [
            name for name, data in self.providers.items()
            if capability in data.get('metadata', {}).get('capabilities', [])
        ]
    
    def get_metadata(self, provider_name: str) -> Dict[str, Any]:
        """Get provider metadata from defaults.yaml."""
        provider_data = self.providers.get(provider_name, {})
        metadata = provider_data.get('metadata', {})
        
        # Provide defaults for missing metadata fields
        return {
            'display_name': metadata.get('display_name', provider_name.capitalize()),
            'description': metadata.get('description', 'No description available'),
            'type': metadata.get('type', 'unknown'),
            'cost_indicator': metadata.get('cost_indicator', '?'),
            'speed_indicator': metadata.get('speed_indicator', '?'),
            'capabilities': metadata.get('capabilities', []),
            'api_key': metadata.get('api_key', {}),
            'docs_url': metadata.get('docs_url', ''),
            'pricing_url': metadata.get('pricing_url', '')
        }
    
    def requires_api_key(self, provider_name: str) -> bool:
        """Check if provider requires API key."""
        metadata = self.get_metadata(provider_name)
        return metadata.get('api_key', {}).get('required', False)
    
    def get_api_key_info(self, provider_name: str) -> Dict[str, str]:
        """Get API key configuration for provider."""
        metadata = self.get_metadata(provider_name)
        api_key_info = metadata.get('api_key', {})
        
        # Provide defaults
        return {
            'env_var': api_key_info.get('env_var', f"{provider_name.upper()}_API_KEY"),
            'display_name': api_key_info.get('display_name', f"{metadata['display_name']} API Key"),
            'required': api_key_info.get('required', False)
        }

    def get_models(self, provider_name: str) -> List[Dict[str, Any]]:
        return self.providers.get(provider_name, {}).get("models", [])

class SetupWizard:
    def __init__(self):
        self.config_path, self.env_path = self._determine_paths()
        self.env_manager = EnvManager(self.env_path)
        self.provider_manager = ProviderManager()
        self.config = self._load_config()
        
    def _determine_paths(self) -> Tuple[Path, Path]:
        """Determine which config/env files to use."""
        # 1. If local config exists, use it (Project mode)
        if LOCAL_CONFIG.exists():
            return LOCAL_CONFIG, LOCAL_ENV
        
        # 2. If we are in the project root (check for amanu package), use local
        if (Path.cwd() / "amanu").exists() and (Path.cwd() / "setup.py").exists():
             return LOCAL_CONFIG, LOCAL_ENV

        # 3. Otherwise, use User Global config
        return USER_CONFIG_FILE, USER_ENV_FILE

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def run(self):
        self._print_banner()
        
        # Ensure directory exists if using global
        if self.config_path == USER_CONFIG_FILE and not self.config_path.parent.exists():
             self.config_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.env_path.exists():
            console.print(f"[yellow]No .env file found at {self.env_path}. Creating from example...[/yellow]")
            if ENV_EXAMPLE_FILE.exists():
                if not self.env_path.parent.exists():
                    self.env_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ENV_EXAMPLE_FILE, self.env_path)
                self.env_manager = EnvManager(self.env_path) # Reload
            else:
                # Create empty if example missing
                self.env_path.touch()
                self.env_manager = EnvManager(self.env_path)

        # Main Loop
        while True:
            self._display_dashboard()
            
            choice = questionary.select(
                "What would you like to configure?",
                choices=[
                    questionary.Choice("1. API Keys", value="keys"),
                    questionary.Choice("2. Transcription Settings", value="transcribe"),
                    questionary.Choice("3. Refinement Settings", value="refine"),
                    questionary.Choice("4. Output Formats", value="outputs"),
                    questionary.Choice("5. Save & Exit", value="save"),
                    questionary.Choice("6. Exit without Saving", value="exit")
                ]
            ).ask()
            
            if choice == "keys":
                self._setup_api_keys()
            elif choice == "transcribe":
                self._setup_transcription()
            elif choice == "refine":
                self._setup_refinement()
            elif choice == "outputs":
                self._setup_outputs()
            elif choice == "save":
                self._save_config()
                console.print(Panel(f"[bold green]Configuration Saved to {self.config_path}![/bold green]", border_style="green"))
                break
            elif choice == "exit":
                console.print("[yellow]Exiting without saving...[/yellow]")
                break
            elif choice is None: # Ctrl+C
                break

    def _print_banner(self):
        console.clear()
        banner = """
   [bold cyan]█████╗ ███╗   ███╗ █████╗ ███╗   ██╗██╗   ██╗[/bold cyan]
  [bold cyan]██╔══██╗████╗ ████║██╔══██╗████╗  ██║██║   ██║[/bold cyan]
  [bold cyan]███████║██╔████╔██║███████║██╔██╗ ██║██║   ██║[/bold cyan]
  [bold cyan]██╔══██║██║╚██╔╝██║██╔══██║██║╚██╗██║██║   ██║[/bold cyan]
  [bold cyan]██║  ██║██║ ╚═╝ ██║██║  ██║██║ ╚████║╚██████╔╝[/bold cyan]
  [bold cyan]╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ [/bold cyan]
        """
        subtitle = f"Config: {self.config_path}"
        console.print(Panel(banner, title="[bold white]Setup Wizard[/bold white]", subtitle=subtitle, border_style="blue"))

    def _display_dashboard(self):
        console.clear()
        self._print_banner()
        
        # Current Config Summary
        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_column(justify="right")
        
        # Transcribe
        t_prov = self.config.get("transcribe", {}).get("provider", "Not Set")
        t_model = self.config.get("transcribe", {}).get("model", "Not Set")
        
        # Refine
        r_prov = self.config.get("refine", {}).get("provider", "Not Set")
        r_model = self.config.get("refine", {}).get("model", "Not Set")
        
        # Outputs
        artifacts = self.config.get("processing", {}).get("output", {}).get("artifacts", [])
        outputs_str = ", ".join([f"{a['plugin']}/{a['template']}" for a in artifacts]) if artifacts else "None"
        if len(outputs_str) > 60: outputs_str = outputs_str[:57] + "..."

        # API Keys Status - dynamically check all providers
        keys_status = []
        all_providers = self.provider_manager.get_all_providers()
        
        for provider in sorted(all_providers):
            if self.provider_manager.requires_api_key(provider):
                key_info = self.provider_manager.get_api_key_info(provider)
                metadata = self.provider_manager.get_metadata(provider)
                env_var = key_info['env_var']
                display_name = metadata['display_name']
                
                if self.env_manager.get(env_var):
                    keys_status.append(f"{display_name}: [green]OK[/green]")
                else:
                    keys_status.append(f"{display_name}: [red]Missing[/red]")

        summary_table = Table(box=box.SIMPLE, show_header=False, expand=True)
        summary_table.add_column("Section", style="bold cyan")
        summary_table.add_column("Value", style="white")
        
        summary_table.add_row("Transcription", f"{t_prov} ({t_model})")
        summary_table.add_row("Refinement", f"{r_prov} ({r_model})")
        summary_table.add_row("Outputs", outputs_str)
        summary_table.add_row("API Keys", ", ".join(keys_status))

        console.print(Panel(summary_table, title="[bold]Current Configuration[/bold]", border_style="green"))

    def _setup_api_keys(self):
        console.print(Panel("[bold]Step 1: API Keys[/bold]", style="cyan"))
        
        # Discover all providers that need API keys
        all_providers = self.provider_manager.get_all_providers()
        providers_needing_keys = [
            p for p in all_providers
            if self.provider_manager.requires_api_key(p)
        ]
        
        for provider in sorted(providers_needing_keys):
            key_info = self.provider_manager.get_api_key_info(provider)
            key_name = key_info['env_var']
            display_name = key_info['display_name']
            current_val = self.env_manager.get(key_name)
            
            # Mask current value for display
            display_val = f"{current_val[:4]}...{current_val[-4:]}" if current_val and len(current_val) > 8 else (current_val or "Not Set")
            
            if questionary.confirm(f"Configure {display_name}? (Current: {display_val})", default=not bool(current_val)).ask():
                new_val = questionary.password(f"Enter {display_name}:", default=current_val or "").ask()
                if new_val:
                    self.env_manager.set(key_name, new_val)
                    console.print(f"[green]Updated {key_name}[/green]")

    def _setup_transcription(self):
        console.clear()
        console.print(Panel("[bold]Step 2: Transcription Configuration[/bold]", style="cyan"))
        
        # 1. Select Provider - dynamically discover providers with transcription capability
        available_providers = self.provider_manager.get_providers_by_capability('transcription')
        
        if not available_providers:
            console.print("[yellow]No transcription providers found![/yellow]")
            return
        
        table = Table(title="Available Transcription Providers", box=box.ROUNDED)
        table.add_column("Provider", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Cost", style="green")
        table.add_column("Speed", style="yellow")
        table.add_column("Description", style="white")

        choices = []
        
        for p in sorted(available_providers):
            metadata = self.provider_manager.get_metadata(p)
            table.add_row(
                metadata['display_name'],
                metadata['type'].capitalize(),
                metadata['cost_indicator'],
                metadata['speed_indicator'].capitalize(),
                metadata['description']
            )
            choices.append(questionary.Choice(metadata['display_name'], value=p))

        console.print(table)
        
        provider = questionary.select(
            "Select Transcription Provider:",
            choices=choices,
            default=self.config.get("transcribe", {}).get("provider")
        ).ask()
        
        if not provider: return

        # 2. Select Model
        models = self.provider_manager.get_models(provider)
        if not models:
            console.print(f"[yellow]No models found for {provider}. Using default.[/yellow]")
            return

        model_table = Table(title=f"Available Models for {provider.capitalize()}", box=box.ROUNDED)
        model_table.add_column("Model Name", style="cyan")
        model_table.add_column("Context", style="magenta")
        model_table.add_column("Input Cost ($/1M)", style="green")
        model_table.add_column("Output Cost ($/1M)", style="green")
        
        model_choices = []
        for m in models:
            name = m["name"]
            ctx = f"{m.get('context_window', {}).get('input_tokens', '?')}"
            cost_in = m.get('cost_per_1M_tokens_usd', {}).get('input', 0.0)
            cost_out = m.get('cost_per_1M_tokens_usd', {}).get('output', 0.0)
            
            model_table.add_row(name, str(ctx), str(cost_in), str(cost_out))
            model_choices.append(questionary.Choice(f"{name} (${cost_in}/{cost_out})", value=name))

        console.print(model_table)
        
        model = questionary.select(
            "Select Model:",
            choices=model_choices,
            default=self.config.get("transcribe", {}).get("model")
        ).ask()

        self.config["transcribe"] = {"provider": provider, "model": model}

    def _setup_refinement(self):
        console.clear()
        console.print(Panel("[bold]Step 3: Refinement Configuration[/bold]", style="cyan"))
        console.print("Refinement uses an LLM to clean up the transcript, fix punctuation, and format speakers.\n")
        
        # Dynamically discover providers with refinement capability
        available_providers = self.provider_manager.get_providers_by_capability('refinement')
        
        if not available_providers:
            console.print("[yellow]No refinement providers found![/yellow]")
            return
        
        table = Table(title="Refinement Providers", box=box.ROUNDED)
        table.add_column("Provider", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Cost", style="green")
        table.add_column("Description", style="white")
        
        choices = []
        for p in sorted(available_providers):
            metadata = self.provider_manager.get_metadata(p)
            table.add_row(
                metadata['display_name'],
                metadata['type'].capitalize(),
                metadata['cost_indicator'],
                metadata['description']
            )
            choices.append(questionary.Choice(metadata['display_name'], value=p))
            
        console.print(table)
        
        provider = questionary.select(
            "Select Refinement Provider:",
            choices=choices,
            default=self.config.get("refine", {}).get("provider")
        ).ask()
        
        if not provider: return

        # Select Model
        models = self.provider_manager.get_models(provider)
        model_choices = [questionary.Choice(m["name"], value=m["name"]) for m in models]
        
        model = questionary.select(
            "Select Model:",
            choices=model_choices,
            default=self.config.get("refine", {}).get("model")
        ).ask()
        
        self.config["refine"] = {"provider": provider, "model": model}

    def _setup_outputs(self):
        console.clear()
        console.print(Panel("[bold]Step 4: Output Formats[/bold]", style="cyan"))
        
        # Scan templates
        templates = {}
        for plugin_dir in TEMPLATES_DIR.iterdir():
            if plugin_dir.is_dir():
                templates[plugin_dir.name] = []
                for t in plugin_dir.glob("*.j2"):
                    templates[plugin_dir.name].append(t.stem)

        # Display options
        console.print("[bold]Available Output Templates:[/bold]")
        for plugin, t_list in templates.items():
            console.print(f"  [cyan]{plugin.upper()}[/cyan]: {', '.join(t_list)}")
        console.print("")

        # Flatten for selection
        choices = []
        current_artifacts = self.config.get("processing", {}).get("output", {}).get("artifacts", [])
        current_ids = {f"{a['plugin']}:{a['template']}" for a in current_artifacts}

        for plugin, t_list in templates.items():
            for t in t_list:
                cid = f"{plugin}:{t}"
                choices.append(questionary.Choice(
                    f"{plugin.upper()} - {t}",
                    value={"plugin": plugin, "template": t},
                    checked=cid in current_ids
                ))
        
        selected = questionary.checkbox(
            "Select outputs to generate:",
            choices=sorted(choices, key=lambda x: x.title),
            validate=lambda x: True # Allow empty
        ).ask()
        
        artifacts = []
        if selected:
            for s in selected:
                artifacts.append({
                    "plugin": s["plugin"],
                    "template": s["template"],
                    "filename": f"{s['template']}"
                })
        
        # Ensure processing.output exists
        if "processing" not in self.config: self.config["processing"] = {}
        if "output" not in self.config["processing"]: self.config["processing"]["output"] = {}
        
        self.config["processing"]["output"]["artifacts"] = artifacts

    def _save_config(self):
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, sort_keys=False)

def run_wizard():
    wizard = SetupWizard()
    wizard.run()

if __name__ == "__main__":
    run_wizard()