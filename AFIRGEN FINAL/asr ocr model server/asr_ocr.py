# asr_ocr_server.py
# -------------------------------------------------------------
# Separate ASR/OCR Server for Whisper and dots_ocr processing
# -------------------------------------------------------------

import os
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("asr_ocr_server.log"), logging.StreamHandler()],
)
log = logging.getLogger("asr_ocr_server")

# Configuration
CONFIG = {
    "max_file_size": 25 * 1024 * 1024,  # 25MB
    "allowed_audio": {"audio/wav", "audio/mpeg", "audio/mp3"},
    "allowed_image": {"image/jpeg", "image/png", "image/jpg"},
    "model_dir": Path(os.getenv("MODEL_DIR", "./models")),
    "temp_dir": Path("./temp_asr_ocr"),
}

CONFIG["temp_dir"].mkdir(exist_ok=True)

# Response models
class ASRResponse(BaseModel):
    success: bool
    transcript: Optional[str] = None
    error: Optional[str] = None

class OCRResponse(BaseModel):
    success: bool
    extracted_text: Optional[str] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    models: dict
    message: Optional[str] = None

# Global model storage
MODELS = {
    "whisper": None,
    "dots_model": None,
    "dots_processor": None
}

def sanitise_text(text: str) -> str:
    """Clean and sanitize extracted text"""
    if not text:
        return ""
    import re
    import string
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = "".join(ch for ch in text if ch in string.printable)
    return text

def load_whisper_model():
    """Load Whisper model for ASR"""
    try:
        import whisper
        model = whisper.load_model("tiny")  # You can change to "base", "small", etc.
        MODELS["whisper"] = model
        log.info("Whisper model loaded successfully")
        return True
    except Exception as e:
        log.error(f"Failed to load Whisper model: {e}")
        return False

def load_dots_ocr_model():
    """Load dots_ocr model for OCR"""
    try:
        from transformers import AutoModelForCausalLM, AutoProcessor
        import torch
        
        model_path = CONFIG["model_dir"] / "dots_ocr"
        if not model_path.exists():
            log.error(f"dots_ocr model directory not found: {model_path}")
            return False

        device_map = "auto" if torch.cuda.is_available() else "cpu"
        torch_dtype = "auto" if torch.cuda.is_available() else torch.float32

        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            torch_dtype=torch_dtype,
            device_map=device_map,
            trust_remote_code=True,
        )
        processor = AutoProcessor.from_pretrained(
            str(model_path), 
            trust_remote_code=True
        )
        
        MODELS["dots_model"] = model
        MODELS["dots_processor"] = processor
        log.info("dots_ocr model loaded successfully")
        return True
        
    except Exception as e:
        log.error(f"Failed to load dots_ocr model: {e}")
        return False

def process_audio_file(file_path: str) -> str:
    """Process audio file with Whisper"""
    if MODELS["whisper"] is None:
        raise RuntimeError("Whisper model not loaded")
    
    try:
        result = MODELS["whisper"].transcribe(file_path)
        return sanitise_text(result["text"])
    except Exception as e:
        log.error(f"Audio processing failed: {e}")
        raise RuntimeError(f"ASR processing failed: {e}")

def process_image_file(file_path: str) -> str:
    """Process image file with dots_ocr"""
    if MODELS["dots_model"] is None or MODELS["dots_processor"] is None:
        raise RuntimeError("dots_ocr model not loaded")
    
    try:
        from PIL import Image
        import torch
        
        device = next(MODELS["dots_model"].parameters()).device
        
        with Image.open(file_path) as img:
            img = img.convert("RGB")
            prompt = "Extract the text from this image in plain text."
            inputs = MODELS["dots_processor"](text=prompt, images=img, return_tensors="pt")
            
            inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v 
                     for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = MODELS["dots_model"].generate(**inputs, max_new_tokens=1024)
            
            generated_text = MODELS["dots_processor"].decode(
                outputs[0][len(inputs['input_ids']):], 
                skip_special_tokens=True
            )
            return sanitise_text(generated_text)
            
    except Exception as e:
        log.error(f"Image processing failed: {e}")
        raise RuntimeError(f"OCR processing failed: {e}")

