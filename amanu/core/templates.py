import yaml
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger("Amanu.Templates")

def load_template(plugin_name: str, template_name: str) -> Tuple[Optional[str], Optional[Path]]:
    """
    Finds and reads the template file.
    Looks for templates in amanu/templates/{plugin_name}/{template_name}.j2
    or amanu/templates/{template_name}.j2
    
    Returns:
        Tuple[str, Path]: The content of the template and its path, or (None, None) if not found.
    """
    # Try plugin-specific path
    # Assuming this file is in amanu/core/templates.py, so parent.parent is amanu/
    base_dir = Path(__file__).parent.parent / "templates"
    
    template_path = base_dir / plugin_name / f"{template_name}.j2"
    
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read(), template_path

    # Fallback to general template directory
    general_template_path = base_dir / f"{template_name}.j2"
    if general_template_path.exists():
        with open(general_template_path, "r", encoding="utf-8") as f:
            return f.read(), general_template_path

    return None, None

def parse_template(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Parses a template string with optional YAML Front Matter.
    
    Format:
    ---
    key: value
    ---
    Template body...
    
    Returns:
        Tuple[Dict, str]: A tuple containing the metadata dict and the template body.
    """
    if not content.startswith("---"):
        return {}, content
    
    try:
        # Split on the second "---"
        parts = content.split("---", 2)
        if len(parts) >= 3:
            # parts[0] is empty string before first ---
            # parts[1] is the yaml content
            # parts[2] is the rest of the file
            metadata = yaml.safe_load(parts[1])
            body = parts[2]
            
            # If body starts with newline, strip it (optional, but cleaner)
            if body.startswith("\n"):
                body = body[1:]
                
            return metadata or {}, body
    except Exception as e:
        logger.warning(f"Failed to parse Front Matter: {e}")
        
    return {}, content
