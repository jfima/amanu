from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field

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

class JobState(BaseModel):
    job_id: str
    original_file: str
    created_at: datetime
    updated_at: datetime
    current_stage: str  # Can be "commissioned" or one of StageName values
    stages: Dict[StageName, StageState] = Field(default_factory=lambda: {
        stage: StageState() for stage in StageName
    })
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    location: Optional[Path] = None # Path to job directory (not serialized by default if we exclude None)

class PricingModel(BaseModel):
    input: float
    output: float

class ModelContextWindow(BaseModel):
    input_tokens: int
    output_tokens: int

class ModelSpec(BaseModel):
    name: str
    context_window: ModelContextWindow
    cost_per_1M_tokens_usd: PricingModel

class ModelPricing(BaseModel):
    # Legacy support for global pricing config
    transcribe_model_cost_per_1m_tokens: PricingModel
    refine_model_cost_per_1m_tokens: PricingModel

class ScribeConfig(BaseModel):
    retry_max: int = 3
    retry_delay_seconds: int = 5
    provider: str = "gemini" # Default provider

class StageConfig(BaseModel):
    provider: str
    model: str

class GeminiConfig(BaseModel):
    api_key: Optional[str] = None
    models: List[ModelSpec] = Field(default_factory=list)

class WhisperModelSpec(ModelSpec):
    path: str

class WhisperConfig(BaseModel):
    whisper_home: Optional[str] = None  # Path to whisper.cpp directory
    models: List[WhisperModelSpec] = Field(default_factory=list)

class ClaudeConfig(BaseModel):
    api_key: Optional[str] = None
    models: List[ModelSpec] = Field(default_factory=list)

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
    strategy: str = "timeline" # timeline, zettelkasten, flat
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
    # Deprecated: template: str (Moved to output.artifacts)
    language: str
    compression_mode: str = "compressed"  # Options: "original", "compressed", "optimized"
    shelve: ShelveConfig = Field(default_factory=ShelveConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    debug: bool = False
    scribe: ScribeConfig = Field(default_factory=ScribeConfig)
    transcribe: StageConfig
    refine: StageConfig

class ConfigContext(BaseModel):
    defaults: JobConfiguration
    available_models: List[ModelSpec] # Keep for backward compatibility or general reference
    providers: Dict[str, Any] = Field(default_factory=dict) # gemini -> GeminiConfig, etc.
    paths: PathsConfig = Field(default_factory=PathsConfig)
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)

class AudioMeta(BaseModel):
    duration_seconds: float | None = None
    format: str | None = None
    bitrate: int | None = None
    file_size_bytes: int | None = None
    language: str | None = None

class TokenStats(BaseModel):
    input: int = 0
    output: int = 0

class ProcessingStats(BaseModel):
    stages_completed: List[str] = Field(default_factory=list)
    total_tokens: TokenStats = Field(default_factory=TokenStats)
    request_count: int = 0
    total_cost_usd: float = 0.0
    total_time_seconds: float = 0.0
    steps: List[Dict[str, Any]] = Field(default_factory=list)

class JobMeta(BaseModel):
    job_id: str
    original_file: str
    created_at: datetime
    updated_at: datetime
    configuration: JobConfiguration
    audio: AudioMeta = Field(default_factory=AudioMeta)
    processing: ProcessingStats = Field(default_factory=ProcessingStats)
