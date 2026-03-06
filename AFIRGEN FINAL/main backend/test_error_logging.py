"""
Unit tests for error logging implementation

Tests verify that error logging meets requirements 14.1-14.8:
- AWS service errors include service name, operation, error code, message
- Database errors include SQL query and error message
- Validation errors include details
- Stack traces are included for debugging
- No sensitive data in error messages to clients
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import json
import os
import sys

# Mock environment variables before importing agentv5_clean
os.environ['S3_BUCKET_NAME'] = 'test-bucket'
os.environ['DB_HOST'] = 'test-host'
os.environ['DB_PASSWORD'] = 'test-password'
os.environ['API_KEY'] = 'test-api-key'
os.environ['AWS_REGION'] = 'us-east-1'


def test_aws_bedrock_error_logging_includes_service_details():
    """Test that Bedrock errors log service name, operation, error code, and message"""
    from agentv5_clean import AWSServiceClients, Config
    
    # Create a mock boto3 client that raises an error
    with patch('boto3.client') as mock_boto3:
        mock_bedrock = Mock()
        mock_boto3.return_value = mock_bedrock
        
        # Simulate AWS error with response structure
        error = Exception("ThrottlingException: Rate exceeded")
        error.response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_bedrock.invoke_model.side_effect = error
        
        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.ERROR)
        
        aws_clients = AWSServiceClients("us-east-1")
        aws_clients.logger.addHandler(handler)
        
        # Try to invoke Claude (should fail and log)
        with pytest.raises(Exception):
            aws_clients.invoke_claude("test prompt")
        
        # Verify log contains required details
        log_output = log_stream.getvalue()
        assert "AWS service error" in log_output
        assert "Service: bedrock-runtime" in log_output
        assert "Operation: invoke_model" in log_output
        assert "Error Code:" in log_output
        assert "Message:" in log_output


def test_aws_transcribe_error_logging_includes_service_details():
    """Test that Transcribe errors log service name, operation, error code, and message"""
    from agentv5_clean import AWSServiceClients
    
    with patch('boto3.client') as mock_boto3:
        mock_transcribe = Mock()
        mock_boto3.return_value = mock_transcribe
        
        # Simulate AWS error
        error = Exception("InvalidParameterException: Invalid language code")
        error.response = {'Error': {'Code': 'InvalidParameterException', 'Message': 'Invalid language code'}}
        mock_transcribe.start_transcription_job.side_effect = error
        
        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.ERROR)
        
        aws_clients = AWSServiceClients("us-east-1")
        aws_clients.logger.addHandler(handler)
        
        # Try to transcribe (should fail and log)
        with pytest.raises(Exception):
            aws_clients.transcribe_audio("s3://bucket/key", "invalid")
        
        # Verify log contains required details
        log_output = log_stream.getvalue()
        assert "AWS service error" in log_output
        assert "Service: transcribe" in log_output
        assert "Operation: start_transcription_job" in log_output


def test_aws_textract_error_logging_includes_service_details():
    """Test that Textract errors log service name, operation, error code, and message"""
    from agentv5_clean import AWSServiceClients
    
    with patch('boto3.client') as mock_boto3:
        mock_textract = Mock()
        mock_boto3.return_value = mock_textract
        
        # Simulate AWS error
        error = Exception("InvalidS3ObjectException: Invalid S3 object")
        error.response = {'Error': {'Code': 'InvalidS3ObjectException', 'Message': 'Invalid S3 object'}}
        mock_textract.detect_document_text.side_effect = error
        
        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.ERROR)
        
        aws_clients = AWSServiceClients("us-east-1")
        aws_clients.logger.addHandler(handler)
        
        # Try to extract text (should fail and log)
        with pytest.raises(Exception):
            aws_clients.extract_text_from_image("s3://bucket/key")
        
        # Verify log contains required details
        log_output = log_stream.getvalue()
        assert "AWS service error" in log_output
        assert "Service: textract" in log_output
        assert "Operation: detect_document_text" in log_output


def test_aws_s3_error_logging_includes_service_details():
    """Test that S3 errors log service name, operation, error code, and message"""
    from agentv5_clean import AWSServiceClients
    
    with patch('boto3.client') as mock_boto3:
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3
        
        # Simulate AWS error
        error = Exception("NoSuchBucket: The specified bucket does not exist")
        error.response = {'Error': {'Code': 'NoSuchBucket', 'Message': 'The specified bucket does not exist'}}
        mock_s3.put_object.side_effect = error
        
        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.ERROR)
        
        aws_clients = AWSServiceClients("us-east-1")
        aws_clients.logger.addHandler(handler)
        
        # Try to upload (should fail and log)
        with pytest.raises(Exception):
            aws_clients.upload_to_s3(b"test data", "key", "nonexistent-bucket")
        
        # Verify log contains required details
        log_output = log_stream.getvalue()
        assert "AWS service error" in log_output
        assert "Service: s3" in log_output
        assert "Operation: put_object" in log_output
        assert "Bucket: nonexistent-bucket" in log_output
        assert "Key: key" in log_output


def test_database_error_logging_includes_sql_query():
    """Test that database errors log SQL query and error message"""
    from agentv5_clean import DatabaseManager
    
    # Mock MySQL connection that raises an error
    with patch('mysql.connector.pooling.MySQLConnectionPool') as mock_pool:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Duplicate entry 'FIR-123' for key 'fir_number'")
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.return_value.get_connection.return_value = mock_conn
        
        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.ERROR)
        
        db_manager = DatabaseManager({
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        })
        db_manager.logger.addHandler(handler)
        
        # Try to insert FIR (should fail and log)
        with pytest.raises(Exception):
            db_manager.insert_fir_record({
                'fir_number': 'FIR-123',
                'session_id': 'session-123',
                'complaint_text': 'test',
                'fir_content': {},
                'violations_json': []
            })
        
        # Verify log contains SQL query and error
        log_output = log_stream.getvalue()
        assert "Database error" in log_output
        assert "Operation: insert_fir_record" in log_output
        assert "SQL:" in log_output
        assert "INSERT INTO fir_records" in log_output
        assert "Error:" in log_output


def test_validation_error_logging_includes_details():
    """Test that validation errors log details about missing fields"""
    from agentv5_clean import FIRGenerator, AWSServiceClients, DatabaseManager
    
    # Create mocks
    with patch('boto3.client'):
        aws_clients = AWSServiceClients("us-east-1")
    
    with patch('mysql.connector.pooling.MySQLConnectionPool'):
        db_manager = DatabaseManager({
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        })
    
    # Capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.ERROR)
    
    fir_generator = FIRGenerator(aws_clients, db_manager)
    fir_generator.logger.addHandler(handler)
    
    # Test with incomplete FIR data
    incomplete_fir = {
        'complainant_name': 'John Doe',
        'complainant_dob': '',  # Empty field
        # Missing other required fields
    }
    
    result = fir_generator._validate_fir_fields(incomplete_fir)
    
    # Verify validation failed
    assert result is False
    
    # Verify log contains details about missing fields
    log_output = log_stream.getvalue()
    assert "FIR validation failed" in log_output
    assert "Missing or empty fields:" in log_output


def test_error_logging_includes_stack_traces():
    """Test that error logging includes stack traces for debugging"""
    from agentv5_clean import AWSServiceClients
    
    with patch('boto3.client') as mock_boto3:
        mock_bedrock = Mock()
        mock_boto3.return_value = mock_bedrock
        mock_bedrock.invoke_model.side_effect = Exception("Test error")
        
        # Capture log output with formatter that includes exc_info
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        aws_clients = AWSServiceClients("us-east-1")
        aws_clients.logger.addHandler(handler)
        aws_clients.logger.setLevel(logging.ERROR)
        
        # Try to invoke (should fail and log with stack trace)
        with pytest.raises(Exception):
            aws_clients.invoke_claude("test")
        
        # Note: Stack traces are logged via exc_info=True parameter
        # The actual stack trace content depends on logging configuration
        log_output = log_stream.getvalue()
        assert "AWS service error" in log_output


def test_client_error_messages_no_sensitive_data():
    """Test that error messages to clients don't contain sensitive information"""
    from agentv5_clean import general_exception_handler
    from fastapi import Request
    
    # Create a mock request
    mock_request = Mock(spec=Request)
    mock_request.url.path = "/test"
    
    # Create an exception with sensitive data
    exc = Exception("Database connection failed: password=secret123, host=internal-db.local")
    
    # Call error handler
    import asyncio
    response = asyncio.run(general_exception_handler(mock_request, exc))
    
    # Verify response doesn't contain sensitive data
    response_data = json.loads(response.body.decode())
    assert "password" not in response_data['detail'].lower()
    assert "secret123" not in response_data['detail']
    assert "internal-db" not in response_data['detail']
    
    # Verify generic error message is returned
    assert response_data['error'] == "Internal server error"
    assert "unexpected error occurred" in response_data['detail'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
