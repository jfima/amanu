"""File management utilities for Amanu."""

import os
import time
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Optional

from .constants import (
    FILE_WAIT_TIMEOUT,
    FILE_STABILIZATION_CHECK_INTERVAL,
    PROCESSED_DIR_NAME,
    QUARANTINE_DIR_NAME,
    CHECKSUM_BLOCK_SIZE,
)

logger = logging.getLogger("Amanu")


class FileManager:
    """Handles file operations and management."""
    
    @staticmethod
    def wait_for_file(filepath: Path, timeout: int = FILE_WAIT_TIMEOUT) -> bool:
        """
        Wait for file to exist and size to stabilize.
        
        Args:
            filepath: Path to the file to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if file is ready, False otherwise
        """
        start = time.time()
        last_size = -1
        
        while time.time() - start < timeout:
            if filepath.exists():
                current_size = filepath.stat().st_size
                if current_size == last_size and current_size > 0:
                    return True
                last_size = current_size
            time.sleep(FILE_STABILIZATION_CHECK_INTERVAL)
        return False
    
    @staticmethod
    def calculate_checksum(filepath: Path) -> str:
        """
        Calculate SHA256 checksum of a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Hexadecimal checksum string
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(CHECKSUM_BLOCK_SIZE), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def move_to_processed(filepath: Path) -> None:
        """
        Move file to processed directory.
        
        Args:
            filepath: Path to the file to move
        """
        processed_dir = filepath.parent / PROCESSED_DIR_NAME
        processed_dir.mkdir(exist_ok=True)
        destination = processed_dir / filepath.name
        shutil.move(str(filepath), str(destination))
        logger.info(f"Moved {filepath.name} to processed directory")
    
    @staticmethod
    def move_to_quarantine(filepath: Path, quarantine_dir: Path) -> None:
        """
        Move file to quarantine directory.
        
        Args:
            filepath: Path to the file to move
            quarantine_dir: Path to the quarantine directory
        """
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        try:
            destination = quarantine_dir / filepath.name
            shutil.move(str(filepath), str(destination))
            logger.info(f"Moved {filepath.name} to quarantine")
        except Exception as e:
            logger.error(f"Failed to move to quarantine: {e}")
    
    @staticmethod
    def get_creation_time(filepath: Path) -> str:
        """
        Get file creation time as formatted string.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Formatted creation time string
        """
        try:
            from datetime import datetime
            creation_time = os.path.getctime(str(filepath))
            return datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.warning(f"Could not get creation time: {e}")
            return "Unknown"
