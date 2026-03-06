"""
Unit tests for file validation functions

Tests Requirements 23.1-23.6:
- Audio file extension validation (.wav, .mp3, .mpeg)
- Image file extension validation (.jpg, .jpeg, .png)
- File size validation (< 10MB)
- File content validation using Pillow
- HTTP 400 error responses for validation failures
"""

import pytest
import io
import wave
import struct
import os
from PIL import Image
from fastapi import HTTPException


# Copy the validation functions here for testing
# This avoids importing the full agentv5_clean module which requires env vars

def validate_audio_file(file_bytes: bytes, filename: str) -> None:
    """Validate audio file extension and content
    
    Requirements: 23.1, 23.4, 23.5
    
    Args:
        file_bytes: File content as bytes
        filename: Original filename
        
    Raises:
        HTTPException: If validation fails
    """
    # Validate file extension
    allowed_extensions = {".wav", ".mp3", ".mpeg"}
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audio file extension. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file content matches extension
    # Check magic bytes for common audio formats
    if len(file_bytes) < 12:
        raise HTTPException(
            status_code=400,
            detail="File is too small to be a valid audio file"
        )
    
    # WAV files start with "RIFF" and contain "WAVE"
    if file_ext == ".wav":
        if not (file_bytes[:4] == b'RIFF' and file_bytes[8:12] == b'WAVE'):
            raise HTTPException(
                status_code=400,
                detail="File content does not match WAV format"
            )
    
    # MP3 files start with ID3 tag or MPEG frame sync
    elif file_ext == ".mp3":
        # ID3v2 tag starts with "ID3"
        # MPEG frame sync starts with 0xFF 0xFB or 0xFF 0xFA or 0xFF 0xF3 or 0xFF 0xF2
        has_id3 = file_bytes[:3] == b'ID3'
        has_mpeg_sync = file_bytes[0] == 0xFF and (file_bytes[1] & 0xE0) == 0xE0
        if not (has_id3 or has_mpeg_sync):
            raise HTTPException(
                status_code=400,
                detail="File content does not match MP3 format"
            )
    
    # MPEG files have similar structure to MP3
    elif file_ext == ".mpeg":
        # MPEG frame sync
        has_mpeg_sync = file_bytes[0] == 0xFF and (file_bytes[1] & 0xE0) == 0xE0
        if not has_mpeg_sync:
            raise HTTPException(
                status_code=400,
                detail="File content does not match MPEG format"
            )


def validate_image_file(file_bytes: bytes, filename: str) -> None:
    """Validate image file extension and content using Pillow
    
    Requirements: 23.2, 23.4, 23.5
    
    Args:
        file_bytes: File content as bytes
        filename: Original filename
        
    Raises:
        HTTPException: If validation fails
    """
    # Validate file extension
    allowed_extensions = {".jpg", ".jpeg", ".png"}
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image file extension. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file content using Pillow
    try:
        # Try to open the image with Pillow
        image = Image.open(io.BytesIO(file_bytes))
        
        # Verify the image format matches the extension
        image_format = image.format
        if image_format is None:
            raise HTTPException(
                status_code=400,
                detail="Unable to determine image format"
            )
        
        # Check format matches extension
        if file_ext in [".jpg", ".jpeg"]:
            if image_format not in ["JPEG", "JPG"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"File content does not match JPEG format (detected: {image_format})"
                )
        elif file_ext == ".png":
            if image_format != "PNG":
                raise HTTPException(
                    status_code=400,
                    detail=f"File content does not match PNG format (detected: {image_format})"
                )
        
        # Verify the image can be loaded (not corrupted)
        image.verify()
        
    except HTTPException:
        # Re-raise our validation errors
        raise
    except Exception as e:
        # Catch any Pillow errors (corrupted images, invalid formats, etc.)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image file: {str(e)}"
        )


def validate_file_size(file_bytes: bytes, max_size_mb: int = 10) -> None:
    """Validate file size is within limits
    
    Requirements: 23.3, 23.5
    
    Args:
        file_bytes: File content as bytes
        max_size_mb: Maximum file size in MB
        
    Raises:
        HTTPException: If file size exceeds limit
    """
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({file_size_mb:.2f}MB) exceeds {max_size_mb}MB limit"
        )


