from pathlib import Path
from typing import Dict, Any, List
import datetime

from .base import BasePlugin

class SRTPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "srt"

    @property
    def description(self) -> str:
        return "Generates SRT subtitle files."

    @property
    def default_extension(self) -> str:
        return "srt"

    def generate(self, context: Dict[str, Any], template_content: str, output_path: Path, raw_transcript: List[Dict[str, Any]] | None = None, **kwargs) -> Path:
        """
        Generate SRT file.
        Uses `raw_transcript` for subtitle segments.
        """
        segments = raw_transcript # Use the provided raw_transcript

        if not segments:
            raise ValueError("No raw transcription segments found for SRT generation.")

        content = self._generate_srt(segments)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return output_path

    def _generate_srt(self, segments: List[Dict[str, Any]]) -> str:
        lines = []
        for i, segment in enumerate(segments, 1):
            start = self._format_time(segment.get("start_time", 0))
            end = self._format_time(segment.get("end_time", 0))
            text = segment.get("text", "").strip()
            
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
            
        return "\n".join(lines)

    def _format_time(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS,mmm format."""
        td = datetime.timedelta(seconds=seconds)
        # Total seconds to hours, minutes, seconds, milliseconds
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        millis = int(td.microseconds / 1000)
        
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
