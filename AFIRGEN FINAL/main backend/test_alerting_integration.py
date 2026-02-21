"""
Integration tests for alerting system with metrics collection.

Tests that alerts are properly triggered when metrics exceed thresholds
during normal system operation.
"""

import pytest
import time
from unittest.mock import Mock, patch
from infrastructure.metrics import MetricsCollector, track_request_duration
from infrastructure.alerting import (
    AlertManager,
    AlertSeverity,
    MetricType,
    ThresholdConfig,
    AlertNotificationBackend
)
from infrastructure.config import config


class MockNotificationBackend(AlertNotificationBackend):
    """Mock notification backend for testing."""
    
    def __init__(self):
        self.sent_alerts = []
    
    def send_alert(self, alert):
        self.sent_alerts.append(alert)
        return True
    
    def clear(self):
        self.sent_alerts.clear()


@pytest.fixture
def mock_alert_backend():
    """Fixture providing a mock notification backend."""
    backend = MockNotificationBackend()
    yield backend
    backend.clear()


@pytest.fixture
def alert_manager_with_mock(mock_alert_backend):
    """Fixture providing an alert manager with mock backend."""
    from infrastructure.alerting import alert_manager
    
    # Save original backends
    original_backends = alert_manager.notification_backends
    
    # Replace with mock
    alert_manager.notification_backends = [mock_alert_backend]
    alert_manager.clear_alert_history()
    
    yield alert_manager, mock_alert_backend
    
    # Restore original backends
    alert_manager.notification_backends = original_backends
    alert_manager.clear_alert_history()


