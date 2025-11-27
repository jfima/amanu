import logging
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Template

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .base import BasePlugin

logger = logging.getLogger("Amanu.Plugins.PDF")

class PDFPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "pdf"

    @property
    def description(self) -> str:
        return "Generates PDF files using ReportLab with UTF-8 support."

    @property
    def default_extension(self) -> str:
        return "pdf"

    def __init__(self):
        super().__init__()
        self._register_fonts()

    def _register_fonts(self):
        """Register fonts that support Cyrillic characters."""
        try:
            # Try to find DejaVuSans on the system
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/dejavu/DejaVuSans.ttf"
            ]
            
            font_path = None
            for path in font_paths:
                if Path(path).exists():
                    font_path = path
                    break
            
            if font_path:
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
                
                # Also try to register Bold and Oblique if available
                base_dir = Path(font_path).parent
                bold_path = base_dir / "DejaVuSans-Bold.ttf"
                oblique_path = base_dir / "DejaVuSans-Oblique.ttf"
                
                if bold_path.exists():
                    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', str(bold_path)))
                if oblique_path.exists():
                    pdfmetrics.registerFont(TTFont('DejaVuSans-Oblique', str(oblique_path)))
                    
                self.font_name = 'DejaVuSans'
                logger.info(f"Registered font: {self.font_name}")
            else:
                logger.warning("DejaVuSans font not found. Cyrillic characters may not display correctly.")
                self.font_name = 'Helvetica' # Fallback
                
        except Exception as e:
            logger.error(f"Failed to register fonts: {e}")
            self.font_name = 'Helvetica'

    def generate(self, context: Dict[str, Any], template_content: str, output_path: Path, raw_transcript: List[Dict[str, Any]] | None = None, **kwargs) -> Path:
        """
        Generate PDF file from rendered Jinja2 template using ReportLab Platypus.
        """
        # 1. Render Jinja2 template to get markdown-like text
        template = Template(template_content)
        rendered_text = template.render(**context)

        # 2. Setup Document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # 3. Define Styles
        styles = getSampleStyleSheet()
        
        # Custom Styles based on registered font
        styles.add(ParagraphStyle(
            name='NormalUTF8',
            parent=styles['Normal'],
            fontName=self.font_name,
            fontSize=10,
            leading=14
        ))
        
        styles.add(ParagraphStyle(
            name='Heading1UTF8',
            parent=styles['Heading1'],
            fontName=self.font_name if self.font_name == 'Helvetica' else f'{self.font_name}-Bold',
            fontSize=18,
            leading=22,
            spaceAfter=12
        ))
        
        styles.add(ParagraphStyle(
            name='Heading2UTF8',
            parent=styles['Heading2'],
            fontName=self.font_name if self.font_name == 'Helvetica' else f'{self.font_name}-Bold',
            fontSize=14,
            leading=18,
            spaceAfter=10
        ))

        styles.add(ParagraphStyle(
            name='QuoteUTF8',
            parent=styles['Normal'],
            fontName=self.font_name if self.font_name == 'Helvetica' else f'{self.font_name}-Oblique',
            fontSize=10,
            leading=14,
            leftIndent=20,
            textColor=colors.gray
        ))

        # 4. Parse Content
        story = []
        lines = rendered_text.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 12))
                continue
            
            if line.startswith('# '):
                text = line[2:].strip()
                story.append(Paragraph(text, styles['Heading1UTF8']))
            elif line.startswith('## '):
                text = line[3:].strip()
                story.append(Paragraph(text, styles['Heading2UTF8']))
            elif line.startswith('### '):
                text = line[4:].strip()
                # Use Heading2 style but slightly smaller if we had a Heading3 style, or just Heading2
                story.append(Paragraph(text, styles['Heading2UTF8']))
            elif line.startswith('- ') or line.startswith('* '):
                text = line[2:].strip()
                # Simple bullet point handling
                story.append(Paragraph(f"• {text}", styles['NormalUTF8']))
            elif line.startswith('> '):
                text = line[2:].strip()
                story.append(Paragraph(text, styles['QuoteUTF8']))
            else:
                story.append(Paragraph(line, styles['NormalUTF8']))

        # 5. Build PDF
        try:
            doc.build(story)
            logger.info(f"PDF generated successfully at {output_path}")
        except Exception as e:
            logger.error(f"Failed to build PDF: {e}")
            raise

        return output_path
