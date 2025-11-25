from pathlib import Path
from typing import Dict, Any, List
import logging
from jinja2 import Template

from .base import BasePlugin

logger = logging.getLogger("Amanu.Plugins.PDF")

class PDFPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "pdf"

    @property
    def description(self) -> str:
        return "Generates PDF files using ReportLab."

    @property
    def default_extension(self) -> str:
        return "pdf"

    def generate(self, context: Dict[str, Any], template_content: str, output_path: Path, raw_transcript: List[Dict[str, Any]] | None = None, **kwargs) -> Path:
        """
        Generate PDF file from rendered Jinja2 template using basic canvas drawing.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import simpleSplit # Still useful for long lines
            # Removed: Paragraph, SimpleDocTemplate, Spacer, styles, ParagraphStyle, enums, colors
        except ImportError:
            logger.error("ReportLab not installed. Cannot generate PDF.")
            raise ImportError("Please install reportlab: pip install reportlab")

        # 1. Render Jinja2 template to get markdown-like text
        template = Template(template_content)
        rendered_text = template.render(**context)

        c = canvas.Canvas(str(output_path), pagesize=letter)
        width, height = letter

        # Initial drawing position and margins
        x_margin = 72
        y_start = height - 72
        line_height = 14
        current_y = y_start

        # Parse rendered text line by line to lay out on canvas
        lines = rendered_text.splitlines()
        for line in lines:
            line = line.strip()

            # Handle page breaks automatically
            if current_y < x_margin: # If we are too close to bottom margin
                c.showPage()
                current_y = y_start # Reset y for new page

            if not line:
                current_y -= line_height / 2 # Smaller gap for empty lines
                continue

            # Basic Markdown heading detection and font size adjustment
            if line.startswith('# '):
                c.setFont("Helvetica-Bold", 16)
                display_text = line[2:].strip()
                current_y -= line_height * 1.5 # Extra space for heading
            elif line.startswith('## '):
                c.setFont("Helvetica-Bold", 12)
                display_text = line[3:].strip()
                current_y -= line_height * 1.2
            elif line.startswith('- '): # Simple list item
                c.setFont("Helvetica", 10)
                display_text = f"• {line[2:].strip()}" # Prepend bullet
                current_y -= line_height
            elif line.startswith('> '): # Simple blockquote
                c.setFont("Helvetica-Oblique", 10) # Italic for quotes
                display_text = f"> {line[2:].strip()}"
                current_y -= line_height
            else:
                c.setFont("Helvetica", 10)
                display_text = line
                current_y -= line_height

            # Use simpleSplit for lines that are too long for the canvas width
            text_lines = simpleSplit(display_text, c._fontname, c._fontsize, width - (2 * x_margin))
            for text_segment in text_lines:
                c.drawString(x_margin, current_y, text_segment)
                current_y -= line_height # Move down for next line of wrapped text

        c.save()
        return output_path
