"""
Unit tests for image classifier.
"""

import pytest
from src.detection.image_classifier import ImageClassifier, DetectionResult


class TestImageClassifier:
    """Test cases for ImageClassifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return ImageClassifier()
    
    def test_classify_promotional(self, classifier):
        """Test classification of promotional content (person + product)."""
        detections = [
            DetectionResult("person", 0.9),
            DetectionResult("bottle", 0.8),
        ]
        category = classifier.classify(detections)
        assert category == "promotional"
    
    def test_classify_product_display(self, classifier):
        """Test classification of product display (product only)."""
        detections = [
            DetectionResult("bottle", 0.85),
            DetectionResult("cup", 0.75),
        ]
        category = classifier.classify(detections)
        assert category == "product_display"
    
    def test_classify_lifestyle(self, classifier):
        """Test classification of lifestyle content (person only)."""
        detections = [
            DetectionResult("person", 0.95),
        ]
        category = classifier.classify(detections)
        assert category == "lifestyle"
    
    def test_classify_other(self, classifier):
        """Test classification of other content."""
        detections = [
            DetectionResult("car", 0.9),
            DetectionResult("dog", 0.85),
        ]
        category = classifier.classify(detections)
        assert category == "other"
    
    def test_classify_empty_detections(self, classifier):
        """Test classification with no detections."""
        category = classifier.classify([])
        assert category == "other"
    
    def test_classify_low_confidence(self, classifier):
        """Test that low confidence detections are filtered out."""
        detections = [
            DetectionResult("person", 0.1),  # Below threshold
            DetectionResult("bottle", 0.15),  # Below threshold
        ]
        category = classifier.classify(detections)
        assert category == "other"
    
    def test_get_category_description(self, classifier):
        """Test category descriptions."""
        assert "promotional" in classifier.get_category_description("promotional").lower()
        assert "product" in classifier.get_category_description("product_display").lower()
        assert "lifestyle" in classifier.get_category_description("lifestyle").lower()
        assert "other" in classifier.get_category_description("other").lower()
