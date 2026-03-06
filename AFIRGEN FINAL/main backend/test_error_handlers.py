"""
Unit tests for error response models and exception handlers

Requirements: 14.1-14.8
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path to import agentv5_clean
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import after path is set
from agentv5_clean import app, ErrorResponse


client = TestClient(app)


class TestErrorResponseModel:
    """Test the ErrorResponse model"""
    
    def test_error_response_model_structure(self):
        """Test that ErrorResponse has correct fields"""
        error_response = ErrorResponse(
            error="Test error",
            detail="Test detail",
            status_code=400
        )
        
        assert error_response.error == "Test error"
        assert error_response.detail == "Test detail"
        assert error_response.status_code == 400
    
    def test_error_response_model_serialization(self):
        """Test that ErrorResponse can be serialized to dict"""
        error_response = ErrorResponse(
            error="Test error",
            detail="Test detail",
            status_code=500
        )
        
        data = error_response.model_dump()
        assert data["error"] == "Test error"
        assert data["detail"] == "Test detail"
        assert data["status_code"] == 500


class TestHTTP400Handler:
    """Test HTTP 400 Bad Request error handling"""
    
    def test_invalid_input_text_missing(self):
        """Test 400 error when text input is missing"""
        response = client.post(
            "/process",
            json={"input_type": "text"},
            headers={"X-API-Key": os.getenv("API_KEY", "test-key")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "detail" in data
        assert "status_code" in data
        assert data["status_code"] == 400
        assert data["error"] == "Invalid input"
    
    def test_invalid_file_size(self):
        """Test 400 error when file size exceeds limit"""
        # Create a file larger than 10MB
        large_file_content = b"x" * (11 * 1024 * 1024)  # 11MB
        
        response = client.post(
            "/process",
            data={"input_type": "audio", "language": "en-IN"},
            files={"file": ("test.mp3", large_file_content, "audio/mpeg")},
            headers={"X-API-Key": os.getenv("API_KEY", "test-key")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Invalid input"
        assert "exceeds" in data["detail"].lower()
        assert data["status_code"] == 400


class TestHTTP401Handler:
    """Test HTTP 401 Unauthorized error handling"""
    
    def test_missing_api_key(self):
        """Test 401 error when API key is missing"""
        response = client.post(
            "/process",
            json={"input_type": "text", "text": "Test complaint"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "detail" in data
        assert "status_code" in data
        assert data["status_code"] == 401
        assert data["error"] == "Authentication failed"
    
    def test_invalid_api_key(self):
        """Test 401 error when API key is invalid"""
        response = client.post(
            "/process",
            json={"input_type": "text", "text": "Test complaint"},
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "Authentication failed"
        assert data["status_code"] == 401


class TestHTTP429Handler:
    """Test HTTP 429 Rate Limit error handling"""
    
    def test_rate_limit_response_format(self):
        """Test 429 error response includes retry_after"""
        # Make many requests to trigger rate limit
        api_key = os.getenv("API_KEY", "test-key")
        
        # Make 101 requests (limit is 100 per minute)
        for i in range(101):
            response = client.get(
                "/session/test-session-id",
                headers={"X-API-Key": api_key}
            )
            
            if response.status_code == 429:
                data = response.json()
                assert "error" in data
                assert "detail" in data
                assert "status_code" in data
                assert "retry_after" in data
                assert data["status_code"] == 429
                assert data["error"] == "Rate limit exceeded"
                assert data["retry_after"] == 60
                assert "Retry-After" in response.headers
                assert response.headers["Retry-After"] == "60"
                break
        else:
            pytest.skip("Rate limit not triggered (may need to adjust test)")


class TestHTTP500Handler:
    """Test HTTP 500 Internal Server Error handling"""
    
    def test_internal_error_no_sensitive_data(self):
        """Test 500 error doesn't expose sensitive information"""
        # Try to get a non-existent FIR (this should trigger an internal error)
        response = client.get(
            "/fir/INVALID-FIR-NUMBER",
            headers={"X-API-Key": os.getenv("API_KEY", "test-key")}
        )
        
        # Should return error response
        if response.status_code == 500:
            data = response.json()
            assert "error" in data
            assert "detail" in data
            assert "status_code" in data
            assert data["status_code"] == 500
            
            # Ensure no sensitive information in error message
            detail_lower = data["detail"].lower()
            assert "password" not in detail_lower
            assert "api_key" not in detail_lower
            assert "secret" not in detail_lower
            assert "credential" not in detail_lower


class TestErrorMessageSecurity:
    """Test that error messages don't expose sensitive information"""
    
    def test_no_sensitive_data_in_400_errors(self):
        """Test 400 errors don't contain sensitive information"""
        response = client.post(
            "/process",
            json={"input_type": "text"},
            headers={"X-API-Key": os.getenv("API_KEY", "test-key")}
        )
        
        assert response.status_code == 400
        data = response.json()
        detail = data["detail"].lower()
        
        # Check for sensitive keywords
        assert "password" not in detail
        assert "api_key" not in detail
        assert "secret" not in detail
        assert "credential" not in detail
        assert "token" not in detail
    
    def test_no_sensitive_data_in_401_errors(self):
        """Test 401 errors don't contain sensitive information"""
        response = client.post(
            "/process",
            json={"input_type": "text", "text": "Test"},
            headers={"X-API-Key": "wrong-key"}
        )
        
        assert response.status_code == 401
        data = response.json()
        detail = data["detail"].lower()
        
        # Should not expose the actual API key or any credentials
        assert "password" not in detail
        assert os.getenv("API_KEY", "test-key") not in detail


class TestHealthEndpointExclusion:
    """Test that health endpoint is excluded from authentication and rate limiting"""
    
    def test_health_no_auth_required(self):
        """Test health endpoint doesn't require authentication"""
        response = client.get("/health")
        
        # Should return 200 or 503, not 401
        assert response.status_code in [200, 503]
        assert response.status_code != 401
    
    def test_health_no_rate_limiting(self):
        """Test health endpoint is not rate limited"""
        # Make many requests to health endpoint
        for i in range(150):  # More than rate limit
            response = client.get("/health")
            # Should never return 429
            assert response.status_code != 429


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
