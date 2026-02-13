"""
Load YOLO detection results to PostgreSQL (robust version)
Run: uv run python src/load_yolo_to_pg.py
"""

import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME", "medical_warehouse"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", 5432)
)
cur = conn.cursor()

# Create table fresh (drops if exists)
cur.execute("""
DROP TABLE IF EXISTS raw.yolo_detections CASCADE;

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE raw.yolo_detections (
    message_id       TEXT PRIMARY KEY,
    channel_name     TEXT,
    image_path       TEXT,
    image_category   TEXT,
    detected_objects TEXT,           -- changed to TEXT for simple string storage
    confidence_scores TEXT,
    processed_at     TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
""")

df = pd.read_csv("data/yolo_detections.csv")

inserted = 0
for _, row in df.iterrows():
    cur.execute("""
    INSERT INTO raw.yolo_detections 
        (message_id, channel_name, image_path, image_category, detected_objects, confidence_scores)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (message_id) DO NOTHING;
    """, (
        row["message_id"],
        row["channel"],
        row["image_path"],
        row["image_category"],
        row["detected_objects"],
        row["confidence_scores"]
    ))
    inserted += cur.rowcount

conn.commit()
cur.close()
conn.close()

print(f"Loaded {inserted} rows into raw.yolo_detections")