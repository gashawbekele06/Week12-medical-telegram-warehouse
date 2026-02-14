"""
Telegram client wrapper with retry logic and error handling.
"""

import asyncio
from typing import Optional, List
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    UsernameNotOccupiedError,
    UsernameInvalidError,
    ChannelPrivateError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Channel, Chat

from src.config import get_settings
from src.utils import get_logger

logger = get_logger(__name__)


class TelegramClientWrapper:
    """
    Wrapper for Telegram client with authentication and entity resolution.
    """
    
    def __init__(self):
        """Initialize Telegram client with configuration."""
        settings = get_settings()
        self.config = settings.telegram
        
        self.client = TelegramClient(
            self.config.session_name,
            self.config.api_id,
            self.config.api_hash
        )
        self._authenticated = False
    
    async def __aenter__(self) -> 'TelegramClientWrapper':
        """Async context manager entry."""
        await self.authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def authenticate(self) -> None:
        """
        Authenticate with Telegram API.
        
        Raises:
            RuntimeError: If authentication fails
        """
        try:
            await self.client.start(phone=self.config.phone)
            self._authenticated = True
            logger.info("Telegram client authenticated successfully")
        except Exception as e:
            logger.error(f"Failed to authenticate Telegram client: {e}")
            raise RuntimeError(f"Authentication failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        if self._authenticated:
            await self.client.disconnect()
            self._authenticated = False
            logger.info("Telegram client disconnected")
    
    async def resolve_entity(self, username: str) -> Optional[Channel | Chat]:
        """
        Smart entity resolution with multiple fallback strategies.
        
        Args:
            username: Channel or group username
            
        Returns:
            Resolved entity or None if resolution fails
        """
        # Try @username format
        try:
            entity = await self.client.get_entity("@" + username)
            logger.debug(f"Resolved entity using @{username}")
            return entity
        except Exception:
            pass
        
        # Try t.me link format
        try:
            entity = await self.client.get_entity(f"https://t.me/{username}")
            logger.debug(f"Resolved entity using t.me link")
            return entity
        except Exception:
            pass
        
        # Try joining and then resolving
        try:
            await self.client(JoinChannelRequest(username))
            await asyncio.sleep(1)  # Give time for join to process
            entity = await self.client.get_entity(f"https://t.me/{username}")
            logger.info(f"Joined and resolved entity: {username}")
            return entity
        except Exception:
            pass
        
        # Final attempt with @username after join
        try:
            entity = await self.client.get_entity("@" + username)
            logger.debug(f"Resolved entity after join using @{username}")
            return entity
        except Exception as e:
            logger.error(f"Failed to resolve entity '{username}': {e}")
            return None
    
    async def download_media_with_retry(
        self,
        message,
        file_path: Path,
        max_retries: int = 3
    ) -> bool:
        """
        Download media with retry logic.
        
        Args:
            message: Telegram message object
            file_path: Destination file path
            max_retries: Maximum retry attempts
            
        Returns:
            True if download successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                await self.client.download_media(message.media, file=file_path)
                logger.debug(f"Downloaded media to {file_path}")
                return True
            except FloodWaitError as e:
                wait_time = e.seconds
                logger.warning(f"Flood wait {wait_time}s during media download")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Max retries reached for media download")
                    return False
            except Exception as e:
                logger.error(f"Failed to download media (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return False
        
        return False
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._authenticated