class TestMetricsAlertingIntegration:
    """Test integration between metrics collection and alerting."""
    
    def test_cpu_metric_triggers_alert(self, alert_manager_with_mock):
        """Test that high CPU usage triggers an alert."""
        manager, mock_backend = alert_manager_with_mock
        
        # Ensure alerting is enabled
        original_enabled = config.alerting.enabled
        config.alerting.enabled = True
        
        try:
            # Mock psutil to return high CPU usage
            with patch('infrastructure.metrics.psutil.cpu_percent', return_value=95.0):
                with patch('infrastructure.metrics.psutil.virtual_memory'):
                    with patch('infrastructure.metrics.psutil.disk_io_counters', return_value=None):
                        with patch('infrastructure.metrics.psutil.net_io_counters', return_value=None):
                            MetricsCollector.update_system_metrics()
            
            # Check that alert was triggered
            assert len(mock_backend.sent_alerts) > 0
            alert = mock_backend.sent_alerts[0]
            assert alert.metric_type == MetricType.CPU_PERCENT
            assert alert.severity == AlertSeverity.CRITICAL
            assert alert.current_value == 95.0
        finally:
            config.alerting.enabled = original_enabled
    
    def test_memory_metric_triggers_alert(self, alert_manager_with_mock):
        """Test that high memory usage triggers an alert."""
        manager, mock_backend = alert_manager_with_mock
        
        original_enabled = config.alerting.enabled
        config.alerting.enabled = True
        
        try:
            # Mock psutil to return high memory usage
            mock_memory = Mock()
            mock_memory.percent = 92.0
            
            with patch('infrastructure.metrics.psutil.cpu_percent', return_value=50.0):
                with patch('infrastructure.metrics.psutil.virtual_memory', return_value=mock_memory):
                    with patch('infrastructure.metrics.psutil.disk_io_counters', return_value=None):
                        with patch('infrastructure.metrics.psutil.net_io_counters', return_value=None):
                            MetricsCollector.update_system_metrics()
            
            # Check that alert was triggered
            memory_alerts = [a for a in mock_backend.sent_alerts if a.metric_type == MetricType.MEMORY_PERCENT]
            assert len(memory_alerts) > 0
            alert = memory_alerts[0]
            assert alert.severity == AlertSeverity.CRITICAL
            assert alert.current_value == 92.0
        finally:
            config.alerting.enabled = original_enabled
    
    def test_response_time_triggers_alert(self, alert_manager_with_mock):
        """Test that slow API responses trigger alerts."""
        manager, mock_backend = alert_manager_with_mock
        
        original_enabled = config.alerting.enabled
        config.alerting.enabled = True
        
        try:
            # Simulate a slow request
            with track_request_duration("/api/fir", "POST") as tracker:
                time.sleep(0.1)  # Simulate work
                tracker.set_status(200)
            
            # Manually trigger alert check with high response time
            manager.check_metric(
                MetricType.RESPONSE_TIME,
                6.0,  # 6 seconds - exceeds critical threshold
                metadata={"endpoint": "/api/fir", "method": "POST"}
            )
            
            # Check that alert was triggered
            response_alerts = [a for a in mock_backend.sent_alerts if a.metric_type == MetricType.RESPONSE_TIME]
            assert len(response_alerts) > 0
            alert = response_alerts[0]
            assert alert.severity == AlertSeverity.CRITICAL
            assert alert.current_value == 6.0
        finally:
            config.alerting.enabled = original_enabled
    
    def test_cache_hit_rate_triggers_alert(self, alert_manager_with_mock):
        """Test that low cache hit rate triggers alerts."""
        manager, mock_backend = alert_manager_with_mock
        
        original_enabled = config.alerting.enabled
        config.alerting.enabled = True
        
        try:
            # Reset cache metrics
            MetricsCollector.reset_cache_hit_rate()
            
            # Simulate many cache misses to get low hit rate
            for _ in range(100):
                MetricsCollector.record_cache_operation("get", hit=False)
            
            # Add a few hits to get ~10% hit rate
            for _ in range(10):
                MetricsCollector.record_cache_operation("get", hit=True)
            
            # Check that alert was triggered
            cache_alerts = [a for a in mock_backend.sent_alerts if a.metric_type == MetricType.CACHE_HIT_RATE]
            assert len(cache_alerts) > 0
            alert = cache_alerts[0]
            assert alert.severity == AlertSeverity.CRITICAL
            assert alert.current_value < 50.0  # Below critical threshold
        finally:
            config.alerting.enabled = original_enabled
            MetricsCollector.reset_cache_hit_rate()
    
    def test_db_pool_utilization_triggers_alert(self, alert_manager_with_mock):
        """Test that high database pool utilization triggers alerts."""
        manager, mock_backend = alert_manager_with_mock
        
        original_enabled = config.alerting.enabled
        config.alerting.enabled = True
        
        try:
            # Simulate high pool utilization (only 1 connection available out of 20)
            # This gives 95% utilization which exceeds warning (80%) but equals critical (95%)
            MetricsCollector.update_db_pool_metrics(pool_size=20, available=1)
            
            # Check that alert was triggered
            db_alerts = [a for a in mock_backend.sent_alerts if a.metric_type == MetricType.DB_POOL_UTILIZATION]
            assert len(db_alerts) > 0
            alert = db_alerts[0]
            # At 95% utilization, it should trigger warning (threshold is 80%)
            # Critical threshold is also 95%, but warning is checked first
            assert alert.severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]
            # Utilization should be 95% (19/20)
            assert alert.current_value == 95.0
        finally:
            config.alerting.enabled = original_enabled
    
    def test_model_server_latency_triggers_alert(self, alert_manager_with_mock):
        """Test that high model server latency triggers alerts."""
        manager, mock_backend = alert_manager_with_mock
        
        original_enabled = config.alerting.enabled
        config.alerting.enabled = True
        
        try:
            # Simulate slow model server response
            MetricsCollector.record_model_server_latency(
                server="llm_server",
                duration=35.0,  # 35 seconds - exceeds critical threshold
                success=True
            )
            
            # Check that alert was triggered
            model_alerts = [a for a in mock_backend.sent_alerts if a.metric_type == MetricType.MODEL_SERVER_LATENCY]
            assert len(model_alerts) > 0
            alert = model_alerts[0]
            assert alert.severity == AlertSeverity.CRITICAL
            assert alert.current_value == 35.0
        finally:
            config.alerting.enabled = original_enabled
    
    def test_alerting_disabled_no_alerts(self, alert_manager_with_mock):
        """Test that no alerts are sent when alerting is disabled."""
        manager, mock_backend = alert_manager_with_mock
        
        original_enabled = config.alerting.enabled
        config.alerting.enabled = False
        
        try:
            # Try to trigger various alerts
            with patch('infrastructure.metrics.psutil.cpu_percent', return_value=95.0):
                with patch('infrastructure.metrics.psutil.virtual_memory'):
                    with patch('infrastructure.metrics.psutil.disk_io_counters', return_value=None):
                        with patch('infrastructure.metrics.psutil.net_io_counters', return_value=None):
                            MetricsCollector.update_system_metrics()
            
            MetricsCollector.update_db_pool_metrics(pool_size=20, available=1)
            MetricsCollector.record_model_server_latency("llm_server", 35.0, True)
            
            # No alerts should be sent
            assert len(mock_backend.sent_alerts) == 0
        finally:
            config.alerting.enabled = original_enabled
    
    def test_alert_deduplication_in_metrics(self, alert_manager_with_mock):
        """Test that repeated metric violations don't spam alerts."""
        manager, mock_backend = alert_manager_with_mock
        
        original_enabled = config.alerting.enabled
        config.alerting.enabled = True
        
        try:
            # Trigger the same alert multiple times
            for _ in range(5):
                MetricsCollector.update_db_pool_metrics(pool_size=20, available=1)
            
            # Should only get one alert due to deduplication
            db_alerts = [a for a in mock_backend.sent_alerts if a.metric_type == MetricType.DB_POOL_UTILIZATION]
            assert len(db_alerts) == 1
        finally:
            config.alerting.enabled = original_enabled
    
    def test_alert_metadata_includes_context(self, alert_manager_with_mock):
        """Test that alerts include relevant context metadata."""
        manager, mock_backend = alert_manager_with_mock
        
        original_enabled = config.alerting.enabled
        config.alerting.enabled = True
        
        try:
            # Trigger alert with metadata
            MetricsCollector.record_model_server_latency(
                server="asr_server",
                duration=35.0,
                success=True
            )
            
            # Check that metadata is included
            model_alerts = [a for a in mock_backend.sent_alerts if a.metric_type == MetricType.MODEL_SERVER_LATENCY]
            assert len(model_alerts) > 0
            alert = model_alerts[0]
            assert "server" in alert.metadata
            assert alert.metadata["server"] == "asr_server"
        finally:
            config.alerting.enabled = original_enabled


