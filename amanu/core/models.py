from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, SecretStr

class StageName(str, Enum):
    INGEST = "ingest"
    SCRIBE = "scribe"
    REFINE = "refine"
    GENERATE = "generate"
    SHELVE = "shelve"

class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class StageState(BaseModel):
    status: StageStatus = StageStatus.PENDING
    timestamp: Optional[datetime] = None
    error: Optional[str] = None

class PricingModel(BaseModel):
    input: float = 0.0
    output: float = 0.0

class ModelContextWindow(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

class ModelSpec(BaseModel):
    name: str
    context_window: ModelContextWindow = Field(default_factory=ModelContextWindow)
    cost_per_1M_tokens_usd: PricingModel = Field(default_factory=PricingModel)

class ScribeConfig(BaseModel):
    retry_max: int = 3
    retry_delay_seconds: int = 5
    timeout: int = 600
    provider: str = "gemini"


class StageConfig(BaseModel):
    provider: str
    model: str

class ArtifactConfig(BaseModel):
    plugin: str
    template: str
    filename: Optional[str] = None

class OutputConfig(BaseModel):
    artifacts: List[ArtifactConfig] = Field(default_factory=list)

class ZettelkastenConfig(BaseModel):
    id_format: str = "%Y%m%d%H%M"
    filename_pattern: str = "{id} {slug}.md"
    tag_routes: Dict[str, str] = Field(default_factory=dict)

class ShelveConfig(BaseModel):
    enabled: bool = True
    root_path: Optional[str] = None 
    strategy: str = "timeline"
    zettelkasten: ZettelkastenConfig = Field(default_factory=ZettelkastenConfig)

class PathsConfig(BaseModel):
    input: str = "./scribe-in"
    work: str = "./scribe-work"
    results: str = "./scribe-out"

class CleanupConfig(BaseModel):
    failed_jobs_retention_days: int = 7
    completed_jobs_retention_days: int = 1
    auto_cleanup_enabled: bool = True

class JobConfiguration(BaseModel):
    language: str = "auto"
    compression_mode: str = "compressed"
    shelve: ShelveConfig = Field(default_factory=ShelveConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    debug: bool = False
    output_mode: str = "standard"
    scribe: ScribeConfig = Field(default_factory=ScribeConfig)
    transcribe: StageConfig
    refine: StageConfig
    # Providers config will be dynamic, but we can keep a generic dict here if needed,
    # or rely on the root ConfigContext to hold provider configs.
    # For job serialization, it's useful to snapshot the config used.
    providers: Dict[str, Any] = Field(default_factory=dict)

class ConfigContext(BaseModel):
    defaults: JobConfiguration
    providers: Dict[str, Any] = Field(default_factory=dict)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)

class AudioMeta(BaseModel):
    duration_seconds: float | None = None
    format: str | None = None
    bitrate: int | None = None
    file_size_bytes: int | None = None
    language: str | None = None
    creation_date: Optional[datetime] = None

class TokenStats(BaseModel):
    input: int = 0
    output: int = 0

class ProcessingStats(BaseModel):
    total_tokens: TokenStats = Field(default_factory=TokenStats)
    request_count: int = 0
    total_cost_usd: float = 0.0
    total_time_seconds: float = 0.0
    steps: List[Dict[str, Any]] = Field(default_factory=list)

class JobMeta(BaseModel):
    """Static metadata about the original file and job creation."""
    original_file: str
    original_file_creation_date: Optional[datetime] = None
    created_at: datetime
    audio: AudioMeta = Field(default_factory=AudioMeta)

class JobObject(BaseModel):
    """Dynamic state of the job, configuration, and processing results."""
    job_id: str
    created_at: datetime
    updated_at: datetime
    configuration: JobConfiguration
    current_stage: str = StageName.INGEST.value
    stages: Dict[StageName, StageState] = Field(default_factory=lambda: {
        stage: StageState() for stage in StageName
    })
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    ingest_result: Optional[Dict[str, Any]] = None
    raw_transcript_file: Optional[str] = None
    enriched_context_file: Optional[str] = None
    final_document_files: List[str] = Field(default_factory=list)
    processing: ProcessingStats = Field(default_factory=ProcessingStats)