# FastAPI app
app = FastAPI(title="ASR/OCR Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Load models on startup"""
    log.info("Starting ASR/OCR server...")
    
    whisper_loaded = load_whisper_model()
    dots_loaded = load_dots_ocr_model()
    
    if not whisper_loaded:
        log.warning("Whisper model failed to load - ASR will be unavailable")
    if not dots_loaded:
        log.warning("dots_ocr model failed to load - OCR will be unavailable")
    
    if not (whisper_loaded or dots_loaded):
        log.error("No models loaded successfully!")
    else:
        log.info("ASR/OCR server startup complete")

@app.post("/asr", response_model=ASRResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio file using Whisper"""
    try:
        # Validate file
        if audio.content_type not in CONFIG["allowed_audio"]:
            raise HTTPException(status_code=415, detail=f"Unsupported audio format: {audio.content_type}")
        
        content = await audio.read()
        if len(content) > CONFIG["max_file_size"]:
            raise HTTPException(status_code=413, detail="Audio file too large")
        
        # Save temporary file
        suffix = Path(audio.filename).suffix.lower() if audio.filename else ".wav"
        temp_file = CONFIG["temp_dir"] / f"{uuid.uuid4().hex}{suffix}"
        
        try:
            temp_file.write_bytes(content)
            transcript = process_audio_file(str(temp_file))
            
            return ASRResponse(
                success=True,
                transcript=transcript
            )
            
        finally:
            # Cleanup temp file
            if temp_file.exists():
                temp_file.unlink()
                
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"ASR processing error: {e}")
        return ASRResponse(
            success=False,
            error=str(e)
        )

@app.post("/ocr", response_model=OCRResponse)
async def extract_text_from_image(image: UploadFile = File(...)):
    """Extract text from image using dots_ocr"""
    try:
        # Validate file
        if image.content_type not in CONFIG["allowed_image"]:
            raise HTTPException(status_code=415, detail=f"Unsupported image format: {image.content_type}")
        
        content = await image.read()
        if len(content) > CONFIG["max_file_size"]:
            raise HTTPException(status_code=413, detail="Image file too large")
        
        # Save temporary file
        suffix = Path(image.filename).suffix.lower() if image.filename else ".jpg"
        temp_file = CONFIG["temp_dir"] / f"{uuid.uuid4().hex}{suffix}"
        
        try:
            temp_file.write_bytes(content)
            extracted_text = process_image_file(str(temp_file))
            
            return OCRResponse(
                success=True,
                extracted_text=extracted_text
            )
            
        finally:
            # Cleanup temp file
            if temp_file.exists():
                temp_file.unlink()
                
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"OCR processing error: {e}")
        return OCRResponse(
            success=False,
            error=str(e)
        )

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Check server health and model status"""
    models_status = {
        "whisper": MODELS["whisper"] is not None,
        "dots_ocr": MODELS["dots_model"] is not None and MODELS["dots_processor"] is not None
    }
    
    loaded_models = sum(models_status.values())
    total_models = len(models_status)
    
    if loaded_models == total_models:
        status = "healthy"
        message = "All models loaded successfully"
    elif loaded_models > 0:
        status = "degraded"
        message = f"{loaded_models}/{total_models} models loaded"
    else:
        status = "unhealthy"
        message = "No models loaded"
    
    return HealthResponse(
        status=status,
        models=models_status,
        message=message
    )

if __name__ == "__main__":
    uvicorn.run(
        "asr_ocr_server:app", 
        host="0.0.0.0", 
        port=int(os.getenv("ASR_OCR_PORT", 8002))
    )
