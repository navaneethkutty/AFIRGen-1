"""
TranscribeClient for audio transcription using Amazon Transcribe.
Supports 10 Indian languages with retry logic and S3 integration.
"""

import asyncio
import logging
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile


logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""
    transcript: str
    language_code: str
    confidence: float
    job_name: str
    duration_seconds: float


class TranscribeError(Exception):
    """Exception raised for Transcribe errors."""
    pass


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class TranscribeClient:
    """
    Manages audio transcription using Amazon Transcribe.
    Supports 10 Indian languages with automatic language detection.
    """
    
    SUPPORTED_LANGUAGES = [
        'hi-IN', 'en-IN', 'ta-IN', 'te-IN', 'bn-IN',
        'mr-IN', 'gu-IN', 'kn-IN', 'ml-IN', 'pa-IN'
    ]
    
    SUPPORTED_FORMATS = ['wav', 'mp3', 'mpeg', 'mp4', 'flac']
    
    
    def __init__(
        self,
        region: str,
        s3_bucket: str,
        kms_key_id: Optional[str] = None,
        max_retries: int = 3,
        poll_interval: int = 5,
        max_poll_time: int = 300
    ):
        """
        Initialize TranscribeClient.
        
        Args:
            region: AWS region
            s3_bucket: S3 bucket for temporary audio files
            kms_key_id: KMS key ID for S3 encryption
            max_retries: Maximum retry attempts
            poll_interval: Polling interval in seconds
            max_poll_time: Maximum polling time in seconds
        """
        self.transcribe_client = boto3.client('transcribe', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.s3_bucket = s3_bucket
        self.kms_key_id = kms_key_id
        self.max_retries = max_retries
        self.poll_interval = poll_interval
        self.max_poll_time = max_poll_time
        self.region = region
    
    async def transcribe_audio(
        self,
        audio_file: UploadFile,
        language_code: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio file to text.
        
        Args:
            audio_file: Audio file (WAV, MP3, MPEG, MP4, FLAC)
            language_code: Optional language code (auto-detect if None)
        
        Returns:
            TranscriptionResult with transcript text and metadata
        
        Raises:
            ValidationError: Invalid file format or language code
            TranscribeError: Transcription failed after retries
        """
        # Validate file format
        file_extension = self._get_file_extension(audio_file.filename)
        if file_extension not in self.SUPPORTED_FORMATS:
            raise ValidationError(
                f"Unsupported audio format: {file_extension}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        # Validate language code
        if language_code and language_code not in self.SUPPORTED_LANGUAGES:
            raise ValidationError(
                f"Unsupported language: {language_code}. "
                f"Supported languages: {', '.join(self.SUPPORTED_LANGUAGES)}"
            )
        
        s3_uri = None
        job_name = None
        
        try:
            # Upload to S3
            s3_uri = await self._upload_to_s3(audio_file)
            logger.info(f"Uploaded audio file to {s3_uri}")
            
            # Start transcription job
            job_name = await self._start_transcription_job(s3_uri, language_code)
            logger.info(f"Started transcription job: {job_name}")
            
            # Poll for completion
            result = await self._poll_transcription_job(job_name)
            
            # Extract transcript
            transcript_uri = result['Transcript']['TranscriptFileUri']
            transcript_data = await self._fetch_transcript(transcript_uri)
            
            return TranscriptionResult(
                transcript=transcript_data['results']['transcripts'][0]['transcript'],
                language_code=result.get('LanguageCode', language_code or 'unknown'),
                confidence=self._calculate_confidence(transcript_data),
                job_name=job_name,
                duration_seconds=result.get('MediaSampleRateHertz', 0) / 1000.0
            )
            
        except ClientError as e:
            logger.error(f"AWS error during transcription: {e}")
            raise TranscribeError(f"Transcription failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during transcription: {e}")
            raise TranscribeError(f"Transcription failed: {str(e)}")
        finally:
            # Cleanup
            if s3_uri:
                await self._cleanup_s3_file(s3_uri)
            if job_name:
                await self._delete_transcription_job(job_name)
    
    async def _upload_to_s3(self, file: UploadFile) -> str:
        """
        Upload file to S3 with SSE-KMS encryption.
        
        Args:
            file: Audio file to upload
        
        Returns:
            S3 URI of uploaded file
        """
        file_key = f"transcribe-temp/{uuid.uuid4()}/{file.filename}"
        
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
    
    async def _start_transcription_job(
        self,
        s3_uri: str,
        language_code: Optional[str]
    ) -> str:
        """
        Start Transcribe job and return job name.
        
        Args:
            s3_uri: S3 URI of audio file
            language_code: Language code or None for auto-detect
        
        Returns:
            Job name
        """
        job_name = f"afirgen-transcribe-{uuid.uuid4()}"
        
        params = {
            'TranscriptionJobName': job_name,
            'Media': {'MediaFileUri': s3_uri},
            'MediaFormat': self._get_media_format(s3_uri),
            'OutputBucketName': self.s3_bucket
        }
        
        if language_code:
            params['LanguageCode'] = language_code
        else:
            # Use identify language for auto-detection
            params['IdentifyLanguage'] = True
            params['LanguageOptions'] = self.SUPPORTED_LANGUAGES
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.transcribe_client.start_transcription_job(**params)
        )
        
        return job_name
    
    async def _poll_transcription_job(self, job_name: str) -> Dict[str, Any]:
        """
        Poll job status until completion with exponential backoff.
        
        Args:
            job_name: Transcription job name
        
        Returns:
            Job result dictionary
        
        Raises:
            TranscribeError: Job failed or timed out
        """
        elapsed_time = 0
        retry_count = 0
        
        while elapsed_time < self.max_poll_time:
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.transcribe_client.get_transcription_job(
                        TranscriptionJobName=job_name
                    )
                )
                
                job = response['TranscriptionJob']
                status = job['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    logger.info(f"Transcription job {job_name} completed")
                    return job
                elif status == 'FAILED':
                    failure_reason = job.get('FailureReason', 'Unknown')
                    raise TranscribeError(f"Transcription job failed: {failure_reason}")
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                elapsed_time += self.poll_interval
                
            except ClientError as e:
                retry_count += 1
                if retry_count >= self.max_retries:
                    raise TranscribeError(f"Failed to poll job status: {str(e)}")
                
                # Exponential backoff
                wait_time = min(2 ** retry_count, 30)
                await asyncio.sleep(wait_time)
        
        raise TranscribeError(f"Transcription job timed out after {self.max_poll_time}s")
    
    async def _fetch_transcript(self, transcript_uri: str) -> Dict[str, Any]:
        """
        Fetch transcript JSON from S3.
        
        Args:
            transcript_uri: URI of transcript file
        
        Returns:
            Transcript data dictionary
        """
        import json
        import urllib.request
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: urllib.request.urlopen(transcript_uri).read()
        )
        
        return json.loads(response.decode('utf-8'))
    
    async def _cleanup_s3_file(self, s3_uri: str):
        """
        Delete temporary file from S3.
        
        Args:
            s3_uri: S3 URI to delete
        """
        try:
            # Parse S3 URI
            parts = s3_uri.replace('s3://', '').split('/', 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ''
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.delete_object(Bucket=bucket, Key=key)
            )
            logger.info(f"Cleaned up S3 file: {s3_uri}")
        except Exception as e:
            logger.warning(f"Failed to cleanup S3 file {s3_uri}: {e}")
    
    async def _delete_transcription_job(self, job_name: str):
        """
        Delete transcription job to cleanup resources.
        
        Args:
            job_name: Job name to delete
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.transcribe_client.delete_transcription_job(
                    TranscriptionJobName=job_name
                )
            )
            logger.info(f"Deleted transcription job: {job_name}")
        except Exception as e:
            logger.warning(f"Failed to delete transcription job {job_name}: {e}")
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    def _get_media_format(self, s3_uri: str) -> str:
        """Determine media format from S3 URI."""
        extension = self._get_file_extension(s3_uri)
        format_map = {
            'wav': 'wav',
            'mp3': 'mp3',
            'mpeg': 'mp3',
            'mp4': 'mp4',
            'flac': 'flac'
        }
        return format_map.get(extension, 'mp3')
    
    def _calculate_confidence(self, transcript_data: Dict[str, Any]) -> float:
        """
        Calculate average confidence score from transcript.
        
        Args:
            transcript_data: Transcript JSON data
        
        Returns:
            Average confidence score (0.0 to 1.0)
        """
        items = transcript_data.get('results', {}).get('items', [])
        if not items:
            return 0.0
        
        confidences = [
            float(item.get('alternatives', [{}])[0].get('confidence', 0))
            for item in items
            if 'alternatives' in item
        ]
        
        return sum(confidences) / len(confidences) if confidences else 0.0

    @staticmethod
    def _is_valid_audio_format(filename: str) -> bool:
        """
        Check if filename has a valid audio format.
        
        Args:
            filename: Name of the file to validate
        
        Returns:
            True if format is valid, False otherwise
        """
        valid_extensions = {'.wav', '.mp3', '.mpeg', '.mp4', '.flac'}
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        return f'.{extension}' in valid_extensions

    @staticmethod
    def _is_valid_audio_format(filename: str) -> bool:
        """
        Check if filename has a valid audio format.

        Args:
            filename: Name of the file to validate

        Returns:
            True if format is valid, False otherwise
        """
        valid_extensions = {'.wav', '.mp3', '.mpeg', '.mp4', '.flac'}
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        return f'.{extension}' in valid_extensions
