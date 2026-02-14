# Medical Telegram Warehouse Capstone Project

**10 Academy – Week 12 Capstone**  
**Author:** Gashaw  
**Date:** February 2026  

End-to-end data pipeline that:

1. Scrapes Ethiopian medical/pharmacy Telegram channels  
2. Loads raw messages into PostgreSQL  
3. Builds a star-schema warehouse with dbt  
4. Enriches messages with YOLOv8 object detection on images  
5. Exposes analytics via FastAPI REST API  
6. Orchestrates the full pipeline with Dagster (scheduled daily)

## Project Structure
├── api/                        # Task 4 – FastAPI analytical API
│   ├── init.py
│   ├── main.py
│   ├── database.py
│   ├── schemas.py
│   └── routers/
│       └── analytics.py
├── data/
│   ├── raw/
│   │   ├── images/             # Downloaded Telegram images
│   │   └── telegram_messages/  # NDJSON raw messages (date-partitioned)
│   └── yolo_detections.csv     # YOLO results
├── logs/                       # Logs from scraper, YOLO, etc.
├── medical_warehouse/          # Task 2 – dbt project
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/
│       └── marts/
├── src/                        # Python scripts
│   ├── scraper.py              # Task 1 – Telegram scraper
│   ├── load_raw_to_pg.py       # Task 1 – Load NDJSON to PostgreSQL
│   ├── yolo_detect.py          # Task 3 – YOLOv8 detection
│   └── load_yolo_to_pg.py      # Task 3 – Load detections to DB
├── pipeline.py                 # Task 5 – Dagster orchestration
├── .env                        # Environment variables (gitignore)
└── README.md                   # This file


## Prerequisites

- Ubuntu / Linux (or WSL on Windows)
- Python 3.10+
- PostgreSQL 14+ server running locally (port 5432)
- uv (preferred) or pip + virtualenv
- Telegram account + API credentials

## Installation

1. Clone the repository

```bash
git clone <your-repo-url>
cd Week12-medical-telegram-warehouse


## Prerequisites

- Ubuntu / Linux (or WSL on Windows)
- Python 3.10+
- PostgreSQL 14+ server running locally (port 5432)
- uv (preferred) or pip + virtualenv
- Telegram account + API credentials

## Installation

1. Clone the repository

```bash
git clone <your-repo-url>
cd Week12-medical-telegram-warehouse

uv sync

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=medical_warehouse
DB_USER=postgres
DB_PASSWORD=your_password_here

# Telegram API (from https://my.telegram.org/apps)
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
TELEGRAM_PHONE=+2519xxxxxxxx  # optional, used for login


# Running the Full Pipeline (Manual)
# Task 1 – Scrape & Load Raw Data

# Scrape channels (update CHANNELS list in src/scraper.py first)
uv run python src/scraper.py

# Load raw messages to PostgreSQL
uv run python src/load_raw_to_pg.py


# Task 2 – dbt Warehouse Build
cd medical_warehouse
dbt debug               # check connection
dbt run --full-refresh  # build all models
dbt test                # run data tests
cd ..

#Task 3 – YOLO Image Enrichment
# Run object detection
uv run python src/yolo_detect.py

# Load results to PostgreSQL
uv run python src/load_yolo_to_pg.py

# Build enrichment model in dbt
cd medical_warehouse
dbt run --select fct_image_detections --full-refresh
cd ..

# Task 4 – Analytical API
uvicorn api.main:app --reload --port 8000

# Task 5 – Dagster Orchestration

dagster dev -f pipeline.py


# Architecture Overview

Telegram Channels ──► Scraper (Telethon) ──► NDJSON + Images
                                            │
                                            ▼
Raw Loader ──► PostgreSQL (raw.telegram_messages)
                                            │
                                            ▼
dbt (Task 2) ──► Star Schema (public_public_marts)
                                            │
                                            ▼
YOLOv8 Detection ──► CSV ──► Loader ──► raw.yolo_detections
                                            │
                                            ▼
dbt Enrichment ──► fct_image_detections
                                            │
                                            ▼
FastAPI API ──► Analytical endpoints
                                            │
                                            ▼
Dagster Job ──► Scheduled full pipeline


