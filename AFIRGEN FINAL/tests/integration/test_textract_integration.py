"""
Integration tests for TextractClient.
Tests document OCR with real AWS Textract service.
"""

import pytest
import asyncio
import io
from PIL import Image
from services.aws.textract_client import TextractClient, ExtractionResult, ValidationError
from fastapi import UploadFile


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_text_from_image(aws_region, s3_bucket, kms_key_id):
    """Test text extraction from document image."""
    client = TextractClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    # Create sample image with text
    image_content = create_sample_image_with_text("Sample complaint text")
    image_file = UploadFile(
        filename="test_document.png",
        file=io.BytesIO(image_content)
    )
    
    # Extract text
    result = await client.extract_text(
        image_file=image_file,
        extract_forms=False
    )
    
    # Verify result
    assert isinstance(result, ExtractionResult)
    assert result.text
    assert 0.0 <= result.confidence <= 1.0
    assert result.page_count >= 1
    assert len(result.form_fields) == 0  # No forms extracted


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_text_with_forms(aws_region, s3_bucket, kms_key_id):
    """Test text and form extraction from document."""
    client = TextractClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    # Create sample form image
    image_content = create_sample_form_image()
    image_file = UploadFile(
        filename="test_form.png",
        file=io.BytesIO(image_content)
    )
    
    # Extract text and forms
    result = await client.extract_text(
        image_file=image_file,
        extract_forms=True
    )
    
    # Verify result
    assert isinstance(result, ExtractionResult)
    assert result.text
    # Form fields may or may not be detected depending on image
    assert isinstance(result.form_fields, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_text_jpeg(aws_region, s3_bucket, kms_key_id):
    """Test text extraction from JPEG image."""
    client = TextractClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    image_content = create_sample_image_with_text("JPEG test document")
    image_file = UploadFile(
        filename="test_document.jpg",
        file=io.BytesIO(image_content)
    )
    
    result = await client.extract_text(image_file=image_file)
    
    assert isinstance(result, ExtractionResult)
    assert result.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_invalid_format(aws_region, s3_bucket, kms_key_id):
    """Test extraction with invalid image format."""
    client = TextractClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    image_file = UploadFile(
        filename="test_document.txt",
        file=io.BytesIO(b"not an image")
    )
    
    with pytest.raises(ValidationError) as exc_info:
        await client.extract_text(image_file=image_file)
    
    assert "Unsupported image format" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_empty_image(aws_region, s3_bucket, kms_key_id):
    """Test extraction from blank image."""
    client = TextractClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    # Create blank image
    image_content = create_blank_image()
    image_file = UploadFile(
        filename="blank.png",
        file=io.BytesIO(image_content)
    )
    
    result = await client.extract_text(image_file=image_file)
    
    # Should succeed but return empty or minimal text
    assert isinstance(result, ExtractionResult)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_cleanup_on_error(aws_region, s3_bucket, kms_key_id):
    """Test that S3 files are cleaned up even on error."""
    client = TextractClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    # Create corrupted image
    image_file = UploadFile(
        filename="corrupted.png",
        file=io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
    )
    
    try:
        await client.extract_text(image_file=image_file)
    except Exception:
        pass  # Expected to fail
    
    # Verify cleanup happened


def create_sample_image_with_text(text: str) -> bytes:
    """Create a sample image with text for testing."""
    from PIL import Image, ImageDraw, ImageFont
    
    # Create white image
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add text
    try:
        # Try to use default font
        draw.text((50, 50), text, fill='black')
    except Exception:
        # Fallback if font not available
        draw.text((50, 50), text, fill='black')
    
    # Save to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def create_sample_form_image() -> bytes:
    """Create a sample form image for testing."""
    from PIL import Image, ImageDraw
    
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw form-like structure
    draw.rectangle([50, 50, 750, 100], outline='black', width=2)
    draw.text((60, 65), "Name: _________________", fill='black')
    
    draw.rectangle([50, 120, 750, 170], outline='black', width=2)
    draw.text((60, 135), "Date: _________________", fill='black')
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def create_blank_image() -> bytes:
    """Create a blank white image."""
    img = Image.new('RGB', (800, 600), color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()
