"""
Pytest configuration and fixtures.
"""

import pytest
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import psycopg2
from psycopg2.extensions import connection as PgConnection

from src.config import get_settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = get_settings()
    return settings


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "raw").mkdir()
    (data_dir / "raw" / "images").mkdir()
    (data_dir / "raw" / "telegram_messages").mkdir()
    return data_dir


@pytest.fixture
def mock_db_connection() -> Generator[MagicMock, None, None]:
    """Mock database connection."""
    conn = MagicMock(spec=PgConnection)
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = None
    yield conn


@pytest.fixture
def sample_telegram_message():
    """Sample Telegram message data."""
    return {
        "message_id": 12345,
        "channel_username": "test_channel",
        "channel_title": "Test Channel",
        "date": "2024-01-01T12:00:00+00:00",
        "text": "Test message",
        "views": 100,
        "forwards": 5,
        "has_media": False,
        "image_path": None,
    }


@pytest.fixture
def sample_yolo_detection():
    """Sample YOLO detection data."""
    return {
        "image_path": "images/test_channel/12345.jpg",
        "message_id": "12345",
        "channel": "test_channel",
        "detected_objects": "person;bottle",
        "confidence_scores": "0.85;0.75",
        "image_category": "promotional",
    }
