# model_server.py
# -------------------------------------------------------------
# External Model Server for GGUF Models (LLM Inference)
# -------------------------------------------------------------

import os
import logging
import asyncio
from pathlib import Path
from typing import Optional, List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import llama-cpp-python for GGUF model loading
from llama_cpp import Llama

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("model_server.log"), logging.StreamHandler()],
)
log = logging.getLogger("model_server")

# Configuration
CONFIG = {
    "model_dir": Path(os.getenv("MODEL_DIR", "./models")),
    "n_ctx": 2048,  # Context length
    "n_threads": os.cpu_count() or 4,
    "verbose": False,
}

# Pydantic Models
class InferenceRequest(BaseModel):
    model_name: str
    prompt: str
    max_tokens: Optional[int] = 120
    temperature: Optional[float] = 0.1
    stop: Optional[List[str]] = None

class InferenceResponse(BaseModel):
    result: str

class HealthResponse(BaseModel):
    status: str
    models_loaded: dict
    message: Optional[str] = None

# Model Manager - Loads and manages GGUF models
class ModelManager:
    def __init__(self):
        self.models = {
            "summariser": None,
            "bns_check": None, 
            "fir_summariser": None
        }
        self.model_paths = {
            "summariser": CONFIG["model_dir"] / "complaint_2summarizing.gguf",
            "bns_check": CONFIG["model_dir"] / "BNS-RAG-q4k.gguf",
            "fir_summariser": CONFIG["model_dir"] / "complaint_summarizing_model.gguf"
        }

    def load_models(self):
        """Load all GGUF models on startup"""
        log.info("Loading GGUF models...")
        
        for model_name, model_path in self.model_paths.items():
            try:
                if not model_path.exists():
                    log.error(f"Model file not found: {model_path}")
                    continue
                
                log.info(f"Loading {model_name} from {model_path}")
                self.models[model_name] = Llama(
                    model_path=str(model_path),
                    n_ctx=CONFIG["n_ctx"],
                    n_threads=CONFIG["n_threads"],
                    verbose=CONFIG["verbose"],
                )
                log.info(f"✅ {model_name} loaded successfully")
                
            except Exception as e:
                log.error(f"❌ Failed to load {model_name}: {e}")
                self.models[model_name] = None

        loaded_count = sum(1 for model in self.models.values() if model is not None)
        total_count = len(self.models)
        
        if loaded_count == 0:
            raise RuntimeError("No models loaded successfully!")
        
        log.info(f"Model loading complete: {loaded_count}/{total_count} models loaded")

    def get_model(self, model_name: str):
        """Get a specific model by name"""
        if model_name not in self.models:
            raise ValueError(f"Unknown model: {model_name}")
        
        model = self.models[model_name]
        if model is None:
            raise RuntimeError(f"Model {model_name} not loaded")
        
        return model

    def inference(self, model_name: str, prompt: str, max_tokens: int = 120, 
                 temperature: float = 0.1, stop: Optional[List[str]] = None) -> str:
        """Run inference on specified model"""
        try:
            model = self.get_model(model_name)
            
            # Prepare generation parameters
            generate_params = {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "echo": False,  # Don't include prompt in response
            }
            
            if stop:
                generate_params["stop"] = stop
            
            # Run inference
            result = model(prompt, **generate_params)
            
            # Extract text from response
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["text"].strip()
            else:
                return str(result).strip()
                
        except Exception as e:
            log.error(f"Inference error for {model_name}: {e}")
            raise RuntimeError(f"Inference failed: {e}")

# Global model manager
model_manager = ModelManager()

# FastAPI app
app = FastAPI(title="GGUF Model Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Load models on startup"""
    try:
        # Run model loading in thread pool to avoid blocking
        await asyncio.get_event_loop().run_in_executor(None, model_manager.load_models)
        log.info("🚀 Model server startup complete")
    except Exception as e:
        log.error(f"💥 Startup failed: {e}")
        raise

@app.post("/inference", response_model=InferenceResponse)
async def inference(request: InferenceRequest):
    """Run inference on specified model"""
    try:
        # Validate model name
        if request.model_name not in model_manager.models:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid model_name: {request.model_name}. Available: {list(model_manager.models.keys())}"
            )
        
        # Run inference in thread pool to avoid blocking
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            model_manager.inference,
            request.model_name,
            request.prompt,
            request.max_tokens,
            request.temperature,
            request.stop
        )
        
        return InferenceResponse(result=result)
        
    except RuntimeError as e:
        log.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check server health and model status"""
    try:
        models_status = {
            name: model is not None 
            for name, model in model_manager.models.items()
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
            models_loaded=models_status,
            message=message
        )
        
    except Exception as e:
        log.error(f"Health check error: {e}")
        return HealthResponse(
            status="unhealthy",
            models_loaded={},
            message=f"Health check failed: {e}"
        )

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "service": "GGUF Model Server",
        "version": "1.0.0",
        "endpoints": {
            "inference": "POST /inference",
            "health": "GET /health"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "model_server:app",
        host="0.0.0.0", 
        port=int(os.getenv("MODEL_SERVER_PORT", 8001)),
        log_level="info"
    )
