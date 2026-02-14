"""
Refactored Telegram scraper with type safety and modular design.
"""

import asyncio
from pathlib import Path
from typing import List, Optional

from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import MessageMediaPhoto
from tqdm import tqdm

from src.config import get_settings
from src.utils import get_logger
from .telegram_client import TelegramClientWrapper
from .message_processor import TelegramMessage, MessageProcessor

logger = get_logger(__name__)


class TelegramScraper:
    """
    Main scraper class for extracting messages from Telegram channels.
    """
    
    def __init__(self):
        """Initialize scraper with configuration."""
        settings = get_settings()
        self.config = settings.telegram
        self.paths = settings.paths
        
        self.client_wrapper = TelegramClientWrapper()
        self.message_processor = MessageProcessor(self.paths.messages_dir)
    
    async def scrape_channel(
        self,
        username: str,
        limit: Optional[int] = None
    ) -> int:
        """
        Scrape messages from a single channel.
        
        Args:
            username: Channel username
            limit: Optional limit on number of messages to scrape
            
        Returns:
            Number of messages scraped
        """
        logger.info(f"🚀 Starting scrape for: {username}")
        
        # Resolve entity
        entity = await self.client_wrapper.resolve_entity(username)
        if not entity:
            logger.error(f"Failed to resolve entity for {username}")
            return 0
        
        channel_title = getattr(entity, "title", username)
        offset_id = 0
        total_saved = 0
        messages_scraped = 0
        
        while True:
            try:
                # Fetch message history
                history = await self.client_wrapper.client(GetHistoryRequest(
                    peer=entity,
                    offset_id=offset_id,
                    offset_date=None,
                    add_offset=0,
                    limit=self.config.limit_per_request,
                    max_id=0,
                    min_id=0,
                    hash=0,
                ))
                
                if not history.messages:
                    break
                
                # Process messages
                batch_messages: List[TelegramMessage] = []
                
                for message in tqdm(
                    history.messages,
                    desc=f"Processing {username}",
                    leave=False
                ):
                    image_path = None
                    
                    # Download media if present
                    if isinstance(message.media, MessageMediaPhoto):
                        img_path = self.paths.images_dir / username / f"{message.id}.jpg"
                        success = await self.client_wrapper.download_media_with_retry(
                            message,
                            img_path
                        )
                        if success:
                            image_path = img_path
                    
                    # Create structured message
                    telegram_msg = TelegramMessage.from_telethon_message(
                        message,
                        username,
                        channel_title,
                        image_path
                    )
                    batch_messages.append(telegram_msg)
                
                # Save batch
                if batch_messages:
                    saved = self.message_processor.save_messages(
                        batch_messages,
                        username
                    )
                    total_saved += saved
                
                messages_scraped += len(history.messages)
                offset_id = history.messages[-1].id
                
                # Check limit
                if limit and messages_scraped >= limit:
                    logger.info(f"Reached message limit ({limit}) for {username}")
                    break
                
                # Check if we've reached the end
                if len(history.messages) < self.config.limit_per_request:
                    break
                
                # Rate limiting
                await asyncio.sleep(self.config.sleep_delay)
                
            except FloodWaitError as e:
                logger.warning(f"⏳ Flood wait {e.seconds}s — pausing")
                await asyncio.sleep(e.seconds)
            
            except Exception as e:
                logger.error(f"⚠️ Error scraping {username}: {e}", exc_info=True)
                break
        
        logger.info(f"✅ Finished {username}: {total_saved} messages saved")
        return total_saved
    
    async def scrape_all_channels(
        self,
        channels: Optional[List[str]] = None
    ) -> dict[str, int]:
        """
        Scrape all configured channels.
        
        Args:
            channels: Optional list of channels to scrape (defaults to config)
            
        Returns:
            Dictionary mapping channel names to message counts
        """
        if channels is None:
            channels = self.config.channels
        
        results = {}
        
        async with self.client_wrapper:
            for channel in channels:
                try:
                    count = await self.scrape_channel(channel)
                    results[channel] = count
                    await asyncio.sleep(2)  # Delay between channels
                except Exception as e:
                    logger.error(f"Failed to scrape {channel}: {e}")
                    results[channel] = 0
        
        return results


async def main() -> None:
    """Main entry point for scraper."""
    scraper = TelegramScraper()
    results = await scraper.scrape_all_channels()
    
    total = sum(results.values())
    logger.info(f"\n{'='*50}")
    logger.info(f"Scraping complete! Total messages: {total}")
    logger.info(f"{'='*50}")
    
    for channel, count in results.items():
        logger.info(f"  {channel}: {count} messages")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scraper stopped by user")
    except Exception as e:
        logger.error(f"Scraper failed: {e}", exc_info=True)
