import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

class APILogger:
    """
    Logs raw API requests and responses to a file.
    """
    def __init__(self, job_dir: Path):
        self.job_dir = job_dir
        self.log_file = job_dir / "api_calls.log"
        self._ensure_log_file()

    def _ensure_log_file(self):
        if not self.log_file.exists():
            with open(self.log_file, "w") as f:
                f.write(f"# API Call Log for Job {self.job_dir.name}\n")
                f.write(f"# Created at: {datetime.now().isoformat()}\n\n")

    def log(self, provider: str, endpoint: str, request: Any, response: Any, error: Optional[str] = None):
        """
        Log an API interaction in human-readable text format.
        """
        timestamp = datetime.now().isoformat()
        
        with open(self.log_file, "a") as f:
            # Write separator and header
            f.write("=" * 80 + "\n")
            f.write(f"[{timestamp}] {provider.upper()} - {endpoint}\n")
            f.write("=" * 80 + "\n\n")
            
            # Write request
            f.write("REQUEST:\n")
            f.write("-" * 80 + "\n")
            f.write(self._format_data(request))
            f.write("\n\n")
            
            # Write response
            f.write("RESPONSE:\n")
            f.write("-" * 80 + "\n")
            if error:
                f.write(f"ERROR: {error}\n")
            else:
                f.write(self._format_data(response))
            f.write("\n\n")
            
            # End separator
            f.write("\n")

    def _format_data(self, data: Any, indent: int = 0) -> str:
        """
        Format data in a human-readable way with indentation.
        """
        prefix = "  " * indent
        
        if data is None:
            return f"{prefix}None"
        
        if isinstance(data, bool):
            return f"{prefix}{data}"
        
        if isinstance(data, (int, float)):
            return f"{prefix}{data}"
        
        if isinstance(data, str):
            # For long strings, add line breaks
            return f"{prefix}{data}"
        
        if isinstance(data, dict):
            if not data:
                return f"{prefix}{{}}"
            
            lines = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._format_data(value, indent + 1))
                else:
                    formatted_value = self._format_data(value, 0).strip()
                    lines.append(f"{prefix}{key}: {formatted_value}")
            return "\n".join(lines)
        
        if isinstance(data, (list, tuple)):
            if not data:
                return f"{prefix}[]"
            
            # For short lists of primitives, keep on one line
            if len(data) <= 3 and all(isinstance(x, (str, int, float, bool, type(None))) for x in data):
                return f"{prefix}{data}"
            
            lines = []
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}[{i}]:")
                    lines.append(self._format_data(item, indent + 1))
                else:
                    formatted_item = self._format_data(item, 0).strip()
                    lines.append(f"{prefix}[{i}]: {formatted_item}")
            return "\n".join(lines)
        
        # Fallback for other objects
        return f"{prefix}{str(data)}"

    def _sanitize(self, data: Any) -> Any:
        """
        Sanitize data for logging (e.g. truncate long strings, hide keys if needed).
        For now, we keep it mostly raw as requested, but handle non-serializable objects.
        """
        if isinstance(data, (str, int, float, bool, type(None))):
            return data
        if isinstance(data, (list, tuple)):
            return [self._sanitize(item) for item in data]
        if isinstance(data, dict):
            return {k: self._sanitize(v) for k, v in data.items()}
        
        # Fallback for objects
        return str(data)
