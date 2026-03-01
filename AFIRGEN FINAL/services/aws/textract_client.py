"""
TextractClient for document OCR using Amazon Textract.
Supports text and form extraction with retry logic and S3 integration.
"""

import asyncio
import logging
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile


logger = logging.getLogger(__name__)


@dataclass
class FormField:
    """Extracted form field."""
    key: str
    value: str
    confidence: float


@dataclass
class ExtractionResult:
    """Result of document text extraction."""
    text: str
    form_fields: List[FormField]
    confidence: float
    page_count: int


class TextractError(Exception):
    """Exception raised for Textract errors."""
    pass


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class TextractClient:
    """
    Manages document text extraction using Amazon Textract.
    Supports both plain text and structured form data extraction.
    """
    
    SUPPORTED_FORMATS = ['jpeg', 'jpg', 'png', 'pdf']
    
    def __init__(
        self,
        region: str,
        s3_bucket: str,
        kms_key_id: Optional[str] = None,
        max_retries: int = 3
    ):
        """
        Initialize TextractClient.
        
        Args:
            region: AWS region
            s3_bucket: S3 bucket for temporary image files
            kms_key_id: KMS key ID for S3 encryption
            max_retries: Maximum retry attempts
        """
        self.textract_client = boto3.client('textract', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.s3_bucket = s3_bucket
        self.kms_key_id = kms_key_id
        self.max_retries = max_retries
        self.region = region
    
    async def extract_text(
        self,
        image_file: UploadFile,
        extract_forms: bool = True
    ) -> ExtractionResult:
        """
        Extract text from document image.
        
        Args:
            image_file: Image file (JPEG, PNG, PDF)
            extract_forms: Whether to extract structured form data
        
        Returns:
            ExtractionResult with extracted text and form data
        
        Raises:
            ValidationError: Invalid file format
            TextractError: Extraction failed after retries
        """
        # Validate file format
        file_extension = self._get_file_extension(image_file.filename)
        if file_extension not in self.SUPPORTED_FORMATS:
            raise ValidationError(
                f"Unsupported image format: {file_extension}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        s3_uri = None
        
        try:
            # Upload to S3
            s3_uri = await self._upload_to_s3(image_file)
            logger.info(f"Uploaded image file to {s3_uri}")
            
            # Extract text
            if extract_forms:
                response = await self._analyze_document(s3_uri)
            else:
                response = await self._detect_document_text(s3_uri)
            
            # Parse response
            text = self._extract_text_from_response(response)
            form_fields = self._extract_forms_from_response(response) if extract_forms else []
            confidence = self._calculate_confidence(response)
            page_count = self._count_pages(response)
            
            return ExtractionResult(
                text=text,
                form_fields=form_fields,
                confidence=confidence,
                page_count=page_count
            )
            
        except ClientError as e:
            logger.error(f"AWS error during text extraction: {e}")
            raise TextractError(f"Text extraction failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during text extraction: {e}")
            raise TextractError(f"Text extraction failed: {str(e)}")
        finally:
            # Cleanup
            if s3_uri:
                await self._cleanup_s3_file(s3_uri)
    
    async def _upload_to_s3(self, file: UploadFile) -> str:
        """
        Upload file to S3 with SSE-KMS encryption.
        
        Args:
            file: Image file to upload
        
        Returns:
            S3 URI of uploaded file
        """
        file_key = f"textract-temp/{uuid.uuid4()}/{file.filename}"
        
        # Read file content
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Upload with encryption
        extra_args = {'ServerSideEncryption': 'aws:kms'}
        if self.kms_key_id:
            extra_args['SSEKMSKeyId'] = self.kms_key_id
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=file_key,
                Body=content,
                **extra_args
            )
        )
        
        return f"s3://{self.s3_bucket}/{file_key}"
    
    async def _detect_document_text(self, s3_uri: str) -> Dict[str, Any]:
        """
        Call Textract DetectDocumentText API.
        
        Args:
            s3_uri: S3 URI of document
        
        Returns:
            Textract response
        """
        bucket, key = self._parse_s3_uri(s3_uri)
        
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.textract_client.detect_document_text(
                        Document={'S3Object': {'Bucket': bucket, 'Name': key}}
                    )
                )
                return response
            except ClientError as e:
                retry_count += 1
                if retry_count >= self.max_retries:
                    raise
                
                # Exponential backoff
                wait_time = min(2 ** retry_count, 30)
                await asyncio.sleep(wait_time)
        
        raise TextractError("Max retries exceeded")
    
    async def _analyze_document(self, s3_uri: str) -> Dict[str, Any]:
        """
        Call Textract AnalyzeDocument API for forms.
        
        Args:
            s3_uri: S3 URI of document
        
        Returns:
            Textract response
        """
        bucket, key = self._parse_s3_uri(s3_uri)
        
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.textract_client.analyze_document(
                        Document={'S3Object': {'Bucket': bucket, 'Name': key}},
                        FeatureTypes=['FORMS']
                    )
                )
                return response
            except ClientError as e:
                retry_count += 1
                if retry_count >= self.max_retries:
                    raise
                
                # Exponential backoff
                wait_time = min(2 ** retry_count, 30)
                await asyncio.sleep(wait_time)
        
        raise TextractError("Max retries exceeded")
    
    async def _cleanup_s3_file(self, s3_uri: str):
        """
        Delete temporary file from S3.
        
        Args:
            s3_uri: S3 URI to delete
        """
        try:
            bucket, key = self._parse_s3_uri(s3_uri)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.delete_object(Bucket=bucket, Key=key)
            )
            logger.info(f"Cleaned up S3 file: {s3_uri}")
        except Exception as e:
            logger.warning(f"Failed to cleanup S3 file {s3_uri}: {e}")
    
    def _extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract plain text from Textract response.
        
        Args:
            response: Textract API response
        
        Returns:
            Extracted text
        """
        blocks = response.get('Blocks', [])
        lines = []
        
        for block in blocks:
            if block['BlockType'] == 'LINE':
                lines.append(block.get('Text', ''))
        
        return '\n'.join(lines)
    
    def _extract_forms_from_response(self, response: Dict[str, Any]) -> List[FormField]:
        """
        Extract form fields from Textract response.
        
        Args:
            response: Textract API response
        
        Returns:
            List of form fields
        """
        blocks = response.get('Blocks', [])
        key_map = {}
        value_map = {}
        block_map = {}
        
        # Build block map
        for block in blocks:
            block_id = block['Id']
            block_map[block_id] = block
            
            if block['BlockType'] == 'KEY_VALUE_SET':
                if 'KEY' in block.get('EntityTypes', []):
                    key_map[block_id] = block
                elif 'VALUE' in block.get('EntityTypes', []):
                    value_map[block_id] = block
        
        # Extract key-value pairs
        form_fields = []
        for key_id, key_block in key_map.items():
            value_block = self._find_value_block(key_block, value_map, block_map)
            if value_block:
                key_text = self._get_text(key_block, block_map)
                value_text = self._get_text(value_block, block_map)
                confidence = min(
                    key_block.get('Confidence', 0),
                    value_block.get('Confidence', 0)
                )
                
                form_fields.append(FormField(
                    key=key_text,
                    value=value_text,
                    confidence=confidence / 100.0
                ))
        
        return form_fields
    
    def _find_value_block(
        self,
        key_block: Dict[str, Any],
        value_map: Dict[str, Any],
        block_map: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find value block associated with key block."""
        relationships = key_block.get('Relationships', [])
        for relationship in relationships:
            if relationship['Type'] == 'VALUE':
                for value_id in relationship['Ids']:
                    if value_id in value_map:
                        return value_map[value_id]
        return None
    
    def _get_text(self, block: Dict[str, Any], block_map: Dict[str, Any]) -> str:
        """Get text from block and its children."""
        text = ''
        if 'Relationships' in block:
            for relationship in block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        child = block_map.get(child_id)
                        if child and child['BlockType'] == 'WORD':
                            text += child.get('Text', '') + ' '
        return text.strip()
    
    def _calculate_confidence(self, response: Dict[str, Any]) -> float:
        """Calculate average confidence score."""
        blocks = response.get('Blocks', [])
        confidences = [
            block.get('Confidence', 0) / 100.0
            for block in blocks
            if 'Confidence' in block
        ]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _count_pages(self, response: Dict[str, Any]) -> int:
        """Count number of pages in document."""
        blocks = response.get('Blocks', [])
        pages = set()
        for block in blocks:
            if 'Page' in block:
                pages.add(block['Page'])
        return len(pages) if pages else 1
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    def _parse_s3_uri(self, s3_uri: str) -> tuple:
        """Parse S3 URI into bucket and key."""
        parts = s3_uri.replace('s3://', '').split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''
        return bucket, key

    @staticmethod
    def _is_valid_image_format(filename: str) -> bool:
        """
        Check if filename has a valid image format.
        
        Args:
            filename: Name of the file to validate
        
        Returns:
            True if format is valid, False otherwise
        """
        valid_extensions = {'.jpeg', '.jpg', '.png', '.pdf', '.tiff', '.tif'}
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        return f'.{extension}' in valid_extensions
