"""
Model Service - Business logic for AI model interactions.

This service handles all interactions with external model servers (LLM, ASR, OCR),
separated from API routing logic.

Requirements: 8.1 - Separate business logic from API routing
"""

import asyncio
import httpx
from typing import Optional, Dict, Any, List, Tuple, Callable
import time

from infrastructure.circuit_breaker import CircuitBreaker
from infrastructure.retry_handler import RetryHandler
from infrastructure.metrics import MetricsCollector
from infrastructure.xray_tracing import AsyncXRaySubsegment
from infrastructure.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class ModelService:
    """
    Service for interacting with external AI model servers.
    
    Encapsulates business logic for model inference, ASR, and OCR operations.
    """
    
    _instance: Optional["ModelService"] = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    def __init__(
        self,
        model_server_url: str = "http://localhost:8001",
        asr_ocr_server_url: str = "http://localhost:8002"
    ) -> None:
        """
        Initialize ModelService.
        
        Args:
            model_server_url: URL of the GGUF model server
            asr_ocr_server_url: URL of the ASR/OCR server
        """
        self.MODEL_SERVER_URL = model_server_url
        self.ASR_OCR_SERVER_URL = asr_ocr_server_url
        
        # Health check cache
        self._health_check_cache: Dict[str, Tuple[float, Tuple[bool, str]]] = {}
        self._health_check_ttl: int = 30  # Cache TTL in seconds
        
        # Shared HTTP client with connection pooling
        limits = httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20
        )
        self._http_client = httpx.AsyncClient(
            timeout=45.0,
            limits=limits,
            http2=True
        )
        
        # Semaphore to limit concurrent model calls
        self._model_semaphore = asyncio.Semaphore(10)
        
        # Circuit breakers for external services
        self.model_server_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception,
            name="model_server"
        )
        self.asr_ocr_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception,
            name="asr_ocr_server"
        )
        
        # Retry handlers
        self.inference_retry = RetryHandler(
            max_retries=2,
            base_delay=1.0,
            max_delay=10.0
        )
        self.asr_ocr_retry = RetryHandler(
            max_retries=2,
            base_delay=2.0,
            max_delay=15.0
        )
        
        logger.info("ModelService initialized with circuit breakers and retry policies")
    
    @classmethod
    async def get_instance(
        cls,
        model_server_url: str = "http://localhost:8001",
        asr_ocr_server_url: str = "http://localhost:8002"
    ) -> "ModelService":
        """Get singleton instance of ModelService."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = ModelService(model_server_url, asr_ocr_server_url)
            return cls._instance
    
    async def _check_server_health(self, server_url: str, server_name: str) -> Tuple[bool, str]:
        """
        Check if a server is healthy and models are loaded.
        
        Args:
            server_url: Server URL
            server_name: Server name for logging
            
        Returns:
            Tuple of (is_healthy, message)
        """
        # Check cache first
        cache_key = f"{server_name}_{server_url}"
        if cache_key in self._health_check_cache:
            cached_time, cached_result = self._health_check_cache[cache_key]
            if time.time() - cached_time < self._health_check_ttl:
                return cached_result
        
        try:
            resp = await self._http_client.get(f"{server_url}/health", timeout=5.0)
            resp.raise_for_status()
            health_data = resp.json()
            
            status = health_data.get("status", "unknown")
            message = health_data.get("message", "No message")
            
            is_healthy = status in ["healthy", "degraded"]
            result: Tuple[bool, str] = (is_healthy, message)
            
            # Cache result
            self._health_check_cache[cache_key] = (time.time(), result)
            
            return result
            
        except Exception as e:
            error_msg = f"{server_name} health check failed: {str(e)}"
            logger.error(error_msg)
            result = (False, error_msg)
            
            # Cache failure for shorter time
            self._health_check_cache[cache_key] = (
                time.time() - self._health_check_ttl + 5,
                result
            )
            
            return result
    
    async def _inference(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int = 120,
        temperature: float = 0.1,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Perform model inference.
        
        Args:
            model_name: Name of the model to use
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop: Stop sequences
            
        Returns:
            Generated text
            
        Raises:
            RuntimeError: If inference fails
        """
        # Check model server health first
        is_healthy, health_msg = await self._check_server_health(
            self.MODEL_SERVER_URL,
            "Model Server"
        )
        if not is_healthy:
            raise RuntimeError(f"Model server is not healthy: {health_msg}")
        
        async def _do_inference():
            async with self._model_semaphore:
                async with AsyncXRaySubsegment(f"model_inference_{model_name}") as subsegment:
                    subsegment.put_annotation("model_name", model_name)
                    subsegment.put_annotation("max_tokens", max_tokens)
                    subsegment.put_metadata("prompt_length", len(prompt))
                    
                    start_time = time.time()
                    success = False
                    
                    payload = {
                        "model_name": model_name,
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                    if stop:
                        payload["stop"] = stop
                    
                    try:
                        resp = await self._http_client.post(
                            f"{self.MODEL_SERVER_URL}/inference",
                            json=payload
                        )
                        resp.raise_for_status()
                        result = resp.json()
                        
                        success = True
                        subsegment.put_annotation("success", True)
                        subsegment.put_metadata("response_length", len(result["result"]))
                        
                        return result["result"]
                        
                    except httpx.RequestError as e:
                        subsegment.put_annotation("error", True)
                        subsegment.put_metadata("error_type", "request_error")
                        logger.error(f"Model server request failed: {e}")
                        raise RuntimeError(f"Model server unavailable: {e}")
                        
                    except httpx.HTTPStatusError as e:
                        subsegment.put_annotation("error", True)
                        subsegment.put_metadata("error_type", "http_error")
                        subsegment.put_metadata("status_code", e.response.status_code)
                        logger.error(f"Model server returned error: {e.response.status_code}")
                        raise RuntimeError(f"Model inference failed: {e.response.text}")
                        
                    finally:
                        duration = time.time() - start_time
                        MetricsCollector.record_model_server_latency(
                            "gguf_model_server",
                            duration,
                            success
                        )
        
        # Apply circuit breaker and retry policy
        return await self.model_server_circuit.call(
            lambda: self.inference_retry.execute_with_retry(
                _do_inference,
                retryable_exceptions=(httpx.RequestError, httpx.HTTPStatusError)
            )
        )
    
    async def two_line_summary(self, text: str) -> str:
        """
        Generate a two-sentence summary of the complaint.
        
        Args:
            text: Input text to summarize
            
        Returns:
            Two-sentence summary
        """
        prompt = (
            f"<|user|>\nSummarise the following complaint in exactly two sentences:\n"
            f"{text}\n<|assistant|>"
        )
        return await self._inference("summariser", prompt, max_tokens=100, temperature=0.1)
    
    async def check_violation(self, summary: str, ref: str) -> bool:
        """
        Check if a summary indicates a legal violation.
        
        Args:
            summary: Complaint summary
            ref: Reference BNS clause
            
        Returns:
            True if violation detected, False otherwise
        """
        prompt = (
            f"<|user|>\nComplaint summary:\n{summary}\n\n"
            f"Reference BNS clause:\n{ref}\n\n"
            f"Does the summary indicate a violation? Answer only YES or NO.\n<|assistant|>"
        )
        response = await self._inference("bns_check", prompt, max_tokens=3, temperature=0.0, stop=["\n"])
        return response.strip().upper().startswith("YES")
    
    async def fir_narrative(self, complaint: str) -> str:
        """
        Create a concise FIR narrative from a complaint.
        
        Args:
            complaint: Input complaint text
            
        Returns:
            FIR narrative (max 3 sentences)
        """
        prompt = (
            f"<|user|>\nCreate a concise FIR narrative (max 3 sentences) from:\n"
            f"{complaint}\n<|assistant|>"
        )
        return await self._inference("fir_summariser", prompt, max_tokens=150, temperature=0.2)
    
    async def whisper_transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio using ASR.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text
            
        Raises:
            RuntimeError: If transcription fails
        """
        # Check ASR/OCR server health first
        is_healthy, health_msg = await self._check_server_health(
            self.ASR_OCR_SERVER_URL,
            "ASR/OCR Server"
        )
        if not is_healthy:
            raise RuntimeError(f"ASR/OCR server is not healthy: {health_msg}")
        
        async def _do_asr():
            async with self._model_semaphore:
                start_time = time.time()
                success = False
                
                try:
                    with open(audio_path, 'rb') as audio_file:
                        files = {"audio": audio_file}
                        resp = await self._http_client.post(
                            f"{self.ASR_OCR_SERVER_URL}/asr",
                            files=files,
                            timeout=180.0
                        )
                        resp.raise_for_status()
                        result = resp.json()
                        
                        if not result.get("success", False):
                            error_detail = result.get('error', 'Unknown error')
                            raise RuntimeError(f"ASR failed: {error_detail}")
                        
                        transcript = result.get("transcript", "")
                        if not transcript:
                            raise RuntimeError("ASR returned empty transcript")
                        
                        success = True
                        return transcript
                        
                except httpx.RequestError as e:
                    logger.error(f"ASR server request failed: {e}")
                    raise RuntimeError(f"ASR server unavailable: {e}")
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"ASR server returned error: {e.response.status_code}")
                    raise RuntimeError(f"ASR processing failed: {e.response.text}")
                    
                finally:
                    duration = time.time() - start_time
                    MetricsCollector.record_model_server_latency(
                        "asr_ocr_server",
                        duration,
                        success
                    )
        
        # Apply circuit breaker and retry policy
        return await self.asr_ocr_circuit.call(
            lambda: self.asr_ocr_retry.execute_with_retry(
                _do_asr,
                retryable_exceptions=(httpx.RequestError, httpx.HTTPStatusError)
            )
        )
    
    async def dots_ocr_sync(self, image_path: str) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text
            
        Raises:
            RuntimeError: If OCR fails
        """
        # Check ASR/OCR server health first
        is_healthy, health_msg = await self._check_server_health(
            self.ASR_OCR_SERVER_URL,
            "ASR/OCR Server"
        )
        if not is_healthy:
            raise RuntimeError(f"ASR/OCR server is not healthy: {health_msg}")
        
        async def _do_ocr():
            async with self._model_semaphore:
                start_time = time.time()
                success = False
                
                try:
                    with open(image_path, 'rb') as image_file:
                        files = {"image": image_file}
                        resp = await self._http_client.post(
                            f"{self.ASR_OCR_SERVER_URL}/ocr",
                            files=files,
                            timeout=120.0
                        )
                        resp.raise_for_status()
                        result = resp.json()
                        
                        if not result.get("success", False):
                            error_detail = result.get('error', 'Unknown error')
                            raise RuntimeError(f"OCR failed: {error_detail}")
                        
                        extracted_text = result.get("extracted_text", "")
                        if not extracted_text:
                            raise RuntimeError("OCR returned empty text")
                        
                        success = True
                        return extracted_text
                        
                except httpx.RequestError as e:
                    logger.error(f"OCR server request failed: {e}")
                    raise RuntimeError(f"OCR server unavailable: {e}")
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"OCR server returned error: {e.response.status_code}")
                    raise RuntimeError(f"OCR processing failed: {e.response.text}")
                    
                finally:
                    duration = time.time() - start_time
                    MetricsCollector.record_model_server_latency(
                        "asr_ocr_server",
                        duration,
                        success
                    )
        
        # Apply circuit breaker and retry policy
        return await self.asr_ocr_circuit.call(
            lambda: self.asr_ocr_retry.execute_with_retry(
                _do_ocr,
                retryable_exceptions=(httpx.RequestError, httpx.HTTPStatusError)
            )
        )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of all model servers.
        
        Returns:
            Dictionary with health status of model servers
        """
        model_is_healthy, model_msg = await self._check_server_health(
            self.MODEL_SERVER_URL,
            "Model Server"
        )
        asr_ocr_is_healthy, asr_ocr_msg = await self._check_server_health(
            self.ASR_OCR_SERVER_URL,
            "ASR/OCR Server"
        )
        
        return {
            "model_server": {
                "healthy": model_is_healthy,
                "message": model_msg,
                "circuit_breaker": self.model_server_circuit.get_stats()
            },
            "asr_ocr_server": {
                "healthy": asr_ocr_is_healthy,
                "message": asr_ocr_msg,
                "circuit_breaker": self.asr_ocr_circuit.get_stats()
            }
        }
