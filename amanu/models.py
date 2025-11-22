"""Data models for the Amanu application."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AudioFile:
    """Represents an audio file with its metadata."""
    path: Path
    original_name: str
    created_at: str
    size_bytes: int
    duration_seconds: float
    checksum_sha256: str


@dataclass
class ProcessingMetrics:
    """Metrics from processing an audio file."""
    timestamp_start: str
    duration_seconds: float
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: str


@dataclass
class ProcessingResult:
    """Complete result of processing an audio file."""
    audio_file: AudioFile
    metrics: ProcessingMetrics
    raw_transcript: list
    clean_transcript: str
    output_dir: Path
    language: str = "auto"
    device_id: Optional[str] = None
    source: Optional[str] = None


@dataclass
class TranscriptSegment:
    """A single segment of a transcript."""
    time: str
    speaker: str
    text: str
