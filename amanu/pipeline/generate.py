import logging
import json
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseStage
from ..core.models import JobMeta, StageName
from ..plugins.manager import PluginManager

logger = logging.getLogger("Amanu.Generate")

class GenerateStage(BaseStage):
    stage_name = StageName.GENERATE

    def __init__(self, manager):
        super().__init__(manager)
        self.plugin_manager = PluginManager()

    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Generate user artifacts using Plugins.
        """
        # Load Enriched Context
        context_file = job_dir / "transcripts" / "enriched_context.json"
        if not context_file.exists():
            raise FileNotFoundError("Enriched context not found. Run Refine first.")
            
        with open(context_file, "r") as f:
            context = json.load(f)

        # Load Raw Transcript (optional, for plugins like SRT)
        raw_transcript_file = job_dir / "transcripts" / "raw_transcript.json"
        raw_transcript: List[Dict[str, Any]] | None = [] # Use | None syntax
        if raw_transcript_file.exists():
            with open(raw_transcript_file, "r") as f:
                raw_transcript = json.load(f)
            
        generated_artifacts = []

        # Iterate through each artifact configuration
        for artifact_config in meta.configuration.output.artifacts:
            plugin_name = artifact_config.plugin
            template_name = artifact_config.template
            custom_filename: str | None = artifact_config.filename # Use | None syntax

            plugin = self.plugin_manager.get_plugin(plugin_name)
            if not plugin:
                logger.warning(f"Plugin '{plugin_name}' not found. Skipping artifact.")
                continue
            
            # Load Template Content - now needs plugin_name for path
            template_content = self._load_template(plugin_name, template_name)
            
            # Determine output filename and path
            # Default to template_name + plugin default extension
            base_filename = custom_filename if custom_filename else template_name
            output_filename = f"{base_filename}.{plugin.default_extension}"
            output_path = job_dir / "transcripts" / output_filename
            
            # Generate - now passing raw_transcript
            # Special handling for SRT: skip if no raw_transcript (Direct Analysis mode)
            if plugin_name == "srt" and not raw_transcript:
                logger.warning(f"Skipping SRT generation: raw_transcript not available (Direct Analysis mode)")
                continue
            
            logger.info(f"Generating artifact using plugin '{plugin_name}' and template '{template_name}' to {output_path}...")
            generated_path = plugin.generate(context, template_content, output_path, raw_transcript=raw_transcript)
            
            generated_artifacts.append({
                "path": str(generated_path.relative_to(job_dir)),
                "type": plugin_name,
                "template": template_name,
                "filename_override": custom_filename # To track if custom name was used
            })
        
        if not generated_artifacts:
            logger.warning("No artifacts were generated based on the configuration.")
            return {"artifacts": []}

        return {
            "artifacts": generated_artifacts
        }

    def _load_template(self, plugin_name: str, template_name: str) -> str:
        """
        Load Jinja2 template.
        Looks for templates in amanu/templates/{plugin_name}/{template_name}.j2
        """
        template_path = Path(__file__).parent.parent / "templates" / plugin_name / f"{template_name}.j2"
        
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()

        # Fallback to general template directory if plugin-specific not found
        general_template_path = Path(__file__).parent.parent / "templates" / f"{template_name}.j2"
        if general_template_path.exists():
            with open(general_template_path, "r", encoding="utf-8") as f:
                return f.read()

        logger.warning(f"Template '{template_name}' for plugin '{plugin_name}' not found at {template_path} or {general_template_path}. Using internal default.")
        
        # Default Jinja2 Template (Fallback)
        default_template = """# {{ summary | default('Transcript Summary') }}

## Metadata
- **Date**: {{ date | default('Unknown') }}
- **Language**: {{ language | default('Unknown') }}
- **Sentiment**: {{ sentiment | default('Unknown') }}

{% if participants %}
## Participants
{% for p in participants %}
- {{ p }}
{% endfor %}
{% endif %}

{% if summary %}
## Summary
{{ summary }}
{% endif %}

{% if keywords %}
## Keywords
{{ keywords | join(', ') }}
{% endif %}

{% if clean_text %}
## Transcript
{{ clean_text }}
{% endif %}
"""
        return default_template
