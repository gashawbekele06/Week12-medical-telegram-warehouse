"""
Dagster Pipeline – Medical Telegram Warehouse
Full end-to-end job: scrape → load raw → dbt build → yolo detection → load detections
"""

import subprocess
import os
from pathlib import Path
from dagster import (
    job, op, schedule, repository, RunConfig, DefaultScheduleStatus,
    AssetIn, asset, define_asset_job, AssetSelection
)
from dagster import get_dagster_logger

logger = get_dagster_logger()

# ─── HELPER ─────────────────────────────────────────────────────────────────────
def run_command(cmd: list[str], cwd: str | Path | None = None):
    """Run shell command and raise on non-zero exit"""
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None
    )
    logger.info(result.stdout)
    if result.stderr:
        logger.warning(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed (exit {result.returncode}):\n{result.stderr}")
    return result

# ─── OPS / ASSETS ───────────────────────────────────────────────────────────────

@op
def scrape_telegram_data():
    run_command(["uv", "run", "python", "src/scraper.py"])
    return "scraped"

@op
def load_raw_to_postgres(scrape_result):
    run_command(["uv", "run", "python", "src/load_raw_to_pg.py"])
    return "loaded"

@op
def run_dbt_transformations(load_result):
    run_command(
        ["dbt", "run", "--full-refresh"],
        cwd="medical_warehouse"
    )
    return "transformed"

@op
def run_yolo_detection(transform_result):
    run_command(["uv", "run", "python", "src/yolo_detect.py"])
    return "detected"

@op
def load_yolo_detections(detection_result):
    run_command(["uv", "run", "python", "src/load_yolo_to_pg.py"])
    return "complete"

# ─── JOB ────────────────────────────────────────────────────────────────────────

@job
def full_medical_pipeline():
    scrape_result = scrape_telegram_data()
    load_result = load_raw_to_postgres(scrape_result)
    transform_result = run_dbt_transformations(load_result)
    detection_result = run_yolo_detection(transform_result)
    load_yolo_detections(detection_result)

# ─── SCHEDULE ───────────────────────────────────────────────────────────────────

@schedule(
    cron_schedule="0 2 * * *",  # every day at 02:00
    job=full_medical_pipeline,
    execution_timezone="Africa/Addis_Ababa",
    default_status=DefaultScheduleStatus.STOPPED  # start manually first
)
def daily_pipeline_schedule():
    return RunConfig()

# ─── REPOSITORY ─────────────────────────────────────────────────────────────────

@repository
def medical_warehouse_repo():
    return [
        full_medical_pipeline,
        daily_pipeline_schedule
    ]