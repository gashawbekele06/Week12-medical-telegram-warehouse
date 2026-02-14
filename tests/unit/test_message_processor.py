"""
Unit tests for message processor.
"""

import json
import pytest
from pathlib import Path
from src.scraper.message_processor import TelegramMessage, MessageProcessor


class TestTelegramMessage:
    """Test cases for TelegramMessage dataclass."""
    
    def test_to_dict(self, sample_telegram_message):
        """Test conversion to dictionary."""
        msg = TelegramMessage(**sample_telegram_message)
        msg_dict = msg.to_dict()
        
        assert msg_dict["message_id"] == 12345
        assert msg_dict["channel_username"] == "test_channel"
        assert msg_dict["text"] == "Test message"
    
    def test_to_json(self, sample_telegram_message):
        """Test conversion to JSON."""
        msg = TelegramMessage(**sample_telegram_message)
        json_str = msg.to_json()
        
        parsed = json.loads(json_str)
        assert parsed["message_id"] == 12345
        assert parsed["views"] == 100


class TestMessageProcessor:
    """Test cases for MessageProcessor."""
    
    @pytest.fixture
    def processor(self, temp_data_dir):
        """Create message processor instance."""
        messages_dir = temp_data_dir / "raw" / "telegram_messages"
        return MessageProcessor(messages_dir)
    
    def test_save_messages(self, processor, sample_telegram_message):
        """Test saving messages to JSONL."""
        msg = TelegramMessage(**sample_telegram_message)
        count = processor.save_messages([msg], "test_channel")
        
        assert count == 1
        
        # Verify file was created
        date_dir = processor.messages_dir / "2024-01-01"
        assert date_dir.exists()
        
        jsonl_file = date_dir / "test_channel.jsonl"
        assert jsonl_file.exists()
        
        # Verify content
        with open(jsonl_file, "r") as f:
            line = f.readline()
            data = json.loads(line)
            assert data["message_id"] == 12345
    
    def test_save_empty_messages(self, processor):
        """Test saving empty message list."""
        count = processor.save_messages([], "test_channel")
        assert count == 0
    
    def test_load_messages(self, processor, sample_telegram_message):
        """Test loading messages from JSONL."""
        # First save a message
        msg = TelegramMessage(**sample_telegram_message)
        processor.save_messages([msg], "test_channel")
        
        # Then load it
        jsonl_file = processor.messages_dir / "2024-01-01" / "test_channel.jsonl"
        loaded_messages = processor.load_messages(jsonl_file)
        
        assert len(loaded_messages) == 1
        assert loaded_messages[0].message_id == 12345
        assert loaded_messages[0].channel_username == "test_channel"
