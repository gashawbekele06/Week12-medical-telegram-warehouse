"""
Message processing and transformation logic.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from telethon.tl.types import Message

from src.utils import get_logger

logger = get_logger(__name__)


@dataclass
class TelegramMessage:
    """Structured representation of a Telegram message."""
    
    message_id: int
    channel_username: str
    channel_title: str
    date: str
    text: str
    views: int
    has_media: bool
    image_path: Optional[str] = None
    forwards: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_telethon_message(
        cls,
        message: Message,
        channel_username: str,
        channel_title: str,
        image_path: Optional[Path] = None
    ) -> 'TelegramMessage':
        """
        Create TelegramMessage from Telethon Message object.
        
        Args:
            message: Telethon message object
            channel_username: Channel username
            channel_title: Channel title
            image_path: Optional path to downloaded image
            
        Returns:
            TelegramMessage instance
        """
        return cls(
            message_id=message.id,
            channel_username=channel_username,
            channel_title=channel_title,
            date=message.date.isoformat() if message.date else "",
            text=message.message or "",
            views=getattr(message, "views", 0) or 0,
            forwards=getattr(message, "forwards", 0) or 0,
            has_media=bool(message.media),
            image_path=str(image_path) if image_path else None
        )


class MessageProcessor:
    """Processes and saves Telegram messages."""
    
    def __init__(self, messages_dir: Path):
        """
        Initialize message processor.
        
        Args:
            messages_dir: Directory to save messages
        """
        self.messages_dir = messages_dir
        self.messages_dir.mkdir(parents=True, exist_ok=True)
    
    def save_messages(
        self,
        messages: list[TelegramMessage],
        channel_username: str
    ) -> int:
        """
        Save messages to JSONL file organized by date.
        
        Args:
            messages: List of TelegramMessage objects
            channel_username: Channel username for file naming
            
        Returns:
            Number of messages saved
        """
        if not messages:
            return 0
        
        try:
            # Group messages by date
            messages_by_date: Dict[str, list[TelegramMessage]] = {}
            for msg in messages:
                if msg.date:
                    date_str = datetime.fromisoformat(msg.date).strftime("%Y-%m-%d")
                    if date_str not in messages_by_date:
                        messages_by_date[date_str] = []
                    messages_by_date[date_str].append(msg)
            
            # Save each date group
            total_saved = 0
            for date_str, date_messages in messages_by_date.items():
                save_dir = self.messages_dir / date_str
                save_dir.mkdir(parents=True, exist_ok=True)
                
                out_file = save_dir / f"{channel_username}.jsonl"
                with open(out_file, "a", encoding="utf-8") as f:
                    for msg in date_messages:
                        f.write(msg.to_json() + "\n")
                
                total_saved += len(date_messages)
                logger.debug(f"Saved {len(date_messages)} messages to {out_file}")
            
            return total_saved
            
        except Exception as e:
            logger.error(f"Failed to save messages: {e}")
            raise
    
    def load_messages(self, file_path: Path) -> list[TelegramMessage]:
        """
        Load messages from JSONL file.
        
        Args:
            file_path: Path to JSONL file
            
        Returns:
            List of TelegramMessage objects
        """
        messages = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        messages.append(TelegramMessage(**data))
            
            logger.debug(f"Loaded {len(messages)} messages from {file_path}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to load messages from {file_path}: {e}")
            return []
