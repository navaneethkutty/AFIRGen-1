"""
Unit tests for TranscribeClient.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import BytesIO
from fastapi import UploadFile

import sys
sys.path.insert(0, 'AFIRGEN FINAL')

from services.aws.transcribe_client import (
    TranscribeClient,
    TranscriptionResult,
    TranscribeError,
    ValidationError
)


@pytest.fixture
def transcribe_client():
    """Create TranscribeClient instance for testing."""
    with patch('boto3.client'):
        client = TranscribeClient(
            region='us-east-1',
            s3_bucket='test-bucket',
            kms_key_id='test-kms-key'
        )
        return client


@pytest.fixture
def mock_audio_file():
    """Create mock audio file."""
    content = b"fake audio content"
    file = UploadFile(
        filename="test_audio.mp3",
        file=BytesIO(content)
    )
    return file


class TestTranscribeClient:
    """Test suite for TranscribeClient."""
    
    def test_init(self, transcribe_client):
        """Test client initialization."""
        assert transcribe_client.s3_bucket == 'test-bucket'
        assert transcribe_client.kms_key_id == 'test-kms-key'
        assert transcribe_client.region == 'us-east-1'
        assert transcribe_client.max_retries == 3
    
    def test_supported_languages(self, transcribe_client):
        """Test supported languages list."""
        expected_languages = [
            'hi-IN', 'en-IN', 'ta-IN', 'te-IN', 'bn-IN',
            'mr-IN', 'gu-IN', 'kn-IN', 'ml-IN', 'pa-IN'
        ]
        assert transcribe_client.SUPPORTED_LANGUAGES == expected_languages
    
    def test_supported_formats(self, transcribe_client):
        """Test supported audio formats."""
        expected_formats = ['wav', 'mp3', 'mpeg', 'mp4', 'flac']
        assert transcribe_client.SUPPORTED_FORMATS == expected_formats
    
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_invalid_format(self, transcribe_client):
        """Test transcription with invalid audio format."""
        invalid_file = UploadFile(
            filename="test.txt",
            file=BytesIO(b"content")
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await transcribe_client.transcribe_audio(invalid_file)
        
        assert "Unsupported audio format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_invalid_language(self, transcribe_client, mock_audio_file):
        """Test transcription with invalid language code."""
        with pytest.raises(ValidationError) as exc_info:
            await transcribe_client.transcribe_audio(
                mock_audio_file,
                language_code='invalid-lang'
            )
        
        assert "Unsupported language" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, transcribe_client, mock_audio_file):
        """Test successful transcription."""
        # Mock S3 upload
        transcribe_client._upload_to_s3 = AsyncMock(
            return_value='s3://test-bucket/test.mp3'
        )
        
        # Mock transcription job start
        transcribe_client._start_transcription_job = AsyncMock(
            return_value='test-job-123'
        )
        
        # Mock job polling
        transcribe_client._poll_transcription_job = AsyncMock(
            return_value={
                'TranscriptionJobStatus': 'COMPLETED',
                'Transcript': {
                    'TranscriptFileUri': 'https://s3.amazonaws.com/transcript.json'
                },
                'LanguageCode': 'en-IN',
                'MediaSampleRateHertz': 16000
            }
        )
        
        # Mock transcript fetch
        transcribe_client._fetch_transcript = AsyncMock(
            return_value={
                'results': {
                    'transcripts': [{'transcript': 'Test transcript text'}],
                    'items': [
                        {'alternatives': [{'confidence': '0.95'}]},
                        {'alternatives': [{'confidence': '0.90'}]}
                    ]
                }
            }
        )
        
        # Mock cleanup
        transcribe_client._cleanup_s3_file = AsyncMock()
        transcribe_client._delete_transcription_job = AsyncMock()
        
        result = await transcribe_client.transcribe_audio(
            mock_audio_file,
            language_code='en-IN'
        )
        
        assert isinstance(result, TranscriptionResult)
        assert result.transcript == 'Test transcript text'
        assert result.language_code == 'en-IN'
        assert result.job_name == 'test-job-123'
        assert 0.0 <= result.confidence <= 1.0
    
    
    @pytest.mark.asyncio
    async def test_upload_to_s3(self, transcribe_client, mock_audio_file):
        """Test S3 upload with encryption."""
        mock_s3_client = MagicMock()
        transcribe_client.s3_client = mock_s3_client
        
        s3_uri = await transcribe_client._upload_to_s3(mock_audio_file)
        
        assert s3_uri.startswith('s3://test-bucket/transcribe-temp/')
        assert 'test_audio.mp3' in s3_uri
        
        # Verify put_object was called with encryption
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs['ServerSideEncryption'] == 'aws:kms'
        assert call_kwargs['SSEKMSKeyId'] == 'test-kms-key'
    
    @pytest.mark.asyncio
    async def test_start_transcription_job_with_language(self, transcribe_client):
        """Test starting transcription job with specified language."""
        mock_transcribe = MagicMock()
        transcribe_client.transcribe_client = mock_transcribe
        
        job_name = await transcribe_client._start_transcription_job(
            's3://bucket/file.mp3',
            'hi-IN'
        )
        
        assert job_name.startswith('afirgen-transcribe-')
        
        # Verify API call
        mock_transcribe.start_transcription_job.assert_called_once()
        call_kwargs = mock_transcribe.start_transcription_job.call_args[1]
        assert call_kwargs['LanguageCode'] == 'hi-IN'
        assert 'IdentifyLanguage' not in call_kwargs
    
    @pytest.mark.asyncio
    async def test_start_transcription_job_auto_detect(self, transcribe_client):
        """Test starting transcription job with auto language detection."""
        mock_transcribe = MagicMock()
        transcribe_client.transcribe_client = mock_transcribe
        
        job_name = await transcribe_client._start_transcription_job(
            's3://bucket/file.mp3',
            None
        )
        
        # Verify API call includes language options
        call_kwargs = mock_transcribe.start_transcription_job.call_args[1]
        assert call_kwargs['IdentifyLanguage'] is True
        assert len(call_kwargs['LanguageOptions']) == 10
    
    @pytest.mark.asyncio
    async def test_poll_transcription_job_completed(self, transcribe_client):
        """Test polling completed job."""
        mock_transcribe = MagicMock()
        mock_transcribe.get_transcription_job.return_value = {
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'COMPLETED',
                'Transcript': {'TranscriptFileUri': 'https://example.com/transcript.json'}
            }
        }
        transcribe_client.transcribe_client = mock_transcribe
        
        result = await transcribe_client._poll_transcription_job('test-job')
        
        assert result['TranscriptionJobStatus'] == 'COMPLETED'
    
    @pytest.mark.asyncio
    async def test_poll_transcription_job_failed(self, transcribe_client):
        """Test polling failed job."""
        mock_transcribe = MagicMock()
        mock_transcribe.get_transcription_job.return_value = {
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'FAILED',
                'FailureReason': 'Invalid audio format'
            }
        }
        transcribe_client.transcribe_client = mock_transcribe
        
        with pytest.raises(TranscribeError) as exc_info:
            await transcribe_client._poll_transcription_job('test-job')
        
        assert 'Invalid audio format' in str(exc_info.value)
    
    def test_get_file_extension(self, transcribe_client):
        """Test file extension extraction."""
        assert transcribe_client._get_file_extension('test.mp3') == 'mp3'
        assert transcribe_client._get_file_extension('test.audio.wav') == 'wav'
        assert transcribe_client._get_file_extension('TEST.MP3') == 'mp3'
        assert transcribe_client._get_file_extension('noextension') == ''
    
    def test_get_media_format(self, transcribe_client):
        """Test media format determination."""
        assert transcribe_client._get_media_format('s3://bucket/file.mp3') == 'mp3'
        assert transcribe_client._get_media_format('s3://bucket/file.wav') == 'wav'
        assert transcribe_client._get_media_format('s3://bucket/file.flac') == 'flac'
    
    def test_calculate_confidence(self, transcribe_client):
        """Test confidence calculation."""
        transcript_data = {
            'results': {
                'items': [
                    {'alternatives': [{'confidence': '0.95'}]},
                    {'alternatives': [{'confidence': '0.90'}]},
                    {'alternatives': [{'confidence': '0.85'}]}
                ]
            }
        }
        
        confidence = transcribe_client._calculate_confidence(transcript_data)
        assert 0.89 < confidence < 0.91  # Average of 0.95, 0.90, 0.85
    
    def test_calculate_confidence_empty(self, transcribe_client):
        """Test confidence calculation with empty data."""
        transcript_data = {'results': {'items': []}}
        confidence = transcribe_client._calculate_confidence(transcript_data)
        assert confidence == 0.0