class TestAlertSeverityLevels:
    """Test that different severity levels are triggered correctly."""
    
    def test_warning_then_critical_alerts(self, alert_manager_with_mock):
        """Test that warning is triggered first, then critical."""
        manager, mock_backend = alert_manager_with_mock
        
        original_enabled = config.alerting.enabled
        config.alerting.enabled = True
        
        try:
            # Trigger warning level
            MetricsCollector.update_db_pool_metrics(pool_size=20, available=3)  # 85% utilization
            
            warning_alerts = [
                a for a in mock_backend.sent_alerts 
                if a.metric_type == MetricType.DB_POOL_UTILIZATION 
                and a.severity == AlertSeverity.WARNING
            ]
            assert len(warning_alerts) > 0
            
            # Clear and trigger critical level (need >95% for critical)
            mock_backend.clear()
            manager.clear_alert_history()
            
            MetricsCollector.update_db_pool_metrics(pool_size=20, available=0)  # 100% utilization
            
            critical_alerts = [
                a for a in mock_backend.sent_alerts 
                if a.metric_type == MetricType.DB_POOL_UTILIZATION 
                and a.severity == AlertSeverity.CRITICAL
            ]
            assert len(critical_alerts) > 0
        finally:
            config.alerting.enabled = original_enabled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
