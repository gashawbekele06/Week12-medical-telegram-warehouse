"""
Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import after mocking to avoid actual database connection
@pytest.fixture
def client():
    """Create test client for API."""
    with patch("api.database.engine"):
        from api.main import app
        return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    return session


class TestAPIEndpoints:
    """Integration tests for API endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Welcome" in response.json()["message"]
    
    def test_top_products_endpoint(self, client):
        """Test top products endpoint."""
        with patch("api.routers.analytics.get_db") as mock_get_db:
            # Mock database response
            mock_session = MagicMock()
            mock_result = [("medicine", 100), ("health", 80)]
            mock_session.execute.return_value.fetchall.return_value = mock_result
            mock_get_db.return_value = mock_session
            
            response = client.get("/api/reports/top-products?limit=10")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["term"] == "medicine"
            assert data[0]["count"] == 100
    
    def test_channel_activity_endpoint(self, client):
        """Test channel activity endpoint."""
        with patch("api.routers.analytics.get_db") as mock_get_db:
            # Mock database response
            mock_session = MagicMock()
            mock_result = [("2024-01-01", 50, 1000.0)]
            mock_session.execute.return_value.fetchall.return_value = mock_result
            mock_get_db.return_value = mock_session
            
            response = client.get("/api/channels/test_channel/activity")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["message_count"] == 50
    
    def test_search_messages_endpoint(self, client):
        """Test message search endpoint."""
        with patch("api.routers.analytics.get_db") as mock_get_db:
            # Mock database response
            mock_session = MagicMock()
            mock_result = [(123, "test_channel", "Test message", 100, "2024-01-01")]
            mock_session.execute.return_value.fetchall.return_value = mock_result
            mock_get_db.return_value = mock_session
            
            response = client.get("/api/search/messages?query=test&limit=20")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["message_id"] == 123
    
    def test_search_messages_validation(self, client):
        """Test search endpoint validates query length."""
        response = client.get("/api/search/messages?query=ab")  # Too short
        assert response.status_code == 422  # Validation error
