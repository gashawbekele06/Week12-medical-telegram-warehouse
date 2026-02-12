"""
Load raw Telegram JSONL files into PostgreSQL raw.telegram_messages
Usage: uv run python src/load_raw_to_pg.py
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Tuple

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from tqdm import tqdm

load_dotenv()

# ─── CONFIG ─────────────────────────────────────────────────────────────────────

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "medical_warehouse")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DATA_ROOT = Path("data/raw")
MESSAGES_DIR = DATA_ROOT / "telegram_messages"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ─── DATABASE CONNECTION ────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )

# ─── CREATE TABLE IF NOT EXISTS ─────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;

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
"""

# ─── LOAD ONE FILE ──────────────────────────────────────────────────────────────

def load_file(file_path: Path, conn) -> int:
    inserted = 0
    batch: List[Tuple] = []

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
                batch.append((
                    msg.get("message_id"),
                    msg.get("channel_username"),
                    msg.get("channel_title"),
                    msg.get("date"),
                    msg.get("text"),
                    msg.get("views"),
                    msg.get("forwards"),
                    msg.get("has_media"),
                    msg.get("image_path"),
                ))
            except json.JSONDecodeError as e:
                logger.warning(f"JSON error in {file_path}: {e} - skipping line")

    if batch:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO raw.telegram_messages (
                    message_id, channel_username, channel_title, date, text,
                    views, forwards, has_media, image_path
                ) VALUES %s
                ON CONFLICT DO NOTHING;
                """,
                batch,
            )
            inserted = cur.rowcount

    return inserted

# ─── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    total_inserted = 0

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        logger.info("Table raw.telegram_messages ready")

        jsonl_files = list(MESSAGES_DIR.rglob("*.jsonl"))
        logger.info(f"Found {len(jsonl_files)} JSONL files to load")

        for file_path in tqdm(jsonl_files, desc="Loading files"):
            inserted = load_file(file_path, conn)
            total_inserted += inserted
            logger.info(f"Loaded {inserted} rows from {file_path.name}")

        conn.commit()
        logger.info(f"Total rows inserted/updated: {total_inserted:,}")

    except Exception as e:
        logger.error(f"Load failed: {str(e)}", exc_info=True)
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()