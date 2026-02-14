"""
Unit tests for configuration module.
"""

import pytest
from src.config import get_settings, DatabaseConfig, TelegramConfig, YOLOConfig


class TestDatabaseConfig:
    """Test cases for DatabaseConfig."""
    
    def test_database_url_construction(self):
        """Test database URL is constructed correctly."""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass"
        )
        
        expected_url = "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert config.url == expected_url
    
    def test_async_url_construction(self):
        """Test async database URL is constructed correctly."""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass"
        )
        
        assert "postgresql+asyncpg://" in config.async_url


class TestTelegramConfig:
    """Test cases for TelegramConfig."""
    
    def test_api_id_validation(self):
        """Test that API ID validation works."""
        with pytest.raises(ValueError, match="TELEGRAM_API_ID must be set"):
            TelegramConfig(api_id=0, api_hash="test", phone="+1234567890")
    
    def test_api_hash_validation(self):
        """Test that API hash validation works."""
        with pytest.raises(ValueError, match="TELEGRAM_API_HASH must be set"):
            TelegramConfig(api_id=12345, api_hash="", phone="+1234567890")


class TestYOLOConfig:
    """Test cases for YOLOConfig."""
    
    def test_confidence_threshold_validation(self):
        """Test confidence threshold must be between 0 and 1."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            YOLOConfig(confidence_threshold=1.5)
        
        with pytest.raises(ValueError, match="between 0 and 1"):
            YOLOConfig(confidence_threshold=-0.1)
    
    def test_valid_confidence_threshold(self):
        """Test valid confidence thresholds."""
        config = YOLOConfig(confidence_threshold=0.5)
        assert config.confidence_threshold == 0.5


class TestSettings:
    """Test cases for main Settings."""
    
    def test_get_settings_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_settings_has_all_configs(self):
        """Test that settings contains all sub-configurations."""
        settings = get_settings()
        
        assert hasattr(settings, "database")
        assert hasattr(settings, "telegram")
        assert hasattr(settings, "yolo")
        assert hasattr(settings, "paths")
