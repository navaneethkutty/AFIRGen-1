"""
External Service Interfaces

Defines abstract base classes for external service integrations.
These interfaces establish contracts for interacting with external services
like model servers, ensuring consistent patterns and enabling testing.

Requirements: 8.3 - Define clear interfaces for external service interactions
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum


class ServiceStatus(str, Enum):
    """Status of an external service."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class IExternalService(ABC):
    """
    Abstract base class for external service integrations.
    
    This interface defines the contract for interacting with external services,
    including health checks, status monitoring, and error handling.
    
    All external service implementations should inherit from this interface
    to ensure consistent patterns across the application.
    
    Requirements: 8.3
    """
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """
        Get the name of the external service.
        
        Returns:
            Service name as string
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the external service is healthy and reachable.
        
        Returns:
            True if service is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def get_status(self) -> ServiceStatus:
        """
        Get the current status of the external service.
        
        Returns:
            ServiceStatus enum value
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the external service.
        
        Returns:
            Dictionary with service metrics (latency, success rate, etc.)
        """
        pass


class IModelServer(IExternalService):
    """
    Abstract base class for model server integrations.
    
    This interface extends IExternalService with model-specific operations
    for calling AI model servers (LLM, ASR, OCR, etc.).
    
    Requirements: 8.3
    """
    
    @abstractmethod
    def call(
        self,
        input_data: Any,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call the model server with input data.
        
        Args:
            input_data: Input data for the model (text, audio, image, etc.)
            **kwargs: Additional parameters for the model
        
        Returns:
            Model response as dictionary
        
        Raises:
            ServiceUnavailableError: If service is unavailable
            ServiceTimeoutError: If request times out
            ServiceError: For other service errors
        """
        pass
    
    @abstractmethod
    def call_with_retry(
        self,
        input_data: Any,
        max_retries: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call the model server with automatic retry on transient failures.
        
        Args:
            input_data: Input data for the model
            max_retries: Maximum number of retry attempts
            **kwargs: Additional parameters for the model
        
        Returns:
            Model response as dictionary
        
        Raises:
            ServiceUnavailableError: If service is unavailable after retries
            ServiceTimeoutError: If request times out after retries
            ServiceError: For other service errors
        """
        pass
    
    @abstractmethod
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Get the status of the circuit breaker protecting this service.
        
        Returns:
            Dictionary with circuit breaker state and statistics
        """
        pass
    
    @abstractmethod
    def reset_circuit_breaker(self) -> None:
        """
        Manually reset the circuit breaker to CLOSED state.
        
        This should be used for administrative purposes or after
        confirming that the service has recovered.
        """
        pass


class ILLMModelServer(IModelServer):
    """
    Abstract base class for Large Language Model (LLM) server integrations.
    
    This interface extends IModelServer with LLM-specific operations.
    
    Requirements: 8.3
    """
    
    @abstractmethod
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
        """
        pass
    
    @abstractmethod
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
        pass


class IASRModelServer(IModelServer):
    """
    Abstract base class for Automatic Speech Recognition (ASR) server integrations.
    
    This interface extends IModelServer with ASR-specific operations.
    
    Requirements: 8.3
    """
    
    @abstractmethod
    def transcribe_audio(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Audio data in bytes
            language: Optional language code (e.g., "en", "hi")
            **kwargs: Additional model parameters
        
        Returns:
            Dictionary with transcribed text and metadata
        """
        pass


class IOCRModelServer(IModelServer):
    """
    Abstract base class for Optical Character Recognition (OCR) server integrations.
    
    This interface extends IModelServer with OCR-specific operations.
    
    Requirements: 8.3
    """
    
    @abstractmethod
    def extract_text(
        self,
        image_data: bytes,
        language: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract text from image.
        
        Args:
            image_data: Image data in bytes
            language: Optional language code (e.g., "en", "hi")
            **kwargs: Additional model parameters
        
        Returns:
            Dictionary with extracted text and metadata
        """
        pass


class IServiceFactory(ABC):
    """
    Abstract factory for creating external service instances.
    
    This interface allows for dependency injection of service factories,
    making it easier to swap implementations or create mock services
    for testing.
    
    Requirements: 8.3
    """
    
    @abstractmethod
    def create_llm_service(self, config: Dict[str, Any]) -> ILLMModelServer:
        """
        Create an LLM model server instance.
        
        Args:
            config: Configuration dictionary for the service
        
        Returns:
            ILLMModelServer instance
        """
        pass
    
    @abstractmethod
    def create_asr_service(self, config: Dict[str, Any]) -> IASRModelServer:
        """
        Create an ASR model server instance.
        
        Args:
            config: Configuration dictionary for the service
        
        Returns:
            IASRModelServer instance
        """
        pass
    
    @abstractmethod
    def create_ocr_service(self, config: Dict[str, Any]) -> IOCRModelServer:
        """
        Create an OCR model server instance.
        
        Args:
            config: Configuration dictionary for the service
        
        Returns:
            IOCRModelServer instance
        """
        pass


# Custom exceptions for external services
class ServiceError(Exception):
    """Base exception for external service errors."""
    pass


class ServiceUnavailableError(ServiceError):
    """Exception raised when external service is unavailable."""
    pass


class ServiceTimeoutError(ServiceError):
    """Exception raised when external service request times out."""
    pass


class CircuitBreakerOpenError(ServiceError):
    """Exception raised when circuit breaker is open."""
    pass
