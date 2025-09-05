"""Centralized configuration for Email Sync System using Pydantic Settings.

This replaces scattered config.py files across services with type-safe,
validated configuration management.
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """
    Database configuration.
    """

    # Main database path (moved to system_data)
    emails_db_path: str = Field(default="data/system_data/emails.db", env="EMAILS_DB_PATH")
    content_db_path: str = Field(default="data/system_data/content.db", env="CONTENT_DB_PATH")

    # Connection settings
    max_connections: int = Field(default=5, env="DB_MAX_CONNECTIONS")
    busy_timeout: int = Field(default=5000, env="DB_BUSY_TIMEOUT")  # milliseconds

    @field_validator("emails_db_path", "content_db_path")
    @classmethod
    def validate_db_paths(cls, v):
        """
        Ensure database directories exist.
        """
        path = Path(v)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)


class GmailSettings(BaseSettings):
    """
    Gmail API configuration.
    """

    credentials_path: str = Field(default=".config/credentials.json", env="GMAIL_CREDENTIALS_PATH")
    token_path: str = Field(default=".config/token.json", env="GMAIL_TOKEN_PATH")

    # Sender filters
    preferred_senders: list[str] = Field(
        default=[
            "jenbarreda@yahoo.com",
            "518stoneman@gmail.com",
            "brad_martinez@att.net",
            "vicki_martinez@att.net",
            "dteshale@teshalelaw.com",
            "info@dignitylawgroup.com",
            "joe@kellenerlaw.com",
            "sally@lotuspropertyservices.net",
            "grace@lotuspropertyservices.net",
            "gaildcalhoun@gmail.com",
        ]
    )

    max_results: int = Field(default=500, env="GMAIL_MAX_RESULTS")
    batch_size: int = Field(default=50, env="GMAIL_BATCH_SIZE")


class EntitySettings(BaseSettings):
    """
    Entity extraction configuration.
    """

    spacy_model: str = Field(default="en_core_web_sm", env="ENTITY_SPACY_MODEL")
    batch_size: int = Field(default=100, env="ENTITY_BATCH_SIZE")
    confidence_threshold: float = Field(default=0.5, env="ENTITY_CONFIDENCE_THRESHOLD")

    entity_types: list[str] = Field(
        default=[
            "PERSON",
            "ORG",
            "GPE",
            "MONEY",
            "DATE",
            "TIME",
            "PERCENT",
            "PRODUCT",
            "EVENT",
            "FAC",
            "LOC",
            "NORP",
            "WORK_OF_ART",
            "LAW",
            "LANGUAGE",
            "QUANTITY",
            "ORDINAL",
            "CARDINAL",
        ]
    )

    max_text_length: int = Field(default=10000, env="ENTITY_MAX_TEXT_LENGTH")
    enable_normalization: bool = Field(default=True, env="ENTITY_NORMALIZE")

    @field_validator("confidence_threshold")
    @classmethod
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")
        return v


class VectorSettings(BaseSettings):
    """
    Vector store and embeddings configuration.
    """

    # Qdrant connection
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_timeout: float = Field(default=60.0, env="QDRANT_TIMEOUT")

    # Embedding model
    # Default to the active 1024D LegalBERT large used by the pipeline
    embedding_model: str = Field(default="pile-of-law/legalbert-large-1.7M-2", env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1024, env="EMBEDDING_DIMENSION")
    batch_size: int = Field(default=32, env="VECTOR_BATCH_SIZE")

    # Collection names
    # Active unified chunk collection
    chunk_collection: str = Field(default="vectors_v2", env="QDRANT_CHUNK_COLLECTION")


class APISettings(BaseSettings):
    """
    External API configuration.
    """

    # OpenAI (for transcription)
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="whisper-1", env="OPENAI_WHISPER_MODEL")

    # Legal BERT API (if external)
    legal_bert_api_url: str | None = Field(default=None, env="LEGAL_BERT_API_URL")
    legal_bert_api_key: str | None = Field(default=None, env="LEGAL_BERT_API_KEY")


class PathSettings(BaseSettings):
    """
    File and directory paths.
    """

    # Data directories
    data_root: str = Field(default="data", env="DATA_ROOT")
    system_data: str = Field(default="data/system_data", env="SYSTEM_DATA_PATH")
    # USER_DATA REMOVED - Case-specific: data/Stoneman_dispute/user_data (CLI/service defaults)

    # Log directories
    logs_path: str = Field(default="logs", env="LOGS_PATH")

    # Config directory
    config_dir: str = Field(default=".config", env="CONFIG_DIR")

    @field_validator(
        "data_root",
        "system_data",
        "logs_path",
        "config_dir",
    )
    @classmethod
    def ensure_directories_exist(cls, v):
        """
        Create directories if they don't exist.
        """
        Path(v).mkdir(parents=True, exist_ok=True)
        return v


class LoggingSettings(BaseSettings):
    """
    Logging configuration.
    """

    level: str = Field(default="INFO", env="LOG_LEVEL")
    format_string: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        env="LOG_FORMAT",
    )
    rotation: str = Field(default="500 MB", env="LOG_ROTATION")
    compression: str = Field(default="zip", env="LOG_COMPRESSION")
    retention: str = Field(default="10 days", env="LOG_RETENTION")


class SystemSettings(BaseSettings):
    """
    System-related files configuration.
    """

    # Sequential thinking storage
    sequential_thinking_dir: str = Field(
        default="data/system_data/sequential_thinking", env="SEQUENTIAL_THINKING_DIR"
    )

    # System cache and temporary files
    cache_dir: str = Field(default="data/system_data/cache", env="SYSTEM_CACHE_DIR")
    temp_dir: str = Field(default="data/system_data/temp", env="SYSTEM_TEMP_DIR")

    # Lock files and process management
    locks_dir: str = Field(default="data/system_data/locks", env="SYSTEM_LOCKS_DIR")

    @field_validator("sequential_thinking_dir", "cache_dir", "temp_dir", "locks_dir")
    @classmethod
    def ensure_system_directories_exist(cls, v):
        """
        Create system directories if they don't exist.
        """
        Path(v).mkdir(parents=True, exist_ok=True)
        return v


class Settings(BaseSettings):
    """
    Main application settings combining all subsystems.
    """

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # Subsystem settings
    database: DatabaseSettings = DatabaseSettings()
    gmail: GmailSettings = GmailSettings()
    entity: EntitySettings = EntitySettings()
    vector: VectorSettings = VectorSettings()
    api: APISettings = APISettings()
    paths: PathSettings = PathSettings()
    logging: LoggingSettings = LoggingSettings()
    system: SystemSettings = SystemSettings()

    class Config:
        # Prefer container/ops path, then project .env, then user Secrets
        env_file = ["/secrets/.env", ".env", "~/Secrets/.env"]
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


class SemanticSettings(BaseSettings):
    """
    Semantic enrichment pipeline configuration.
    """

    # Master switch for semantic processing on ingestion
    semantics_on_ingest: bool = Field(default=True, env="SEMANTICS_ON_INGEST")

    # Steps to run in order
    semantics_steps: list[str] = Field(
        default=["summary", "entities", "embeddings", "timeline"], env="SEMANTICS_STEPS"
    )

    # Batch processing settings
    semantics_max_batch: int = Field(default=200, env="SEMANTICS_MAX_BATCH")
    semantics_timeout_s: int = Field(default=20, env="SEMANTICS_TIMEOUT_S")  # per step

    # Cache settings
    entity_cache_days: int = Field(default=7, env="ENTITY_CACHE_DAYS")

    class Config:
        env_prefix = "SEMANTIC_"


# Global settings instance
settings = Settings()
semantic_settings = SemanticSettings()


def get_db_path() -> str:
    """
    Get the database path from settings or environment.
    """
    return settings.database.emails_db_path
