import logging
import json
import shutil
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import unicodedata

from .base import BaseStage
from ..core.models import JobMeta, StageName, ShelveConfig

logger = logging.getLogger("Amanu.Shelve")

class Renamer:
    def __init__(self, config: ShelveConfig):
        self.config = config

    def generate_id(self, timestamp: datetime) -> str:
        """Generate unique ID based on config format."""
        return timestamp.strftime(self.config.zettelkasten.id_format)

    def slugify(self, text: str) -> str:
        """
        Convert text to a filename-safe slug.
        Non-ASCII characters are kept if possible, but unsafe chars are removed.
        Spaces to dashes.
        """
        if not text:
            return "untitled"
            
        # Normalize unicode characters
        text = unicodedata.normalize('NFKC', text)
        
        # Replace non-alphanumeric (allowing unicode letters) with separators
        # We want to keep Cyrillic etc.
        # Simple regex: replace anything that is not a word char or whitespace with empty
        # Then replace whitespace with space/dash
        
        # Strip unsafe filesystem chars: / \ : * ? " < > |
        safe_text = re.sub(r'[\\/*?:":<>|]', "", text)
        safe_text = safe_text.strip()
        
        # Replace spaces with dashes or spaces depending on preference?
        # Usually slugs use dashes, but user might want spaces in filename pattern.
        # Let's keep spaces for now, but collapse multiple spaces
        safe_text = re.sub(r'\s+', " ", safe_text)
        
        # Truncate
        if len(safe_text) > 50:
            safe_text = safe_text[:50].strip()
            
        return safe_text

    def get_new_filename(self, artifact_path: Path, context: Dict[str, Any], timestamp: datetime) -> str:
        """Generate new filename based on pattern."""
        file_id = self.generate_id(timestamp)
        
        # Determine title/summary for slug
        summary = context.get("summary", "")
        title = context.get("title", summary.split('\n')[0] if summary else "Untitled")
        slug = self.slugify(title)
        
        date_str = timestamp.strftime("%Y-%m-%d")
        
        pattern = self.config.zettelkasten.filename_pattern
        
        # If pattern doesn't have extension, we should append original extension
        ext = artifact_path.suffix
        
        # Replacements
        filename = pattern.format(
            id=file_id,
            slug=slug,
            date=date_str,
            title=slug # synonymous here
        )
        
        # Ensure extension matches
        if not filename.endswith(ext):
            filename += ext
            
        return filename

class Router:
    def __init__(self, config: ShelveConfig, root_path: Path):
        self.config = config
        self.root_path = root_path

    def determine_destination(self, context: Dict[str, Any]) -> Path:
        """Determine destination folder based on tags."""
        # Get tags/keywords/topics
        tags = set()
        if context.get("keywords"):
            tags.update([k.lower() for k in context["keywords"]])
        if context.get("topics"):
            tags.update([t.lower() for t in context["topics"]])
            
        # Check routes
        routes = self.config.zettelkasten.tag_routes
        target_folder = "Inbox" # Default
        
        for tag, folder in routes.items():
            if tag.lower() in tags:
                target_folder = folder
                break # First match wins
        
        # Strategy: Flat or Folders?
        # If flat, we ignore routes? No, specs say routes are for subfolders.
        
        dest_dir = self.root_path / target_folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        return dest_dir

class ShelveStage(BaseStage):
    stage_name = StageName.SHELVE

    def execute(self, job_dir: Path, meta: JobMeta, **kwargs) -> Dict[str, Any]:
        """
        Organize artifacts into the user's library.
        """
        config = meta.configuration.shelve
        if not config.enabled:
            logger.info("Shelving disabled in configuration.")
            return {"status": "disabled"}

        # Determine Root Path
        # Resolve ~ and relative paths
        if config.root_path:
            root_path = Path(config.root_path).expanduser().resolve()
        else:
            # Default to results_dir passed from manager/pipeline usually
            # But here we don't have access to global results_dir easily without context
            # We can use job_dir/../.. but that's brittle.
            # Fallback: ./scribe-out (default in Config)
            root_path = Path("./scribe-out").resolve()

        if not root_path.exists():
             logger.info(f"Creating shelve root: {root_path}")
             root_path.mkdir(parents=True, exist_ok=True)

        # Load Context
        context_file = job_dir / "transcripts" / "enriched_context.json"
        if context_file.exists():
            with open(context_file, "r") as f:
                context = json.load(f)
        else:
            context = {}

        renamer = Renamer(config)
        router = Router(config, root_path)

        # Find Generated Artifacts
        # We look at Generate stage output, OR just scan "transcripts" folder
        # The Generate stage saves results in _stages/generate.json
        generate_result_file = job_dir / "_stages" / "generate.json"
        artifacts_to_shelve = []
        
        if generate_result_file.exists():
            with open(generate_result_file, "r") as f:
                gen_data = json.load(f)
                for artifact in gen_data.get("artifacts", []):
                    # Artifact path is relative to job_dir
                    p = job_dir / artifact["path"]
                    if p.exists():
                        artifacts_to_shelve.append(p)
        else:
            # Fallback: scan transcripts folder
            logger.warning("Generate stage result not found. Scanning transcripts directory.")
            transcripts_dir = job_dir / "transcripts"
            if transcripts_dir.exists():
                for f in transcripts_dir.iterdir():
                    if f.name not in ["raw_transcript.json", "enriched_context.json", "analysis.json"]:
                        artifacts_to_shelve.append(f)

        results = []
        
        for artifact_path in artifacts_to_shelve:
            # 1. Rename
            if config.strategy == "zettelkasten":
                new_filename = renamer.get_new_filename(artifact_path, context, meta.created_at)
            else:
                # Timeline or default: Keep original name or just ensure safe name
                new_filename = artifact_path.name

            # 2. Route
            if config.strategy == "zettelkasten":
                dest_dir = router.determine_destination(context)
            elif config.strategy == "timeline":
                # Year/Month/Day/JobName structure
                date_folder = meta.created_at.strftime("%Y/%m/%d")
                dest_dir = root_path / date_folder / meta.job_id
                dest_dir.mkdir(parents=True, exist_ok=True)
            else:
                # Flat or custom
                dest_dir = root_path

            # 3. Move/Copy
            final_path = dest_dir / new_filename
            
            # If path exists, handle collision
            if final_path.exists():
                stem = final_path.stem
                ext = final_path.suffix
                final_path = dest_dir / f"{stem}_{int(datetime.now().timestamp())}{ext}"
            
            shutil.copy2(artifact_path, final_path)
            logger.info(f"Shelved {artifact_path.name} -> {final_path}")
            
            results.append({
                "original": str(artifact_path),
                "shelved": str(final_path),
                "strategy": config.strategy
            })
            
            # Optional: Move raw assets too? For now, we only shelve output artifacts.

        return {
            "shelved_count": len(results),
            "files": results
        }