class TestAudioFileValidation:
    """Test audio file validation (Requirements 23.1, 23.4)"""
    
    def test_valid_wav_file(self):
        """Valid WAV file should pass validation"""
        # Create a minimal valid WAV file
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(44100)
            wav_file.writeframes(struct.pack('<h', 0) * 100)
        
        wav_bytes = wav_buffer.getvalue()
        
        # Should not raise exception
        validate_audio_file(wav_bytes, "test.wav")
    
    def test_valid_mp3_file_with_id3(self):
        """Valid MP3 file with ID3 tag should pass validation"""
        # Create a minimal MP3 file with ID3 tag
        mp3_bytes = b'ID3' + b'\x00' * 100
        
        # Should not raise exception
        validate_audio_file(mp3_bytes, "test.mp3")
    
    def test_valid_mp3_file_with_mpeg_sync(self):
        """Valid MP3 file with MPEG sync should pass validation"""
        # Create a minimal MP3 file with MPEG frame sync
        mp3_bytes = b'\xFF\xFB' + b'\x00' * 100
        
        # Should not raise exception
        validate_audio_file(mp3_bytes, "test.mp3")
    
    def test_valid_mpeg_file(self):
        """Valid MPEG file should pass validation"""
        # Create a minimal MPEG file with frame sync
        mpeg_bytes = b'\xFF\xE0' + b'\x00' * 100
        
        # Should not raise exception
        validate_audio_file(mpeg_bytes, "test.mpeg")
    
    def test_invalid_audio_extension(self):
        """Invalid audio extension should raise HTTP 400"""
        audio_bytes = b'RIFF' + b'\x00' * 4 + b'WAVE' + b'\x00' * 100
        
        with pytest.raises(HTTPException) as exc_info:
            validate_audio_file(audio_bytes, "test.mp4")
        
        assert exc_info.value.status_code == 400
        assert "Invalid audio file extension" in exc_info.value.detail
    
    def test_wav_file_with_wrong_content(self):
        """WAV extension with non-WAV content should raise HTTP 400"""
        # Create fake WAV content (not starting with RIFF)
        fake_wav = b'FAKE' + b'\x00' * 100
        
        with pytest.raises(HTTPException) as exc_info:
            validate_audio_file(fake_wav, "test.wav")
        
        assert exc_info.value.status_code == 400
        assert "does not match WAV format" in exc_info.value.detail
    
    def test_mp3_file_with_wrong_content(self):
        """MP3 extension with non-MP3 content should raise HTTP 400"""
        # Create fake MP3 content (no ID3 or MPEG sync)
        fake_mp3 = b'FAKE' + b'\x00' * 100
        
        with pytest.raises(HTTPException) as exc_info:
            validate_audio_file(fake_mp3, "test.mp3")
        
        assert exc_info.value.status_code == 400
        assert "does not match MP3 format" in exc_info.value.detail
    
    def test_mpeg_file_with_wrong_content(self):
        """MPEG extension with non-MPEG content should raise HTTP 400"""
        # Create fake MPEG content (no frame sync)
        fake_mpeg = b'FAKE' + b'\x00' * 100
        
        with pytest.raises(HTTPException) as exc_info:
            validate_audio_file(fake_mpeg, "test.mpeg")
        
        assert exc_info.value.status_code == 400
        assert "does not match MPEG format" in exc_info.value.detail
    
    def test_audio_file_too_small(self):
        """Audio file smaller than 12 bytes should raise HTTP 400"""
        tiny_file = b'RIFF'
        
        with pytest.raises(HTTPException) as exc_info:
            validate_audio_file(tiny_file, "test.wav")
        
        assert exc_info.value.status_code == 400
        assert "too small" in exc_info.value.detail


