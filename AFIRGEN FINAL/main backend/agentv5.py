"""
AFIRGen Backend - AWS Bedrock Architecture
Minimal, production-ready FIR generation system

This is a clean implementation using only AWS managed services:
- AWS Bedrock (Claude 3 Sonnet) for text generation
- AWS Transcribe for audio transcription
- AWS Textract for document OCR
- Amazon RDS MySQL for persistent storage
- Amazon S3 for temporary file storage
- SQLite for session management
"""

# ============================================================================
# IMPORTS
# ============================================================================
import os
import sys
import json
import uuid
import time
import logging
import sqlite3
import threading
import asyncio
import io
from datetime import datetime, timedelta
from typing import Optional, Literal, Dict, List, Any
from pathlib import Path
from contextlib import asynccontextmanager

import boto3
from botocore.exceptions import ClientError
import mysql.connector
from mysql.connector import pooling
from fastapi import FastAPI, File, UploadFile, Header, HTTPException, Request, Query, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import inch
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ============================================================================
# CONFIGURATION
# ============================================================================
class Config:
    """Application configuration from environment variables"""
    
    # AWS Configuration
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    BEDROCK_MODEL_ID: str = os.getenv(
        "BEDROCK_MODEL_ID",
        "amazon.nova-pro-v1:0"  # Amazon Nova Pro (no marketplace needed)
    )
    
    # Database Configuration
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "admin")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "afirgen_db")
    
    # API Configuration
    API_KEY: str = os.getenv("API_KEY", "")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    
    # File Validation
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    ALLOWED_AUDIO_EXTENSIONS: set = {".wav", ".mp3", ".mpeg"}
    ALLOWED_IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png"}
    
    # Timeouts
    TRANSCRIBE_TIMEOUT_SECONDS: int = int(os.getenv("TRANSCRIBE_TIMEOUT_SECONDS", "180"))
    BEDROCK_TIMEOUT_SECONDS: int = int(os.getenv("BEDROCK_TIMEOUT_SECONDS", "60"))
    
    # Retry Configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))
    RETRY_DELAY_SECONDS: int = int(os.getenv("RETRY_DELAY_SECONDS", "2"))
    
    def validate(self) -> None:
        """Validate required configuration"""
        required = {
            "S3_BUCKET_NAME": self.S3_BUCKET_NAME,
            "DB_HOST": self.DB_HOST,
            "DB_PASSWORD": self.DB_PASSWORD,
            "API_KEY": self.API_KEY
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
    
    def get_mysql_config(self) -> dict:
        """Get MySQL connection configuration"""
        return {
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "database": self.DB_NAME
        }


# ============================================================================
# LOGGING SETUP
# ============================================================================
def setup_logging():
    """Configure structured JSON logging"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        handlers=[
            logging.FileHandler(log_dir / "main_backend.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


# ============================================================================
# AWS SERVICE CLIENTS
# ============================================================================
class AWSServiceClients:
    """Manages AWS service clients"""
    
    def __init__(self, region: str):
        self.region = region
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        self.transcribe = boto3.client('transcribe', region_name=region)
        self.textract = boto3.client('textract', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.logger = logging.getLogger(__name__)
    
    def invoke_claude(self, prompt: str, max_tokens: int = 4096) -> str:
        """Invoke Claude via Bedrock Native API with retry logic and exponential backoff"""
        retries = 0
        last_error = None
        
        while retries <= config.MAX_RETRIES:
            try:
                start_time = time.time()
                
                # Format the request using the model's native structure
                native_request = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": 0.5,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": prompt}]
                        }
                    ]
                }
                
                # Convert to JSON
                request_body = json.dumps(native_request)
                
                self.logger.info(f"Invoking Bedrock Claude (attempt {retries + 1}/{config.MAX_RETRIES + 1})")
                
                response = self.bedrock_runtime.invoke_model(
                    modelId=config.BEDROCK_MODEL_ID,
                    body=request_body
                )
                
                # Decode the response body
                model_response = json.loads(response["body"].read())
                
                # Extract response text
                result = model_response["content"][0]["text"]
                
                duration = time.time() - start_time
                self.logger.info(f"Bedrock invocation successful (duration: {duration:.2f}s)")
                
                return result
            
            except Exception as e:
                last_error = e
                retries += 1
                
                # Log with service name, operation, error details, and stack trace
                error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else type(e).__name__
                error_message = str(e)
                
                self.logger.error(
                    f"AWS service error - Service: bedrock-runtime, Operation: invoke_model, "
                    f"Error Code: {error_code}, Message: {error_message}, "
                    f"Attempt: {retries}/{config.MAX_RETRIES + 1}",
                    exc_info=True
                )
                
                if retries <= config.MAX_RETRIES:
                    # Exponential backoff: 2^(retries-1) * RETRY_DELAY_SECONDS
                    delay = (2 ** (retries - 1)) * config.RETRY_DELAY_SECONDS
                    self.logger.info(f"Retrying in {delay} seconds (exponential backoff)...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Bedrock invocation failed after {config.MAX_RETRIES + 1} attempts")
                    raise last_error
    
    def transcribe_audio(self, s3_uri: str, language_code: str) -> str:
        """Transcribe audio file using AWS Transcribe with retry logic and exponential backoff"""
        job_name = f"transcribe-{uuid.uuid4()}"
        retries = 0
        last_error = None
        
        # Start transcription job with retry and exponential backoff
        while retries <= config.MAX_RETRIES:
            try:
                self.logger.info(f"Starting Transcribe job: {job_name} (language: {language_code})")
                
                self.transcribe.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={'MediaFileUri': s3_uri},
                    MediaFormat='mp3',  # Adjust based on file type if needed
                    LanguageCode=language_code
                )
                break
            
            except Exception as e:
                last_error = e
                retries += 1
                
                # Log with service name, operation, error details, and stack trace
                error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else type(e).__name__
                error_message = str(e)
                
                self.logger.error(
                    f"AWS service error - Service: transcribe, Operation: start_transcription_job, "
                    f"Error Code: {error_code}, Message: {error_message}, "
                    f"Attempt: {retries}/{config.MAX_RETRIES + 1}",
                    exc_info=True
                )
                
                if retries <= config.MAX_RETRIES:
                    # Exponential backoff: 2^(retries-1) * RETRY_DELAY_SECONDS
                    delay = (2 ** (retries - 1)) * config.RETRY_DELAY_SECONDS
                    self.logger.info(f"Retrying in {delay} seconds (exponential backoff)...")
                    time.sleep(delay)
                else:
                    raise last_error
        
        # Poll job status
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > config.TRANSCRIBE_TIMEOUT_SECONDS:
                self.logger.error(f"Transcribe job timeout after {config.TRANSCRIBE_TIMEOUT_SECONDS}s")
                raise TimeoutError(f"Transcription timeout after {config.TRANSCRIBE_TIMEOUT_SECONDS} seconds")
            
            try:
                response = self.transcribe.get_transcription_job(TranscriptionJobName=job_name)
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                self.logger.info(f"Transcribe job status: {status} (elapsed: {elapsed:.1f}s)")
                
                if status == 'COMPLETED':
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    
                    # Download transcript
                    import httpx
                    transcript_response = httpx.get(transcript_uri)
                    transcript_data = transcript_response.json()
                    transcript_text = transcript_data['results']['transcripts'][0]['transcript']
                    
                    self.logger.info(f"Transcription completed successfully (length: {len(transcript_text)} chars)")
                    return transcript_text
                
                elif status == 'FAILED':
                    failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown')
                    self.logger.error(
                        f"AWS service error - Service: transcribe, Operation: get_transcription_job, "
                        f"Error Code: TranscriptionFailed, Message: {failure_reason}",
                        exc_info=True
                    )
                    raise Exception(f"Transcription failed: {failure_reason}")
                
                # Wait before polling again
                time.sleep(5)
            
            except Exception as e:
                if "FAILED" in str(e) or "failed" in str(e):
                    raise
                
                # Log polling errors with service details
                error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else type(e).__name__
                self.logger.error(
                    f"AWS service error - Service: transcribe, Operation: get_transcription_job, "
                    f"Error Code: {error_code}, Message: {str(e)}",
                    exc_info=True
                )
                time.sleep(5)
    
    def extract_text_from_image(self, s3_uri: str) -> str:
        """Extract text from image using AWS Textract with retry logic and exponential backoff"""
        retries = 0
        last_error = None
        
        # Parse S3 URI
        parts = s3_uri.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]
        
        while retries <= config.MAX_RETRIES:
            try:
                self.logger.info(f"Extracting text from image: {s3_uri} (attempt {retries + 1}/{config.MAX_RETRIES + 1})")
                
                response = self.textract.detect_document_text(
                    Document={
                        'S3Object': {
                            'Bucket': bucket,
                            'Name': key
                        }
                    }
                )
                
                # Extract text from blocks
                text_blocks = []
                for block in response['Blocks']:
                    if block['BlockType'] == 'LINE':
                        text_blocks.append(block['Text'])
                
                extracted_text = '\n'.join(text_blocks)
                
                if not extracted_text:
                    self.logger.warning("Textract returned empty text")
                    raise Exception("No text extracted from image")
                
                self.logger.info(f"Text extraction successful (length: {len(extracted_text)} chars)")
                return extracted_text
            
            except Exception as e:
                last_error = e
                retries += 1
                
                # Log with service name, operation, error details, and stack trace
                error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else type(e).__name__
                error_message = str(e)
                
                self.logger.error(
                    f"AWS service error - Service: textract, Operation: detect_document_text, "
                    f"Error Code: {error_code}, Message: {error_message}, "
                    f"Attempt: {retries}/{config.MAX_RETRIES + 1}",
                    exc_info=True
                )
                
                if retries <= config.MAX_RETRIES:
                    # Exponential backoff: 2^(retries-1) * RETRY_DELAY_SECONDS
                    delay = (2 ** (retries - 1)) * config.RETRY_DELAY_SECONDS
                    self.logger.info(f"Retrying in {delay} seconds (exponential backoff)...")
                    time.sleep(delay)
                else:
                    raise last_error
    
    def upload_to_s3(self, file_bytes: bytes, key: str, bucket: str) -> str:
        """Upload file to S3 with encryption, retry logic, and exponential backoff"""
        retries = 0
        last_error = None
        
        while retries <= config.MAX_RETRIES:
            try:
                self.logger.info(f"Uploading to S3: s3://{bucket}/{key} (attempt {retries + 1}/{config.MAX_RETRIES + 1})")
                
                self.s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=file_bytes,
                    ServerSideEncryption='AES256'
                )
                
                s3_uri = f"s3://{bucket}/{key}"
                self.logger.info(f"S3 upload successful: {s3_uri}")
                return s3_uri
            
            except Exception as e:
                last_error = e
                retries += 1
                
                # Log with service name, operation, error details, and stack trace
                error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else type(e).__name__
                error_message = str(e)
                
                self.logger.error(
                    f"AWS service error - Service: s3, Operation: put_object, "
                    f"Error Code: {error_code}, Message: {error_message}, "
                    f"Bucket: {bucket}, Key: {key}, Attempt: {retries}/{config.MAX_RETRIES + 1}",
                    exc_info=True
                )
                
                if retries <= config.MAX_RETRIES:
                    # Exponential backoff: 2^(retries-1) * RETRY_DELAY_SECONDS
                    delay = (2 ** (retries - 1)) * config.RETRY_DELAY_SECONDS
                    self.logger.info(f"Retrying in {delay} seconds (exponential backoff)...")
                    time.sleep(delay)
                else:
                    raise last_error
    
    def delete_from_s3(self, key: str, bucket: str) -> None:
        """Delete file from S3 with retry logic and exponential backoff"""
        retries = 0
        last_error = None
        
        while retries <= config.MAX_RETRIES:
            try:
                self.logger.info(f"Deleting from S3: s3://{bucket}/{key}")
                self.s3.delete_object(Bucket=bucket, Key=key)
                self.logger.info(f"S3 delete successful: s3://{bucket}/{key}")
                return
            
            except Exception as e:
                last_error = e
                retries += 1
                
                # Log with service name, operation, error details, and stack trace
                error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown') if hasattr(e, 'response') else type(e).__name__
                error_message = str(e)
                
                self.logger.error(
                    f"AWS service error - Service: s3, Operation: delete_object, "
                    f"Error Code: {error_code}, Message: {error_message}, "
                    f"Bucket: {bucket}, Key: {key}, Attempt: {retries}/{config.MAX_RETRIES + 1}",
                    exc_info=True
                )
                
                if retries <= config.MAX_RETRIES:
                    # Exponential backoff: 2^(retries-1) * RETRY_DELAY_SECONDS
                    delay = (2 ** (retries - 1)) * config.RETRY_DELAY_SECONDS
                    self.logger.info(f"Retrying in {delay} seconds (exponential backoff)...")
                    time.sleep(delay)
                else:
                    # Log but don't raise - cleanup failures shouldn't break the workflow
                    self.logger.error(f"S3 delete failed after {config.MAX_RETRIES + 1} attempts, continuing anyway")


# ============================================================================
# DATABASE MANAGEMENT
# ============================================================================
class DatabaseManager:
    """Manages MySQL RDS and SQLite connections"""
    
    def __init__(self, mysql_config: dict):
        self.logger = logging.getLogger(__name__)
        
        # MySQL connection pool
        self.mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="afirgen_pool",
            pool_size=5,
            **mysql_config
        )
        
        # SQLite for sessions
        self.sqlite_conn = sqlite3.connect('sessions.db', check_same_thread=False)
        self.sqlite_lock = threading.Lock()
        
        self._initialize_tables()
    
    def _initialize_tables(self) -> None:
            """Create tables if they don't exist"""
            # MySQL tables
            fir_records_table = """
            CREATE TABLE IF NOT EXISTS fir_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fir_number VARCHAR(50) UNIQUE NOT NULL,
                session_id VARCHAR(100) NOT NULL,
                complaint_text TEXT NOT NULL,
                fir_content JSON NOT NULL,
                violations_json JSON NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_fir_number (fir_number),
                INDEX idx_session_id (session_id),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            );
            """

            # Updated schema with category and source fields
            ipc_sections_table = """
            CREATE TABLE IF NOT EXISTS ipc_sections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                section_number VARCHAR(20) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL,
                penalty VARCHAR(500),
                category VARCHAR(200),
                source VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_section_number (section_number),
                INDEX idx_category (category),
                FULLTEXT idx_description (description, title)
            );
            """

            try:
                conn = self.mysql_pool.get_connection()
                cursor = conn.cursor()
                cursor.execute(fir_records_table)
                cursor.execute(ipc_sections_table)
                conn.commit()
                cursor.close()
                conn.close()
                self.logger.info("MySQL tables initialized")
            except Exception as e:
                self.logger.error(f"MySQL table initialization failed: {str(e)}")

            # SQLite sessions table
            with self.sqlite_lock:
                cursor = self.sqlite_conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        transcript TEXT,
                        summary TEXT,
                        violations TEXT,
                        fir_content TEXT,
                        fir_number TEXT,
                        error TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_at ON sessions(created_at)
                """)
                self.sqlite_conn.commit()
                self.logger.info("SQLite tables initialized")


    
    def insert_fir_record(self, fir_data: dict) -> str:
        """Insert FIR record and return fir_number"""
        try:
            conn = self.mysql_pool.get_connection()
            cursor = conn.cursor()
            
            query = """
            INSERT INTO fir_records 
            (fir_number, session_id, complaint_text, fir_content, violations_json, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                fir_data['fir_number'],
                fir_data['session_id'],
                fir_data['complaint_text'],
                json.dumps(fir_data['fir_content']),
                json.dumps(fir_data['violations_json']),
                fir_data.get('status', 'draft')
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info(f"FIR record inserted: {fir_data['fir_number']}")
            return fir_data['fir_number']
        
        except Exception as e:
            # Log with SQL query and error details
            self.logger.error(
                f"Database error - Operation: insert_fir_record, "
                f"SQL: INSERT INTO fir_records (fir_number, session_id, complaint_text, fir_content, violations_json, status) VALUES (...), "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    
    def get_fir_by_number(self, fir_number: str) -> dict:
        """Retrieve FIR by number"""
        try:
            conn = self.mysql_pool.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
            SELECT fir_number, session_id, complaint_text, fir_content, 
                   violations_json, status, created_at, updated_at
            FROM fir_records
            WHERE fir_number = %s
            """
            
            cursor.execute(query, (fir_number,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                # Parse JSON fields
                result['fir_content'] = json.loads(result['fir_content'])
                result['violations_json'] = json.loads(result['violations_json'])
                # Convert datetime to string
                result['created_at'] = result['created_at'].isoformat()
                result['updated_at'] = result['updated_at'].isoformat()
                
                self.logger.info(f"FIR retrieved: {fir_number}")
                return result
            else:
                self.logger.warning(f"FIR not found: {fir_number}")
                return None
        
        except Exception as e:
            # Log with SQL query and error details
            self.logger.error(
                f"Database error - Operation: get_fir_by_number, "
                f"SQL: SELECT * FROM fir_records WHERE fir_number = '{fir_number}', "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    
    def list_firs(self, limit: int = 20, offset: int = 0) -> dict:
        """List FIRs with pagination
        
        Returns a dictionary with:
        - firs: list of FIR records
        - total: total count of FIRs in database
        """
        try:
            conn = self.mysql_pool.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM fir_records"
            cursor.execute(count_query)
            total = cursor.fetchone()['total']
            
            # Get paginated results
            query = """
            SELECT fir_number, session_id, complaint_text, fir_content, 
                   violations_json, status, created_at, updated_at
            FROM fir_records
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """
            
            cursor.execute(query, (limit, offset))
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Parse JSON fields and convert datetime
            for result in results:
                result['fir_content'] = json.loads(result['fir_content'])
                result['violations_json'] = json.loads(result['violations_json'])
                result['created_at'] = result['created_at'].isoformat()
                result['updated_at'] = result['updated_at'].isoformat()
            
            self.logger.info(f"Listed {len(results)} FIRs out of {total} total (limit: {limit}, offset: {offset})")
            return {
                'firs': results,
                'total': total
            }
        
        except Exception as e:
            # Log with SQL query and error details
            self.logger.error(
                f"Database error - Operation: list_firs, "
                f"SQL: SELECT * FROM fir_records ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}, "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    
    def update_fir_status(self, fir_number: str, status: str) -> None:
        """Update FIR status to 'finalized' or other status"""
        try:
            conn = self.mysql_pool.get_connection()
            cursor = conn.cursor()
            
            query = """
            UPDATE fir_records
            SET status = %s
            WHERE fir_number = %s
            """
            
            cursor.execute(query, (status, fir_number))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            self.logger.info(f"FIR status updated: {fir_number} -> {status}")
        
        except Exception as e:
            # Log with SQL query and error details
            self.logger.error(
                f"Database error - Operation: update_fir_status, "
                f"SQL: UPDATE fir_records SET status = '{status}' WHERE fir_number = '{fir_number}', "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    
    def get_ipc_sections(self, keywords: list = None) -> list:
        """Retrieve IPC sections using SQL LIKE queries"""
        try:
            conn = self.mysql_pool.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            if keywords and len(keywords) > 0:
                # Build LIKE query for keyword matching
                conditions = []
                params = []
                
                for keyword in keywords[:5]:  # Limit to 5 keywords
                    keyword_pattern = f"%{keyword}%"
                    conditions.append("(description LIKE %s OR title LIKE %s)")
                    params.extend([keyword_pattern, keyword_pattern])
                
                query = f"""
                SELECT section_number, title, description, penalty, category, source
                FROM ipc_sections
                WHERE {' OR '.join(conditions)}
                LIMIT 10
                """
                
                cursor.execute(query, params)
            else:
                # Return all sections if no keywords
                query = """
                SELECT section_number, title, description, penalty, category, source
                FROM ipc_sections
                LIMIT 10
                """
                cursor.execute(query)
            
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            self.logger.info(f"Retrieved {len(results)} IPC sections")
            return results
        
        except Exception as e:
            # Log with SQL query and error details
            self.logger.error(
                f"Database error - Operation: get_ipc_sections, "
                f"SQL: SELECT * FROM ipc_sections WHERE description LIKE '%...%' OR title LIKE '%...%', "
                f"Error: {str(e)}",
                exc_info=True
            )
            # Return empty list on error to allow workflow to continue
            return []
    
    def load_ipc_sections(self, json_file_path: str) -> None:
        """Load IPC sections from JSON file on first startup"""
        try:
            conn = self.mysql_pool.get_connection()
            cursor = conn.cursor()
            
            # Check if table already has data
            cursor.execute("SELECT COUNT(*) FROM ipc_sections")
            count = cursor.fetchone()[0]
            
            if count > 0:
                self.logger.info(f"IPC sections already loaded: {count} sections")
                cursor.close()
                conn.close()
                return
            
            # Load from JSON file
            if not os.path.exists(json_file_path):
                self.logger.warning(f"IPC sections JSON file not found: {json_file_path}")
                cursor.close()
                conn.close()
                return
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                sections = json.load(f)
            
            # Insert sections with new fields (category, source)
            query = """
            INSERT INTO ipc_sections (section_number, title, description, penalty, category, source)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            for section in sections:
                cursor.execute(query, (
                    section.get('section_number', ''),
                    section.get('title', ''),
                    section.get('description', ''),
                    section.get('penalty', ''),
                    section.get('category', ''),
                    section.get('source', '')
                ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info(f"Loaded {len(sections)} IPC sections from {json_file_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to load IPC sections: {str(e)}")
            # Don't raise - this is optional initialization
    
    def create_session(self, session_id: str) -> None:
        """Create new session"""
        try:
            with self.sqlite_lock:
                cursor = self.sqlite_conn.cursor()
                now = time.time()
                
                cursor.execute("""
                    INSERT INTO sessions 
                    (session_id, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (session_id, "processing", now, now))
                
                self.sqlite_conn.commit()
                self.logger.info(f"Session created: {session_id}")
        
        except Exception as e:
            # Log with SQL query and error details
            self.logger.error(
                f"Database error - Operation: create_session, "
                f"SQL: INSERT INTO sessions (session_id, status, created_at, updated_at) VALUES ('{session_id}', 'processing', ...), "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    
    def update_session(self, session_id: str, data: dict) -> None:
        """Update session data"""
        try:
            with self.sqlite_lock:
                cursor = self.sqlite_conn.cursor()
                now = time.time()
                
                # Build update query dynamically based on provided data
                update_fields = []
                params = []
                
                for key, value in data.items():
                    if key in ['status', 'transcript', 'summary', 'violations', 
                              'fir_content', 'fir_number', 'error']:
                        update_fields.append(f"{key} = ?")
                        # Convert dict/list to JSON string
                        if isinstance(value, (dict, list)):
                            params.append(json.dumps(value))
                        else:
                            params.append(value)
                
                if not update_fields:
                    self.logger.warning(f"No valid fields to update for session: {session_id}")
                    return
                
                # Always update updated_at
                update_fields.append("updated_at = ?")
                params.append(now)
                params.append(session_id)
                
                query = f"""
                    UPDATE sessions
                    SET {', '.join(update_fields)}
                    WHERE session_id = ?
                """
                
                cursor.execute(query, params)
                self.sqlite_conn.commit()
                
                self.logger.info(f"Session updated: {session_id}")
        
        except Exception as e:
            # Log with SQL query and error details
            self.logger.error(
                f"Database error - Operation: update_session, "
                f"SQL: UPDATE sessions SET {', '.join([f'{k}=?' for k in data.keys()])} WHERE session_id = '{session_id}', "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    
    def get_session(self, session_id: str) -> dict:
        """Retrieve session data"""
        try:
            with self.sqlite_lock:
                cursor = self.sqlite_conn.cursor()
                cursor.row_factory = sqlite3.Row
                
                cursor.execute("""
                    SELECT session_id, status, transcript, summary, violations,
                           fir_content, fir_number, error, created_at, updated_at
                    FROM sessions
                    WHERE session_id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                
                if row:
                    result = dict(row)
                    
                    # Parse JSON fields
                    if result.get('violations'):
                        try:
                            result['violations'] = json.loads(result['violations'])
                        except:
                            pass
                    
                    if result.get('fir_content'):
                        try:
                            result['fir_content'] = json.loads(result['fir_content'])
                        except:
                            pass
                    
                    self.logger.info(f"Session retrieved: {session_id}")
                    return result
                else:
                    self.logger.warning(f"Session not found: {session_id}")
                    return None
        
        except Exception as e:
            # Log with SQL query and error details
            self.logger.error(
                f"Database error - Operation: get_session, "
                f"SQL: SELECT * FROM sessions WHERE session_id = '{session_id}', "
                f"Error: {str(e)}",
                exc_info=True
            )
            raise
    
    def cleanup_old_sessions(self) -> None:
        """Delete sessions older than 24 hours"""
        try:
            with self.sqlite_lock:
                cursor = self.sqlite_conn.cursor()
                cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
                
                cursor.execute("""
                    DELETE FROM sessions
                    WHERE created_at < ?
                """, (cutoff_time,))
                
                deleted_count = cursor.rowcount
                self.sqlite_conn.commit()
                
                if deleted_count > 0:
                    self.logger.info(f"Cleaned up {deleted_count} old sessions")
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup old sessions: {str(e)}")
            # Don't raise - cleanup failures shouldn't break the application


# ============================================================================
# FIR GENERATOR
# ============================================================================
class FIRGenerator:
    """Orchestrates FIR generation workflow"""
    
    def __init__(self, aws_clients: AWSServiceClients, db: DatabaseManager):
        """Initialize FIR generator with dependencies"""
        self.aws = aws_clients
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # All 30 required FIR fields
        self.required_fields = [
            "complainant_name",
            "complainant_dob",
            "complainant_nationality",
            "complainant_father_husband_name",
            "complainant_address",
            "complainant_contact",
            "complainant_passport",
            "complainant_occupation",
            "incident_date_from",
            "incident_date_to",
            "incident_time_from",
            "incident_time_to",
            "incident_location",
            "incident_address",
            "incident_description",
            "delayed_reporting_reasons",
            "incident_summary",
            "legal_acts",
            "legal_sections",
            "suspect_details",
            "investigating_officer_name",
            "investigating_officer_rank",
            "witnesses",
            "action_taken",
            "investigation_status",
            "date_of_despatch",
            "investigating_officer_signature",
            "investigating_officer_date",
            "complainant_signature",
            "complainant_date"
        ]
    
    def generate_from_text(self, text: str, session_id: str) -> dict:
        """Generate FIR from complaint text"""
        try:
            self.logger.info(f"Starting FIR generation from text for session {session_id}")
            
            # Stage 1: Generate formal narrative
            self.db.update_session(session_id, {"status": "generating_narrative"})
            narrative = self._generate_formal_narrative(text)
            self.db.update_session(session_id, {"summary": narrative})
            
            # Stage 2: Extract metadata
            self.db.update_session(session_id, {"status": "extracting_metadata"})
            metadata = self._extract_metadata(narrative)
            
            # Stage 3: Retrieve IPC sections
            self.db.update_session(session_id, {"status": "retrieving_ipc_sections"})
            ipc_sections = self._retrieve_ipc_sections(metadata)
            
            # Stage 4: Generate complete FIR
            self.db.update_session(session_id, {"status": "generating_fir"})
            fir_data = self._generate_complete_fir(narrative, metadata, ipc_sections)
            
            # Stage 5: Validate FIR fields
            if not self._validate_fir_fields(fir_data):
                raise ValueError("Generated FIR is missing required fields")
            
            # Generate FIR number
            fir_number = self._generate_fir_number()
            
            # Store FIR in database
            self.db.insert_fir_record({
                "fir_number": fir_number,
                "session_id": session_id,
                "complaint_text": text,
                "fir_content": fir_data,
                "violations_json": ipc_sections,
                "status": "draft"
            })
            
            # Update session with complete data
            self.db.update_session(session_id, {
                "status": "completed",
                "fir_content": json.dumps(fir_data),
                "violations": json.dumps(ipc_sections),
                "fir_number": fir_number
            })
            
            self.logger.info(f"FIR generation completed for session {session_id}, FIR number: {fir_number}")
            
            return {
                "fir_number": fir_number,
                "fir_content": fir_data,
                "violations": ipc_sections
            }
            
        except Exception as e:
            self.logger.error(f"FIR generation failed for session {session_id}: {str(e)}")
            self.db.update_session(session_id, {
                "status": "failed",
                "error": str(e)
            })
            raise
    
    def generate_from_audio(self, audio_bytes: bytes, language: str, session_id: str) -> dict:
        """Generate FIR from audio file"""
        audio_key = None
        try:
            self.logger.info(f"Starting FIR generation from audio for session {session_id}")
            
            # Upload audio to S3
            audio_key = f"audio/{uuid.uuid4()}.mp3"
            s3_uri = self.aws.upload_to_s3(audio_bytes, audio_key, os.getenv("S3_BUCKET_NAME"))
            
            # Transcribe audio
            self.db.update_session(session_id, {"status": "transcribing"})
            transcript = self.aws.transcribe_audio(s3_uri, language)
            
            # Delete audio from S3
            self.aws.delete_from_s3(audio_key, os.getenv("S3_BUCKET_NAME"))
            
            # Update session with transcript
            self.db.update_session(session_id, {"transcript": transcript})
            
            # Continue with text workflow
            return self.generate_from_text(transcript, session_id)
            
        except Exception as e:
            self.logger.error(f"Audio FIR generation failed for session {session_id}: {str(e)}")
            # Clean up S3 file even on failure
            if audio_key:
                try:
                    self.aws.delete_from_s3(audio_key, os.getenv("S3_BUCKET_NAME"))
                    self.logger.info(f"Cleaned up S3 file {audio_key} after failure")
                except Exception as cleanup_error:
                    self.logger.warning(f"Failed to clean up S3 file {audio_key}: {str(cleanup_error)}")
            
            # Mark session as failed and store error message
            self.db.update_session(session_id, {
                "status": "failed",
                "error": str(e)
            })
            raise
    
    def generate_from_image(self, image_bytes: bytes, session_id: str) -> dict:
        """Generate FIR from image file"""
        image_key = None
        try:
            self.logger.info(f"Starting FIR generation from image for session {session_id}")
            
            # Upload image to S3
            image_key = f"images/{uuid.uuid4()}.jpg"
            s3_uri = self.aws.upload_to_s3(image_bytes, image_key, os.getenv("S3_BUCKET_NAME"))
            
            # Extract text from image
            self.db.update_session(session_id, {"status": "extracting_text"})
            extracted_text = self.aws.extract_text_from_image(s3_uri)
            
            # Delete image from S3
            self.aws.delete_from_s3(image_key, os.getenv("S3_BUCKET_NAME"))
            
            # Update session with extracted text
            self.db.update_session(session_id, {"transcript": extracted_text})
            
            # Continue with text workflow
            return self.generate_from_text(extracted_text, session_id)
            
        except Exception as e:
            self.logger.error(f"Image FIR generation failed for session {session_id}: {str(e)}")
            # Clean up S3 file even on failure
            if image_key:
                try:
                    self.aws.delete_from_s3(image_key, os.getenv("S3_BUCKET_NAME"))
                    self.logger.info(f"Cleaned up S3 file {image_key} after failure")
                except Exception as cleanup_error:
                    self.logger.warning(f"Failed to clean up S3 file {image_key}: {str(cleanup_error)}")
            
            # Mark session as failed and store error message
            self.db.update_session(session_id, {
                "status": "failed",
                "error": str(e)
            })
            raise
    
    def _generate_formal_narrative(self, complaint_text: str) -> str:
        """Stage 1: Generate formal narrative using Claude"""
        prompt = f"""You are a police officer writing a formal First Information Report (FIR) narrative.

Convert the following complaint into a formal, professional narrative suitable for an official police report:

{complaint_text}

Requirements:
- Use formal, objective language
- Include all relevant details
- Maintain chronological order
- Use third-person perspective
- Be concise but complete

Generate only the formal narrative, no additional commentary."""
        
        narrative = self.aws.invoke_claude(prompt, max_tokens=4096)
        self.logger.info("Formal narrative generated successfully")
        return narrative
    
    def _extract_metadata(self, narrative: str) -> dict:
        """Stage 2: Extract metadata using Claude"""
        prompt = f"""Extract structured metadata from this FIR narrative.

Narrative:
{narrative}

Extract the following information in JSON format:
{{
  "complainant_name": "string",
  "incident_date": "string",
  "incident_time": "string",
  "incident_location": "string",
  "incident_type": "string",
  "keywords": ["string"]
}}

Return only valid JSON, no additional text."""
        
        try:
            response = self.aws.invoke_claude(prompt, max_tokens=2048)
            
            # Parse JSON response
            metadata = json.loads(response)
            self.logger.info("Metadata extracted successfully")
            return metadata
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse metadata JSON: {str(e)}. Using basic defaults.")
            # Use basic defaults if metadata extraction fails
            return {
                "complainant_name": "Unknown",
                "incident_date": "Unknown",
                "incident_time": "Unknown",
                "incident_location": "Unknown",
                "incident_type": "Unknown",
                "keywords": []
            }
        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {str(e)}. Using basic defaults.")
            # Use basic defaults if metadata extraction fails
            return {
                "complainant_name": "Unknown",
                "incident_date": "Unknown",
                "incident_time": "Unknown",
                "incident_location": "Unknown",
                "incident_type": "Unknown",
                "keywords": []
            }
    
    def _retrieve_ipc_sections(self, metadata: dict) -> list:
        """Stage 3: Retrieve relevant IPC sections from MySQL"""
        try:
            keywords = metadata.get("keywords", [])
            if metadata.get("incident_type"):
                keywords.append(metadata["incident_type"])
            
            ipc_sections = self.db.get_ipc_sections(keywords)
            self.logger.info(f"Retrieved {len(ipc_sections)} IPC sections")
            return ipc_sections
            
        except Exception as e:
            self.logger.warning(f"Failed to retrieve IPC sections: {str(e)}. Continuing with empty IPC sections.")
            # Return empty list on failure - workflow can continue
            return []
    
    def _generate_complete_fir(self, narrative: str, metadata: dict, ipc_sections: list) -> dict:
        """Stage 4: Generate complete FIR with all 30 fields using Claude"""
        
        # Format IPC sections for prompt
        if ipc_sections:
            ipc_sections_text = "\n".join([
                f"Section {s['section_number']}: {s['title']}\n{s['description']}\nPenalty: {s.get('penalty', 'N/A')}"
                for s in ipc_sections[:10]  # Limit to top 10 sections
            ])
        else:
            ipc_sections_text = "No specific IPC sections retrieved. Use general applicable sections based on the incident."
            self.logger.info("Generating FIR with empty IPC sections - will use general sections")
        
        prompt = f"""Generate a complete First Information Report (FIR) with all required fields.

Formal Narrative:
{narrative}

Metadata:
{json.dumps(metadata, indent=2)}

Relevant IPC Sections:
{ipc_sections_text}

Generate a complete FIR in JSON format with ALL of the following 30 fields:

{{
  "complainant_name": "Full name of complainant",
  "complainant_dob": "Date of birth (DD/MM/YYYY)",
  "complainant_nationality": "Nationality",
  "complainant_father_husband_name": "Father's or husband's name",
  "complainant_address": "Complete address",
  "complainant_contact": "Contact number",
  "complainant_passport": "Passport number (if applicable, else 'N/A')",
  "complainant_occupation": "Occupation",
  "incident_date_from": "Incident start date (DD/MM/YYYY)",
  "incident_date_to": "Incident end date (DD/MM/YYYY)",
  "incident_time_from": "Incident start time (HH:MM)",
  "incident_time_to": "Incident end time (HH:MM)",
  "incident_location": "Location name",
  "incident_address": "Complete incident address",
  "incident_description": "Detailed description",
  "delayed_reporting_reasons": "Reasons for delay (if any, else 'N/A')",
  "incident_summary": "Brief summary",
  "legal_acts": "Applicable legal acts",
  "legal_sections": "Applicable IPC sections",
  "suspect_details": "Suspect information (if known, else 'Unknown')",
  "investigating_officer_name": "Officer name (use 'TBD' if not assigned)",
  "investigating_officer_rank": "Officer rank (use 'TBD' if not assigned)",
  "witnesses": "Witness information (if any, else 'None')",
  "action_taken": "Initial action taken",
  "investigation_status": "Current status",
  "date_of_despatch": "Date of despatch (DD/MM/YYYY)",
  "investigating_officer_signature": "Placeholder for signature",
  "investigating_officer_date": "Date (DD/MM/YYYY)",
  "complainant_signature": "Placeholder for signature",
  "complainant_date": "Date (DD/MM/YYYY)"
}}

IMPORTANT: 
- All fields must be present
- Use "N/A" or "Unknown" for unavailable information
- Use "None" for empty lists
- Extract information from the narrative
- Use the provided IPC sections for legal_sections field
- Return ONLY the JSON object, no markdown, no explanation

Return the complete JSON object."""
        
        response = self.aws.invoke_claude(prompt, max_tokens=8192)
        
        # Log the raw response for debugging
        self.logger.info(f"Raw FIR response length: {len(response)} chars")
        self.logger.debug(f"Raw FIR response: {response[:500]}...")
        
        # Extract JSON from response (handle markdown code blocks)
        json_str = response.strip()
        
        # Remove markdown code blocks if present
        if json_str.startswith("```"):
            # Find the actual JSON content between ```json and ```
            import re
            match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', json_str, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                # Try to find JSON between any ``` markers
                json_str = json_str.split("```")[1] if "```" in json_str else json_str
                json_str = json_str.replace("json", "", 1).strip()
        
        # Parse JSON response
        try:
            fir_data = json.loads(json_str)
            self.logger.info("Complete FIR generated successfully")
            return fir_data
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse FIR JSON: {str(e)}")
            self.logger.error(f"Attempted to parse: {json_str[:500]}...")
            raise ValueError(f"Failed to generate valid FIR: {str(e)}")
    
    def _validate_fir_fields(self, fir_data: dict) -> bool:
        """Validate that all 30 required fields are present"""
        missing_fields = []
        
        for field in self.required_fields:
            if field not in fir_data:
                missing_fields.append(field)
            elif not fir_data[field] or fir_data[field].strip() == "":
                missing_fields.append(f"{field} (empty)")
        
        if missing_fields:
            self.logger.error(f"FIR validation failed. Missing or empty fields: {', '.join(missing_fields)}")
            return False
        
        self.logger.info("FIR validation passed - all 30 fields present")
        return True
    
    def _generate_fir_number(self) -> str:
        """Generate unique FIR number with format: FIR-YYYYMMDD-XXXXX"""
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Get count of FIRs created today to generate sequence number
        try:
            conn = self.db.mysql_pool.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT COUNT(*) FROM fir_records 
            WHERE fir_number LIKE %s
            """
            cursor.execute(query, (f"FIR-{date_str}-%",))
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            # Generate sequence number (5 digits, zero-padded)
            sequence = str(count + 1).zfill(5)
            fir_number = f"FIR-{date_str}-{sequence}"
            
            return fir_number
            
        except Exception as e:
            self.logger.error(f"Failed to generate FIR number: {str(e)}")
            # Fallback to UUID-based number
            return f"FIR-{date_str}-{str(uuid.uuid4())[:5].upper()}"


# ============================================================================
# PDF GENERATOR
# ============================================================================
class PDFGenerator:
    """Generates FIR PDF documents with all 30 required fields"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_fir_pdf(self, fir_data: dict) -> bytes:
        """
        Generate PDF from FIR data with all 30 fields
        
        Args:
            fir_data: Dictionary containing all 30 FIR template fields
            
        Returns:
            PDF document as bytes
        """
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        
        try:
            # Create PDF buffer
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                   rightMargin=0.5*inch, leftMargin=0.5*inch,
                                   topMargin=0.5*inch, bottomMargin=0.5*inch)
            
            # Container for PDF elements
            elements = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=12,
                alignment=1  # Center
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=6,
                spaceBefore=12
            )
            
            # Header Section
            self._add_header(elements, fir_data, title_style)
            elements.append(Spacer(1, 0.2*inch))
            
            # Complainant Section (8 fields)
            self._add_complainant_section(elements, fir_data, heading_style, styles)
            elements.append(Spacer(1, 0.15*inch))
            
            # Incident Section (10 fields)
            self._add_incident_section(elements, fir_data, heading_style, styles)
            elements.append(Spacer(1, 0.15*inch))
            
            # Legal Section (3 fields)
            self._add_legal_section(elements, fir_data, heading_style, styles)
            elements.append(Spacer(1, 0.15*inch))
            
            # Investigation Section (6 fields)
            self._add_investigation_section(elements, fir_data, heading_style, styles)
            elements.append(Spacer(1, 0.15*inch))
            
            # Signatures Section (4 fields)
            self._add_signature_section(elements, fir_data, heading_style, styles)
            
            # Build PDF
            doc.build(elements)
            
            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            self.logger.info(f"Generated PDF with {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            self.logger.error(f"Failed to generate PDF: {str(e)}")
            raise
    
    def _add_header(self, elements, fir_data, title_style):
        """Add PDF header with FIR number"""
        from reportlab.platypus import Paragraph
        
        fir_number = fir_data.get('fir_number', 'N/A')
        title = Paragraph(f"<b>FIRST INFORMATION REPORT</b><br/>FIR No: {fir_number}", title_style)
        elements.append(title)
    
    def _add_complainant_section(self, elements, fir_data, heading_style, styles):
        """Add complainant details section (8 fields)"""
        from reportlab.platypus import Paragraph, Table, TableStyle
        from reportlab.lib import colors
        
        elements.append(Paragraph("<b>COMPLAINANT DETAILS</b>", heading_style))
        
        # Complainant fields
        complainant_data = [
            ["Name:", fir_data.get('complainant_name', 'N/A')],
            ["Date of Birth:", fir_data.get('complainant_dob', 'N/A')],
            ["Nationality:", fir_data.get('complainant_nationality', 'N/A')],
            ["Father/Husband Name:", fir_data.get('complainant_father_husband_name', 'N/A')],
            ["Address:", fir_data.get('complainant_address', 'N/A')],
            ["Contact Number:", fir_data.get('complainant_contact', 'N/A')],
            ["Passport Number:", fir_data.get('complainant_passport', 'N/A')],
            ["Occupation:", fir_data.get('complainant_occupation', 'N/A')]
        ]
        
        table = Table(complainant_data, colWidths=[2*inch, 5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
    
    def _add_incident_section(self, elements, fir_data, heading_style, styles):
        """Add incident details section (10 fields)"""
        from reportlab.platypus import Paragraph, Table, TableStyle
        from reportlab.lib import colors
        
        elements.append(Paragraph("<b>INCIDENT DETAILS</b>", heading_style))
        
        # Incident fields
        incident_data = [
            ["Date From:", fir_data.get('incident_date_from', 'N/A')],
            ["Date To:", fir_data.get('incident_date_to', 'N/A')],
            ["Time From:", fir_data.get('incident_time_from', 'N/A')],
            ["Time To:", fir_data.get('incident_time_to', 'N/A')],
            ["Location:", fir_data.get('incident_location', 'N/A')],
            ["Address:", fir_data.get('incident_address', 'N/A')],
            ["Description:", fir_data.get('incident_description', 'N/A')],
            ["Delayed Reporting Reasons:", fir_data.get('delayed_reporting_reasons', 'N/A')],
            ["Summary:", fir_data.get('incident_summary', 'N/A')],
            ["Suspect Details:", fir_data.get('suspect_details', 'N/A')]
        ]
        
        table = Table(incident_data, colWidths=[2*inch, 5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
    
    def _add_legal_section(self, elements, fir_data, heading_style, styles):
        """Add legal provisions section (3 fields)"""
        from reportlab.platypus import Paragraph, Table, TableStyle
        from reportlab.lib import colors
        
        elements.append(Paragraph("<b>LEGAL PROVISIONS</b>", heading_style))
        
        # Legal fields
        legal_data = [
            ["Acts:", fir_data.get('legal_acts', 'N/A')],
            ["Sections:", fir_data.get('legal_sections', 'N/A')],
            ["Suspect Details:", fir_data.get('suspect_details', 'N/A')]
        ]
        
        table = Table(legal_data, colWidths=[2*inch, 5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
    
    def _add_investigation_section(self, elements, fir_data, heading_style, styles):
        """Add investigation details section (6 fields)"""
        from reportlab.platypus import Paragraph, Table, TableStyle
        from reportlab.lib import colors
        
        elements.append(Paragraph("<b>INVESTIGATION DETAILS</b>", heading_style))
        
        # Investigation fields
        investigation_data = [
            ["Investigating Officer Name:", fir_data.get('investigating_officer_name', 'N/A')],
            ["Investigating Officer Rank:", fir_data.get('investigating_officer_rank', 'N/A')],
            ["Witnesses:", fir_data.get('witnesses', 'N/A')],
            ["Action Taken:", fir_data.get('action_taken', 'N/A')],
            ["Investigation Status:", fir_data.get('investigation_status', 'N/A')],
            ["Date of Despatch:", fir_data.get('date_of_despatch', 'N/A')]
        ]
        
        table = Table(investigation_data, colWidths=[2*inch, 5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
    
    def _add_signature_section(self, elements, fir_data, heading_style, styles):
        """Add signature fields section (4 fields)"""
        from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
        from reportlab.lib import colors
        
        elements.append(Paragraph("<b>SIGNATURES</b>", heading_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Signature fields in two columns
        signature_data = [
            ["Investigating Officer Signature:", fir_data.get('investigating_officer_signature', '_' * 30)],
            ["Date:", fir_data.get('investigating_officer_date', 'N/A')],
            ["", ""],  # Spacer row
            ["Complainant Signature:", fir_data.get('complainant_signature', '_' * 30)],
            ["Date:", fir_data.get('complainant_date', 'N/A')]
        ]
        
        table = Table(signature_data, colWidths=[2*inch, 5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)


# ============================================================================
# API MODELS
# ============================================================================
class ProcessRequest(BaseModel):
    """Request model for /process endpoint"""
    input_type: Literal["text", "audio", "image"]
    text: Optional[str] = None
    language: Optional[str] = "en-IN"  # For audio: "en-IN" or "hi-IN"


class ProcessResponse(BaseModel):
    """Response model for /process endpoint"""
    session_id: str
    status: str
    message: str


class SessionResponse(BaseModel):
    """Response model for /session endpoint"""
    session_id: str
    status: str
    transcript: Optional[str] = None
    summary: Optional[str] = None
    violations: Optional[list] = None
    fir_content: Optional[dict] = None
    fir_number: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for /health endpoint"""
    status: str
    checks: dict
    timestamp: str


class AuthenticateRequest(BaseModel):
    """Request model for /authenticate endpoint"""
    session_id: str
    complainant_signature: str
    officer_signature: str


class AuthenticateResponse(BaseModel):
    """Response model for /authenticate endpoint"""
    fir_number: str
    pdf_url: str
    status: str


class FIRResponse(BaseModel):
    """Response model for /fir/{fir_number} endpoint"""
    fir_number: str
    session_id: str
    complaint_text: str
    fir_content: dict
    violations_json: list
    status: str
    created_at: str


class FIRListResponse(BaseModel):
    """Response model for /firs endpoint with pagination"""
    firs: List[FIRResponse]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    """Standardized error response model
    
    Requirements: 14.1-14.8
    """
    error: str
    detail: str
    status_code: int


# ============================================================================
# RATE LIMITING
# ============================================================================



# ============================================================================
# RATE LIMITING
# ============================================================================
class RateLimiter:
    """In-memory rate limiter"""
    
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = {}
        self.lock = threading.Lock()
    
    def is_allowed(self, ip_address: str) -> bool:
        """Check if request is allowed"""
        with self.lock:
            now = time.time()
            
            # Initialize or clean up old requests
            if ip_address not in self.requests:
                self.requests[ip_address] = []
            
            # Remove requests older than 1 minute
            self.requests[ip_address] = [
                req_time for req_time in self.requests[ip_address]
                if now - req_time < 60
            ]
            
            # Check if limit exceeded
            if len(self.requests[ip_address]) >= self.requests_per_minute:
                return False
            
            # Add current request
            self.requests[ip_address].append(now)
            return True


# ============================================================================
# FILE VALIDATION
# ============================================================================

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


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

# Initialize configuration
config = Config()
logger = setup_logging()

# Validate configuration on startup
try:
    config.validate()
    logger.info("Configuration validated successfully")
except ValueError as e:
    logger.error(f"Configuration validation failed: {str(e)}")
    sys.exit(1)

# Initialize global instances
aws_clients = AWSServiceClients(config.AWS_REGION)
db_manager = DatabaseManager(config.get_mysql_config())
rate_limiter = RateLimiter(config.RATE_LIMIT_PER_MINUTE)
fir_generator = FIRGenerator(aws_clients, db_manager)
pdf_generator = PDFGenerator()


async def lifespan(app: FastAPI):
    """Application lifespan manager

    Handles startup and shutdown events for the application.

    Startup:
    - Validates configuration
    - Initializes database tables
    - Loads IPC sections from JSON file if table is empty
    - Logs startup messages

    Shutdown:
    - Closes database connections
    - Flushes logs to disk
    - Logs shutdown messages

    Requirements: 16.1-16.10, 25.1-25.7
    """
    # Startup
    logger.info("=" * 80)
    logger.info("AFIRGen Backend starting up...")
    logger.info("=" * 80)

    try:
        # Configuration is already validated before this point
        logger.info("✓ Configuration validated")

        # Database tables are already initialized in DatabaseManager.__init__
        logger.info("✓ Database tables initialized")

        # Load legal sections from comprehensive KB (988 sections)
        legal_sections_path = os.path.join(os.path.dirname(__file__), "legal_sections.json")
        if os.path.exists(legal_sections_path):
            db_manager.load_ipc_sections(legal_sections_path)
            logger.info("✓ Legal sections loaded from comprehensive KB")
        else:
            # Fallback to old IPC sections file (24 sections)
            ipc_json_path = os.path.join(os.path.dirname(__file__), "ipc_sections.json")
            if os.path.exists(ipc_json_path):
                db_manager.load_ipc_sections(ipc_json_path)
                logger.info("✓ IPC sections loaded (fallback)")
            else:
                logger.warning(f"⚠ IPC sections JSON file not found: {ipc_json_path}")
                logger.warning("  Application will continue but IPC section retrieval may not work")

        # Log AWS configuration
        logger.info(f"✓ AWS Region: {config.AWS_REGION}")
        logger.info(f"✓ S3 Bucket: {config.S3_BUCKET_NAME}")
        logger.info(f"✓ Bedrock Model: {config.BEDROCK_MODEL_ID}")

        # Log database configuration
        logger.info(f"✓ MySQL Host: {config.DB_HOST}:{config.DB_PORT}")
        logger.info(f"✓ MySQL Database: {config.DB_NAME}")

        logger.info("=" * 80)
        logger.info("AFIRGen Backend startup complete - Ready to accept requests")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"✗ Startup failed: {str(e)}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("=" * 80)
    logger.info("AFIRGen Backend shutting down...")
    logger.info("=" * 80)

    try:
        # Close database connections
        logger.info("Closing database connections...")

        # Close MySQL connection pool
        if hasattr(db_manager, 'mysql_pool') and db_manager.mysql_pool:
            try:
                # Close all connections in the pool
                # Note: mysql.connector.pooling.MySQLConnectionPool doesn't have a close_all method
                # Connections will be closed when the pool is garbage collected
                logger.info("✓ MySQL connection pool will be closed on exit")
            except Exception as e:
                logger.error(f"Error closing MySQL pool: {str(e)}")

        # Close SQLite connection
        if hasattr(db_manager, 'sqlite_conn') and db_manager.sqlite_conn:
            try:
                db_manager.sqlite_conn.close()
                logger.info("✓ SQLite connection closed")
            except Exception as e:
                logger.error(f"Error closing SQLite connection: {str(e)}")

        # Flush logs to disk
        for handler in logger.handlers:
            try:
                handler.flush()
            except Exception as e:
                logger.error(f"Error flushing log handler: {str(e)}")

        logger.info("✓ Logs flushed to disk")

        logger.info("=" * 80)
        logger.info("AFIRGen Backend shutdown complete")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"✗ Shutdown error: {str(e)}", exc_info=True)




app = FastAPI(
    title="AFIRGen Backend",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with standardized error response
    
    Requirements: 14.1-14.8
    """
    # Map status codes to error categories
    error_messages = {
        400: "Invalid input",
        401: "Authentication failed",
        429: "Rate limit exceeded",
        500: "Service temporarily unavailable"
    }
    
    error = error_messages.get(exc.status_code, "Request failed")
    
    # For 429 errors, include retry_after in response
    if exc.status_code == 429:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": error,
                "detail": exc.detail,
                "status_code": exc.status_code,
                "retry_after": 60
            },
            headers={"Retry-After": "60"}
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error,
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions as 400 Bad Request
    
    Requirements: 14.3
    """
    logger.error(f"ValueError in request {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid input",
            "detail": str(exc),
            "status_code": 400
        }
    )


@app.exception_handler(TimeoutError)
async def timeout_error_handler(request: Request, exc: TimeoutError):
    """Handle TimeoutError exceptions as 500 Internal Server Error
    
    Requirements: 14.6
    """
    logger.error(f"TimeoutError in request {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Service temporarily unavailable",
            "detail": "Request timeout. Please try again later.",
            "status_code": 500
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions as 500 Internal Server Error
    
    Requirements: 14.6, 14.7
    """
    # Log full error details for debugging
    logger.error(
        f"Unhandled exception in request {request.url.path}: {str(exc)}",
        exc_info=True
    )
    
    # Return generic error message to client (don't expose sensitive information)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "status_code": 500
        }
    )


# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    # Remove server version header (Requirement 22.6)
    if "Server" in response.headers:
        del response.headers["Server"]
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting for health endpoint
    if request.url.path == "/health":
        return await call_next(request)
    
    client_ip = request.client.host
    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "detail": "Maximum 100 requests per minute",
                "retry_after": 60
            },
            headers={"Retry-After": "60"}
        )
    
    return await call_next(request)


@app.middleware("http")
async def api_key_authentication_middleware(request: Request, call_next):
    """API key authentication middleware
    
    Verifies X-API-Key header matches configured API_KEY for all endpoints
    except /health. Returns HTTP 401 for invalid or missing API key.
    
    Requirements: 15.10
    """
    # Skip authentication for health endpoint
    if request.url.path == "/health":
        return await call_next(request)
    
    # Skip authentication for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Get API key from header
    api_key = request.headers.get("x-api-key")
    
    # Verify API key
    if not api_key or api_key != config.API_KEY:
        return JSONResponse(
            status_code=401,
            content={
                "error": "Authentication failed",
                "detail": "Invalid or missing API key"
            }
        )
    
    return await call_next(request)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/process", response_model=ProcessResponse)
async def process_complaint(
    input_type: str = Form(...),
    text: Optional[str] = Form(None),
    language: Optional[str] = Form("en-IN"),
    file: Optional[UploadFile] = File(None)
):
    """Process complaint and generate FIR
    
    Accepts text, audio, or image inputs and starts the FIR generation workflow.
    Returns immediately with session_id for status polling.
    
    Requirements: 15.1-15.3, 23.1-23.6
    """
    # Validate input_type
    if input_type not in ["text", "audio", "image"]:
        raise HTTPException(status_code=400, detail="input_type must be 'text', 'audio', or 'image'")
    
    # Validate input based on input_type
    if input_type == "text":
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Text input is required for input_type 'text'")
    elif input_type in ["audio", "image"]:
        if not file:
            raise HTTPException(status_code=400, detail=f"File upload is required for input_type '{input_type}'")
        
        # Read file bytes once
        file_bytes = await file.read()
        
        # Validate file size first (Requirement 23.3)
        validate_file_size(file_bytes, config.MAX_FILE_SIZE_MB)
        
        # Validate file extension and content (Requirements 23.1, 23.2, 23.4)
        if input_type == "audio":
            validate_audio_file(file_bytes, file.filename)
        elif input_type == "image":
            validate_image_file(file_bytes, file.filename)
        
        # Store file_bytes for later use in background task
        # Reset file pointer is not needed since we already have the bytes
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Create session in database
    try:
        db_manager.create_session(session_id)
        logger.info(f"Created session {session_id} for input_type {input_type}")
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create session")
    
    # Start async FIR generation workflow in background
    async def generate_fir_async():
        """Background task to generate FIR"""
        try:
            if input_type == "text":
                # Generate FIR from text
                result = fir_generator.generate_from_text(text, session_id)
            elif input_type == "audio":
                # Use file_bytes from outer scope
                # Generate FIR from audio
                result = fir_generator.generate_from_audio(
                    file_bytes, 
                    language, 
                    session_id
                )
            elif input_type == "image":
                # Use file_bytes from outer scope
                # Generate FIR from image
                result = fir_generator.generate_from_image(file_bytes, session_id)
            
            logger.info(f"FIR generation completed for session {session_id}: {result.get('fir_number')}")
        except Exception as e:
            logger.error(f"FIR generation failed for session {session_id}: {str(e)}", exc_info=True)
            # Update session with error
            try:
                db_manager.update_session(session_id, {
                    "status": "failed",
                    "error": str(e)
                })
            except Exception as update_error:
                logger.error(f"Failed to update session with error: {str(update_error)}")
    
    # Start background task (fire and forget)
    asyncio.create_task(generate_fir_async())
    
    # Return immediately with session_id
    return ProcessResponse(
        session_id=session_id,
        status="processing",
        message="FIR generation started. Use session_id to poll for status."
    )


@app.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str
):
    """Get session status and data
    
    Retrieves current session status and all available data including
    transcript, summary, violations, FIR content, and FIR number.
    
    Requirements: 15.4-15.5
    """
    # Retrieve session from SQLite
    try:
        session_data = db_manager.get_session(session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        
        # Return session data
        return SessionResponse(
            session_id=session_data['session_id'],
            status=session_data['status'],
            transcript=session_data.get('transcript'),
            summary=session_data.get('summary'),
            violations=session_data.get('violations'),
            fir_content=session_data.get('fir_content'),
            fir_number=session_data.get('fir_number'),
            error=session_data.get('error')
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve session data")


@app.post("/authenticate", response_model=AuthenticateResponse)
async def authenticate_fir(
    request: AuthenticateRequest
):
    """Finalize FIR and generate PDF
    
    Retrieves FIR from session, generates PDF with signatures, uploads to S3,
    and updates FIR status to "finalized" in MySQL.
    
    Requirements: 15.6
    """
    try:
        # Retrieve session data
        session_data = db_manager.get_session(request.session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")
        
        # Check if session is completed
        if session_data['status'] != 'completed':
            raise HTTPException(
                status_code=400, 
                detail=f"Session is not completed. Current status: {session_data['status']}"
            )
        
        # Get FIR content and number from session
        fir_content = session_data.get('fir_content')
        fir_number = session_data.get('fir_number')
        
        if not fir_content or not fir_number:
            raise HTTPException(
                status_code=400, 
                detail="FIR content or number not found in session"
            )
        
        # Add signatures to FIR content
        fir_content['complainant_signature'] = request.complainant_signature
        fir_content['investigating_officer_signature'] = request.officer_signature
        
        # Generate PDF with signatures
        logger.info(f"Generating PDF for FIR {fir_number}")
        pdf_bytes = pdf_generator.generate_fir_pdf(fir_content)
        
        # Upload PDF to S3
        pdf_key = f"pdfs/{fir_number}.pdf"
        logger.info(f"Uploading PDF to S3: {pdf_key}")
        pdf_url = aws_clients.upload_to_s3(
            pdf_bytes, 
            pdf_key, 
            config.S3_BUCKET_NAME
        )
        
        # Update FIR status to "finalized" in MySQL
        logger.info(f"Updating FIR {fir_number} status to finalized")
        db_manager.update_fir_status(fir_number, "finalized")
        
        logger.info(f"FIR {fir_number} finalized successfully")
        
        return AuthenticateResponse(
            fir_number=fir_number,
            pdf_url=pdf_url,
            status="finalized"
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to authenticate FIR for session {request.session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to finalize FIR")


@app.get("/fir/{fir_number}", response_model=FIRResponse)
async def get_fir(
    fir_number: str
):
    """Retrieve FIR by FIR number
    
    Retrieves a specific FIR record from MySQL by its FIR number.
    Returns all FIR data including content, violations, and metadata.
    
    Requirements: 15.7
    """
    try:
        # Retrieve FIR from MySQL by fir_number
        fir_data = db_manager.get_fir_by_number(fir_number)
        
        if not fir_data:
            raise HTTPException(status_code=404, detail=f"FIR not found: {fir_number}")
        
        # Return FIR data
        return FIRResponse(
            fir_number=fir_data['fir_number'],
            session_id=fir_data['session_id'],
            complaint_text=fir_data['complaint_text'],
            fir_content=fir_data['fir_content'],
            violations_json=fir_data['violations_json'],
            status=fir_data['status'],
            created_at=fir_data['created_at']
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve FIR {fir_number}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve FIR")


@app.get("/firs", response_model=FIRListResponse)
async def list_firs(
    limit: int = Query(default=20, ge=1, le=100, description="Number of FIRs to return (max 100)"),
    offset: int = Query(default=0, ge=0, description="Number of FIRs to skip")
):
    """List all FIRs with pagination
    
    Retrieves a paginated list of FIR records from MySQL.
    Returns FIR data with pagination metadata (total count, limit, offset).
    
    Requirements: 15.9
    """
    try:
        # Retrieve FIRs from MySQL with pagination
        firs_data = db_manager.list_firs(limit=limit, offset=offset)
        
        # Convert to FIRResponse models
        firs = [
            FIRResponse(
                fir_number=fir['fir_number'],
                session_id=fir['session_id'],
                complaint_text=fir['complaint_text'],
                fir_content=fir['fir_content'],
                violations_json=fir['violations_json'],
                status=fir['status'],
                created_at=fir['created_at']
            )
            for fir in firs_data['firs']
        ]
        
        # Return paginated response
        return FIRListResponse(
            firs=firs,
            total=firs_data['total'],
            limit=limit,
            offset=offset
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to list FIRs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list FIRs")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    checks = {
        "mysql": False,
        "bedrock": False
    }
    
    # Check MySQL
    try:
        conn = db_manager.mysql_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        checks["mysql"] = True
    except Exception as e:
        logger.error(f"MySQL health check failed: {str(e)}")
    
    # Check Bedrock
    try:
        # Simple check - list models
        bedrock = boto3.client('bedrock', region_name=config.AWS_REGION)
        bedrock.list_foundation_models()
        checks["bedrock"] = True
    except Exception as e:
        logger.error(f"Bedrock health check failed: {str(e)}")
    
    status = "healthy" if all(checks.values()) else "unhealthy"
    
    return HealthResponse(
        status=status,
        checks=checks,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
