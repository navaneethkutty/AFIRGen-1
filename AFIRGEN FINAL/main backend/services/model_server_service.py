"""
Model server service with circuit breaker protection.

This module provides a service layer for calling model servers (GGUF LLM, ASR/OCR)
with circuit breaker protection to prevent cascading failures.

Validates: Requirements 6.3
"""

from typing import Any, Dict, Optional
import requests
from infrastructure.circuit_breaker import get_circuit_breaker, CircuitBreakerError
from infrastructure.retry_handler import RetryHandler
from infrastructure.metrics import MetricsCollector


class ModelServerService:
    """
    Service for calling model servers with circuit breaker protection.
    
    Provides methods to call GGUF LLM and ASR/OCR model servers with:
    - Circuit breaker protection
    - Retry logic for transient failures
    - Metrics tracking
    - Fallback strategies
    
    Validates: Requirements 6.3
    """
    
    def __init__(
        self,
        gguf_url: str,
        asr_ocr_url: str,
        timeout: int = 30,
        enable_circuit_breaker: bool = True,
        enable_retry: bool = True
    ):
        """
        Initialize ModelServerService.
        
        Args:
            gguf_url: URL of the GGUF LLM model server
            asr_ocr_url: URL of the ASR/OCR model server
            timeout: Request timeout in seconds (default: 30)
            enable_circuit_breaker: Enable circuit breaker protection (default: True)
            enable_retry: Enable retry logic (default: True)
        """
        self.gguf_url = gguf_url
        self.asr_ocr_url = asr_ocr_url
        self.timeout = timeout
        self.enable_circuit_breaker = enable_circuit_breaker
        self.enable_retry = enable_retry
        
        # Initialize circuit breakers for each model server
        if enable_circuit_breaker:
            self.gguf_circuit_breaker = get_circuit_breaker(
                name="gguf_model_server",
                failure_threshold=5,
                recovery_timeout=60,
                half_open_max_calls=3
            )
            self.asr_ocr_circuit_breaker = get_circuit_breaker(
                name="asr_ocr_server",
                failure_threshold=5,
                recovery_timeout=60,
                half_open_max_calls=3
            )
        
        # Initialize retry handler
        if enable_retry:
            self.retry_handler = RetryHandler(
                max_retries=3,
                base_delay=1.0,
                max_delay=10.0,
                exponential_base=2.0,
                jitter=True
            )
    
    def call_gguf_model(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call GGUF LLM model server with circuit breaker protection.
        
        Args:
            prompt: Input prompt for the model
            max_tokens: Maximum tokens to generate (default: 512)
            temperature: Sampling temperature (default: 0.7)
            **kwargs: Additional parameters for the model
        
        Returns:
            Model response as dictionary
        
        Raises:
            CircuitBreakerError: If circuit breaker is open
            requests.RequestException: If request fails after retries
        
        Example:
            >>> service = ModelServerService(gguf_url="http://localhost:8000")
            >>> response = service.call_gguf_model("Generate FIR report for...")
            >>> print(response["text"])
        
        Validates: Requirements 6.3
        """
        def _make_request():
            """Internal function to make the actual request."""
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs
            }
            
            response = requests.post(
                f"{self.gguf_url}/generate",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        
        # Execute with circuit breaker and retry protection
        return self._execute_with_protection(
            _make_request,
            "gguf_model_server",
            self.gguf_circuit_breaker if self.enable_circuit_breaker else None
        )
    
    def call_asr_ocr_model(
        self,
        audio_data: Optional[bytes] = None,
        image_data: Optional[bytes] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call ASR/OCR model server with circuit breaker protection.
        
        Args:
            audio_data: Audio data for ASR (optional)
            image_data: Image data for OCR (optional)
            **kwargs: Additional parameters for the model
        
        Returns:
            Model response as dictionary
        
        Raises:
            CircuitBreakerError: If circuit breaker is open
            requests.RequestException: If request fails after retries
            ValueError: If neither audio_data nor image_data is provided
        
        Example:
            >>> service = ModelServerService(asr_ocr_url="http://localhost:8001")
            >>> with open("audio.wav", "rb") as f:
            ...     response = service.call_asr_ocr_model(audio_data=f.read())
            >>> print(response["text"])
        
        Validates: Requirements 6.3
        """
        if audio_data is None and image_data is None:
            raise ValueError("Either audio_data or image_data must be provided")
        
        def _make_request():
            """Internal function to make the actual request."""
            files = {}
            if audio_data:
                files["audio"] = ("audio.wav", audio_data, "audio/wav")
            if image_data:
                files["image"] = ("image.jpg", image_data, "image/jpeg")
            
            response = requests.post(
                f"{self.asr_ocr_url}/process",
                files=files,
                data=kwargs,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        
        # Execute with circuit breaker and retry protection
        return self._execute_with_protection(
            _make_request,
            "asr_ocr_server",
            self.asr_ocr_circuit_breaker if self.enable_circuit_breaker else None
        )
    
    def _execute_with_protection(
        self,
        func,
        server_name: str,
        circuit_breaker=None
    ) -> Dict[str, Any]:
        """
        Execute a function with circuit breaker and retry protection.
        
        Args:
            func: Function to execute
            server_name: Name of the server (for metrics)
            circuit_breaker: Circuit breaker instance (optional)
        
        Returns:
            Result of function execution
        
        Raises:
            CircuitBreakerError: If circuit breaker is open
            Exception: If execution fails after retries
        """
        import time
        start_time = time.time()
        success = False
        
        try:
            if circuit_breaker and self.enable_circuit_breaker:
                # Execute with circuit breaker
                if self.enable_retry:
                    # Combine circuit breaker with retry
                    result = circuit_breaker.call(
                        self.retry_handler.execute_with_retry,
                        func,
                        None  # Use automatic error classification
                    )
                else:
                    # Circuit breaker only
                    result = circuit_breaker.call(func)
            elif self.enable_retry:
                # Retry only (no circuit breaker)
                result = self.retry_handler.execute_with_retry(func, None)
            else:
                # No protection
                result = func()
            
            success = True
            return result
        
        finally:
            # Record metrics
            duration = time.time() - start_time
            MetricsCollector.record_model_server_latency(
                server_name,
                duration,
                success
            )
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all circuit breakers.
        
        Returns:
            Dictionary mapping server names to circuit breaker stats
        
        Example:
            >>> service = ModelServerService(gguf_url="...", asr_ocr_url="...")
            >>> status = service.get_circuit_breaker_status()
            >>> print(status["gguf_model_server"]["state"])
            'closed'
        """
        if not self.enable_circuit_breaker:
            return {}
        
        return {
            "gguf_model_server": self.gguf_circuit_breaker.get_stats().to_dict(),
            "asr_ocr_server": self.asr_ocr_circuit_breaker.get_stats().to_dict()
        }
    
    def reset_circuit_breakers(self) -> None:
        """
        Manually reset all circuit breakers to CLOSED state.
        
        This should be used for administrative purposes or after
        confirming that services have recovered.
        
        Example:
            >>> service = ModelServerService(gguf_url="...", asr_ocr_url="...")
            >>> service.reset_circuit_breakers()
        """
        if self.enable_circuit_breaker:
            self.gguf_circuit_breaker.reset()
            self.asr_ocr_circuit_breaker.reset()


# Example usage with fallback strategies
class ModelServerServiceWithFallback(ModelServerService):
    """
    Extended model server service with fallback strategies.
    
    Provides fallback mechanisms when circuit breakers are open:
    - Cached responses
    - Default responses
    - Alternative model servers
    """
    
    def __init__(self, *args, cache_manager=None, **kwargs):
        """
        Initialize with optional cache manager for fallback.
        
        Args:
            cache_manager: CacheManager instance for caching responses
            *args, **kwargs: Arguments for ModelServerService
        """
        super().__init__(*args, **kwargs)
        self.cache_manager = cache_manager
    
    def call_gguf_model_with_fallback(
        self,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call GGUF model with fallback to cached response.
        
        If circuit breaker is open, returns cached response if available.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters
        
        Returns:
            Model response or cached response
        """
        try:
            return self.call_gguf_model(prompt, **kwargs)
        except CircuitBreakerError:
            # Circuit is open, try fallback
            if self.cache_manager:
                cache_key = f"gguf:response:{hash(prompt)}"
                cached = self.cache_manager.get(cache_key, namespace="model_responses")
                if cached:
                    return {
                        "text": cached,
                        "from_cache": True,
                        "circuit_breaker_open": True
                    }
            
            # No cache available, return error response
            return {
                "error": "Model server unavailable",
                "circuit_breaker_open": True,
                "text": ""
            }
    
    def call_asr_ocr_model_with_fallback(
        self,
        audio_data: Optional[bytes] = None,
        image_data: Optional[bytes] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call ASR/OCR model with fallback to cached response.
        
        If circuit breaker is open, returns cached response if available.
        
        Args:
            audio_data: Audio data (optional)
            image_data: Image data (optional)
            **kwargs: Additional parameters
        
        Returns:
            Model response or cached response
        """
        try:
            return self.call_asr_ocr_model(audio_data, image_data, **kwargs)
        except CircuitBreakerError:
            # Circuit is open, return error response
            return {
                "error": "ASR/OCR server unavailable",
                "circuit_breaker_open": True,
                "text": ""
            }
