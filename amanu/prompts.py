import os

BASE_INSTRUCTION = """
You are an expert audio analyst and transcriber. Your task is to process the provided audio file and generate two distinct outputs in a single response, separated by a specific delimiter.

**Input:** An audio file (lecture, meeting, or voice note).

**CRITICAL INSTRUCTION - LANGUAGE:**
- Detect the dominant language of the audio.
- **ALL OUTPUT MUST BE IN THE SAME LANGUAGE AS THE AUDIO.**
- If the audio is in Russian, the transcription, summary, headings, and bullet points MUST be in Russian.

**Output Structure:**

You must generate two parts separated by exactly this line: `---SPLIT_OUTPUT_HERE---`

### PART 1: Raw Transcript (JSON)
- **Format**: A strict JSON array of objects. Do not wrap in markdown code blocks (no ```json ... ```).
- **Content**: A stream of events.
- **Schema**:
  ```json
  [
    {"time": "MM:SS", "speaker": "Speaker Name", "text": "Verbatim text..."},
    {"time": "MM:SS", "speaker": "Speaker Name", "text": "Verbatim text..."}
  ]
  ```
- **Rules**:
    - `time`: Start time of the segment.
    - `speaker`: Identify speakers (Speaker A, Speaker B, or names if known).
    - `text`: The exact words spoken.

`---SPLIT_OUTPUT_HERE---`
"""

def load_template(template_name):
    """
    Loads a template from:
    1. ./templates/{name}.md
    2. ~/.config/amanu/templates/{name}.md
    3. Package templates (amanu/templates/{name}.md)
    """
    filename = f"{template_name}.md"
    
    # 1. Local project templates
    local_path = os.path.join("templates", filename)
    if os.path.exists(local_path):
        with open(local_path, "r") as f:
            return f.read()
            
    # 2. User config templates
    user_path = os.path.expanduser(os.path.join("~/.config/amanu/templates", filename))
    if os.path.exists(user_path):
        with open(user_path, "r") as f:
            return f.read()
            
    # 3. Package templates
    # Assuming this file is in amanu/prompts.py, templates are in amanu/templates/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pkg_path = os.path.join(base_dir, "templates", filename)
    if os.path.exists(pkg_path):
        with open(pkg_path, "r") as f:
            return f.read()
            
    # Fallback if not found
    raise FileNotFoundError(f"Template '{template_name}' not found.")

def get_system_prompt(template_name="default"):
    try:
        template_content = load_template(template_name)
    except FileNotFoundError:
        # Fallback to default if specified template fails, or re-raise?
        # Let's try to load default if custom fails, but warn?
        # For now, let's just fail so user knows.
        raise

    return BASE_INSTRUCTION + "\n" + template_content
