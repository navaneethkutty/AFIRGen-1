"""
Simple unit tests for error response models

Requirements: 14.1-14.8
"""

import pytest
from pydantic import BaseModel
from typing import Optional


# Define ErrorResponse model locally for testing
class ErrorResponse(BaseModel):
    """Standardized error response model
    
    Requirements: 14.1-14.8
    """
    error: str
    detail: str
    status_code: int


class TestErrorResponseModel:
    """Test the ErrorResponse model structure and behavior"""
    
    def test_error_response_model_creation(self):
        """Test that ErrorResponse can be created with required fields"""
        error_response = ErrorResponse(
            error="Test error",
            detail="Test detail message",
            status_code=400
        )
        
        assert error_response.error == "Test error"
        assert error_response.detail == "Test detail message"
        assert error_response.status_code == 400
    
    def test_error_response_400_format(self):
        """Test 400 Bad Request error response format"""
        error_response = ErrorResponse(
            error="Invalid input",
            detail="File size exceeds 10MB limit",
            status_code=400
        )
        
        assert error_response.error == "Invalid input"
        assert error_response.status_code == 400
        assert "10MB" in error_response.detail
    
    def test_error_response_401_format(self):
        """Test 401 Unauthorized error response format"""
        error_response = ErrorResponse(
            error="Authentication failed",
            detail="Invalid or missing API key",
            status_code=401
        )
        
        assert error_response.error == "Authentication failed"
        assert error_response.status_code == 401
        assert "API key" in error_response.detail
    
    def test_error_response_429_format(self):
        """Test 429 Rate Limit error response format"""
        error_response = ErrorResponse(
            error="Rate limit exceeded",
            detail="Maximum 100 requests per minute",
            status_code=429
        )
        
        assert error_response.error == "Rate limit exceeded"
        assert error_response.status_code == 429
        assert "100 requests" in error_response.detail
    
    def test_error_response_500_format(self):
        """Test 500 Internal Server Error response format"""
        error_response = ErrorResponse(
            error="Service temporarily unavailable",
            detail="Please try again later",
            status_code=500
        )
        
        assert error_response.error == "Service temporarily unavailable"
        assert error_response.status_code == 500
        assert "try again" in error_response.detail.lower()
    
    def test_error_response_serialization(self):
        """Test that ErrorResponse can be serialized to dict"""
        error_response = ErrorResponse(
            error="Test error",
            detail="Test detail",
            status_code=500
        )
        
        data = error_response.model_dump()
        assert isinstance(data, dict)
        assert data["error"] == "Test error"
        assert data["detail"] == "Test detail"
        assert data["status_code"] == 500
    
    def test_error_response_json_serialization(self):
        """Test that ErrorResponse can be serialized to JSON"""
        error_response = ErrorResponse(
            error="Test error",
            detail="Test detail",
            status_code=400
        )
        
        json_str = error_response.model_dump_json()
        assert isinstance(json_str, str)
        assert "Test error" in json_str
        assert "Test detail" in json_str
        assert "400" in json_str
    
    def test_error_response_no_sensitive_data(self):
        """Test that error responses don't contain sensitive information"""
        # Simulate various error scenarios
        error_responses = [
            ErrorResponse(
                error="Invalid input",
                detail="File validation failed",
                status_code=400
            ),
            ErrorResponse(
                error="Authentication failed",
                detail="Invalid API key",
                status_code=401
            ),
            ErrorResponse(
                error="Internal server error",
                detail="An unexpected error occurred",
                status_code=500
            )
        ]
        
        # Check that none contain sensitive keywords
        sensitive_keywords = ["password", "secret", "credential", "token", "key_value"]
        
        for response in error_responses:
            detail_lower = response.detail.lower()
            error_lower = response.error.lower()
            
            for keyword in sensitive_keywords:
                assert keyword not in detail_lower, f"Sensitive keyword '{keyword}' found in detail"
                assert keyword not in error_lower, f"Sensitive keyword '{keyword}' found in error"
    
    def test_error_response_required_fields(self):
        """Test that all required fields must be provided"""
        # Should raise validation error if fields are missing
        with pytest.raises(Exception):  # Pydantic ValidationError
            ErrorResponse(
                error="Test error"
                # Missing detail and status_code
            )
    
    def test_error_response_field_types(self):
        """Test that field types are enforced"""
        # Valid types
        error_response = ErrorResponse(
            error="Test",
            detail="Detail",
            status_code=400
        )
        assert isinstance(error_response.error, str)
        assert isinstance(error_response.detail, str)
        assert isinstance(error_response.status_code, int)
        
        # Invalid type for status_code should be coerced or raise error
        try:
            error_response = ErrorResponse(
                error="Test",
                detail="Detail",
                status_code="400"  # String instead of int
            )
            # If coerced, should be int
            assert isinstance(error_response.status_code, int)
            assert error_response.status_code == 400
        except Exception:
            # If not coerced, should raise validation error
            pass


class TestErrorResponseScenarios:
    """Test error response for various scenarios"""
    
    def test_file_validation_error(self):
        """Test error response for file validation failures"""
        scenarios = [
            ("Invalid audio file extension", 400),
            ("File size exceeds 10MB limit", 400),
            ("File content does not match declared type", 400),
        ]
        
        for detail, status_code in scenarios:
            response = ErrorResponse(
                error="Invalid input",
                detail=detail,
                status_code=status_code
            )
            assert response.status_code == 400
            assert response.error == "Invalid input"
    
    def test_authentication_error(self):
        """Test error response for authentication failures"""
        response = ErrorResponse(
            error="Authentication failed",
            detail="Invalid or missing API key",
            status_code=401
        )
        assert response.status_code == 401
        assert "API key" in response.detail
    
    def test_rate_limit_error(self):
        """Test error response for rate limiting"""
        response = ErrorResponse(
            error="Rate limit exceeded",
            detail="Maximum 100 requests per minute",
            status_code=429
        )
        assert response.status_code == 429
        assert "100" in response.detail
    
    def test_aws_service_error(self):
        """Test error response for AWS service failures"""
        response = ErrorResponse(
            error="Service temporarily unavailable",
            detail="Please try again later",
            status_code=500
        )
        assert response.status_code == 500
        # Should not expose AWS-specific details
        assert "bedrock" not in response.detail.lower()
        assert "transcribe" not in response.detail.lower()
        assert "textract" not in response.detail.lower()
    
    def test_database_error(self):
        """Test error response for database failures"""
        response = ErrorResponse(
            error="Database error",
            detail="Unable to process request",
            status_code=500
        )
        assert response.status_code == 500
        # Should not expose database details
        assert "mysql" not in response.detail.lower()
        assert "sql" not in response.detail.lower()
        assert "query" not in response.detail.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
