from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

class StageName(str, Enum):
    SCOUT = "scout"
    PREP = "prep"
    SCRIBE = "scribe"
    REFINE = "refine"
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

class PathsConfig(BaseModel):
    input: str = "./scribe-in"
    work: str = "./scribe-work"
    results: str = "./scribe-out"

class CleanupConfig(BaseModel):
    failed_jobs_retention_days: int = 7
    completed_jobs_retention_days: int = 1
    auto_cleanup_enabled: bool = True

class JobConfiguration(BaseModel):
    template: str
    language: str
    compression_mode: str = "compressed"  # Options: "original", "compressed", "optimized"
    debug: bool = False
    scribe: ScribeConfig = Field(default_factory=ScribeConfig)
    transcribe: ModelSpec
    refine: ModelSpec

class ConfigContext(BaseModel):
    defaults: JobConfiguration
    available_models: List[ModelSpec]
    paths: PathsConfig = Field(default_factory=PathsConfig)
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)

class AudioMeta(BaseModel):
    duration_seconds: Optional[float] = None
    format: Optional[str] = None
    bitrate: Optional[int] = None
    file_size_bytes: Optional[int] = None

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
