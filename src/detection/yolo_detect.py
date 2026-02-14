"""
Refactored YOLO object detection with type safety and modular design.
"""

import csv
from pathlib import Path
from typing import List, Optional
from contextlib import ExitStack

import torch
from ultralytics import YOLO
from tqdm import tqdm

from src.config import get_settings
from src.utils import get_logger
from .image_classifier import ImageClassifier, DetectionResult

logger = get_logger(__name__)


# PyTorch safe deserialization setup
_HAS_SAFE_GLOBALS_CTX = hasattr(torch.serialization, "safe_globals")

# Common torch classes for safe loading
from torch.nn import (
    Identity, ModuleList, ModuleDict, Linear, Conv2d, BatchNorm2d, SiLU, Sigmoid
)
from torch.nn.modules.container import Sequential
from torch.nn.modules.pooling import MaxPool2d

COMMON_TORCH_CLASSES = [
    Identity, ModuleList, ModuleDict, Linear, Conv2d, BatchNorm2d,
    SiLU, Sigmoid, Sequential, MaxPool2d
]


class YOLODetector:
    """
    YOLO-based object detection for images.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize YOLO detector.
        
        Args:
            model_name: YOLO model file (defaults to config)
        """
        settings = get_settings()
        self.config = settings.yolo
        self.paths = settings.paths
        
        self.model_name = model_name or self.config.model_name
        self.classifier = ImageClassifier()
        self.model: Optional[YOLO] = None
    
    def load_model(self) -> None:
        """Load YOLO model with safe deserialization."""
        logger.info(f"Loading YOLO model: {self.model_name}")
        
        try:
            if _HAS_SAFE_GLOBALS_CTX:
                with ExitStack() as stack:
                    if COMMON_TORCH_CLASSES:
                        stack.enter_context(
                            torch.serialization.safe_globals(COMMON_TORCH_CLASSES)
                        )
                    self.model = YOLO(self.model_name)
            else:
                self.model = YOLO(self.model_name)
            
            logger.info("YOLO model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def detect_objects(
        self,
        image_path: Path
    ) -> tuple[List[DetectionResult], str]:
        """
        Detect objects in an image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (detections list, category)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        try:
            results = self.model(image_path, verbose=False)[0]
            boxes = results.boxes
            names = results.names
            
            detections: List[DetectionResult] = []
            
            if boxes is not None and boxes.cls is not None:
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    conf = float(boxes.conf[i].item())
                    class_name = names.get(cls_id, str(cls_id))
                    
                    detections.append(DetectionResult(class_name, conf))
            
            category = self.classifier.classify(detections)
            
            return detections, category
            
        except Exception as e:
            logger.error(f"Detection failed for {image_path}: {e}")
            return [], "other"
    
    def process_all_images(self) -> int:
        """
        Process all images in the images directory.
        
        Returns:
            Number of images processed
        """
        self.load_model()
        
        # Find all images
        image_files: List[Path] = []
        for ext in ("*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.png", "*.PNG"):
            image_files.extend(self.paths.images_dir.rglob(ext))
        
        logger.info(f"Found {len(image_files)} images to process")
        
        if not image_files:
            logger.warning("No images found")
            return 0
        
        # Prepare output CSV
        self.paths.yolo_output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.paths.yolo_output, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "image_path", "message_id", "channel",
                "detected_objects", "confidence_scores", "image_category"
            ])
            
            for img_path in tqdm(image_files, desc="Detecting objects"):
                try:
                    channel = img_path.parent.name
                    message_id = img_path.stem
                    
                    detections, category = self.detect_objects(img_path)
                    
                    # Filter by confidence threshold
                    valid_detections = [
                        d for d in detections
                        if d.confidence >= self.config.confidence_threshold
                    ]
                    
                    detected_names = [d.class_name for d in valid_detections]
                    confidences = [f"{d.confidence:.3f}" for d in valid_detections]
                    
                    writer.writerow([
                        str(img_path.relative_to(Path("data/raw"))),
                        message_id,
                        channel,
                        ";".join(detected_names) if detected_names else "",
                        ";".join(confidences) if confidences else "",
                        category
                    ])
                    
                except Exception as e:
                    logger.error(f"Failed to process {img_path}: {e}")
                    continue
        
        logger.info(f"✅ Results saved to {self.paths.yolo_output}")
        logger.info(f"Processed {len(image_files)} images")
        
        return len(image_files)


def main() -> None:
    """Main entry point for YOLO detection."""
    try:
        detector = YOLODetector()
        count = detector.process_all_images()
        logger.info(f"Detection complete! {count} images processed")
    except Exception as e:
        logger.error(f"Detection failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
