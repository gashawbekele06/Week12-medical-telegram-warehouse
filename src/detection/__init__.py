"""Detection module for YOLO object detection."""

from .yolo_detect import YOLODetector, main
from .image_classifier import ImageClassifier, DetectionResult

__all__ = [
    "YOLODetector",
    "ImageClassifier",
    "DetectionResult",
    "main"
]
