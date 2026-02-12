
import asyncio
import json
import logging
import os

from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    UsernameNotOccupiedError,
    UsernameInvalidError,
    ChannelPrivateError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import MessageMediaPhoto
from tqdm import tqdm

# ───────────────────────────
# CONFIG
# ───────────────────────────
load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE = os.getenv("TELEGRAM_PHONE", "")

if not API_ID or not API_HASH:
    raise ValueError("API credentials missing in .env")

SESSION_NAME = "medical_scraper_session"

# Correct channel usernames (verified)
CHANNELS = [
    "CheMed123",
    "lobelia4cosmetics",
    "tikvahpharma",
    "ethiopharmaceutical",
    "yenehealth",
]

# Storage
DATA_ROOT = Path("data/raw")
IMAGES_DIR = DATA_ROOT / "images"
MESSAGES_DIR = DATA_ROOT / "telegram_messages"
LOGS_DIR = Path("logs")

for d in [DATA_ROOT, IMAGES_DIR, MESSAGES_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "scraper.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

LIMIT_PER_REQUEST = 120
SLEEP_DELAY = 2


# ───────────────────────────
# AUTHENTICATE
# ───────────────────────────
async def get_client():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(phone=PHONE)
    logger.info("Client authenticated successfully")
    return client


# ───────────────────────────
# SMART RESOLVER (fixes your errors)
# ───────────────────────────
async def smart_resolve(client: TelegramClient, username: str):
    # Try @username
    try:
        return await client.get_entity("@" + username)
    except:
        pass

    # Try link form
    try:
        return await client.get_entity(f"https://t.me/{username}")
    except:
        pass

    # Try auto-join (works for groups + channels)
    try:
        await client(JoinChannelRequest(username))
        return await client.get_entity(f"https://t.me/{username}")
    except:
        pass

    # Try again after join using @username
    try:
        return await client.get_entity("@" + username)
    except:
        logger.error(f"❌ Cannot resolve entity for '{username}'")
        return None


# ───────────────────────────
# SCRAPE ONE CHANNEL/GROUP
# ───────────────────────────
async def scrape_channel(client: TelegramClient, username: str):
    logger.info(f"🚀 Starting scrape for: {username}")

    entity = await smart_resolve(client, username)
    if not entity:
        return

    channel_title = getattr(entity, "title", username)
    offset_id = 0
    total_saved = 0

    while True:
        try:
            history = await client(GetHistoryRequest(
                peer=entity,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=LIMIT_PER_REQUEST,
                max_id=0,
                min_id=0,
                hash=0,
            ))

            if not history.messages:
                break

            msgs = []

            for message in tqdm(history.messages, desc=f"{username}", leave=False):

                msg_json = {
                    "message_id": message.id,
                    "channel_username": username,
                    "channel_title": channel_title,
                    "date": message.date.isoformat() if message.date else "",
                    "text": message.message or "",
                    "views": getattr(message, "views", 0),
                    "has_media": bool(message.media),
                    "image_path": None,
                }

                # Download media
                if isinstance(message.media, MessageMediaPhoto):
                    img_path = IMAGES_DIR / username / f"{message.id}.jpg"
                    img_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        await client.download_media(message.media, file=img_path)
                        msg_json["image_path"] = str(img_path)
                    except Exception as e:
                        logger.error(f"⚠️ Failed to download image {message.id}: {e}")

                msgs.append(msg_json)

            # SAVE MESSAGES
            if msgs:
                date_folder = datetime.fromisoformat(msgs[0]["date"]).strftime("%Y-%m-%d")
                save_dir = MESSAGES_DIR / date_folder
                save_dir.mkdir(parents=True, exist_ok=True)

                out_file = save_dir / f"{username}.jsonl"
                with open(out_file, "a", encoding="utf-8") as f:
                    for m in msgs:
                        f.write(json.dumps(m, ensure_ascii=False) + "\n")

            total_saved += len(msgs)
            offset_id = history.messages[-1].id

            if len(history.messages) < LIMIT_PER_REQUEST:
                break

            await asyncio.sleep(SLEEP_DELAY)

        except FloodWaitError as e:
            logger.warning(f"⏳ Flood wait {e.seconds}s — pausing")
            await asyncio.sleep(e.seconds)

        except Exception as e:
            logger.error(f"⚠️ Error scraping {username}: {e}")
            break

    logger.info(f"✅ Finished {username}: {total_saved} messages saved.")


# ───────────────────────────
# MAIN
# ───────────────────────────
async def main():
    async with await get_client() as client:
        for ch in CHANNELS:
            await scrape_channel(client, ch)
            await asyncio.sleep(2)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scraper stopped by user.")
