"""
Refactored YOLO detections loader to PostgreSQL.
"""

import csv
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
class YOLODetection:
    """Data model for YOLO detection records."""
    
    image_path: str
    message_id: str
    channel: str
    detected_objects: str
    confidence_scores: str
    image_category: str
    
    def to_tuple(self) -> Tuple:
        """Convert to tuple for database insertion."""
        return (
            self.image_path,
            self.message_id,
            self.channel,
            self.detected_objects,
            self.confidence_scores,
            self.image_category,
        )


class YOLODetectionLoader:
    """Loads YOLO detection results into PostgreSQL."""
    
    CREATE_SCHEMA_SQL = "CREATE SCHEMA IF NOT EXISTS public_marts;"
    
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS public_marts.fct_image_detections (
        image_path        TEXT,
        message_id        TEXT,
        channel           TEXT,
        detected_objects  TEXT,
        confidence_scores TEXT,
        image_category    TEXT,
        loaded_at         TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (message_id, channel)
    );
    
    CREATE INDEX IF NOT EXISTS idx_image_detections_category 
        ON public_marts.fct_image_detections(image_category);
    CREATE INDEX IF NOT EXISTS idx_image_detections_channel 
        ON public_marts.fct_image_detections(channel);
    """
    
    def __init__(self):
        """Initialize loader with configuration."""
        settings = get_settings()
        self.yolo_output = settings.paths.yolo_output
    
    def ensure_table_exists(self) -> None:
        """Create schema and table if they don't exist."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(self.CREATE_SCHEMA_SQL)
                    cursor.execute(self.CREATE_TABLE_SQL)
            logger.info("Table public_marts.fct_image_detections ready")
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise
    
    def load_detections(self) -> int:
        """
        Load YOLO detections from CSV file.
        
        Returns:
            Number of rows inserted
        """
        if not self.yolo_output.exists():
            logger.warning(f"YOLO output file not found: {self.yolo_output}")
            return 0
        
        batch: List[Tuple] = []
        
        try:
            with open(self.yolo_output, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    detection = YOLODetection(
                        image_path=row.get("image_path", ""),
                        message_id=row.get("message_id", ""),
                        channel=row.get("channel", ""),
                        detected_objects=row.get("detected_objects", ""),
                        confidence_scores=row.get("confidence_scores", ""),
                        image_category=row.get("image_category", "other"),
                    )
                    batch.append(detection.to_tuple())
            
            # Insert batch
            if batch:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        execute_values(
                            cursor,
                            """
                            INSERT INTO public_marts.fct_image_detections (
                                image_path, message_id, channel,
                                detected_objects, confidence_scores, image_category
                            ) VALUES %s
                            ON CONFLICT (message_id, channel) DO UPDATE SET
                                detected_objects = EXCLUDED.detected_objects,
                                confidence_scores = EXCLUDED.confidence_scores,
                                image_category = EXCLUDED.image_category,
                                loaded_at = CURRENT_TIMESTAMP;
                            """,
                            batch,
                        )
                        inserted = cursor.rowcount
                
                logger.info(f"✅ Loaded {inserted} YOLO detections")
                return inserted
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to load YOLO detections: {e}")
            raise
    
    def load_all(self) -> int:
        """
        Load all YOLO detections.
        
        Returns:
            Total number of rows inserted
        """
        self.ensure_table_exists()
        return self.load_detections()


def main() -> None:
    """Main entry point for YOLO detection loader."""
    try:
        loader = YOLODetectionLoader()
        total = loader.load_all()
        logger.info(f"Load complete! {total} detections processed")
    except Exception as e:
        logger.error(f"Load failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
