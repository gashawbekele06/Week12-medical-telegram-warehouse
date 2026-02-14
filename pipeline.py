"""
Updated pipeline with refactored modules.
"""

import subprocess
from pathlib import Path
from typing import List

from dagster import (
    job, op, schedule, repository, RunConfig, DefaultScheduleStatus,
    get_dagster_logger
)

logger = get_dagster_logger()


def run_command(cmd: List[str], cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    """
    Run shell command and raise on non-zero exit.
    
    Args:
        cmd: Command and arguments as list
        cwd: Working directory
        
    Returns:
        CompletedProcess instance
        
    Raises:
        RuntimeError: If command fails
    """
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


@op
def scrape_telegram_data() -> str:
    """Scrape Telegram channels for messages and media."""
    run_command(["uv", "run", "python", "-m", "src.scraper.scraper"])
    return "scraped"


@op
def load_raw_to_postgres(scrape_result: str) -> str:
    """Load raw messages to PostgreSQL."""
    run_command(["uv", "run", "python", "-m", "src.loaders.load_raw_to_pg"])
    return "loaded"


@op
def run_dbt_transformations(load_result: str) -> str:
    """Run dbt transformations."""
    run_command(
        ["dbt", "run", "--full-refresh"],
        cwd="medical_warehouse"
    )
    return "transformed"


@op
def run_yolo_detection(transform_result: str) -> str:
    """Run YOLO object detection on images."""
    run_command(["uv", "run", "python", "-m", "src.detection.yolo_detect"])
    return "detected"


@op
def load_yolo_detections(detection_result: str) -> str:
    """Load YOLO detection results to PostgreSQL."""
    run_command(["uv", "run", "python", "-m", "src.loaders.load_yolo_to_pg"])
    return "complete"


@job
def full_medical_pipeline():
    """
    Full end-to-end pipeline:
    scrape → load raw → dbt build → yolo detection → load detections
    """
    scrape_result = scrape_telegram_data()
    load_result = load_raw_to_postgres(scrape_result)
    transform_result = run_dbt_transformations(load_result)
    detection_result = run_yolo_detection(transform_result)
    load_yolo_detections(detection_result)


@schedule(
    cron_schedule="0 2 * * *",  # every day at 02:00
    job=full_medical_pipeline,
    execution_timezone="Africa/Addis_Ababa",
    default_status=DefaultScheduleStatus.STOPPED  # start manually first
)
def daily_pipeline_schedule() -> RunConfig:
    """Daily pipeline schedule."""
    return RunConfig()


@repository
def medical_warehouse_repo():
    """Dagster repository definition."""
    return [
        full_medical_pipeline,
        daily_pipeline_schedule
    ]