#!/usr/bin/env python3
"""
Mock ASR/OCR Server
Simulates the ASR/OCR server without requiring actual models
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import time
import base64

app = FastAPI(title="Mock ASR/OCR Server")

class HealthResponse(BaseModel):
    status: str
    models_loaded: Dict[str, bool]
    uptime: float

class ASRResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration: float

class OCRResponse(BaseModel):
    text: str
    language: str
    confidence: float
    pages: int

start_time = time.time()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        models_loaded={
            "whisper": True,
            "dots_ocr": True
        },
        uptime=time.time() - start_time
    )

@app.post("/transcribe", response_model=ASRResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """Mock audio transcription endpoint"""
    
    # Simulate processing time
    time.sleep(0.2)
    
    mock_transcription = """
Mock Audio Transcription:

I want to file a complaint regarding a theft that occurred at my residence on 21st February 2026.
The incident happened around 10:30 PM when unknown persons broke into my house through the back door.
They stole jewelry worth approximately 2 lakh rupees, a laptop, and some cash.
I noticed the theft when I returned home around 11:00 PM.
The lock on the back door was broken and the house was ransacked.
I request immediate action and investigation into this matter.

[This is a MOCK transcription generated for testing purposes]
"""
    
    return ASRResponse(
        text=mock_transcription.strip(),
        language="en",
        confidence=0.92,
        duration=0.2
    )

@app.post("/ocr", response_model=OCRResponse)
async def extract_text_from_image(file: UploadFile = File(...)):
    """Mock OCR endpoint"""
    
    # Simulate processing time
    time.sleep(0.15)
    
    mock_ocr_text = """
Mock OCR Extracted Text:

COMPLAINT LETTER

Date: 21-02-2026

To,
The Station House Officer
[Police Station Name]

Subject: Complaint regarding theft

Respected Sir/Madam,

I, [Complainant Name], resident of [Address], would like to file a complaint regarding
a theft that occurred at my residence on 21st February 2026 at approximately 10:30 PM.

Details of the incident:
- Date: 21-02-2026
- Time: 10:30 PM
- Location: [Address]
- Items stolen: Gold jewelry (worth Rs. 2,00,000), Laptop (Dell, worth Rs. 50,000), Cash (Rs. 10,000)

I request you to kindly register my complaint and take necessary action.

Thanking you,
[Signature]
[Name]

[This is a MOCK OCR extraction generated for testing purposes]
"""
    
    return OCRResponse(
        text=mock_ocr_text.strip(),
        language="en",
        confidence=0.88,
        pages=1
    )

@app.post("/detect_language")
async def detect_language(request: Dict[str, Any]):
    """Mock language detection endpoint"""
    time.sleep(0.02)
    
    return {
        "language": "en",
        "confidence": 0.95,
        "alternatives": [
            {"language": "hi", "confidence": 0.03},
            {"language": "ta", "confidence": 0.02}
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting Mock ASR/OCR Server on port 8002...")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
