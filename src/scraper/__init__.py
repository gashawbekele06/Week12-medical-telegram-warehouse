"""Scraper module for Telegram data extraction."""

from .scraper import TelegramScraper, main
from .telegram_client import TelegramClientWrapper
from .message_processor import TelegramMessage, MessageProcessor

__all__ = [
    "TelegramScraper",
    "TelegramClientWrapper",
    "TelegramMessage",
    "MessageProcessor",
    "main"
]
