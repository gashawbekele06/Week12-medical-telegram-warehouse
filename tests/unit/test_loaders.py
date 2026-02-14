"""
Unit tests for data loaders.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.loaders.load_raw_to_pg import RawDataLoader, RawMessage
from src.loaders.load_yolo_to_pg import YOLODetectionLoader, YOLODetection


class TestRawMessage:
    """Test cases for RawMessage dataclass."""
    
    def test_to_tuple(self, sample_telegram_message):
        """Test conversion to tuple for database insertion."""
        msg = RawMessage(**sample_telegram_message)
        tuple_data = msg.to_tuple()
        
        assert tuple_data[0] == 12345  # message_id
        assert tuple_data[1] == "test_channel"  # channel_username
        assert len(tuple_data) == 9


class TestRawDataLoader:
    """Test cases for RawDataLoader."""
    
    @pytest.fixture
    def loader(self, temp_data_dir):
        """Create loader instance."""
        with patch("src.loaders.load_raw_to_pg.get_settings") as mock_settings:
            settings = MagicMock()
            settings.paths.messages_dir = temp_data_dir / "raw" / "telegram_messages"
            mock_settings.return_value = settings
            return RawDataLoader()
    
    def test_load_file(self, loader, temp_data_dir, sample_telegram_message):
        """Test loading a single JSONL file."""
        # Create test file
        messages_dir = temp_data_dir / "raw" / "telegram_messages"
        messages_dir.mkdir(parents=True, exist_ok=True)
        test_file = messages_dir / "test.jsonl"
        
        with open(test_file, "w") as f:
            f.write(json.dumps(sample_telegram_message) + "\n")
        
        # Mock database connection
        with patch("src.loaders.load_raw_to_pg.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            count = loader.load_file(test_file)
            assert count == 1


class TestYOLODetection:
    """Test cases for YOLODetection dataclass."""
    
    def test_to_tuple(self, sample_yolo_detection):
        """Test conversion to tuple for database insertion."""
        detection = YOLODetection(**sample_yolo_detection)
        tuple_data = detection.to_tuple()
        
        assert tuple_data[1] == "12345"  # message_id
        assert tuple_data[2] == "test_channel"  # channel
        assert tuple_data[5] == "promotional"  # image_category
        assert len(tuple_data) == 6
