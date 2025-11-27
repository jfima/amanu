from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Template

from .base import BasePlugin

class TxtPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "txt"

    @property
    def description(self) -> str:
        return "Generates plain text files using Jinja2 templates."

    @property
    def default_extension(self) -> str:
        return "txt"

    def generate(self, context: Dict[str, Any], template_content: str, output_path: Path, raw_transcript: List[Dict[str, Any]] | None = None, **kwargs) -> Path:
        """
        Generate TXT file.
        """
        # Create a copy of context to avoid modifying the original
        render_context = context.copy()
        
        # Add raw_transcript to context so templates can access segments directly
        if raw_transcript:
            render_context['transcript_segments'] = raw_transcript
            
        # Create Jinja2 template from content
        template = Template(template_content)
        
        # Render
        rendered_content = template.render(**render_context)
        
        # Save
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_content)
            
        return output_path