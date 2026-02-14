"""
Centralized configuration management using Pydantic for type safety.
Supports environment-based configuration with validation.
"""

import os
from pathlib import Path
from typing import List, Optional
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class DatabaseConfig(BaseSettings):
    """Database connection configuration."""
    
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="medical_warehouse", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(default="postgres", description="Database password")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        case_sensitive=False
    )
    
    @property
    def url(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    @property
    def async_url(self) -> str:
        """Construct async database URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class TelegramConfig(BaseSettings):
    """Telegram API configuration."""
    
    api_id: int = Field(description="Telegram API ID")
    api_hash: str = Field(description="Telegram API hash")
    phone: str = Field(description="Phone number for authentication")
    session_name: str = Field(default="medical_scraper_session", description="Session name")
    
    # Scraping parameters
    channels: List[str] = Field(
        default=[
            "CheMed123",
            "lobelia4cosmetics",
            "tikvahpharma",
            "ethiopharmaceutical",
            "yenehealth",
        ],
        description="List of channels to scrape"
    )
    limit_per_request: int = Field(default=120, description="Messages per request")
    sleep_delay: int = Field(default=2, description="Delay between requests (seconds)")
    
    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM_",
        case_sensitive=False
    )
    
    @field_validator("api_id")
    @classmethod
    def validate_api_id(cls, v: int) -> int:
        if v == 0:
            raise ValueError("TELEGRAM_API_ID must be set")
        return v
    
    @field_validator("api_hash")
    @classmethod
    def validate_api_hash(cls, v: str) -> str:
        if not v:
            raise ValueError("TELEGRAM_API_HASH must be set")
        return v


class YOLOConfig(BaseSettings):
    """YOLO detection configuration."""
    
    model_name: str = Field(default="yolov8n.pt", description="YOLO model file")
    confidence_threshold: float = Field(default=0.25, description="Detection confidence threshold")
    batch_size: int = Field(default=16, description="Batch size for processing")
    
    # Classification categories
    product_keywords: List[str] = Field(
        default=[
            "bottle", "cup", "bowl", "cell phone", "book", "vase", "scissors",
            "teddy bear", "hair drier", "toothbrush", "remote", "keyboard", "mouse",
            "laptop", "tv", "microwave", "oven", "toaster", "sink", "refrigerator"
        ],
        description="Keywords for product classification"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="YOLO_",
        case_sensitive=False
    )
    
    @field_validator("confidence_threshold")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence threshold must be between 0 and 1")
        return v


class PathConfig(BaseSettings):
    """File system paths configuration."""
    
    data_root: Path = Field(default=Path("data/raw"), description="Root data directory")
    images_dir: Path = Field(default=Path("data/raw/images"), description="Images directory")
    messages_dir: Path = Field(default=Path("data/raw/telegram_messages"), description="Messages directory")
    logs_dir: Path = Field(default=Path("logs"), description="Logs directory")
    yolo_output: Path = Field(default=Path("data/yolo_detections.csv"), description="YOLO output CSV")
    
    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        for path in [self.data_root, self.images_dir, self.messages_dir, self.logs_dir]:
            path.mkdir(parents=True, exist_ok=True)
        self.yolo_output.parent.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment
    environment: str = Field(default="development", description="Environment (development/staging/production)")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    yolo: YOLOConfig = Field(default_factory=YOLOConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="API worker processes")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
        protected_namespaces=('settings_',)  # Fix model_ namespace warning
    )
    
    def model_post_init(self, __context) -> None:
        """Post-initialization: ensure directories exist."""
        self.paths.ensure_directories()


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache to ensure singleton pattern.
    """
    return Settings()


# Constants
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2
REQUEST_TIMEOUT = 30
BATCH_SIZE = 1000
