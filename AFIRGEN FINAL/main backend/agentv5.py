# fir_pipeline_production_ready.py
# -------------------------------------------------------------
# FIR Pipeline with Production Fixes - Race Conditions, Memory Leaks, etc.
# -------------------------------------------------------------
import httpx
import asyncio
from typing import Optional
import os
import json
import logging
import uuid
import asyncio
import re
import string
import gc
import sqlite3
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from datetime import datetime, timedelta
from contextlib import contextmanager, asynccontextmanager
from enum import Enum

import chromadb
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Try to import python-magic, fallback to basic validation
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logging.warning("python-magic not available, using basic MIME validation")

# ------------------------------------------------------------- CONFIGURATION DICTIONARY    
CFG = {
    "max_file_size": 25 * 1024 * 1024,
    "max_text_len": 50_000,
    "temp_dir": Path("temp_files"),
    "session_timeout": 3600,
    "session_db_path": "sessions.db",  # SQLite for session persistence
    "mysql": {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", 3306)),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DB"),
        "charset": "utf8mb4",
        "autocommit": True,
        "pool_size": 10,
        "pool_reset_session": True,  # FIX: Reset session on connection return
        "pool_timeout": 30,  # FIX: Connection timeout
    },
    "chroma": {"persist_dir": "./chroma_kb"},
    "kb_dir": Path("./kb"),
    "allowed_image": {"image/jpeg", "image/png", "image/jpg"},
    "allowed_audio": {"audio/wav", "audio/mpeg", "audio/mp3"},
    "allowed_extensions": {".jpg", ".jpeg", ".png", ".wav", ".mp3", ".mpeg"},
    "auth_key": os.getenv("FIR_AUTH_KEY"),
    "model_timeouts": {
        "summary": 60.0,  # FIX: Increased timeouts
        "ocr": 120.0,
        "asr": 180.0,
    }
}
CFG["temp_dir"].mkdir(exist_ok=True)
CFG["kb_dir"].mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("fir_pipeline.log"), logging.StreamHandler()],
)
log = logging.getLogger("pipeline")

# ------------------------------------------------------------- ENUMS & UTILS
class ValidationStep(str, Enum):
    TRANSCRIPT_REVIEW = "transcript_review"
    SUMMARY_REVIEW = "summary_review" 
    VIOLATIONS_REVIEW = "violations_review"
    FIR_NARRATIVE_REVIEW = "fir_narrative_review"
    FINAL_REVIEW = "final_review"

class SessionStatus(str, Enum):
    PROCESSING = "processing"
    AWAITING_VALIDATION = "awaiting_validation"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ERROR = "error"

# DateTime JSON encoder
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

def sanitise(text: str) -> str:
    if text is None:
        return ""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = "".join(ch for ch in text if ch in string.printable)
    return text

# FIX: File validation with proper MIME checking
def validate_uploaded_file(file_path: Path, content_type: str) -> bool:
    """Validate file extension and MIME type"""
    # Check extension
    ext = file_path.suffix.lower()
    if ext not in CFG["allowed_extensions"]:
        raise HTTPException(status_code=415, detail=f"Invalid file extension: {ext}")
    
    # MIME validation
    if MAGIC_AVAILABLE:
        try:
            detected_mime = magic.Magic(mime=True).from_file(str(file_path))
            # Check against allowed types
            if content_type.startswith("image/") and detected_mime not in CFG["allowed_image"]:
                raise HTTPException(status_code=415, detail=f"Invalid image MIME type: {detected_mime}")
            elif content_type.startswith("audio/") and detected_mime not in CFG["allowed_audio"]:
                raise HTTPException(status_code=415, detail=f"Invalid audio MIME type: {detected_mime}")
        except Exception as e:
            log.warning(f"MIME detection failed: {e}")
    else:
        # Basic fallback validation
        if content_type not in (CFG["allowed_image"] | CFG["allowed_audio"]):
            raise HTTPException(status_code=415, detail=f"Unsupported content type: {content_type}")
    
    return True

