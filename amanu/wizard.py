import os
import sys
import subprocess
from pathlib import Path
import yaml
from typing import Dict, Any, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.panel import Panel
    import questionary
    import google.generativeai as genai
except ImportError:
    print("Error: Required libraries are missing.")
    print("Please install them with: pip install rich questionary google-generativeai")
    sys.exit(1)

console = Console()

# --- Main Configuration Class ---

class Wizard:
    def __init__(self):
        self.config, self.is_existing, self.config_path = self._load_config()

    def _load_config(self) -> Tuple[Dict[str, Any], bool, Path]:
        """Load config from standard locations, return (config, is_existing, path_to_save)."""
        # Check for existing config in the same order as load_config(), plus project directory
        project_config = Path(__file__).parent.parent / "config.yaml"
        paths_to_check = [
            Path("config.yaml"),  # Current directory
            project_config,  # Project directory (where amanu is installed)
            Path.home() / ".config" / "amanu" / "config.yaml"  # User config dir
        ]
        
        for config_path in paths_to_check:
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        return yaml.safe_load(f) or {}, True, config_path
                except Exception as e:
                    console.print(f"[red]Error reading {config_path}: {e}[/red]")
                    sys.exit(1)
        
        # No existing config found, load example and determine save location
        # Look for config.example.yaml in the package directory
        example_config_path = Path(__file__).parent.parent / "config.example.yaml"
        try:
            with open(example_config_path, "r") as f:
                example_config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            console.print(f"[red]Error: config.example.yaml not found at {example_config_path}[/red]")
            sys.exit(1)
        
        # Determine where to save new config
        # Prefer current directory if we're in the project directory, otherwise use ~/.config/amanu/
        if Path.cwd() == project_config.parent:
            # We're in the project directory
            save_path = Path("config.yaml")
        else:
            # We're elsewhere, use user config directory
            save_path = Path.home() / ".config" / "amanu" / "config.yaml"
            save_path.parent.mkdir(parents=True, exist_ok=True)
        
        return example_config, False, save_path

    def run(self):
        try:
            if not self.is_existing:
                self._run_full_setup()
            else:
                self._run_main_menu()
        except (KeyboardInterrupt, TypeError):
            console.print("\n\n[yellow]Wizard cancelled by user.[/yellow]")
            sys.exit(0)

    def _run_full_setup(self):
        self._print_banner()
        console.print("\n[bold]Welcome to Amanu![/bold] Let's set up your `config.yaml` file.")
        if not questionary.confirm("Ready to begin?", default=True).ask():
            return

        self._configure_providers()
        self._configure_outputs()
        self._configure_final_settings()
        self._review_and_save()

    def _run_main_menu(self):
        while True:
            self._print_banner()
            self._display_summary()
            
            choice = questionary.select(
                "What would you like to do?",
                choices=[
                    "1. Edit All Settings",
                    "2. Edit AI Providers",
                    "3. Edit Output Formats",
                    "4. Edit Final Settings",
                    "5. Save and Exit",
                    "6. Exit Without Saving"
                ]
            ).ask()

            if choice is None or "6." in choice:
                break
            elif "1." in choice:
                self._configure_providers()
                self._configure_outputs()
                self._configure_final_settings()
            elif "2." in choice:
                self._configure_providers()
            elif "3." in choice:
                self._configure_outputs()
            elif "4." in choice:
                self._configure_final_settings()
            elif "5." in choice:
                self._save_config()
                break

    def _configure_providers(self):
        console.clear()
        console.print(Panel("[bold cyan]Step 1: Configure AI Providers[/bold cyan]"))

        # Gemini
        current_key = self.config.get("providers", {}).get("gemini", {}).get("api_key")
        gemini_models = self._get_gemini_models(current_key)
        if questionary.confirm("Configure Gemini provider?", default=True).ask():
            new_key = questionary.password("Enter Gemini API Key:", default=current_key or "").ask()
            if new_key and new_key != current_key:
                gemini_models = self._get_gemini_models(new_key)
                if gemini_models:
                    self.config["providers"]["gemini"]["api_key"] = new_key
        
        gemini_available = bool(gemini_models)

        # Zai
        current_zai_key = self.config.get("providers", {}).get("zai", {}).get("api_key")
        zai_available = False
        if questionary.confirm("Configure Zai (Zhipu AI) provider?", default=False).ask():
            new_zai_key = questionary.password("Enter Zai API Key:", default=current_zai_key or "").ask()
            if new_zai_key:
                self.config.setdefault("providers", {}).setdefault("zai", {})["api_key"] = new_zai_key
                zai_available = True
        elif current_zai_key:
            zai_available = True

        # Transcribe
        current_provider = self.config.get("transcribe", {}).get("provider")
        provider_choices = [
            questionary.Choice("Gemini", "gemini", disabled=not gemini_available),
            questionary.Choice("Whisper", "whisper", disabled=not self._check_whisper()),
            questionary.Choice("Zai", "zai", disabled=not zai_available),
        ]
        provider = questionary.select(
            "Select transcription provider:",
            choices=provider_choices,
            default=current_provider if current_provider in [c.value for c in provider_choices if not c.disabled] else None
        ).ask()

        if provider == "gemini":
            current_model = self.config.get("transcribe", {}).get("model")
            model = questionary.select("Select Gemini model:", choices=gemini_models, default=current_model if current_model in gemini_models else None).ask()
            self.config["transcribe"] = {"provider": "gemini", "model": model}
        elif provider == "whisper":
            current_model = self.config.get("transcribe", {}).get("model")
            whisper_models = [m["name"] for m in self.config["providers"]["whisper"]["models"]]
            model = questionary.select("Select Whisper model:", choices=whisper_models, default=current_model if current_model in whisper_models else None).ask()
            self.config["transcribe"] = {"provider": "whisper", "model": model}
        elif provider == "zai":
            current_model = self.config.get("transcribe", {}).get("model")
            # Assuming glm-asr is the primary model for now
            zai_models = [m["name"] for m in self.config.get("providers", {}).get("zai", {}).get("models", [])]
            if not zai_models: zai_models = ["glm-asr"] # Fallback
            model = questionary.select("Select Zai model:", choices=zai_models, default=current_model if current_model in zai_models else None).ask()
            self.config["transcribe"] = {"provider": "zai", "model": model}

        # Refine
        current_provider = self.config.get("refine", {}).get("provider")
        provider = questionary.select(
            "Select refinement provider:",
            choices=[questionary.Choice("Gemini", "gemini", disabled=not gemini_available)],
            default=current_provider if gemini_available else None
        ).ask()
        if provider == "gemini":
            current_model = self.config.get("refine", {}).get("model")
            model = questionary.select("Select Gemini model:", choices=gemini_models, default=current_model if current_model in gemini_models else None).ask()
            self.config["refine"] = {"provider": "gemini", "model": model}

    def _configure_outputs(self):
        console.clear()
        console.print(Panel("[bold cyan]Step 2: Select Output Formats[/bold cyan]"))
        
        current_artifacts = self.config.get("processing", {}).get("output", {}).get("artifacts", [])
        current_selection_ids = {f"{a['plugin']}:{a['template']}" for a in current_artifacts}

        output_choices = []
        templates_dir = Path(__file__).parent.parent / "amanu" / "templates"
        for plugin_dir in templates_dir.iterdir():
            if plugin_dir.is_dir():
                plugin_name = plugin_dir.name
                for template_file in plugin_dir.glob("*.j2"):
                    template_name = template_file.stem
                    choice_id = f"{plugin_name}:{template_name}"
                    output_choices.append(
                        questionary.Choice(
                            f"{plugin_name.capitalize()}: {template_name}",
                            value={"plugin": plugin_name, "template": template_name},
                            checked=choice_id in current_selection_ids
                        )
                    )

        selected_outputs = questionary.checkbox("Select your desired output artifacts:", choices=sorted(output_choices, key=lambda c: c.title)).ask()

        artifacts = []
        for output in selected_outputs:
            filename = f"{output['template']}"
            artifacts.append({"plugin": output["plugin"], "template": output["template"], "filename": filename})
        
        self.config["processing"]["output"]["artifacts"] = artifacts

    def _configure_final_settings(self):
        console.clear()
        console.print(Panel("[bold cyan]Step 3: Final Settings[/bold cyan]"))

        current_lang = self.config.get("processing", {}).get("language", "auto")
        lang = questionary.select("Primary language:", choices=["auto", "en", "ru", "de", "fr", "es"], default=current_lang).ask()
        self.config["processing"]["language"] = lang

        current_paths = self.config.get("paths", {})
        input_path = questionary.text("Input directory:", default=current_paths.get("input", "./scribe-in")).ask()
        results_path = questionary.text("Output directory:", default=current_paths.get("results", "./scribe-out")).ask()
        self.config["paths"] = {"input": input_path, "results": results_path}
        
        if questionary.confirm("Create directories now?", default=True).ask():
            Path(input_path).mkdir(parents=True, exist_ok=True)
            Path(results_path).mkdir(parents=True, exist_ok=True)

        current_cleanup = self.config.get("cleanup", {}).get("auto_cleanup_enabled", True)
        enable_cleanup = questionary.confirm("Enable auto-cleanup?", default=current_cleanup).ask()
        self.config["cleanup"]["auto_cleanup_enabled"] = enable_cleanup

    def _review_and_save(self):
        console.clear()
        console.print(Panel("[bold green]🎉 Configuration Review 🎉[/bold green]"))
        yaml_str = yaml.dump(self.config, sort_keys=False)
        console.print(Panel(yaml_str, title="config.yaml"))
        if questionary.confirm("Save this configuration?", default=True).ask():
            self._save_config()

    def _save_config(self):
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, sort_keys=False)
        console.print(f"\n[green]Configuration saved to {self.config_path}![/green]")

    def _check_whisper(self) -> bool:
        try:
            subprocess.run(["whisper-cli", "--version"], capture_output=True, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def _get_gemini_models(self, api_key: Optional[str]) -> List[str]:
        if not api_key:
            return []
        try:
            genai.configure(api_key=api_key)
            return [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except Exception:
            return []

    def _print_banner(self):
        banner_text = """
         [bold cyan]█████╗ [/bold cyan][bold blue]███╗   ███╗[/bold blue][bold magenta]  █████╗ [/bold magenta][bold red]███╗   ██╗[/bold red][bold yellow]██╗   ██╗[/bold yellow]
        [bold cyan]██╔══██╗[/bold cyan][bold blue]████╗ ████║[/bold blue][bold magenta] ██╔══██╗[/bold magenta][bold red]████╗  ██║[/bold red][bold yellow]██║   ██║[/bold yellow]
        [bold cyan]███████║[/bold cyan][bold blue]██╔████╔██║[/bold blue][bold magenta] ███████║[/bold magenta][bold red]██╔██╗ ██║[/bold red][bold yellow]██║   ██║[/bold yellow]
        [bold cyan]██╔══██║[/bold cyan][bold blue]██║╚██╔╝██║[/bold blue][bold magenta] ██╔══██║[/bold magenta][bold red]██║╚██╗██║[/bold red][bold yellow]██║   ██║[/bold yellow]
        [bold cyan]██║  ██║[/bold cyan][bold blue]██║ ╚═╝ ██║[/bold blue][bold magenta] ██║  ██║[/bold magenta][bold red]██║ ╚████║[/bold red][bold yellow]╚██████╔╝[/bold yellow]
        [bold cyan]╚═╝  ╚═╝[/bold cyan][bold blue]╚═╝     ╚═╝[/bold blue][bold magenta] ╚═╝  ╚═╝[/bold magenta][bold red]╚═╝  ╚═══╝[/bold red][bold yellow] ╚═════╝[/bold yellow]
        """
        console.print(Panel(banner_text, title="[bold white]Amanu Configuration Wizard[/bold white]", border_style="magenta"))

    def _display_summary(self):
        console.print(Panel(f"[bold white]Current Configuration[/bold white]\n[dim]{self.config_path}[/dim]", border_style="green"))
        
        transcribe_provider = self.config.get("transcribe", {}).get("provider", "N/A")
        transcribe_model = self.config.get("transcribe", {}).get("model", "N/A")
        console.print(f"  [bold]Transcribe[/bold]: {transcribe_provider} ({transcribe_model})")

        refine_provider = self.config.get("refine", {}).get("provider", "N/A")
        refine_model = self.config.get("refine", {}).get("model", "N/A")
        console.print(f"  [bold]Refine[/bold]:     {refine_provider} ({refine_model})")

        artifacts = self.config.get("processing", {}).get("output", {}).get("artifacts", [])
        console.print(f"  [bold]Outputs[/bold]:    {len(artifacts)} artifact(s)")
        console.print("")

def run_wizard():
    wizard = Wizard()
    wizard.run()

if __name__ == "__main__":
    run_wizard()