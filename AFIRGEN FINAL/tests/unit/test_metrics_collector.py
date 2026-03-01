"""
Unit tests for MetricsCollector.
Tests CloudWatch metrics emission for all AWS services.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, call
from datetime import datetime

from services.monitoring.metrics_collector import MetricsCollector


class TestMetricsCollector:
    """Test suite for MetricsCollector."""
    
    def test_initialization_enabled(self):
        """Test metrics collector initializes when enabled."""
        with patch('boto3.client') as mock_boto:
            collector = MetricsCollector(region='us-east-1', enabled=True)
            
            assert collector.region == 'us-east-1'
            assert collector.enabled is True
            assert collector.cloudwatch is not None
            assert collector.batch_size == 20
            mock_boto.assert_called_once_with('cloudwatch', region_name='us-east-1')
    
    def test_initialization_disabled(self):
        """Test metrics collector initializes when disabled."""
        collector = MetricsCollector(region='us-east-1', enabled=False)
        
        assert collector.enabled is False
        assert collector.cloudwatch is None
    
    @pytest.mark.asyncio
    async def test_record_transcribe_operation_success(self):
        """Test recording successful Transcribe operation."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            await collector.record_transcribe_operation(
                duration_seconds=45.5,
                success=True,
                language_code='hi-IN',
                audio_duration=120.0
            )
            
            # Check metrics were batched
            assert len(collector.batch_metrics) == 3
            
            # Verify metric names
            metric_names = [m['MetricName'] for m in collector.batch_metrics]
            assert 'TranscribeLatency' in metric_names
            assert 'TranscribeSuccess' in metric_names
            assert 'AudioDuration' in metric_names
    
    @pytest.mark.asyncio
    async def test_record_transcribe_operation_failure(self):
        """Test recording failed Transcribe operation."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            await collector.record_transcribe_operation(
                duration_seconds=10.0,
                success=False,
                language_code='en-IN',
                audio_duration=60.0,
                error_type='ThrottlingException'
            )
            
            # Should have error metric
            assert len(collector.batch_metrics) == 4
            
            error_metrics = [m for m in collector.batch_metrics if m['MetricName'] == 'TranscribeErrors']
            assert len(error_metrics) == 1
            assert error_metrics[0]['Value'] == 1.0
    
    @pytest.mark.asyncio
    async def test_record_textract_operation(self):
        """Test recording Textract operation."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            await collector.record_textract_operation(
                duration_seconds=15.5,
                success=True,
                page_count=3
            )
            
            assert len(collector.batch_metrics) == 3
            
            metric_names = [m['MetricName'] for m in collector.batch_metrics]
            assert 'TextractLatency' in metric_names
            assert 'TextractSuccess' in metric_names
            assert 'PageCount' in metric_names
    
    @pytest.mark.asyncio
    async def test_record_bedrock_operation(self):
        """Test recording Bedrock operation with token usage."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            await collector.record_bedrock_operation(
                operation='generate_narrative',
                duration_seconds=8.5,
                success=True,
                model_id='anthropic.claude-3-sonnet',
                input_tokens=150,
                output_tokens=75
            )
            
            assert len(collector.batch_metrics) == 4
            
            metric_names = [m['MetricName'] for m in collector.batch_metrics]
            assert 'BedrockLatency' in metric_names
            assert 'BedrockSuccess' in metric_names
            assert 'InputTokens' in metric_names
            assert 'OutputTokens' in metric_names
            
            # Verify token values
            input_token_metric = [m for m in collector.batch_metrics if m['MetricName'] == 'InputTokens'][0]
            assert input_token_metric['Value'] == 150.0
            
            output_token_metric = [m for m in collector.batch_metrics if m['MetricName'] == 'OutputTokens'][0]
            assert output_token_metric['Value'] == 75.0
    
    @pytest.mark.asyncio
    async def test_record_vector_db_operation_search(self):
        """Test recording vector database search operation."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            await collector.record_vector_db_operation(
                operation='search',
                duration_seconds=1.2,
                success=True,
                result_count=5
            )
            
            assert len(collector.batch_metrics) == 3
            
            metric_names = [m['MetricName'] for m in collector.batch_metrics]
            assert 'VectorDBLatency' in metric_names
            assert 'VectorDBSuccess' in metric_names
            assert 'SearchResultCount' in metric_names
    
    @pytest.mark.asyncio
    async def test_record_fir_generation(self):
        """Test recording FIR generation metrics."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            await collector.record_fir_generation(
                duration_seconds=120.5,
                success=True,
                source_type='audio',
                cache_hit=True
            )
            
            assert len(collector.batch_metrics) == 3
            
            metric_names = [m['MetricName'] for m in collector.batch_metrics]
            assert 'FIRGenerationLatency' in metric_names
            assert 'FIRGenerationSuccess' in metric_names
            assert 'CacheHitRate' in metric_names
    
    @pytest.mark.asyncio
    async def test_metrics_disabled_no_emission(self):
        """Test no metrics emitted when disabled."""
        collector = MetricsCollector(region='us-east-1', enabled=False)
        
        await collector.record_transcribe_operation(
            duration_seconds=10.0,
            success=True,
            language_code='hi-IN',
            audio_duration=60.0
        )
        
        assert len(collector.batch_metrics) == 0
    
    @pytest.mark.asyncio
    async def test_batch_flush_when_full(self):
        """Test metrics are flushed when batch is full."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            collector.batch_size = 5  # Small batch for testing
            
            # Add metrics to fill batch
            await collector.record_transcribe_operation(
                duration_seconds=10.0,
                success=True,
                language_code='hi-IN',
                audio_duration=60.0
            )
            
            # Should have 3 metrics
            assert len(collector.batch_metrics) == 3
            
            # Add more to exceed batch size
            await collector.record_textract_operation(
                duration_seconds=5.0,
                success=True,
                page_count=1
            )
            
            # Should have flushed and reset
            collector.cloudwatch.put_metric_data.assert_called_once()
            assert len(collector.batch_metrics) == 0
    
    @pytest.mark.asyncio
    async def test_flush_metrics_manually(self):
        """Test manual flush of metrics."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            await collector.record_transcribe_operation(
                duration_seconds=10.0,
                success=True,
                language_code='hi-IN',
                audio_duration=60.0
            )
            
            assert len(collector.batch_metrics) == 3
            
            # Manual flush
            await collector.flush()
            
            collector.cloudwatch.put_metric_data.assert_called_once()
            assert len(collector.batch_metrics) == 0
    
    @pytest.mark.asyncio
    async def test_metrics_include_timestamp(self):
        """Test all metrics include timestamp."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            await collector.record_transcribe_operation(
                duration_seconds=10.0,
                success=True,
                language_code='hi-IN',
                audio_duration=60.0
            )
            
            # All metrics should have timestamp
            for metric in collector.batch_metrics:
                assert 'Timestamp' in metric
                assert isinstance(metric['Timestamp'], datetime)
    
    @pytest.mark.asyncio
    async def test_metrics_include_dimensions(self):
        """Test metrics include correct dimensions."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            await collector.record_bedrock_operation(
                operation='generate_fir',
                duration_seconds=10.0,
                success=True,
                model_id='anthropic.claude-3-sonnet',
                input_tokens=100,
                output_tokens=50
            )
            
            # Check dimensions
            latency_metric = [m for m in collector.batch_metrics if m['MetricName'] == 'BedrockLatency'][0]
            dimensions = {d['Name']: d['Value'] for d in latency_metric['Dimensions']}
            
            assert dimensions['Service'] == 'Bedrock'
            assert dimensions['Operation'] == 'generate_fir'
            assert dimensions['ModelId'] == 'anthropic.claude-3-sonnet'
    
    @pytest.mark.asyncio
    async def test_flush_handles_client_error(self):
        """Test flush handles CloudWatch client errors gracefully."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            # Mock the put_metric_data to raise an exception
            from botocore.exceptions import ClientError
            collector.cloudwatch.put_metric_data.side_effect = ClientError(
                {'Error': {'Code': 'InternalError', 'Message': 'CloudWatch error'}},
                'PutMetricData'
            )
            
            await collector.record_transcribe_operation(
                duration_seconds=10.0,
                success=True,
                language_code='hi-IN',
                audio_duration=60.0
            )
            
            # Should not raise exception - error is logged
            try:
                await collector.flush()
            except Exception as e:
                pytest.fail(f"flush() should not raise exception, but raised: {e}")
    
    @pytest.mark.asyncio
    async def test_success_metric_values(self):
        """Test success metric has correct values."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            # Success case
            await collector.record_transcribe_operation(
                duration_seconds=10.0,
                success=True,
                language_code='hi-IN',
                audio_duration=60.0
            )
            
            success_metric = [m for m in collector.batch_metrics if m['MetricName'] == 'TranscribeSuccess'][0]
            assert success_metric['Value'] == 1.0
            
            collector.batch_metrics = []
            
            # Failure case
            await collector.record_transcribe_operation(
                duration_seconds=10.0,
                success=False,
                language_code='hi-IN',
                audio_duration=60.0
            )
            
            success_metric = [m for m in collector.batch_metrics if m['MetricName'] == 'TranscribeSuccess'][0]
            assert success_metric['Value'] == 0.0
    
    @pytest.mark.asyncio
    async def test_namespace_constant(self):
        """Test metrics use correct namespace."""
        assert MetricsCollector.NAMESPACE == "AFIRGen/Bedrock"
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_metric(self):
        """Test cache hit rate metric values."""
        with patch('boto3.client'):
            collector = MetricsCollector(region='us-east-1', enabled=True)
            collector.cloudwatch = Mock()
            
            # Cache hit
            await collector.record_fir_generation(
                duration_seconds=10.0,
                success=True,
                source_type='text',
                cache_hit=True
            )
            
            cache_metric = [m for m in collector.batch_metrics if m['MetricName'] == 'CacheHitRate'][0]
            assert cache_metric['Value'] == 1.0
            
            collector.batch_metrics = []
            
            # Cache miss
            await collector.record_fir_generation(
                duration_seconds=10.0,
                success=True,
                source_type='text',
                cache_hit=False
            )
            
            cache_metric = [m for m in collector.batch_metrics if m['MetricName'] == 'CacheHitRate'][0]
            assert cache_metric['Value'] == 0.0
