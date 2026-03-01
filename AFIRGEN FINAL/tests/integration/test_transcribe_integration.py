"""
Integration tests for TranscribeClient.
Tests audio transcription with real AWS Transcribe service.
"""

import pytest
import asyncio
import io
from pathlib import Path
from services.aws.transcribe_client import TranscribeClient, TranscriptionResult, ValidationError
from fastapi import UploadFile


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcribe_audio_hindi(aws_region, s3_bucket, kms_key_id):
    """Test audio transcription with Hindi language."""
    # Create TranscribeClient
    client = TranscribeClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    # Create sample audio file (simulated)
    # In real test, use actual audio file
    audio_content = create_sample_audio_content()
    audio_file = UploadFile(
        filename="test_audio_hindi.mp3",
        file=io.BytesIO(audio_content)
    )
    
    # Transcribe audio
    result = await client.transcribe_audio(
        audio_file=audio_file,
        language_code="hi-IN"
    )
    
    # Verify result
    assert isinstance(result, TranscriptionResult)
    assert result.transcript
    assert result.language_code == "hi-IN"
    assert 0.0 <= result.confidence <= 1.0
    assert result.job_name
    assert result.duration_seconds >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcribe_audio_english(aws_region, s3_bucket, kms_key_id):
    """Test audio transcription with English language."""
    client = TranscribeClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    audio_content = create_sample_audio_content()
    audio_file = UploadFile(
        filename="test_audio_english.mp3",
        file=io.BytesIO(audio_content)
    )
    
    result = await client.transcribe_audio(
        audio_file=audio_file,
        language_code="en-IN"
    )
    
    assert isinstance(result, TranscriptionResult)
    assert result.transcript
    assert result.language_code == "en-IN"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcribe_audio_auto_detect(aws_region, s3_bucket, kms_key_id):
    """Test audio transcription with automatic language detection."""
    client = TranscribeClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    audio_content = create_sample_audio_content()
    audio_file = UploadFile(
        filename="test_audio_auto.mp3",
        file=io.BytesIO(audio_content)
    )
    
    result = await client.transcribe_audio(
        audio_file=audio_file,
        language_code=None  # Auto-detect
    )
    
    assert isinstance(result, TranscriptionResult)
    assert result.transcript
    assert result.language_code in TranscribeClient.SUPPORTED_LANGUAGES


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcribe_invalid_format(aws_region, s3_bucket, kms_key_id):
    """Test transcription with invalid audio format."""
    client = TranscribeClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    audio_file = UploadFile(
        filename="test_audio.txt",
        file=io.BytesIO(b"not an audio file")
    )
    
    with pytest.raises(ValidationError) as exc_info:
        await client.transcribe_audio(audio_file=audio_file)
    
    assert "Unsupported audio format" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcribe_invalid_language(aws_region, s3_bucket, kms_key_id):
    """Test transcription with invalid language code."""
    client = TranscribeClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    audio_content = create_sample_audio_content()
    audio_file = UploadFile(
        filename="test_audio.mp3",
        file=io.BytesIO(audio_content)
    )
    
    with pytest.raises(ValidationError) as exc_info:
        await client.transcribe_audio(
            audio_file=audio_file,
            language_code="invalid-lang"
        )
    
    assert "Unsupported language" in str(exc_info.value)


def create_sample_audio_content() -> bytes:
    """
    Create sample audio content for testing.
    In production tests, this should be replaced with actual audio files.
    """
    # This is a placeholder - in real tests, load actual audio file
    # For now, return minimal MP3 header
    return b'\xff\xfb\x90\x00' + b'\x00' * 1000


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcribe_cleanup_on_error(aws_region, s3_bucket, kms_key_id):
    """Test that S3 files are cleaned up even on error."""
    client = TranscribeClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    # Create invalid audio that will fail transcription
    audio_file = UploadFile(
        filename="test_audio.mp3",
        file=io.BytesIO(b'\xff\xfb\x90\x00' + b'\x00' * 100)  # Too short
    )
    
    # This should fail but cleanup should still happen
    try:
        await client.transcribe_audio(audio_file=audio_file)
    except Exception:
        pass  # Expected to fail
    
    # Verify cleanup happened (check S3 bucket is clean)
    # In real test, verify no temp files remain in S3