def get_fir_data(session_state: dict) -> dict:
    from datetime import datetime

    now = datetime.now()
    present_date = now.strftime("%d %B %Y")
    present_time = now.strftime("%H:%M:%S")

    # Construct FIR data dict using available session_state and defaults
    fir_data = {
        'fir_number': session_state.get('fir_number', 'N/A'),
        'police_station': 'Central Police Station',  # hardcoded or derived from config/session
        'district': 'Metro City',
        'state': 'State of Example',
        'year': present_date.split()[-1],
        'date': present_date,

        'Acts': session_state.get('Acts', ['IPC 379 (Theft)', 'IPC 34 (Common Intention)', 'IPC 506 (Criminal Intimidation)']),
        'Sections': session_state.get('Sections', ['IPC 379', 'IPC 34', 'IPC 506']),

        'Occurrence of Offence': '',
        'Date from': session_state.get('date_from', present_date),
        'Date to': session_state.get('date_to', present_date),
        'Time from': session_state.get('time_from', ''),
        'Time to': session_state.get('time_to', ''),
        'Information recieved': f"{present_date} at {present_time}",

        'Place of Occurrence': session_state.get('occurrence_place', 'Central Park, Metro City'),
        'Address of Occurrence': session_state.get('occurrence_address', 'Near the fountain area, Central Park, Metro City'),

        'complainant_name': session_state.get('complainant_name', 'John Doe'),
        'dateofbirth': session_state.get('date_of_birth', '01 January 1990'),
        'Nationality': session_state.get('nationality', 'Indian'),
        'father_name/husband_name': session_state.get('father_name', 'Richard Doe'),
        'complainant_address': session_state.get('complainant_address', '123 Main St.'),
        'complainant_contact': session_state.get('complainant_contact', '9876543210'),
        'passport_number': session_state.get('passport_number', ''),
        'occupation': session_state.get('occupation', ''),

        'Suspect_details': session_state.get('suspect_details', 'Unknown'),

        'reasons_for_delayed_reporting': session_state.get('delay_reason', 'No delay reported'),

        'incident_description': session_state.get('incident_description', ''),
        'summary': session_state.get('summary', ''),
        'action_taken': session_state.get('action_taken', ''),

        'io_name': session_state.get('io_name', 'Inspector Rajesh Kumar'),
        'io_rank': session_state.get('io_rank', 'Inspector'),
        'witnesses': session_state.get('witnesses', ''),
        'date_of_despatch': present_date,

        'investigation_status': session_state.get('investigation_status', 'Preliminary investigation started'),
    }

    return fir_data


fir_template = """
FIRST INFORMATION REPORT

------------------------------------------------------------------------------------------------------

FIR No.: {fir_number}                 Year: {year}
Police Station: {police_station}
District: {district}
State: {state}

Date of Report: {date}
Information Received: {Information recieved}

1. COMPLAINANT DETAILS:
   - Full Name: {complainant_name}
   - Date of Birth: {dateofbirth}
   - Nationality: {Nationality}
   - Father's/Husband's Name: {father_name/husband_name}
   - Complete Address: {complainant_address}
   - Contact Number: {complainant_contact}
   - Passport Number: {passport_number}
   - Occupation: {occupation}

2. INCIDENT DETAILS:
   - Date from: {Date from}
   - Date to: {Date to}
   - Time from: {Time from}
   - Time to: {Time to}
   - Place of Occurrence: {Place of Occurrence}
   - Address of Occurrence: {Address of Occurrence}
   - Detailed Description:
     {incident_description}
   - Reason for Delayed Reporting:
     {reasons_for_delayed_reporting}
   - Summary:
     {summary}

3. LEGAL PROVISIONS:
   - Applicable Acts: {Acts}
   - Applicable Sections: {Sections}

4. SUSPECT DETAILS:
   - {Suspect_details}

5. INVESTIGATION DETAILS:
   - Investigating Officer: {io_name} ({io_rank})
   - Witnesses: {witnesses}
   - Action Taken: {action_taken}
   - Investigation Status: {investigation_status}
   - Date of Despatch: {date_of_despatch}

------------------------------------------------------------------------------------------------------

(Signature of Investigating Officer)

(Signature of Complainant)

{io_name}
{io_rank}
{police_station}
Date: {date}
"""


