"""
Unit tests for SAP Tools API endpoints.
"""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add project root to Python path for tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main import create_app


class TestSAPToolsAPI:
    """Test suite for SAP Tools API."""
    
    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_sap_tools_valid_query(self, client: TestClient):
        """Test SAP tools endpoint with valid query."""
        with patch('src.routers.sap_tools.create_sap_agent') as mock_agent:
            # Mock agent response
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = {
                "messages": [MagicMock(content="Table MAKT has 5 fields")]
            }
            mock_agent.return_value = mock_instance
            
            response = client.get("/tools?user_query=Get schema for MAKT table")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "MAKT" in data["response"]
    
    def test_sap_tools_empty_query(self, client: TestClient):
        """Test SAP tools endpoint with empty query."""
        response = client.get("/tools?user_query=")
        assert response.status_code == 422  # Validation error
    
    def test_sap_tools_agent_error(self, client: TestClient):
        """Test SAP tools endpoint when agent throws error."""
        with patch('src.routers.sap_tools.create_sap_agent') as mock_agent:
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = Exception("SAP connection failed")
            mock_agent.return_value = mock_instance
            
            response = client.get("/tools?user_query=Get schema for MAKT table")
            
            # Should return 500 for internal server errors now
            assert response.status_code == 500
            data = response.json()
            assert "Internal server error" in data["detail"]


class TestSAPGenericService:
    """Test suite for SAP Generic Service."""
    
    @pytest.fixture  
    def service(self):
        """Create SAP generic service instance."""
        from src.utils.sap_generic_service import sap_generic_service
        return sap_generic_service
    
    def test_call_sap_api_missing_system_id(self, service):
        """Test API call with missing system ID."""
        with pytest.raises(Exception) as exc_info:
            service.call_sap_api_generic(
                http_method="GET",
                service_name="TEST_SERVICE",
                entity_name="TestEntity"
            )
        assert "sap system id" in str(exc_info.value).lower()
    
    def test_call_sap_api_invalid_http_method(self, service):
        """Test API call with invalid HTTP method."""
        with pytest.raises(Exception) as exc_info:
            service.call_sap_api_generic(
                http_method="INVALID",
                service_name="TEST_SERVICE", 
                entity_name="TestEntity",
                system_id="D2A",
                service_namespace="TEST_NAMESPACE"  # Add required namespace
            )
        assert "invalid http method" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__])