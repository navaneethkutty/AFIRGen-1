#!/usr/bin/env python3
"""
Mock GGUF Model Server
Simulates the model server without requiring actual models
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import time

app = FastAPI(title="Mock GGUF Model Server")

class InferenceRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    model: Optional[str] = "default"

class InferenceResponse(BaseModel):
    text: str
    model: str
    tokens_generated: int
    inference_time: float

class HealthResponse(BaseModel):
    status: str
    models_loaded: Dict[str, bool]
    uptime: float

start_time = time.time()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        models_loaded={
            "fir_generator": True,
            "text_classifier": True,
            "summarizer": True
        },
        uptime=time.time() - start_time
    )

@app.post("/generate", response_model=InferenceResponse)
async def generate_text(request: InferenceRequest):
    """Mock text generation endpoint"""
    
    # Simulate processing time
    time.sleep(0.1)
    
    # Generate mock FIR content based on prompt
    mock_response = f"""
FIRST INFORMATION REPORT (FIR)
================================

FIR Number: FIR-2026-{int(time.time()) % 10000}
Date: 22-02-2026
Time: {time.strftime('%H:%M:%S')}

COMPLAINANT DETAILS:
Name: [Mock Complainant Name]
Address: [Mock Address]
Contact: [Mock Contact]

INCIDENT DETAILS:
Date of Incident: 22-02-2026
Time of Incident: [Mock Time]
Place of Incident: [Mock Location]

DESCRIPTION:
{request.prompt[:200]}...

[This is a MOCK FIR generated for testing purposes]

ACCUSED DETAILS:
Name: [Mock Accused Name]
Description: [Mock Description]

SECTIONS APPLIED:
IPC Section 420 (Cheating)
IPC Section 406 (Criminal Breach of Trust)

INVESTIGATING OFFICER:
Name: [Mock Officer Name]
Badge Number: [Mock Badge]

Status: Under Investigation
"""
    
    return InferenceResponse(
        text=mock_response,
        model=request.model or "mock-model",
        tokens_generated=len(mock_response.split()),
        inference_time=0.1
    )

@app.post("/classify")
async def classify_text(request: Dict[str, Any]):
    """Mock text classification endpoint"""
    time.sleep(0.05)
    
    return {
        "classification": "criminal_complaint",
        "confidence": 0.95,
        "categories": ["theft", "fraud", "assault"],
        "severity": "high"
    }

@app.post("/summarize")
async def summarize_text(request: Dict[str, Any]):
    """Mock text summarization endpoint"""
    time.sleep(0.05)
    
    text = request.get("text", "")
    return {
        "summary": f"Mock summary of: {text[:100]}...",
        "key_points": [
            "Mock key point 1",
            "Mock key point 2",
            "Mock key point 3"
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting Mock GGUF Model Server on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
