"""
Centralized configuration management using Pydantic Settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List, Union
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Context-Aware Translation System"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = Field(default="development", env="APP_ENV")
    
    # Database
    # Default to a local SQLite DB for development if DATABASE_URL is not provided
    database_url: str = Field(
        default=f"sqlite:///{Path(__file__).resolve().parent.parent.parent}/database.db",
        env="DATABASE_URL",
    )
    pool_size: int = 5
    max_overflow: int = 10
    pool_pre_ping: bool = True
    
    # Storage
    storage_backend: str = "local"  # local, s3, gcs
    upload_directory: str = Field(default="uploads", env="UPLOAD_DIR")
    job_storage_base: str = Field(default="logs/jobs", env="JOB_STORAGE_BASE")
    max_file_size: int = 100_000_000  # 100MB
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [
            ".txt", ".md", ".pdf", ".docx", ".epub", 
            ".doc", ".odt", ".rtf"
        ]
    )
    
    # CORS
    cors_origins: Union[str, List[str]] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: List[str] = Field(default_factory=lambda: ["*"])
    
    # API Keys
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    # Optional in development; required only if using OpenRouter
    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    clerk_secret_key: str = Field(..., env="CLERK_SECRET_KEY")
    # Frontend-only; make optional for backend startup
    clerk_publishable_key: Optional[str] = Field(default=None, env="CLERK_PUBLISHABLE_KEY")
    admin_secret_key: str = Field(..., env="ADMIN_SECRET_KEY")
    
    # Redis (for Celery and Caching)
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_max_connections: int = 10
    cache_ttl: int = 3600  # 1 hour default cache TTL
    
    # Security
    # Provide a sensible default for local development
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10
    
    # File Processing
    chunk_size: int = 8192
    temp_directory: str = "/tmp/translation_temp"
    cleanup_interval: int = 3600  # Clean temp files every hour
    
    # Translation Settings
    default_model: str = Field(default="gemini-1.5-pro", env="DEFAULT_MODEL")
    illustration_model: str = Field(default="gemini-2.5-flash-image-preview", env="ILLUSTRATION_MODEL")
    max_retries: int = 3
    retry_delay: int = 1  # seconds
    request_timeout: int = 300  # 5 minutes
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = "json"  # json or text
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    enable_metrics: bool = Field(default=False, env="ENABLE_METRICS")
    metrics_endpoint: str = "/metrics"
    
    # S3 Storage (optional)
    s3_bucket: Optional[str] = Field(default=None, env="S3_BUCKET")
    s3_region: Optional[str] = Field(default="us-east-1", env="S3_REGION")
    s3_access_key: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    s3_secret_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    s3_endpoint_url: Optional[str] = Field(default=None, env="S3_ENDPOINT_URL")

    # S3 Task Output Persistence
    s3_task_persistence_enabled: bool = Field(default=False, env="S3_TASK_PERSISTENCE_ENABLED")
    s3_task_output_bucket: Optional[str] = Field(default=None, env="S3_TASK_OUTPUT_BUCKET")
    s3_compress_threshold_mb: int = Field(default=10, env="S3_COMPRESS_THRESHOLD_MB")
    s3_server_side_encryption: bool = Field(default=True, env="S3_SERVER_SIDE_ENCRYPTION")
    
    @field_validator("cors_origins", mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if not v:  # Handle empty string
                return ["http://localhost:3000"]
            return [origin.strip() for origin in v.split(",")]
        elif v is None:
            return ["http://localhost:3000"]
        return v
    
    @field_validator("upload_directory")
    @classmethod
    def ensure_upload_dir(cls, v):
        path = Path(v)
        if not path.is_absolute():
            path = Path(os.getcwd()) / path
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    @field_validator("temp_directory")
    @classmethod
    def ensure_temp_dir(cls, v):
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    @field_validator("job_storage_base")
    @classmethod
    def ensure_job_storage_dir(cls, v):
        path = Path(v)
        if not path.is_absolute():
            path = Path(os.getcwd()) / path
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the settings singleton instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    global _settings
    _settings = Settings()
    return _settings


# Environment-specific configuration loading
def load_environment_config(env: str = None) -> Settings:
    """Load environment-specific configuration."""
    if env:
        os.environ["APP_ENV"] = env
    
    settings = get_settings()
    
    # Apply environment-specific overrides
    if settings.is_production:
        settings.debug = False
        settings.log_level = "WARNING"
    elif settings.is_development:
        settings.debug = True
        settings.log_level = "DEBUG"
    elif settings.is_testing:
        settings.debug = True
        settings.log_level = "INFO"
        settings.database_url = "sqlite:///./test.db"
    
    return settings
