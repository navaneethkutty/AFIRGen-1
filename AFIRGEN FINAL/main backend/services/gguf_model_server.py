"""
GGUF LLM Model Server Implementation

Concrete implementation of ILLMModelServer interface for GGUF model server.
Provides circuit breaker protection and retry logic for LLM calls.

Requirements: 6.3, 8.3
"""

from typing import Any, Dict, Optional
import requests
import time

from interfaces.external_service import (
    ILLMModelServer,
    ServiceStatus,
    ServiceUnavailableError,
    ServiceTimeoutError,
    CircuitBreakerOpenError
)
from infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerError
from infrastructure.retry_handler import RetryHandler
from infrastructure.metrics import MetricsCollector
from infrastructure.logging import get_logger


logger = get_logger(__name__)


class GGUFModelServer(ILLMModelServer):
    """
    GGUF LLM model server implementation.
    
    Implements ILLMModelServer interface with:
    - Circuit breaker protection
    - Automatic retry on transient failures
    - Health checks and status monitoring
    - Metrics tracking
    
    Requirements: 6.3, 8.3
    """
    
    def __init__(
        self,
        url: str,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_handler: Optional[RetryHandler] = None,
        timeout: int = 30
    ):
        """
        Initialize GGUF model server.
        
        Args:
            url: Base URL of the GGUF model server
            circuit_breaker: Optional circuit breaker instance
            retry_handler: Optional retry handler instance
            timeout: Request timeout in seconds (default: 30)
        """
        self._url = url.rstrip('/')
        self._timeout = timeout
        
        # Initialize circuit breaker
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            name="gguf_model_server",
            failure_threshold=5,
            recovery_timeout=60,
            half_open_max_calls=3
        )
        
        # Initialize retry handler
        self._retry_handler = retry_handler or RetryHandler(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True
        )
        
        logger.info("GGUFModelServer initialized", url=self._url)
    
    @property
    def service_name(self) -> str:
        """Get the name of the service."""
        return "gguf_llm_server"
    
    def health_check(self) -> bool:
        """
        Check if the GGUF model server is healthy.
        
        Returns:
            True if server is reachable and healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self._url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning("Health check failed", error=str(e), service=self.service_name)
            return False
    
    def get_status(self) -> ServiceStatus:
        """
        Get the current status of the model server.
        
        Returns:
            ServiceStatus enum value
        """
        # Check circuit breaker state
        cb_stats = self._circuit_breaker.get_stats()
        
        if cb_stats.state == "open":
            return ServiceStatus.UNAVAILABLE
        
        if cb_stats.state == "half_open":
            return ServiceStatus.DEGRADED
        
        # Check health
        if self.health_check():
            return ServiceStatus.AVAILABLE
        
        return ServiceStatus.UNAVAILABLE
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the model server.
        
        Returns:
            Dictionary with service metrics
        """
        cb_stats = self._circuit_breaker.get_stats()
        
        return {
            "service_name": self.service_name,
            "status": self.get_status().value,
            "circuit_breaker": {
                "state": cb_stats.state,
                "failure_count": cb_stats.failure_count,
                "success_count": cb_stats.success_count,
                "last_failure_time": cb_stats.last_failure_time,
                "last_success_time": cb_stats.last_success_time
            }
        }
    
    def call(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        Call the model server with input data.
        
        Args:
            input_data: Input prompt for the model
            **kwargs: Additional parameters (max_tokens, temperature, etc.)
        
        Returns:
            Model response as dictionary
        
        Raises:
            ServiceUnavailableError: If service is unavailable
            ServiceTimeoutError: If request times out
            CircuitBreakerOpenError: If circuit breaker is open
        """
        if not isinstance(input_data, str):
            raise ValueError("input_data must be a string prompt")
        
        return self.generate_text(
            prompt=input_data,
            **kwargs
        )
    
    def call_with_retry(
        self,
        input_data: Any,
        max_retries: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call the model server with automatic retry.
        
        Args:
            input_data: Input prompt for the model
            max_retries: Maximum number of retry attempts
            **kwargs: Additional parameters
        
        Returns:
            Model response as dictionary
        """
        # Create temporary retry handler with custom max_retries
        temp_retry_handler = RetryHandler(
            max_retries=max_retries,
            base_delay=self._retry_handler.base_delay,
            max_delay=self._retry_handler.max_delay,
            exponential_base=self._retry_handler.exponential_base,
            jitter=self._retry_handler.jitter
        )
        
        def _call():
            return self.call(input_data, **kwargs)
        
        try:
            return temp_retry_handler.execute_with_retry(_call, None)
        except Exception as e:
            logger.error(
                "Model server call failed after retries",
                error=str(e),
                max_retries=max_retries,
                service=self.service_name
            )
            raise ServiceUnavailableError(f"Service unavailable after {max_retries} retries: {e}")
    
    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using the LLM.
        
        Args:
            prompt: Input prompt for text generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            **kwargs: Additional model parameters
        
        Returns:
            Dictionary with generated text and metadata
        
        Raises:
            ServiceUnavailableError: If service is unavailable
            ServiceTimeoutError: If request times out
            CircuitBreakerOpenError: If circuit breaker is open
        """
        def _make_request():
            """Internal function to make the actual request."""
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs
            }
            
            try:
                response = requests.post(
                    f"{self._url}/generate",
                    json=payload,
                    timeout=self._timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.Timeout as e:
                raise ServiceTimeoutError(f"Request timed out: {e}")
            except requests.RequestException as e:
                raise ServiceUnavailableError(f"Request failed: {e}")
        
        # Execute with circuit breaker and retry protection
        return self._execute_with_protection(_make_request)
    
    def generate_completion(
        self,
        prompt: str,
        stop_sequences: Optional[list[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion for a prompt.
        
        Args:
            prompt: Input prompt
            stop_sequences: Optional list of sequences to stop generation
            **kwargs: Additional model parameters
        
        Returns:
            Dictionary with completion text and metadata
        """
        if stop_sequences:
            kwargs['stop'] = stop_sequences
        
        return self.generate_text(prompt, **kwargs)
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Get the status of the circuit breaker.
        
        Returns:
            Dictionary with circuit breaker state and statistics
        """
        return self._circuit_breaker.get_stats().to_dict()
    
    def reset_circuit_breaker(self) -> None:
        """
        Manually reset the circuit breaker to CLOSED state.
        """
        self._circuit_breaker.reset()
        logger.info("Circuit breaker reset", service=self.service_name)
    
    def _execute_with_protection(self, func) -> Dict[str, Any]:
        """
        Execute a function with circuit breaker and retry protection.
        
        Args:
            func: Function to execute
        
        Returns:
            Result of function execution
        
        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            ServiceUnavailableError: If execution fails after retries
        """
        start_time = time.time()
        success = False
        
        try:
            # Execute with circuit breaker and retry
            result = self._circuit_breaker.call(
                self._retry_handler.execute_with_retry,
                func,
                None  # Use automatic error classification
            )
            success = True
            return result
        
        except CircuitBreakerError as e:
            logger.error(
                "Circuit breaker open",
                service=self.service_name,
                error=str(e)
            )
            raise CircuitBreakerOpenError(f"Circuit breaker is open: {e}")
        
        except Exception as e:
            logger.error(
                "Model server call failed",
                service=self.service_name,
                error=str(e)
            )
            raise
        
        finally:
            # Record metrics
            duration = time.time() - start_time
            MetricsCollector.record_model_server_latency(
                self.service_name,
                duration,
                success
            )
