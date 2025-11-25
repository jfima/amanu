from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Template

from .base import BasePlugin

class MarkdownPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "markdown"

    @property
    def description(self) -> str:
        return "Generates Markdown files using Jinja2 templates."

    @property
    def default_extension(self) -> str:
        return "md"

    def generate(self, context: Dict[str, Any], template_content: str, output_path: Path, raw_transcript: List[Dict[str, Any]] | None = None, **kwargs) -> Path:
        """
        Generate Markdown file.
        """
        # Create Jinja2 template from content
        template = Template(template_content)
        
        # Render
        rendered_content = template.render(**context)
        
        # Save
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_content)
            
        return output_path
