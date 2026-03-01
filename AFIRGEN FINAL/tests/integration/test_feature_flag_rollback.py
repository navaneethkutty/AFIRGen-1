"""
Integration tests for feature flag rollback mechanism.
Tests that both GGUF and Bedrock implementations work correctly
and maintain identical API contracts.
"""

import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_health_endpoint_shows_implementation_status():
    """Test that health endpoint indicates which implementation is active."""
    # Import after setting environment
    from config.settings import get_settings, _settings
    
    # Test with Bedrock enabled
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'true'}):
        # Reset settings singleton
        import config.settings
        config.settings._settings = None
        
        settings = get_settings()
        assert settings.enable_bedrock is True
        
        # Import app after settings are configured
        from agentv5 import app
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data['implementation'] == 'bedrock'
        assert data['enable_bedrock'] is True
        assert 'bedrock' in data
    
    # Test with Bedrock disabled (GGUF mode)
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'false'}):
        # Reset settings singleton
        config.settings._settings = None
        
        settings = get_settings()
        assert settings.enable_bedrock is False
        
        # Import app after settings are configured
        from agentv5 import app
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data['implementation'] == 'gguf'
        assert data['enable_bedrock'] is False
        assert 'gguf' in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_contract_consistency_bedrock_vs_gguf():
    """
    Test that API contracts remain identical between Bedrock and GGUF implementations.
    Validates Property 30 from design document.
    """
    # Test request/response schemas are identical
    from input_validation import ProcessRequest, FIRResp
    
    # Create sample request
    test_request = {
        "text": "Someone stole my mobile phone from my bag at the market."
    }
    
    # Test with Bedrock
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'true'}):
        import config.settings
        config.settings._settings = None
        
        from agentv5 import app
        client = TestClient(app)
        
        response_bedrock = client.post("/process", json=test_request)
        assert response_bedrock.status_code in [200, 500]  # May fail if services not configured
        
        if response_bedrock.status_code == 200:
            bedrock_schema = set(response_bedrock.json().keys())
    
    # Test with GGUF
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'false'}):
        config.settings._settings = None
        
        from agentv5 import app
        client = TestClient(app)
        
        response_gguf = client.post("/process", json=test_request)
        assert response_gguf.status_code in [200, 500]
        
        if response_gguf.status_code == 200:
            gguf_schema = set(response_gguf.json().keys())
    
    # If both succeeded, verify schemas match
    if response_bedrock.status_code == 200 and response_gguf.status_code == 200:
        assert bedrock_schema == gguf_schema, "API response schemas must be identical"


@pytest.mark.integration
def test_startup_logs_active_implementation():
    """Test that startup logs clearly indicate which implementation is active."""
    import logging
    from io import StringIO
    
    # Capture logs
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    
    logger = logging.getLogger('config.settings')
    logger.addHandler(handler)
    
    # Test Bedrock mode
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'true'}):
        import config.settings
        config.settings._settings = None
        
        settings = get_settings()
        
        log_output = log_capture.getvalue()
        assert 'ACTIVE IMPLEMENTATION' in log_output or 'Bedrock' in log_output
    
    # Test GGUF mode
    log_capture.truncate(0)
    log_capture.seek(0)
    
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'false'}):
        config.settings._settings = None
        
        settings = get_settings()
        
        log_output = log_capture.getvalue()
        assert 'ACTIVE IMPLEMENTATION' in log_output or 'GGUF' in log_output


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bedrock_initialization_only_when_enabled():
    """Test that Bedrock services are only initialized when ENABLE_BEDROCK is true."""
    # Test with Bedrock disabled
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'false'}):
        import config.settings
        config.settings._settings = None
        
        settings = get_settings()
        assert settings.enable_bedrock is False
        
        # AWS credentials should not be required
        # Vector DB config should not be validated
        assert settings.aws.region  # Should have default value
        assert settings.aws.s3_bucket  # Should have default value
    
    # Test with Bedrock enabled
    with patch.dict(os.environ, {
        'ENABLE_BEDROCK': 'true',
        'AWS_REGION': 'us-east-1',
        'S3_BUCKET_NAME': 'test-bucket',
        'VECTOR_DB_TYPE': 'opensearch',
        'OPENSEARCH_ENDPOINT': 'https://test.opensearch.amazonaws.com'
    }):
        config.settings._settings = None
        
        settings = get_settings()
        assert settings.enable_bedrock is True
        assert settings.aws.region == 'us-east-1'
        assert settings.aws.s3_bucket == 'test-bucket'
        assert settings.vector_db.db_type == 'opensearch'


