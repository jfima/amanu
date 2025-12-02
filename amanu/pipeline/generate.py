import logging
import json
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseStage
from ..core.models import JobObject, StageName
from ..plugins.manager import PluginManager

logger = logging.getLogger("Amanu.Generate")

class GenerateStage(BaseStage):
    stage_name = StageName.GENERATE

    def __init__(self, manager):
        super().__init__(manager)
        self.plugin_manager = PluginManager()

    def validate_prerequisites(self, job_dir: Path, job: JobObject) -> None:
        """
        Validate prerequisites for generate stage.
        """
        # Check that refine stage completed successfully
        if job.enriched_context_file:
            context_file = job_dir / job.enriched_context_file
        else:
            context_file = job_dir / "transcripts" / "enriched_context.json"
            
        if not context_file.exists():
            raise ValueError(
                f"Cannot run 'generate' stage: enriched context not found.\n"
                f"Please run 'refine' stage first."
            )

    def execute(self, job_dir: Path, job: JobObject, **kwargs) -> Dict[str, Any]:
        """
        Generate user artifacts using Plugins.
        """
        logger.debug(f"Executing GenerateStage. Initial job_dir type: {type(job_dir)}, value: {job_dir}")
        job_dir = Path(job_dir) # Ensure job_dir is a Path object
        logger.debug(f"job_dir is now type: {type(job_dir)}")
        # Load Enriched Context
        if job.enriched_context_file:
            context_file = job_dir / job.enriched_context_file
        else:
            context_file = job_dir / "transcripts" / "enriched_context.json"
            
        context: Dict[str, Any] = {}
        if context_file.exists():
            with open(context_file, "r") as f:
                context = json.load(f)
        else:
            logger.warning("Enriched context not found. Proceeding with minimal context from raw transcript.")

        # Load Raw Transcript (optional, for plugins like SRT)
        if job.raw_transcript_file:
            raw_transcript_file = job_dir / job.raw_transcript_file
        else:
            raw_transcript_file = job_dir / "transcripts" / "raw_transcript.json"
            
        raw_transcript: List[Dict[str, Any]] | None = []
        if raw_transcript_file.exists():
            with open(raw_transcript_file, "r") as f:
                raw_transcript = json.load(f)
            # If context is empty, populate it with raw transcript for basic templates
            if not context and raw_transcript:
                context['raw_transcript'] = raw_transcript
                logger.info("Using raw_transcript as the main context for generation.")
        
        if not context:
            raise FileNotFoundError("No context available for generation. Enriched context and raw transcript are both missing.")
            
        generated_artifacts = []

        # Iterate through each artifact configuration
        for artifact_config in job.configuration.output.artifacts:
            plugin_name = artifact_config.plugin
            template_name = artifact_config.template
            custom_filename: str | None = artifact_config.filename

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
            
            rel_path = str(generated_path.relative_to(job_dir))
            generated_artifacts.append({
                "path": rel_path,
                "type": plugin_name,
                "template": template_name,
                "filename_override": custom_filename
            })
            
            # Update Job Object
            if rel_path not in job.final_document_files:
                job.final_document_files.append(rel_path)
        
        if not generated_artifacts:
            logger.warning("No artifacts were generated based on the configuration.")
            return {"artifacts": []}

        return {
            "artifacts": generated_artifacts
        }

    def _load_template(self, plugin_name: str, template_name: str) -> str:
        """
        Load Jinja2 template using shared utility.
        """
        from ..core.templates import load_template, parse_template
        
        content, path = load_template(plugin_name, template_name)
        
        if content:
            metadata, body = parse_template(content)
            return body

        logger.warning(f"Template '{template_name}' for plugin '{plugin_name}' not found. Using internal default.")
        
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
