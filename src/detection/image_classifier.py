"""
Image classification logic for YOLO detections.
"""

from typing import List, Set
from dataclasses import dataclass

from src.config import get_settings
from src.utils import get_logger

logger = get_logger(__name__)


@dataclass
class DetectionResult:
    """Represents a single object detection."""
    
    class_name: str
    confidence: float
    
    def __str__(self) -> str:
        return f"{self.class_name} ({self.confidence:.3f})"


class ImageClassifier:
    """
    Classifies images based on detected objects.
    
    Categories:
    - promotional: Person + product
    - product_display: Product only
    - lifestyle: Person only
    - other: Everything else
    """
    
    def __init__(self):
        """Initialize classifier with configuration."""
        settings = get_settings()
        self.product_keywords: Set[str] = set(settings.yolo.product_keywords)
        self.confidence_threshold = settings.yolo.confidence_threshold
    
    def classify(
        self,
        detections: List[DetectionResult]
    ) -> str:
        """
        Classify image based on detected objects.
        
        Args:
            detections: List of detection results
            
        Returns:
            Category string
        """
        if not detections:
            return "other"
        
        # Filter by confidence
        valid_detections = [
            d for d in detections
            if d.confidence >= self.confidence_threshold
        ]
        
        if not valid_detections:
            return "other"
        
        # Check for person and products
        has_person = any(d.class_name == "person" for d in valid_detections)
        has_product = any(
            d.class_name in self.product_keywords
            for d in valid_detections
        )
        
        # Classify
        if has_person and has_product:
            return "promotional"
        elif has_product:
            return "product_display"
        elif has_person:
            return "lifestyle"
        else:
            return "other"
    
    def get_category_description(self, category: str) -> str:
        """Get human-readable description of category."""
        descriptions = {
            "promotional": "Promotional content (person + product)",
            "product_display": "Product display only",
            "lifestyle": "Lifestyle content (person only)",
            "other": "Other content"
        }
        return descriptions.get(category, "Unknown category")