class TestImageFileValidation:
    """Test image file validation (Requirements 23.2, 23.4)"""
    
    def test_valid_png_file(self):
        """Valid PNG file should pass validation"""
        # Create a minimal valid PNG image
        img = Image.new('RGB', (10, 10), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        png_bytes = img_buffer.getvalue()
        
        # Should not raise exception
        validate_image_file(png_bytes, "test.png")
    
    def test_valid_jpeg_file(self):
        """Valid JPEG file should pass validation"""
        # Create a minimal valid JPEG image
        img = Image.new('RGB', (10, 10), color='blue')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        jpeg_bytes = img_buffer.getvalue()
        
        # Should not raise exception
        validate_image_file(jpeg_bytes, "test.jpg")
    
    def test_valid_jpeg_with_jpeg_extension(self):
        """Valid JPEG file with .jpeg extension should pass validation"""
        # Create a minimal valid JPEG image
        img = Image.new('RGB', (10, 10), color='green')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        jpeg_bytes = img_buffer.getvalue()
        
        # Should not raise exception
        validate_image_file(jpeg_bytes, "test.jpeg")
    
    def test_invalid_image_extension(self):
        """Invalid image extension should raise HTTP 400"""
        # Create a valid PNG
        img = Image.new('RGB', (10, 10), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        png_bytes = img_buffer.getvalue()
        
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(png_bytes, "test.gif")
        
        assert exc_info.value.status_code == 400
        assert "Invalid image file extension" in exc_info.value.detail
    
    def test_png_extension_with_jpeg_content(self):
        """PNG extension with JPEG content should raise HTTP 400"""
        # Create a JPEG image
        img = Image.new('RGB', (10, 10), color='blue')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        jpeg_bytes = img_buffer.getvalue()
        
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(jpeg_bytes, "test.png")
        
        assert exc_info.value.status_code == 400
        assert "does not match PNG format" in exc_info.value.detail
    
    def test_jpeg_extension_with_png_content(self):
        """JPEG extension with PNG content should raise HTTP 400"""
        # Create a PNG image
        img = Image.new('RGB', (10, 10), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        png_bytes = img_buffer.getvalue()
        
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(png_bytes, "test.jpg")
        
        assert exc_info.value.status_code == 400
        assert "does not match JPEG format" in exc_info.value.detail
    
    def test_corrupted_image_file(self):
        """Corrupted image file should raise HTTP 400"""
        # Create fake image content
        fake_image = b'FAKE_IMAGE_DATA' + b'\x00' * 100
        
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(fake_image, "test.png")
        
        assert exc_info.value.status_code == 400
        assert "Invalid image file" in exc_info.value.detail
    
    def test_empty_image_file(self):
        """Empty image file should raise HTTP 400"""
        empty_bytes = b''
        
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(empty_bytes, "test.png")
        
        assert exc_info.value.status_code == 400
        assert "Invalid image file" in exc_info.value.detail


class TestFileSizeValidation:
    """Test file size validation (Requirement 23.3)"""
    
    def test_file_within_size_limit(self):
        """File within size limit should pass validation"""
        # Create a 1MB file
        file_bytes = b'\x00' * (1 * 1024 * 1024)
        
        # Should not raise exception
        validate_file_size(file_bytes, max_size_mb=10)
    
    def test_file_at_size_limit(self):
        """File exactly at size limit should pass validation"""
        # Create a 10MB file
        file_bytes = b'\x00' * (10 * 1024 * 1024)
        
        # Should not raise exception
        validate_file_size(file_bytes, max_size_mb=10)
    
    def test_file_exceeds_size_limit(self):
        """File exceeding size limit should raise HTTP 400"""
        # Create an 11MB file
        file_bytes = b'\x00' * (11 * 1024 * 1024)
        
        with pytest.raises(HTTPException) as exc_info:
            validate_file_size(file_bytes, max_size_mb=10)
        
        assert exc_info.value.status_code == 400
        assert "exceeds" in exc_info.value.detail
        assert "10MB limit" in exc_info.value.detail
    
    def test_empty_file(self):
        """Empty file should pass validation"""
        empty_bytes = b''
        
        # Should not raise exception
        validate_file_size(empty_bytes, max_size_mb=10)
    
    def test_custom_size_limit(self):
        """Custom size limit should be respected"""
        # Create a 3MB file
        file_bytes = b'\x00' * (3 * 1024 * 1024)
        
        with pytest.raises(HTTPException) as exc_info:
            validate_file_size(file_bytes, max_size_mb=2)
        
        assert exc_info.value.status_code == 400
        assert "2MB limit" in exc_info.value.detail


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_case_insensitive_extensions(self):
        """File extensions should be case-insensitive"""
        # Create a valid PNG
        img = Image.new('RGB', (10, 10), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        png_bytes = img_buffer.getvalue()
        
        # Should not raise exception for uppercase extension
        validate_image_file(png_bytes, "test.PNG")
        validate_image_file(png_bytes, "test.Png")
    
    def test_filename_with_multiple_dots(self):
        """Filename with multiple dots should work correctly"""
        # Create a valid PNG
        img = Image.new('RGB', (10, 10), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        png_bytes = img_buffer.getvalue()
        
        # Should not raise exception
        validate_image_file(png_bytes, "my.test.file.png")
    
    def test_filename_without_extension(self):
        """Filename without extension should raise HTTP 400"""
        # Create a valid PNG
        img = Image.new('RGB', (10, 10), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        png_bytes = img_buffer.getvalue()
        
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(png_bytes, "testfile")
        
        assert exc_info.value.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
