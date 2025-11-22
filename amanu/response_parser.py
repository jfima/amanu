"""Response parsing utilities for Amanu."""

import json
import logging
from typing import Tuple, List, Dict, Any

from .constants import RESPONSE_DELIMITER

logger = logging.getLogger("Amanu")


class ResponseParser:
    """Handles parsing of AI responses into structured data."""
    
    @staticmethod
    def parse_response(text_content: str) -> Tuple[str, str]:
        """
        Split response into raw JSON and clean markdown parts.
        
        Args:
            text_content: The full response text from the AI
            
        Returns:
            Tuple of (raw_json_str, clean_markdown)
        """
        parts = text_content.split(RESPONSE_DELIMITER)
        
        if len(parts) >= 2:
            raw_json_str = parts[0].strip()
            clean_markdown = parts[1].strip()
        else:
            logger.warning(
                "Could not split response into two parts. "
                "Saving all to clean transcript."
            )
            raw_json_str = ""
            clean_markdown = text_content
            
        return raw_json_str, clean_markdown
    
    @staticmethod
    def clean_json(json_str: str) -> str:
        """
        Remove markdown code blocks from JSON string.
        
        Args:
            json_str: JSON string potentially wrapped in markdown
            
        Returns:
            Cleaned JSON string
        """
        return json_str.replace("```json", "").replace("```", "").strip()
    
    @staticmethod
    def parse_transcript_json(json_str: str) -> List[Dict[str, Any]]:
        """
        Parse transcript JSON string into a list of segments.
        
        Args:
            json_str: JSON string containing transcript data
            
        Returns:
            List of transcript segments
            
        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        cleaned = ResponseParser.clean_json(json_str)
        if not cleaned:
            return []
        return json.loads(cleaned)