# ------------------------------------------------------------- PERSISTENT SESSION MANAGER
class PersistentSessionManager:
    """FIX: Session persistence using SQLite"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = datetime.now()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    state TEXT,
                    status TEXT,
                    created_at TEXT,
                    last_activity TEXT,
                    validation_history TEXT
                )
            """)
    
    def create_session(self, session_id: str, initial_state: Dict) -> None:
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, json.dumps(initial_state, cls=DateTimeEncoder), 
                 SessionStatus.PROCESSING, now, now, "[]")
            )
        self._cleanup_old_sessions()
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        self._cleanup_old_sessions()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            # Update last activity
            now = datetime.now().isoformat()
            conn.execute(
                "UPDATE sessions SET last_activity = ? WHERE session_id = ?",
                (now, session_id)
            )
            
            return {
                "session_id": row[0],
                "state": json.loads(row[1]),
                "status": row[2],
                "created_at": datetime.fromisoformat(row[3]),
                "last_activity": datetime.fromisoformat(row[4]),
                "validation_history": json.loads(row[5])
            }
    
    def update_session(self, session_id: str, updates: Dict) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        
        session["state"].update(updates)
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET state = ?, last_activity = ? WHERE session_id = ?",
                (json.dumps(session["state"], cls=DateTimeEncoder), now, session_id)
            )
        return True
    
    def set_session_status(self, session_id: str, status: SessionStatus) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE sessions SET status = ?, last_activity = ? WHERE session_id = ?",
                (status, datetime.now().isoformat(), session_id)
            )
            return cursor.rowcount > 0
    
    def add_validation_step(self, session_id: str, step: ValidationStep, content: Dict) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        
        history = session["validation_history"]
        history.append({
            "step": step,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET validation_history = ? WHERE session_id = ?",
                (json.dumps(history, cls=DateTimeEncoder), session_id)
            )
        return True
    
    def _cleanup_old_sessions(self):
        now = datetime.now()
        if (now - self._last_cleanup).seconds < self._cleanup_interval:
            return
        
        cutoff = (now - timedelta(seconds=CFG["session_timeout"])).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE sessions SET status = ? WHERE last_activity < ? AND status != ?",
                (SessionStatus.EXPIRED, cutoff, SessionStatus.EXPIRED)
            )
            if cursor.rowcount > 0:
                log.info(f"Expired {cursor.rowcount} old sessions")
        
        self._last_cleanup = now

session_manager = PersistentSessionManager(CFG["session_db_path"])

# ------------------------------------------------------------- TEMP FILE MANAGER
class TempFileManager:
    def __init__(self):
        self.temp_paths: List[Path] = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for path in self.temp_paths:
            try:
                if path.exists():
                    path.unlink()
                    log.debug(f"Cleaned up temp file: {path}")
            except Exception as e:
                log.warning(f"Failed to cleanup {path}: {e}")
    
    async def save_audio(self, audio: UploadFile) -> str:
        if audio.content_type not in CFG["allowed_audio"]:
            raise HTTPException(status_code=415, detail="Unsupported audio format")
        
        # FIX: Use pathlib for secure filename handling
        safe_filename = f"{uuid.uuid4().hex}{Path(audio.filename).suffix.lower()}"
        path = CFG["temp_dir"] / safe_filename
        content = await audio.read()
        
        if len(content) > CFG["max_file_size"]:
            raise HTTPException(status_code=413, detail="Audio file too large")
        
        path.write_bytes(content)
        validate_uploaded_file(path, audio.content_type)
        self.temp_paths.append(path)
        return str(path)
    
    async def save_image(self, image: UploadFile) -> str:
        if image.content_type not in CFG["allowed_image"]:
            raise HTTPException(status_code=415, detail="Unsupported image format")
        
        # FIX: Use pathlib for secure filename handling
        safe_filename = f"{uuid.uuid4().hex}{Path(image.filename).suffix.lower()}"
        path = CFG["temp_dir"] / safe_filename
        content = await image.read()
        
        if len(content) > CFG["max_file_size"]:
            raise HTTPException(status_code=413, detail="Image file too large")
        
        path.write_bytes(content)
        validate_uploaded_file(path, image.content_type)
        self.temp_paths.append(path)
        return str(path)
    

