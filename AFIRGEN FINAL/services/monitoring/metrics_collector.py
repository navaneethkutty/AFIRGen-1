"""
CloudWatch metrics collector for AWS service operations.
Tracks latency, success rate, token usage, and costs.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and emits CloudWatch metrics for all AWS service operations.
    Tracks performance, usage, and costs.
    """
    
    NAMESPACE = "AFIRGen/Bedrock"
    
    def __init__(self, region: str, enabled: bool = True):
        """
        Initialize metrics collector.
        
        Args:
            region: AWS region
            enabled: Whether metrics collection is enabled
        """
        self.region = region
        self.enabled = enabled
        self.cloudwatch = boto3.client('cloudwatch', region_name=region) if enabled else None
        self.batch_metrics: List[Dict[str, Any]] = []
        self.batch_size = 20  # CloudWatch limit
    
    async def record_transcribe_operation(
        self,
        duration_seconds: float,
        success: bool,
        language_code: str,
        audio_duration: float,
        error_type: Optional[str] = None
    ) -> None:
        """
        Record Transcribe operation metrics.
        
        Args:
            duration_seconds: Operation duration
            success: Whether operation succeeded
            language_code: Language code used
            audio_duration: Duration of audio file
            error_type: Error type if failed
        """
        if not self.enabled:
            return
        
        metrics = [
            {
                'MetricName': 'TranscribeLatency',
                'Value': duration_seconds,
                'Unit': 'Seconds',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'Transcribe'},
                    {'Name': 'Language', 'Value': language_code}
                ]
            },
            {
                'MetricName': 'TranscribeSuccess',
                'Value': 1.0 if success else 0.0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'Transcribe'},
                    {'Name': 'Language', 'Value': language_code}
                ]
            },
            {
                'MetricName': 'AudioDuration',
                'Value': audio_duration,
                'Unit': 'Seconds',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'Transcribe'}
                ]
            }
        ]
        
        if not success and error_type:
            metrics.append({
                'MetricName': 'TranscribeErrors',
                'Value': 1.0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'Transcribe'},
                    {'Name': 'ErrorType', 'Value': error_type}
                ]
            })
        
        await self._emit_metrics(metrics)
    
    async def record_textract_operation(
        self,
        duration_seconds: float,
        success: bool,
        page_count: int,
        error_type: Optional[str] = None
    ) -> None:
        """Record Textract operation metrics."""
        if not self.enabled:
            return
        
        metrics = [
            {
                'MetricName': 'TextractLatency',
                'Value': duration_seconds,
                'Unit': 'Seconds',
                'Dimensions': [{'Name': 'Service', 'Value': 'Textract'}]
            },
            {
                'MetricName': 'TextractSuccess',
                'Value': 1.0 if success else 0.0,
                'Unit': 'Count',
                'Dimensions': [{'Name': 'Service', 'Value': 'Textract'}]
            },
            {
                'MetricName': 'PageCount',
                'Value': float(page_count),
                'Unit': 'Count',
                'Dimensions': [{'Name': 'Service', 'Value': 'Textract'}]
            }
        ]
        
        if not success and error_type:
            metrics.append({
                'MetricName': 'TextractErrors',
                'Value': 1.0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'Textract'},
                    {'Name': 'ErrorType', 'Value': error_type}
                ]
            })
        
        await self._emit_metrics(metrics)
    
    async def record_bedrock_operation(
        self,
        operation: str,
        duration_seconds: float,
        success: bool,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        error_type: Optional[str] = None
    ) -> None:
        """Record Bedrock operation metrics with token usage."""
        if not self.enabled:
            return
        
        metrics = [
            {
                'MetricName': 'BedrockLatency',
                'Value': duration_seconds,
                'Unit': 'Seconds',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'Bedrock'},
                    {'Name': 'Operation', 'Value': operation},
                    {'Name': 'ModelId', 'Value': model_id}
                ]
            },
            {
                'MetricName': 'BedrockSuccess',
                'Value': 1.0 if success else 0.0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'Bedrock'},
                    {'Name': 'Operation', 'Value': operation}
                ]
            },
            {
                'MetricName': 'InputTokens',
                'Value': float(input_tokens),
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'Bedrock'},
                    {'Name': 'ModelId', 'Value': model_id}
                ]
            },
            {
                'MetricName': 'OutputTokens',
                'Value': float(output_tokens),
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'Bedrock'},
                    {'Name': 'ModelId', 'Value': model_id}
                ]
            }
        ]
        
        if not success and error_type:
            metrics.append({
                'MetricName': 'BedrockErrors',
                'Value': 1.0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'Bedrock'},
                    {'Name': 'ErrorType', 'Value': error_type}
                ]
            })
        
        await self._emit_metrics(metrics)
    
    async def record_vector_db_operation(
        self,
        operation: str,
        duration_seconds: float,
        success: bool,
        result_count: int = 0,
        error_type: Optional[str] = None
    ) -> None:
        """Record vector database operation metrics."""
        if not self.enabled:
            return
        
        metrics = [
            {
                'MetricName': 'VectorDBLatency',
                'Value': duration_seconds,
                'Unit': 'Seconds',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'VectorDB'},
                    {'Name': 'Operation', 'Value': operation}
                ]
            },
            {
                'MetricName': 'VectorDBSuccess',
                'Value': 1.0 if success else 0.0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'VectorDB'},
                    {'Name': 'Operation', 'Value': operation}
                ]
            }
        ]
        
        if operation == 'search' and success:
            metrics.append({
                'MetricName': 'SearchResultCount',
                'Value': float(result_count),
                'Unit': 'Count',
                'Dimensions': [{'Name': 'Service', 'Value': 'VectorDB'}]
            })
        
        if not success and error_type:
            metrics.append({
                'MetricName': 'VectorDBErrors',
                'Value': 1.0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'VectorDB'},
                    {'Name': 'ErrorType', 'Value': error_type}
                ]
            })
        
        await self._emit_metrics(metrics)
    
    async def record_fir_generation(
        self,
        duration_seconds: float,
        success: bool,
        source_type: str,  # 'text', 'audio', 'image'
        cache_hit: bool,
        error_type: Optional[str] = None
    ) -> None:
        """Record end-to-end FIR generation metrics."""
        if not self.enabled:
            return
        
        metrics = [
            {
                'MetricName': 'FIRGenerationLatency',
                'Value': duration_seconds,
                'Unit': 'Seconds',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'FIRGeneration'},
                    {'Name': 'SourceType', 'Value': source_type}
                ]
            },
            {
                'MetricName': 'FIRGenerationSuccess',
                'Value': 1.0 if success else 0.0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'FIRGeneration'},
                    {'Name': 'SourceType', 'Value': source_type}
                ]
            },
            {
                'MetricName': 'CacheHitRate',
                'Value': 1.0 if cache_hit else 0.0,
                'Unit': 'Count',
                'Dimensions': [{'Name': 'Service', 'Value': 'FIRGeneration'}]
            }
        ]
        
        if not success and error_type:
            metrics.append({
                'MetricName': 'FIRGenerationErrors',
                'Value': 1.0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'FIRGeneration'},
                    {'Name': 'ErrorType', 'Value': error_type}
                ]
            })
        
        await self._emit_metrics(metrics)
    
    async def _emit_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """
        Emit metrics to CloudWatch in batches.
        
        Args:
            metrics: List of metric data
        """
        if not self.enabled or not self.cloudwatch:
            return
        
        # Add timestamp to all metrics
        timestamp = datetime.utcnow()
        for metric in metrics:
            metric['Timestamp'] = timestamp
        
        # Add to batch
        self.batch_metrics.extend(metrics)
        
        # Emit if batch is full
        if len(self.batch_metrics) >= self.batch_size:
            await self._flush_metrics()
    
    async def _flush_metrics(self) -> None:
        """Flush batched metrics to CloudWatch."""
        if not self.batch_metrics:
            return
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.NAMESPACE,
                MetricData=self.batch_metrics
            )
            logger.debug(f"Emitted {len(self.batch_metrics)} metrics to CloudWatch")
            self.batch_metrics = []
            
        except ClientError as e:
            logger.error(f"Failed to emit metrics: {e}")
    
    async def flush(self) -> None:
        """Manually flush any remaining metrics."""
        await self._flush_metrics()
