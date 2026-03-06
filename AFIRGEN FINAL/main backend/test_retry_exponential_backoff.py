"""
Test exponential backoff retry logic for AWS service calls.

This test verifies that:
1. Retry logic attempts up to 2 retries (3 total attempts)
2. Exponential backoff is used: 2s, 4s delays
3. All AWS service methods implement retry logic
"""

import pytest
import time
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Set required environment variables before importing agentv5_clean
os.environ['S3_BUCKET_NAME'] = 'test-bucket'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PASSWORD'] = 'test-password'
os.environ['API_KEY'] = 'test-api-key'


class TestRetryExponentialBackoff:
    """Test retry logic with exponential backoff for AWS service calls"""
    
    def test_bedrock_retry_exponential_backoff(self):
        """Test Bedrock invocation uses exponential backoff (2s, 4s)"""
        from agentv5_clean import AWSServiceClients, config
        
        # Mock the bedrock client to fail twice, then succeed
        mock_bedrock = Mock()
        call_count = 0
        call_times = []
        
        def mock_invoke(*args, **kwargs):
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count <= 2:
                raise Exception("Throttling error")
            # Success on third attempt
            response = {
                'body': Mock(read=lambda: json.dumps({
                    'content': [{'text': 'Test response'}]
                }).encode())
            }
            return response
        
        mock_bedrock.invoke_model = mock_invoke
        
        # Create AWS client and replace bedrock client
        aws_client = AWSServiceClients(region='us-east-1')
        aws_client.bedrock_runtime = mock_bedrock
        
        # Call should succeed after retries
        start_time = time.time()
        result = aws_client.invoke_claude("test prompt")
        total_time = time.time() - start_time
        
        # Verify 3 attempts were made
        assert call_count == 3, f"Expected 3 attempts, got {call_count}"
        
        # Verify exponential backoff delays (2s + 4s = 6s minimum)
        assert total_time >= 6.0, f"Expected at least 6s delay, got {total_time:.2f}s"
        
        # Verify delays between calls
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            
            # First retry: 2^0 * 2 = 2 seconds
            assert 1.9 <= delay1 <= 2.5, f"First retry delay should be ~2s, got {delay1:.2f}s"
            
            # Second retry: 2^1 * 2 = 4 seconds
            assert 3.9 <= delay2 <= 4.5, f"Second retry delay should be ~4s, got {delay2:.2f}s"
        
        assert result == 'Test response'
    
    def test_transcribe_retry_exponential_backoff(self):
        """Test Transcribe job start uses exponential backoff (2s, 4s)"""
        from agentv5_clean import AWSServiceClients, config
        
        # Mock the transcribe client to fail twice, then succeed
        mock_transcribe = Mock()
        call_count = 0
        call_times = []
        
        def mock_start_job(*args, **kwargs):
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count <= 2:
                raise Exception("Service unavailable")
            return {}
        
        mock_transcribe.start_transcription_job = mock_start_job
        mock_transcribe.get_transcription_job = Mock(return_value={
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'COMPLETED',
                'Transcript': {
                    'TranscriptFileUri': 'http://example.com/transcript.json'
                }
            }
        })
        
        # Create AWS client and replace transcribe client
        aws_client = AWSServiceClients(region='us-east-1')
        aws_client.transcribe = mock_transcribe
        
        # Mock httpx to return transcript
        with patch('httpx.get') as mock_get:
            mock_get.return_value.json.return_value = {
                'results': {
                    'transcripts': [{'transcript': 'Test transcript'}]
                }
            }
            
            start_time = time.time()
            result = aws_client.transcribe_audio("s3://bucket/audio.mp3", "en-IN")
            total_time = time.time() - start_time
        
        # Verify 3 attempts were made
        assert call_count == 3, f"Expected 3 attempts, got {call_count}"
        
        # Verify exponential backoff delays (2s + 4s = 6s minimum)
        assert total_time >= 6.0, f"Expected at least 6s delay, got {total_time:.2f}s"
        
        assert result == 'Test transcript'
    
    def test_s3_upload_retry_exponential_backoff(self):
        """Test S3 upload uses exponential backoff (2s, 4s)"""
        from agentv5_clean import AWSServiceClients, config
        
        # Mock the S3 client to fail twice, then succeed
        mock_s3 = Mock()
        call_count = 0
        call_times = []
        
        def mock_put_object(*args, **kwargs):
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count <= 2:
                raise Exception("Network error")
            return {}
        
        mock_s3.put_object = mock_put_object
        
        # Create AWS client and replace S3 client
        aws_client = AWSServiceClients(region='us-east-1')
        aws_client.s3 = mock_s3
        
        start_time = time.time()
        result = aws_client.upload_to_s3(b"test data", "test.txt", "test-bucket")
        total_time = time.time() - start_time
        
        # Verify 3 attempts were made
        assert call_count == 3, f"Expected 3 attempts, got {call_count}"
        
        # Verify exponential backoff delays (2s + 4s = 6s minimum)
        assert total_time >= 6.0, f"Expected at least 6s delay, got {total_time:.2f}s"
        
        # Verify delays between calls
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            
            # First retry: 2^0 * 2 = 2 seconds
            assert 1.9 <= delay1 <= 2.5, f"First retry delay should be ~2s, got {delay1:.2f}s"
            
            # Second retry: 2^1 * 2 = 4 seconds
            assert 3.9 <= delay2 <= 4.5, f"Second retry delay should be ~4s, got {delay2:.2f}s"
        
        assert result == "s3://test-bucket/test.txt"
    
    def test_textract_retry_exponential_backoff(self):
        """Test Textract extraction uses exponential backoff (2s, 4s)"""
        from agentv5_clean import AWSServiceClients, config
        
        # Mock the Textract client to fail twice, then succeed
        mock_textract = Mock()
        call_count = 0
        call_times = []
        
        def mock_detect_text(*args, **kwargs):
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count <= 2:
                raise Exception("Service error")
            return {
                'Blocks': [
                    {'BlockType': 'LINE', 'Text': 'Test text line 1'},
                    {'BlockType': 'LINE', 'Text': 'Test text line 2'}
                ]
            }
        
        mock_textract.detect_document_text = mock_detect_text
        
        # Create AWS client and replace Textract client
        aws_client = AWSServiceClients(region='us-east-1')
        aws_client.textract = mock_textract
        
        start_time = time.time()
        result = aws_client.extract_text_from_image("s3://bucket/image.jpg")
        total_time = time.time() - start_time
        
        # Verify 3 attempts were made
        assert call_count == 3, f"Expected 3 attempts, got {call_count}"
        
        # Verify exponential backoff delays (2s + 4s = 6s minimum)
        assert total_time >= 6.0, f"Expected at least 6s delay, got {total_time:.2f}s"
        
        assert "Test text line 1" in result
        assert "Test text line 2" in result
    
    def test_max_retries_configuration(self):
        """Test that MAX_RETRIES is set to 2 as required"""
        from agentv5_clean import config
        
        assert config.MAX_RETRIES == 2, f"MAX_RETRIES should be 2, got {config.MAX_RETRIES}"
    
    def test_retry_delay_configuration(self):
        """Test that RETRY_DELAY_SECONDS is set to 2 as required"""
        from agentv5_clean import config
        
        assert config.RETRY_DELAY_SECONDS == 2, f"RETRY_DELAY_SECONDS should be 2, got {config.RETRY_DELAY_SECONDS}"
    
    def test_exponential_backoff_formula(self):
        """Test that exponential backoff formula is correct: 2^(retries-1) * RETRY_DELAY_SECONDS"""
        from agentv5_clean import config
        
        # For MAX_RETRIES = 2, RETRY_DELAY_SECONDS = 2:
        # Attempt 1: no delay (initial attempt)
        # Attempt 2: 2^0 * 2 = 2 seconds delay
        # Attempt 3: 2^1 * 2 = 4 seconds delay
        
        retry_1_delay = (2 ** 0) * config.RETRY_DELAY_SECONDS
        retry_2_delay = (2 ** 1) * config.RETRY_DELAY_SECONDS
        
        assert retry_1_delay == 2, f"First retry delay should be 2s, got {retry_1_delay}s"
        assert retry_2_delay == 4, f"Second retry delay should be 4s, got {retry_2_delay}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