#==============MODEL POOL=================================
class ModelPool:
    _instance: Optional["ModelPool"] = None
    _lock = asyncio.Lock()
    
    def __init__(self, model_server_url: str = "http://localhost:8001", asr_ocr_server_url: str = "http://localhost:8002"):
        self.MODEL_SERVER_URL = model_server_url
        self.ASR_OCR_SERVER_URL = asr_ocr_server_url  # ADD THIS LINE
        log.info("ModelPool initialized for external model server communication")

    @classmethod
    async def get(cls, model_server_url: str = "http://localhost:8001", asr_ocr_server_url: str = "http://localhost:8002") -> "ModelPool":  # ADD PARAMETER
        async with cls._lock:
            if cls._instance is None:
                cls._instance = ModelPool(model_server_url, asr_ocr_server_url)  
            return cls._instance

    async def _inference(self, model_name: str, prompt: str, max_tokens: int = 120, temperature: float = 0.1, stop: list = None) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model_name": model_name,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            if stop:
                payload["stop"] = stop

            try:
                resp = await client.post(f"{self.MODEL_SERVER_URL}/inference", json=payload)
                resp.raise_for_status()
                result = resp.json()
                return result["result"]
            except httpx.RequestError as e:
                log.error(f"Model server request failed: {e}")
                raise RuntimeError(f"Model server unavailable: {e}")
            except httpx.HTTPStatusError as e:
                log.error(f"Model server returned error: {e.response.status_code}")
                raise RuntimeError(f"Model inference failed: {e.response.text}")

    async def two_line_summary(self, text: str) -> str:
        prompt = f"<|user|>\nSummarise the following complaint in exactly two sentences:\n{text}\n<|assistant|>"
        return await self._inference("summariser", prompt, max_tokens=120, temperature=0.1)

    async def check_violation(self, summary: str, ref: str) -> bool:
        prompt = f"<|user|>\nComplaint summary:\n{summary}\n\nReference BNS clause:\n{ref}\n\nDoes the summary indicate a violation? Answer only YES or NO.\n<|assistant|>"
        response = await self._inference("bns_check", prompt, max_tokens=4, temperature=0.0, stop=["\n"])
        return response.strip().upper().startswith("YES")

    async def fir_narrative(self, complaint: str) -> str:
        prompt = f"<|user|>\nCreate a concise FIR narrative (max 3 sentences) from:\n{complaint}\n<|assistant|>"
        return await self._inference("fir_summariser", prompt, max_tokens=180, temperature=0.2)
    
    async def whisper_transcribe(self, audio_path: str) -> str:
        """ASR transcription via external ASR/OCR server"""
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                with open(audio_path, 'rb') as audio_file:
                    files = {"audio": audio_file}
                    resp = await client.post(f"{self.ASR_OCR_SERVER_URL}/asr", files=files)
                    resp.raise_for_status()
                    result = resp.json()
                    
                    if not result["success"]:
                        raise RuntimeError(f"ASR failed: {result.get('error', 'Unknown error')}")
                    
                    return result["transcript"]
                    
        except httpx.RequestError as e:
            log.error(f"ASR server request failed: {e}")
            raise RuntimeError(f"ASR server unavailable: {e}")
        except httpx.HTTPStatusError as e:
            log.error(f"ASR server returned error: {e.response.status_code}")
            raise RuntimeError(f"ASR processing failed: {e.response.text}")
    
    async def dots_ocr_sync(self, image_path: str) -> str:
        """OCR processing via external ASR/OCR server"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(image_path, 'rb') as image_file:
                    files = {"image": image_file}
                    resp = await client.post(f"{self.ASR_OCR_SERVER_URL}/ocr", files=files)
                    resp.raise_for_status()
                    result = resp.json()
                    
                    if not result["success"]:
                        raise RuntimeError(f"OCR failed: {result.get('error', 'Unknown error')}")
                    
                    return result["extracted_text"]
                    
        except httpx.RequestError as e:
            log.error(f"OCR server request failed: {e}")
            raise RuntimeError(f"OCR server unavailable: {e}")
        except httpx.HTTPStatusError as e:
            log.error(f"OCR server returned error: {e.response.status_code}")
            raise RuntimeError(f"OCR processing failed: {e.response.text}")

# ------------------------------------------------------------- KB 
class KB:
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(path=CFG["chroma"]["persist_dir"])
            self.cols = {}
            self._load_jsonl_dbs()
            log.info("Knowledge base initialized successfully")
        except Exception as e:
            log.error(f"KB initialization failed: {e}")
            raise

    def _load_jsonl_dbs(self):
        for file in CFG["kb_dir"].glob("*.jsonl"):
            try:
                name = file.stem
                col = self.client.get_or_create_collection(name)
                if col.count() == 0:
                    docs, metas, ids = [], [], []
                    with open(file, encoding="utf-8") as f:
                        for idx, line in enumerate(f):
                            row = json.loads(line)
                            docs.append(row["text"])
                            metas.append({"section": row["section"], "title": row.get("title", "")})
                            ids.append(f"{name}_{idx}")
                    if docs:
                        col.add(documents=docs, metadatas=metas, ids=ids)
                        log.info(f"Loaded {len(docs)} documents into {name}")
                self.cols[name] = col
            except Exception as e:
                log.error(f"Failed to load {file}: {e}")

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        hits = []
        for db_name, col in self.cols.items():
            try:
                res = col.query(query_texts=[query], n_results=20)
                for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
                    hits.append({"db": db_name, "section": meta["section"], "text": doc})
            except Exception as e:
                log.warning(f"Query failed for {db_name}: {e}")
        return hits

KB = KB()

# ------------------------------------------------------------- ENHANCED RAG WITH VALIDATION
async def generate_summary_with_validation(session_id: str, transcript: str, user_input: Optional[str] = None) -> str:
    pool = await ModelPool.get()
    
    text_to_process = transcript
    if user_input:
        text_to_process = f"{transcript}\n\nAdditional user input: {user_input}"
    
    summary = await asyncio.wait_for(
        pool.two_line_summary(text_to_process),
        timeout=CFG["model_timeouts"]["summary"]
    )

    session_manager.add_validation_step(session_id, ValidationStep.SUMMARY_REVIEW, {
        "summary": summary,
        "original_transcript": transcript,
        "user_input": user_input
    })
    
    return summary

async def find_violations_with_validation(session_id: str, summary: str, user_input: Optional[str] = None) -> List[Dict[str, Any]]:
    pool = await ModelPool.get()
    
    search_text = summary
    if user_input:
        search_text = f"{summary}\n\nAdditional context: {user_input}"
    
    hits = await asyncio.wait_for(
        asyncio.to_thread(KB.retrieve, search_text),
        timeout=15.0  # FIX: Increased timeout
    )

    violations = []
    seen = set()
    for h in hits:
        try:
            if await asyncio.wait_for(
                pool.check_violation(search_text, h["text"]),
                timeout=10.0
            ):

                key = (h["section"], h["text"])
                if key not in seen:
                    seen.add(key)
                    violations.append(h)
        except asyncio.TimeoutError:
            log.warning("Violation check timeout")
            continue

    session_manager.add_validation_step(session_id, ValidationStep.VIOLATIONS_REVIEW, {
        "violations": violations,
        "search_text": search_text,
        "user_input": user_input
    })
    
    return violations

async def generate_fir_narrative_with_validation(session_id: str, transcript: str, user_input: Optional[str] = None) -> str:
    pool = await ModelPool.get()
    
    text_to_process = transcript
    if user_input:
        text_to_process = f"{transcript}\n\nAdditional details: {user_input}"
    
    narrative = await asyncio.wait_for(
        pool.fir_narrative(text_to_process),
        timeout=CFG["model_timeouts"]["summary"]
    )

    
    session_manager.add_validation_step(session_id, ValidationStep.FIR_NARRATIVE_REVIEW, {
        "narrative": narrative,
        "original_transcript": transcript,
        "user_input": user_input
    })
    
    return narrative

# -------------------------------------------------------------  IMPROVED DB WITH CONNECTION MANAGEMENT
class DB:
    def __init__(self):
        import mysql.connector.pooling as pooling
        
        try:
            # FIX: Added pool_reset_session and pool_timeout
            self.pool = pooling.MySQLConnectionPool(
                pool_name="fir_pool", 
                **CFG["mysql"]
            )
            
            with self._cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                if result:
                    log.info("Database connection established successfully")
                    
            with self._cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS fir_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        fir_number VARCHAR(100) UNIQUE NOT NULL,
                        session_id VARCHAR(100),
                        complaint_text TEXT,
                        fir_content TEXT,
                        violations_json LONGTEXT,
                        status ENUM('pending', 'finalized') DEFAULT 'pending',
                        finalized_at TIMESTAMP NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                log.info("Database tables initialized")
                
        except Exception as e:
            log.error(f"Database initialization failed: {e}")
            raise RuntimeError(f"Database connection failed: {e}")

    @contextmanager
    def _cursor(self):
        conn = None
        try:
            conn = self.pool.get_connection()
            conn.autocommit = True
            with conn.cursor(dictionary=True) as cur:
                yield cur
        except Exception as e:
            log.error(f"Database operation failed: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def save(self, fir_number: str, session_id: str, complaint: str, content: str, violations_json: str):
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO fir_records "
                "(fir_number, session_id, complaint_text, fir_content, violations_json, status) "
                "VALUES (%s,%s,%s,%s,%s,'pending')",
                (fir_number, session_id, complaint, content, violations_json),
            )
            log.info(f"FIR {fir_number} saved successfully")

    def finalize_fir(self, fir_number: str):
        with self._cursor() as cur:
            cur.execute(
                "UPDATE fir_records SET status = 'finalized', finalized_at = NOW() WHERE fir_number = %s AND status = 'pending'",
                (fir_number,)
            )
            if cur.rowcount == 0:
                raise ValueError("FIR not found or already finalized")
            log.info(f"FIR {fir_number} finalized")

    def get_fir(self, fir_number: str) -> Optional[Dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM fir_records WHERE fir_number = %s",
                (fir_number,)
            )
            return cur.fetchone()

db = DB()

# ------------------------------------------------------------- INTERACTIVE STATE & WORKFLOW
class InteractiveFIRState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    audio_path: Optional[str] = None
    image_path: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    fir_narrative: Optional[str] = None
    fir_content: str = ""
    fir_number: str = ""
    error: str = ""
    steps: List[str] = Field(default_factory=list)
    current_validation_step: Optional[ValidationStep] = None
    awaiting_validation: bool = False
    user_inputs: Dict[str, str] = Field(default_factory=dict)

async def initial_processing(state: InteractiveFIRState) -> InteractiveFIRState:
    try:
        pool = await ModelPool.get()
        
        if state.audio_path:
            log.info(f"Session {state.session_id}: Starting ASR processing")
            state.transcript = await asyncio.wait_for(
                pool.whisper_transcribe(state.audio_path),  # ✅ Direct async call
                timeout=CFG["model_timeouts"]["asr"]
            )
            state.steps.append("asr_done")
            
        elif state.image_path:
            log.info(f"Session {state.session_id}: Starting OCR processing")
            state.transcript = await asyncio.wait_for(
                pool.dots_ocr_sync(state.image_path),  # ✅ Direct async call
                timeout=CFG["model_timeouts"]["ocr"]
            )
            state.steps.append("ocr_done")
        
        session_manager.add_validation_step(state.session_id, ValidationStep.TRANSCRIPT_REVIEW, {
            "transcript": state.transcript
        })
        
        state.current_validation_step = ValidationStep.TRANSCRIPT_REVIEW
        state.awaiting_validation = True
        session_manager.set_session_status(state.session_id, SessionStatus.AWAITING_VALIDATION)
        
        log.info(f"Session {state.session_id}: Transcript ready for validation")
        
    except Exception as e:
        state.error = f"processing_error:{e}"
        log.error(f"Session {state.session_id}: Processing error: {e}")
        
    return state


# ------------------------------------------------------------- FASTAPI WITH CORS
class FIRResp(BaseModel):
    success: bool
    session_id: str
    fir_number: Optional[str]
    fir_content: Optional[str]
    error: Optional[str]
    steps: List[str] = Field(default_factory=list)
    requires_validation: bool = False
    current_step: Optional[ValidationStep] = None
    content_for_validation: Optional[Dict[str, Any]] = None

class ValidationRequest(BaseModel):
    session_id: str
    approved: bool
    user_input: Optional[str] = None
    regenerate: bool = False

class ValidationResponse(BaseModel):
    success: bool
    session_id: str
    current_step: ValidationStep
    content: Dict[str, Any]
    message: str
    requires_validation: bool = True
    completed: bool = False

class AuthRequest(BaseModel):
    fir_number: str
    auth_key: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    fir_number: Optional[str] = None

app = FastAPI(version="8.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

@app.post("/process", response_model=FIRResp)
async def process_endpoint(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = None,
):
    """Start FIR processing with enhanced validation and error handling"""
    if not any([audio, image, text]):
        raise HTTPException(status_code=400, detail="No input provided")

    state = InteractiveFIRState()
    
    async with TempFileManager() as tmp_manager:
        try:
            if audio:
                state.audio_path = await tmp_manager.save_audio(audio)
            elif image:
                state.image_path = await tmp_manager.save_image(image)
            elif text:
                if len(text) > CFG["max_text_len"]:
                    raise HTTPException(status_code=413, detail="Text too long")
                state.transcript = sanitise(text)
                session_manager.add_validation_step(state.session_id, ValidationStep.TRANSCRIPT_REVIEW, {
                    "transcript": state.transcript
                })
                state.current_validation_step = ValidationStep.TRANSCRIPT_REVIEW
                state.awaiting_validation = True
            
            session_manager.create_session(state.session_id, state.dict())
            
            if audio or image:
                state = await initial_processing(state)
                session_manager.update_session(state.session_id, state.dict())
            
            if state.error:
                return FIRResp(
                    success=False,
                    session_id=state.session_id,
                    error=state.error,
                    steps=state.steps
                )
            
            return FIRResp(
                success=True,
                session_id=state.session_id,
                steps=state.steps,
                requires_validation=True,
                current_step=state.current_validation_step,
                content_for_validation={"transcript": state.transcript}
            )
            
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"Processing error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/validate", response_model=ValidationResponse)
async def validate_step(validation_req: ValidationRequest):
    """Enhanced validation with better timeout handling"""
    session = session_manager.get_session(validation_req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    if session["status"] != SessionStatus.AWAITING_VALIDATION:
        raise HTTPException(status_code=400, detail="Session not awaiting validation")
    
    state_dict = session["state"]
    current_step = state_dict.get("current_validation_step")
    
    try:
        if not validation_req.approved:
            return ValidationResponse(
                success=True,
                session_id=validation_req.session_id,
                current_step=current_step,
                content={"message": "Please provide corrections or additional input"},
                message="Validation rejected. You can provide additional input to improve the result.",
                requires_validation=True
            )
        
        # Process validation steps with enhanced timeouts
        if current_step == ValidationStep.TRANSCRIPT_REVIEW:
            summary = await generate_summary_with_validation(
                validation_req.session_id, 
                state_dict["transcript"], 
                validation_req.user_input
            )
            state_dict.update({
                "summary": summary,
                "current_validation_step": ValidationStep.SUMMARY_REVIEW,
                "user_inputs": {**state_dict.get("user_inputs", {}), "transcript": validation_req.user_input or ""}
            })
            
            next_content = {"summary": summary, "original_transcript": state_dict["transcript"]}
            next_message = "Summary generated. Please review and validate."
            
        elif current_step == ValidationStep.SUMMARY_REVIEW:
            violations = await find_violations_with_validation(
                validation_req.session_id,
                state_dict["summary"],
                validation_req.user_input
            )
            state_dict.update({
                "violations": violations,
                "current_validation_step": ValidationStep.VIOLATIONS_REVIEW,
                "user_inputs": {**state_dict.get("user_inputs", {}), "summary": validation_req.user_input or ""}
            })
            
            next_content = {"violations": violations, "summary": state_dict["summary"]}
            next_message = "Legal violations identified. Please review and validate."
            
        elif current_step == ValidationStep.VIOLATIONS_REVIEW:
            narrative = await generate_fir_narrative_with_validation(
                validation_req.session_id,
                state_dict["transcript"],
                validation_req.user_input
            )
            state_dict.update({
                "fir_narrative": narrative,
                "current_validation_step": ValidationStep.FIR_NARRATIVE_REVIEW,
                "user_inputs": {**state_dict.get("user_inputs", {}), "violations": validation_req.user_input or ""}
            })
            
            next_content = {"fir_narrative": narrative}
            next_message = "FIR narrative generated. Please review and validate."
            
        elif current_step == ValidationStep.FIR_NARRATIVE_REVIEW:
            fir_number = f"FIR-{validation_req.session_id[:8]}-{datetime.now():%Y%m%d%H%M%S}"
            
            # Generate structured FIR data
            fir_data = get_fir_data(state_dict, fir_number)
            
            # Render FIR using template
            fir_content = fir_template.format(**fir_data).strip()
            
            # Use DateTimeEncoder for JSON serialization
            violations_json = json.dumps(state_dict["violations"], cls=DateTimeEncoder)
            
            # Save to database
            db.save(fir_number, validation_req.session_id, state_dict["transcript"], fir_content, violations_json)
            
            state_dict.update({
                "fir_number": fir_number,
                "fir_content": fir_content,
                "current_validation_step": ValidationStep.FINAL_REVIEW,
                "user_inputs": {**state_dict.get("user_inputs", {}), "narrative": validation_req.user_input or ""}
            })
            
            next_content = {"fir_content": fir_content, "fir_number": fir_number}
            next_message = "FIR generated successfully. Final review required."

            
        elif current_step == ValidationStep.FINAL_REVIEW:
            session_manager.set_session_status(validation_req.session_id, SessionStatus.COMPLETED)
            state_dict["awaiting_validation"] = False
            
            session_manager.update_session(validation_req.session_id, state_dict)
            
            return ValidationResponse(
                success=True,
                session_id=validation_req.session_id,
                current_step=ValidationStep.FINAL_REVIEW,
                content={"fir_content": state_dict["fir_content"], "fir_number": state_dict["fir_number"]},
                message="FIR processing completed successfully!",
                requires_validation=False,
                completed=True
            )
        
        session_manager.update_session(validation_req.session_id, state_dict)
        
        return ValidationResponse(
            success=True,
            session_id=validation_req.session_id,
            current_step=state_dict["current_validation_step"],
            content=next_content,
            message=next_message,
            requires_validation=True
        )
        
    except asyncio.TimeoutError:
        log.error(f"Validation timeout for session {validation_req.session_id}")
        raise HTTPException(status_code=504, detail="Processing timeout - please try again")
    except Exception as e:
        log.error(f"Validation error: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")


@app.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    return {
        "session_id": session_id,
        "status": session["status"],
        "current_step": session["state"].get("current_validation_step"),
        "awaiting_validation": session["state"].get("awaiting_validation", False),
        "created_at": session["created_at"].isoformat(),
        "last_activity": session["last_activity"].isoformat(),
        "validation_history": session["validation_history"]
    }

@app.post("/regenerate/{session_id}")
async def regenerate_step(session_id: str, step: ValidationStep, user_input: Optional[str] = None):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    state_dict = session["state"]
    
    try:
        if step == ValidationStep.SUMMARY_REVIEW:
            summary = await generate_summary_with_validation(session_id, state_dict["transcript"], user_input)
            state_dict["summary"] = summary
            content = {"summary": summary}
            
        elif step == ValidationStep.VIOLATIONS_REVIEW:
            violations = await find_violations_with_validation(session_id, state_dict["summary"], user_input)
            state_dict["violations"] = violations
            content = {"violations": violations}
            
        elif step == ValidationStep.FIR_NARRATIVE_REVIEW:
            narrative = await generate_fir_narrative_with_validation(session_id, state_dict["transcript"], user_input)
            state_dict["fir_narrative"] = narrative
            content = {"fir_narrative": narrative}
            
        else:
            raise HTTPException(status_code=400, detail="Invalid step for regeneration")
        
        session_manager.update_session(session_id, state_dict)
        
        return {
            "success": True,
            "session_id": session_id,
            "step": step,
            "content": content,
            "message": f"Content regenerated for {step}"
        }
        
    except Exception as e:
        log.error(f"Regeneration error: {e}")
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {e}")

@app.post("/authenticate", response_model=AuthResponse)
async def authenticate_fir(auth_req: AuthRequest):
    if auth_req.auth_key != CFG["auth_key"]:
        raise HTTPException(status_code=401, detail="Invalid authentication key")
    
    try:
        fir_record = db.get_fir(auth_req.fir_number)
        if not fir_record:
            raise HTTPException(status_code=404, detail="FIR not found")
        
        if fir_record["status"] == "finalized":
            raise HTTPException(status_code=400, detail="FIR already finalized")
        
        db.finalize_fir(auth_req.fir_number)
        
        return AuthResponse(
            success=True,
            message="FIR successfully finalized",
            fir_number=auth_req.fir_number
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@app.get("/fir/{fir_number}")
async def get_fir_status(fir_number: str):
    try:
        fir_record = db.get_fir(fir_number)
        if not fir_record:
            raise HTTPException(status_code=404, detail="FIR not found")
            
        return {
            "fir_number": fir_number,
            "status": fir_record["status"],
            "created_at": fir_record["created_at"],
            "finalized_at": fir_record.get("finalized_at"),
            "content": fir_record["fir_content"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving FIR: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve FIR")

@app.get("/health")
async def health():
    try:
        pool = await ModelPool.get()
        
        # Check model server
        async with httpx.AsyncClient(timeout=5.0) as client:
            model_resp = await client.get(f"{pool.MODEL_SERVER_URL}/health")
            model_server_status = model_resp.json()
            
            # Check ASR/OCR server
            asr_ocr_resp = await client.get(f"{pool.ASR_OCR_SERVER_URL}/health")
            asr_ocr_server_status = asr_ocr_resp.json()
        
        overall_status = "healthy"
        if model_server_status.get("status") != "healthy" or asr_ocr_server_status.get("status") != "healthy":
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "model_server": model_server_status,
            "asr_ocr_server": asr_ocr_server_status,
            "database": "connected",
            "kb_collections": len(KB.cols),
            "session_persistence": "sqlite",
            "magic_available": MAGIC_AVAILABLE,
        }
    except Exception as e:
        log.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/view_fir_records", response_class=HTMLResponse)
def view_fir_records():
    with db._cursor() as cur:
        cur.execute("SELECT fir_number, status, created_at FROM fir_records ORDER BY created_at DESC LIMIT 100")
        records = cur.fetchall()

    # Simple HTML table to display records
    html_content = """
    <html>
      <head><title>FIR Records</title></head>
      <body>
        <h1>FIR Records (Latest 100)</h1>
        <table border="1" cellspacing="0" cellpadding="5">
          <tr>
            <th>FIR Number</th>
            <th>Status</th>
            <th>Created At</th>
            <th>View FIR</th>
          </tr>
    """

    for r in records:
        html_content += f"""
          <tr>
            <td>{r['fir_number']}</td>
            <td>{r['status']}</td>
            <td>{r['created_at']}</td>
            <td><a href="/view_fir/{r['fir_number']}" target="_blank">View</a></td>
          </tr>
        """

    html_content += """
        </table>
      </body>
    </html>
    """

    return html_content


@app.get("/view_fir/{fir_number}", response_class=HTMLResponse)
def view_fir(fir_number: str):
    record = db.get_fir(fir_number)
    if not record:
        return HTMLResponse(content="<h2>FIR not found</h2>", status_code=404)

    fir_text = record['fir_content'].replace('\n', '<br/>')
    return f"""
    <html>
      <head><title>View FIR {fir_number}</title></head>
      <body>
        <h1>FIR Number: {fir_number}</h1>
        <div style="white-space: pre-wrap; font-family: monospace;">{fir_text}</div>
      </body>
    </html>
    """
@app.get("/list_firs")
def list_firs():
    with db._cursor() as cur:
        cur.execute("SELECT fir_number, status FROM fir_records ORDER BY created_at DESC LIMIT 20")
        records = cur.fetchall()
    return records


if __name__ == "__main__":
    uvicorn.run("fir_pipeline_production_ready:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
