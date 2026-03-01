"""
Unit tests for TextractClient.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from io import BytesIO
from fastapi import UploadFile

import sys
sys.path.insert(0, 'AFIRGEN FINAL')

from services.aws.textract_client import (
    TextractClient,
    ExtractionResult,
    FormField,
    TextractError,
    ValidationError
)


@pytest.fixture
def textract_client():
    """Create TextractClient instance for testing."""
    with pytest.mock.patch('boto3.client'):
        client = TextractClient(
            region='us-east-1',
            s3_bucket='test-bucket',
            kms_key_id='test-kms-key'
        )
        return client


@pytest.fixture
def mock_image_file():
    """Create mock image file."""
    content = b"fake image content"
    file = UploadFile(
        filename="test_image.jpg",
        file=BytesIO(content)
    )
    return file


class TestTextractClient:
    """Test suite for TextractClient."""
    
    def test_init(self, textract_client):
        """Test client initialization."""
        assert textract_client.s3_bucket == 'test-bucket'
        assert textract_client.kms_key_id == 'test-kms-key'
        assert textract_client.region == 'us-east-1'
        assert textract_client.max_retries == 3
    
    def test_supported_formats(self, textract_client):
        """Test supported image formats."""
        expected_formats = ['jpeg', 'jpg', 'png', 'pdf']
        assert textract_client.SUPPORTED_FORMATS == expected_formats
    
    @pytest.mark.asyncio
    async def test_extract_text_invalid_format(self, textract_client):
        """Test extraction with invalid image format."""
        invalid_file = UploadFile(
            filename="test.txt",
            file=BytesIO(b"content")
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await textract_client.extract_text(invalid_file)
        
        assert "Unsupported image format" in str(exc_info.value)
    
    
    @pytest.mark.asyncio
    async def test_extract_text_success_no_forms(self, textract_client, mock_image_file):
        """Test successful text extraction without forms."""
        # Mock S3 upload
        textract_client._upload_to_s3 = AsyncMock(
            return_value='s3://test-bucket/test.jpg'
        )
        
        # Mock text detection
        textract_client._detect_document_text = AsyncMock(
            return_value={
                'Blocks': [
                    {
                        'BlockType': 'LINE',
                        'Text': 'Line 1',
                        'Confidence': 95.0,
                        'Page': 1
                    },
                    {
                        'BlockType': 'LINE',
                        'Text': 'Line 2',
                        'Confidence': 90.0,
                        'Page': 1
                    }
                ]
            }
        )
        
        # Mock cleanup
        textract_client._cleanup_s3_file = AsyncMock()
        
        result = await textract_client.extract_text(mock_image_file, extract_forms=False)
        
        assert isinstance(result, ExtractionResult)
        assert 'Line 1' in result.text
        assert 'Line 2' in result.text
        assert result.form_fields == []
        assert result.page_count == 1
        assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_extract_text_success_with_forms(self, textract_client, mock_image_file):
        """Test successful text extraction with forms."""
        # Mock S3 upload
        textract_client._upload_to_s3 = AsyncMock(
            return_value='s3://test-bucket/test.jpg'
        )
        
        # Mock document analysis
        textract_client._analyze_document = AsyncMock(
            return_value={
                'Blocks': [
                    {
                        'BlockType': 'LINE',
                        'Text': 'Form data',
                        'Confidence': 95.0,
                        'Page': 1
                    },
                    {
                        'BlockType': 'KEY_VALUE_SET',
                        'Id': 'key1',
                        'EntityTypes': ['KEY'],
                        'Confidence': 90.0,
                        'Relationships': [
                            {'Type': 'VALUE', 'Ids': ['value1']},
                            {'Type': 'CHILD', 'Ids': ['word1']}
                        ]
                    },
                    {
                        'BlockType': 'KEY_VALUE_SET',
                        'Id': 'value1',
                        'EntityTypes': ['VALUE'],
                        'Confidence': 85.0,
                        'Relationships': [
                            {'Type': 'CHILD', 'Ids': ['word2']}
                        ]
                    },
                    {
                        'BlockType': 'WORD',
                        'Id': 'word1',
                        'Text': 'Name'
                    },
                    {
                        'BlockType': 'WORD',
                        'Id': 'word2',
                        'Text': 'John'
                    }
                ]
            }
        )
        
        # Mock cleanup
        textract_client._cleanup_s3_file = AsyncMock()
        
        result = await textract_client.extract_text(mock_image_file, extract_forms=True)
        
        assert isinstance(result, ExtractionResult)
        assert 'Form data' in result.text
        assert len(result.form_fields) > 0
        assert result.page_count == 1
    
    def test_extract_text_from_response(self, textract_client):
        """Test text extraction from response."""
        response = {
            'Blocks': [
                {'BlockType': 'LINE', 'Text': 'First line'},
                {'BlockType': 'LINE', 'Text': 'Second line'},
                {'BlockType': 'WORD', 'Text': 'ignored'}
            ]
        }
        
        text = textract_client._extract_text_from_response(response)
        assert text == 'First line\nSecond line'
    
    def test_calculate_confidence(self, textract_client):
        """Test confidence calculation."""
        response = {
            'Blocks': [
                {'Confidence': 95.0},
                {'Confidence': 90.0},
                {'Confidence': 85.0}
            ]
        }
        
        confidence = textract_client._calculate_confidence(response)
        assert 0.89 < confidence < 0.91  # Average of 0.95, 0.90, 0.85
    
    def test_count_pages(self, textract_client):
        """Test page counting."""
        response = {
            'Blocks': [
                {'Page': 1},
                {'Page': 1},
                {'Page': 2},
                {'Page': 3}
            ]
        }
        
        page_count = textract_client._count_pages(response)
        assert page_count == 3
    
    def test_get_file_extension(self, textract_client):
        """Test file extension extraction."""
        assert textract_client._get_file_extension('test.jpg') == 'jpg'
        assert textract_client._get_file_extension('test.image.png') == 'png'
        assert textract_client._get_file_extension('TEST.JPEG') == 'jpeg'
        assert textract_client._get_file_extension('noextension') == ''
    
    def test_parse_s3_uri(self, textract_client):
        """Test S3 URI parsing."""
        bucket, key = textract_client._parse_s3_uri('s3://my-bucket/path/to/file.jpg')
        assert bucket == 'my-bucket'
        assert key == 'path/to/file.jpg'
