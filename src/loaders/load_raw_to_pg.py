"""
Refactored data loader for raw Telegram messages to PostgreSQL.
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

from psycopg2.extras import execute_values
from tqdm import tqdm

from src.config import get_settings
from src.config.database import get_db_connection
from src.utils import get_logger

logger = get_logger(__name__)


@dataclass
class RawMessage:
    """Data model for raw message records."""
    
    message_id: int
    channel_username: str
    channel_title: str
    date: str
    text: str
    views: int
    forwards: int
    has_media: bool
    image_path: Optional[str]
    
    def to_tuple(self) -> Tuple:
        """Convert to tuple for database insertion."""
        return (
            self.message_id,
            self.channel_username,
            self.channel_title,
            self.date,
            self.text,
            self.views,
            self.forwards,
            self.has_media,
            self.image_path,
        )


class RawDataLoader:
    """Loads raw Telegram messages into PostgreSQL."""
    
    CREATE_SCHEMA_SQL = "CREATE SCHEMA IF NOT EXISTS raw;"
    
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS raw.telegram_messages (
        message_id       BIGINT,
        channel_username TEXT,
        channel_title    TEXT,
        date             TIMESTAMP WITH TIME ZONE,
        text             TEXT,
        views            INTEGER,
        forwards         INTEGER,
        has_media        BOOLEAN,
        image_path       TEXT,
        loaded_at        TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (message_id, channel_username)
    );
    
    CREATE INDEX IF NOT EXISTS idx_telegram_messages_channel 
        ON raw.telegram_messages(channel_username);
    CREATE INDEX IF NOT EXISTS idx_telegram_messages_date 
        ON raw.telegram_messages(date);
    """
    
    def __init__(self):
        """Initialize loader with configuration."""
        settings = get_settings()
        self.messages_dir = settings.paths.messages_dir
    
    def ensure_table_exists(self) -> None:
        """Create schema and table if they don't exist."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(self.CREATE_SCHEMA_SQL)
                    cursor.execute(self.CREATE_TABLE_SQL)
            logger.info("Table raw.telegram_messages ready")
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise
    
    def load_file(self, file_path: Path) -> int:
        """
        Load messages from a single JSONL file.
        
        Args:
            file_path: Path to JSONL file
            
        Returns:
            Number of rows inserted
        """
        batch: List[Tuple] = []
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        msg_data = json.loads(line)
                        message = RawMessage(
                            message_id=msg_data.get("message_id"),
                            channel_username=msg_data.get("channel_username"),
                            channel_title=msg_data.get("channel_title"),
                            date=msg_data.get("date"),
                            text=msg_data.get("text"),
                            views=msg_data.get("views", 0),
                            forwards=msg_data.get("forwards", 0),
                            has_media=msg_data.get("has_media", False),
                            image_path=msg_data.get("image_path"),
                        )
                        batch.append(message.to_tuple())
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON error in {file_path}: {e} - skipping line")
                    except Exception as e:
                        logger.warning(f"Error processing line in {file_path}: {e}")
            
            # Insert batch
            if batch:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        execute_values(
                            cursor,
                            """
                            INSERT INTO raw.telegram_messages (
                                message_id, channel_username, channel_title, date, text,
                                views, forwards, has_media, image_path
                            ) VALUES %s
                            ON CONFLICT (message_id, channel_username) DO UPDATE SET
                                views = EXCLUDED.views,
                                forwards = EXCLUDED.forwards,
                                loaded_at = CURRENT_TIMESTAMP;
                            """,
                            batch,
                        )
                        inserted = cursor.rowcount
                
                logger.debug(f"Loaded {inserted} rows from {file_path.name}")
                return inserted
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}")
            raise
    
    def load_all(self) -> int:
        """
        Load all JSONL files from messages directory.
        
        Returns:
            Total number of rows inserted
        """
        self.ensure_table_exists()
        
        jsonl_files = list(self.messages_dir.rglob("*.jsonl"))
        logger.info(f"Found {len(jsonl_files)} JSONL files to load")
        
        if not jsonl_files:
            logger.warning("No JSONL files found")
            return 0
        
        total_inserted = 0
        
        for file_path in tqdm(jsonl_files, desc="Loading files"):
            try:
                inserted = self.load_file(file_path)
                total_inserted += inserted
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                continue
        
        logger.info(f"✅ Total rows inserted/updated: {total_inserted:,}")
        return total_inserted


def main() -> None:
    """Main entry point for raw data loader."""
    try:
        loader = RawDataLoader()
        total = loader.load_all()
        logger.info(f"Load complete! {total} rows processed")
    except Exception as e:
        logger.error(f"Load failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