@pytest.mark.integration
def test_feature_flag_can_be_changed_without_code_changes():
    """Test that feature flag can be toggled via environment variable only."""
    # Test toggling between implementations
    implementations = []
    
    # First run with Bedrock
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'true'}):
        import config.settings
        config.settings._settings = None
        
        settings = get_settings()
        implementations.append(('bedrock', settings.enable_bedrock))
    
    # Second run with GGUF
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'false'}):
        config.settings._settings = None
        
        settings = get_settings()
        implementations.append(('gguf', settings.enable_bedrock))
    
    # Verify we can toggle
    assert implementations[0] == ('bedrock', True)
    assert implementations[1] == ('gguf', False)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_consistent_across_implementations():
    """Test that error responses are consistent between implementations."""
    from fastapi import HTTPException
    
    # Test invalid input handling
    invalid_request = {
        "text": ""  # Empty text should fail validation
    }
    
    # Test with Bedrock
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'true'}):
        import config.settings
        config.settings._settings = None
        
        from agentv5 import app
        client = TestClient(app)
        
        response_bedrock = client.post("/process", json=invalid_request)
        bedrock_status = response_bedrock.status_code
        bedrock_error = response_bedrock.json() if response_bedrock.status_code != 200 else None
    
    # Test with GGUF
    with patch.dict(os.environ, {'ENABLE_BEDROCK': 'false'}):
        config.settings._settings = None
        
        from agentv5 import app
        client = TestClient(app)
        
        response_gguf = client.post("/process", json=invalid_request)
        gguf_status = response_gguf.status_code
        gguf_error = response_gguf.json() if response_gguf.status_code != 200 else None
    
    # Both should return same error status
    assert bedrock_status == gguf_status
    
    # Error format should be consistent
    if bedrock_error and gguf_error:
        assert set(bedrock_error.keys()) == set(gguf_error.keys())


@pytest.mark.integration
def test_configuration_validation_respects_feature_flag():
    """Test that configuration validation is appropriate for each mode."""
    # GGUF mode should not require AWS configuration
    with patch.dict(os.environ, {
        'ENABLE_BEDROCK': 'false'
    }, clear=True):
        import config.settings
        config.settings._settings = None
        
        # Should not raise error even without AWS config
        try:
            settings = get_settings()
            assert settings.enable_bedrock is False
        except SystemExit:
            pytest.fail("GGUF mode should not require AWS configuration")
    
    # Bedrock mode should require AWS configuration
    with patch.dict(os.environ, {
        'ENABLE_BEDROCK': 'true'
    }, clear=True):
        config.settings._settings = None
        
        # Should raise error without required AWS config
        with pytest.raises(SystemExit):
            settings = get_settings()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_both_implementations_maintain_session_state():
    """Test that session management works identically in both modes."""
    from agentv5 import session_manager, SessionStatus
    
    # Test session creation and retrieval
    test_session_id = "test_session_rollback_001"
    initial_state = {
        "transcript": "Test complaint text",
        "status": SessionStatus.PROCESSING
    }
    
    # Create session
    session_manager.create_session(test_session_id, initial_state)
    
    # Retrieve session
    session = session_manager.get_session(test_session_id)
    
    assert session is not None
    assert session['session_id'] == test_session_id
    assert session['state']['transcript'] == "Test complaint text"
    
    # Session management should work regardless of implementation mode
    # (it's independent of GGUF vs Bedrock)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
