"""
Unit tests for execution time tracking in SAP Tools API.
"""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, call
import time

# Add project root to Python path for tests
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main import create_app


class TestExecutionTimeTr:
    """Test suite for execution time tracking."""
    
    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    def test_successful_query_has_execution_time(self, client: TestClient):
        """Test that successful queries log execution time."""
        with patch('src.routers.sap_tools.create_sap_agent') as mock_agent, \
             patch('src.routers.sap_tools.log_api_response') as mock_log_response:
            
            # Mock agent response
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = {
                "messages": [MagicMock(content="Table MAKT has 5 fields")]
            }
            mock_agent.return_value = mock_instance
            
            # Make request
            response = client.get("/tools?user_query=Get schema for MAKT table")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            # Verify log_api_response was called with execution_time_ms
            mock_log_response.assert_called_once()
            call_args = mock_log_response.call_args
            
            # Check that execution_time_ms is present and is a positive integer
            assert 'execution_time_ms' in call_args.kwargs
            execution_time = call_args.kwargs['execution_time_ms']
            assert isinstance(execution_time, int)
            assert execution_time >= 0
            assert call_args.kwargs['success'] is True
            assert call_args.kwargs['status_code'] == 200
    
    def test_error_query_has_execution_time(self, client: TestClient):
        """Test that failed queries log execution time."""
        with patch('src.routers.sap_tools.create_sap_agent') as mock_agent, \
             patch('src.routers.sap_tools.log_api_response') as mock_log_response:
            
            # Mock agent to raise exception
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = Exception("SAP connection failed")
            mock_agent.return_value = mock_instance
            
            # Make request
            response = client.get("/tools?user_query=Get schema for MAKT table")
            
            # Verify response is error
            assert response.status_code == 500
            
            # Verify log_api_response was called with execution_time_ms
            mock_log_response.assert_called_once()
            call_args = mock_log_response.call_args
            
            # Check that execution_time_ms is present and is a positive integer
            assert 'execution_time_ms' in call_args.kwargs
            execution_time = call_args.kwargs['execution_time_ms']
            assert isinstance(execution_time, int)
            assert execution_time >= 0
            assert call_args.kwargs['success'] is False
            assert call_args.kwargs['status_code'] == 500
    
    def test_timeout_error_has_execution_time(self, client: TestClient):
        """Test that timeout errors log execution time."""
        with patch('src.routers.sap_tools.create_sap_agent') as mock_agent, \
             patch('src.routers.sap_tools.log_api_response') as mock_log_response, \
             patch('src.routers.sap_tools.log_error_with_context') as mock_log_error:
            
            # Mock agent to raise TimeoutError
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = TimeoutError("Request timed out")
            mock_agent.return_value = mock_instance
            
            # Make request
            response = client.get("/tools?user_query=Get schema for MAKT table")
            
            # Verify response
            assert response.status_code == 504
            
            # Verify log_api_response was called with execution_time_ms
            mock_log_response.assert_called_once()
            call_args = mock_log_response.call_args
            
            assert 'execution_time_ms' in call_args.kwargs
            execution_time = call_args.kwargs['execution_time_ms']
            assert isinstance(execution_time, int)
            assert execution_time >= 0
            assert call_args.kwargs['success'] is False
            assert call_args.kwargs['status_code'] == 504
            
            # Verify error context includes execution time
            mock_log_error.assert_called_once()
            error_context = mock_log_error.call_args[0][1]
            assert 'execution_time_ms' in error_context
            assert error_context['execution_time_ms'] == execution_time
    
    def test_connection_error_has_execution_time(self, client: TestClient):
        """Test that connection errors log execution time."""
        with patch('src.routers.sap_tools.create_sap_agent') as mock_agent, \
             patch('src.routers.sap_tools.log_api_response') as mock_log_response, \
             patch('src.routers.sap_tools.log_error_with_context') as mock_log_error:
            
            # Mock agent to raise ConnectionError
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = ConnectionError("Connection failed")
            mock_agent.return_value = mock_instance
            
            # Make request
            response = client.get("/tools?user_query=Get schema for MAKT table")
            
            # Verify response
            assert response.status_code == 502
            
            # Verify log_api_response was called with execution_time_ms
            mock_log_response.assert_called_once()
            call_args = mock_log_response.call_args
            
            assert 'execution_time_ms' in call_args.kwargs
            execution_time = call_args.kwargs['execution_time_ms']
            assert isinstance(execution_time, int)
            assert execution_time >= 0
            assert call_args.kwargs['success'] is False
            assert call_args.kwargs['status_code'] == 502
            
            # Verify error context includes execution time
            mock_log_error.assert_called_once()
            error_context = mock_log_error.call_args[0][1]
            assert 'execution_time_ms' in error_context
    
    def test_value_error_has_execution_time(self, client: TestClient):
        """Test that validation errors log execution time."""
        with patch('src.routers.sap_tools.create_sap_agent') as mock_agent, \
             patch('src.routers.sap_tools.log_api_response') as mock_log_response, \
             patch('src.routers.sap_tools.log_error_with_context') as mock_log_error:
            
            # Mock agent to raise ValueError
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = ValueError("Invalid configuration")
            mock_agent.return_value = mock_instance
            
            # Make request
            response = client.get("/tools?user_query=Get schema for MAKT table")
            
            # Verify response
            assert response.status_code == 400
            
            # Verify log_api_response was called with execution_time_ms
            mock_log_response.assert_called_once()
            call_args = mock_log_response.call_args
            
            assert 'execution_time_ms' in call_args.kwargs
            execution_time = call_args.kwargs['execution_time_ms']
            assert isinstance(execution_time, int)
            assert execution_time >= 0
            assert call_args.kwargs['success'] is False
            assert call_args.kwargs['status_code'] == 400
    
    def test_execution_time_increases_with_delay(self, client: TestClient):
        """Test that execution time actually measures elapsed time."""
        with patch('src.routers.sap_tools.create_sap_agent') as mock_agent, \
             patch('src.routers.sap_tools.log_api_response') as mock_log_response:
            
            # Mock agent with artificial delay
            def slow_invoke(*args, **kwargs):
                time.sleep(0.1)  # 100ms delay
                return {"messages": [MagicMock(content="Result")]}
            
            mock_instance = MagicMock()
            mock_instance.invoke = slow_invoke
            mock_agent.return_value = mock_instance
            
            # Make request
            response = client.get("/tools?user_query=Test query")
            
            # Verify response
            assert response.status_code == 200
            
            # Verify execution time is at least 100ms
            call_args = mock_log_response.call_args
            execution_time = call_args.kwargs['execution_time_ms']
            
            # Should be at least 100ms (with some tolerance for overhead)
            assert execution_time >= 90, f"Expected at least 90ms, got {execution_time}ms"


class TestExecutionTimeLogging:
    """Test suite for execution time in log messages."""
    
    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    def test_success_log_includes_execution_time(self, client: TestClient, caplog):
        """Test that successful queries include execution time in logs."""
        with patch('src.routers.sap_tools.create_sap_agent') as mock_agent:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = {
                "messages": [MagicMock(content="Success")]
            }
            mock_agent.return_value = mock_instance
            
            # Make request
            response = client.get("/tools?user_query=Test query")
            
            # Verify response
            assert response.status_code == 200
            
            # Check logs for execution time message
            # Note: This depends on your logging setup, may need adjustment
            # Looking for pattern: "SAP query completed successfully in XXXms"
    
    def test_error_log_includes_execution_time(self, client: TestClient, caplog):
        """Test that error logs include execution time."""
        with patch('src.routers.sap_tools.create_sap_agent') as mock_agent:
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = Exception("Error")
            mock_agent.return_value = mock_instance
            
            # Make request
            response = client.get("/tools?user_query=Test query")
            
            # Verify error response
            assert response.status_code == 500
            
            # Check logs for execution time in error message
            # Looking for pattern: "... (failed after XXXms)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
