"""
Unit tests for the alerting system.

Tests threshold configuration, alert emission, deduplication,
and notification backends.
"""

import pytest
from datetime import datetime, timedelta
from infrastructure.alerting import (
    AlertManager,
    AlertSeverity,
    MetricType,
    ThresholdConfig,
    Alert,
    AlertNotificationBackend,
    LogNotificationBackend,
    create_default_alert_manager
)


class TestThresholdConfig:
    """Test threshold configuration."""
    
    def test_threshold_config_with_warning_only(self):
        """Test creating threshold with only warning level."""
        config = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0
        )
        assert config.warning_threshold == 70.0
        assert config.critical_threshold is None
    
    def test_threshold_config_with_critical_only(self):
        """Test creating threshold with only critical level."""
        config = ThresholdConfig(
            metric_type=MetricType.MEMORY_PERCENT,
            critical_threshold=90.0
        )
        assert config.warning_threshold is None
        assert config.critical_threshold == 90.0
    
    def test_threshold_config_with_both_levels(self):
        """Test creating threshold with both warning and critical levels."""
        config = ThresholdConfig(
            metric_type=MetricType.RESPONSE_TIME,
            warning_threshold=2.0,
            critical_threshold=5.0
        )
        assert config.warning_threshold == 2.0
        assert config.critical_threshold == 5.0
    
    def test_threshold_config_requires_at_least_one_threshold(self):
        """Test that at least one threshold must be set."""
        with pytest.raises(ValueError, match="At least one threshold"):
            ThresholdConfig(metric_type=MetricType.CPU_PERCENT)
    
    def test_threshold_config_invalid_comparison(self):
        """Test that invalid comparison raises error."""
        with pytest.raises(ValueError, match="Invalid comparison"):
            ThresholdConfig(
                metric_type=MetricType.CPU_PERCENT,
                warning_threshold=70.0,
                comparison="invalid"
            )
    
    def test_threshold_config_valid_comparisons(self):
        """Test all valid comparison types."""
        for comparison in ["greater_than", "less_than", "equals"]:
            config = ThresholdConfig(
                metric_type=MetricType.CPU_PERCENT,
                warning_threshold=70.0,
                comparison=comparison
            )
            assert config.comparison == comparison


class TestAlert:
    """Test Alert data class."""
    
    def test_alert_creation(self):
        """Test creating an alert."""
        alert = Alert(
            metric_type=MetricType.CPU_PERCENT,
            severity=AlertSeverity.WARNING,
            current_value=75.0,
            threshold_value=70.0,
            message="CPU usage exceeded threshold"
        )
        assert alert.metric_type == MetricType.CPU_PERCENT
        assert alert.severity == AlertSeverity.WARNING
        assert alert.current_value == 75.0
        assert alert.threshold_value == 70.0
        assert alert.message == "CPU usage exceeded threshold"
        assert isinstance(alert.timestamp, datetime)
    
    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        alert = Alert(
            metric_type=MetricType.MEMORY_PERCENT,
            severity=AlertSeverity.CRITICAL,
            current_value=95.0,
            threshold_value=90.0,
            message="Memory critical",
            metadata={"host": "server1"}
        )
        alert_dict = alert.to_dict()
        
        assert alert_dict["metric_type"] == "memory_percent"
        assert alert_dict["severity"] == "critical"
        assert alert_dict["current_value"] == 95.0
        assert alert_dict["threshold_value"] == 90.0
        assert alert_dict["message"] == "Memory critical"
        assert alert_dict["metadata"] == {"host": "server1"}
        assert "timestamp" in alert_dict


class MockNotificationBackend(AlertNotificationBackend):
    """Mock notification backend for testing."""
    
    def __init__(self):
        self.sent_alerts = []
        self.should_fail = False
    
    def send_alert(self, alert: Alert) -> bool:
        if self.should_fail:
            raise Exception("Notification failed")
        self.sent_alerts.append(alert)
        return True


class TestAlertManager:
    """Test AlertManager functionality."""
    
    def test_alert_manager_initialization(self):
        """Test creating an alert manager."""
        manager = AlertManager()
        assert len(manager.thresholds) == 0
        assert len(manager.notification_backends) == 1
        assert isinstance(manager.notification_backends[0], LogNotificationBackend)
    
    def test_alert_manager_with_thresholds(self):
        """Test creating alert manager with thresholds."""
        thresholds = [
            ThresholdConfig(
                metric_type=MetricType.CPU_PERCENT,
                warning_threshold=70.0,
                critical_threshold=90.0
            )
        ]
        manager = AlertManager(thresholds=thresholds)
        assert len(manager.thresholds) == 1
        assert MetricType.CPU_PERCENT in manager.thresholds
    
    def test_add_threshold(self):
        """Test adding a threshold to alert manager."""
        manager = AlertManager()
        threshold = ThresholdConfig(
            metric_type=MetricType.MEMORY_PERCENT,
            warning_threshold=75.0
        )
        manager.add_threshold(threshold)
        assert MetricType.MEMORY_PERCENT in manager.thresholds
    
    def test_remove_threshold(self):
        """Test removing a threshold from alert manager."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0
        )
        manager = AlertManager(thresholds=[threshold])
        manager.remove_threshold(MetricType.CPU_PERCENT)
        assert MetricType.CPU_PERCENT not in manager.thresholds
    
    def test_check_metric_no_threshold(self):
        """Test checking metric with no configured threshold."""
        manager = AlertManager()
        alert = manager.check_metric(MetricType.CPU_PERCENT, 80.0)
        assert alert is None
    
    def test_check_metric_below_threshold(self):
        """Test checking metric below threshold."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0
        )
        manager = AlertManager(thresholds=[threshold])
        alert = manager.check_metric(MetricType.CPU_PERCENT, 60.0)
        assert alert is None
    
    def test_check_metric_warning_threshold_exceeded(self):
        """Test checking metric that exceeds warning threshold."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0,
            critical_threshold=90.0
        )
        mock_backend = MockNotificationBackend()
        manager = AlertManager(
            thresholds=[threshold],
            notification_backends=[mock_backend]
        )
        
        alert = manager.check_metric(MetricType.CPU_PERCENT, 75.0)
        
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.current_value == 75.0
        assert alert.threshold_value == 70.0
        assert len(mock_backend.sent_alerts) == 1
    
    def test_check_metric_critical_threshold_exceeded(self):
        """Test checking metric that exceeds critical threshold."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0,
            critical_threshold=90.0
        )
        mock_backend = MockNotificationBackend()
        manager = AlertManager(
            thresholds=[threshold],
            notification_backends=[mock_backend]
        )
        
        alert = manager.check_metric(MetricType.CPU_PERCENT, 95.0)
        
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.current_value == 95.0
        assert alert.threshold_value == 90.0
        assert len(mock_backend.sent_alerts) == 1
    
    def test_check_metric_less_than_comparison(self):
        """Test checking metric with less_than comparison."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CACHE_HIT_RATE,
            warning_threshold=70.0,
            critical_threshold=50.0,
            comparison="less_than"
        )
        mock_backend = MockNotificationBackend()
        manager = AlertManager(
            thresholds=[threshold],
            notification_backends=[mock_backend]
        )
        
        # Should trigger warning (below 70%)
        alert = manager.check_metric(MetricType.CACHE_HIT_RATE, 65.0)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        
        # Should trigger critical (below 50%)
        manager.clear_alert_history()
        alert = manager.check_metric(MetricType.CACHE_HIT_RATE, 45.0)
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL
    
    def test_alert_deduplication(self):
        """Test that duplicate alerts are suppressed."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0
        )
        mock_backend = MockNotificationBackend()
        manager = AlertManager(
            thresholds=[threshold],
            notification_backends=[mock_backend],
            deduplication_window=60  # 1 minute
        )
        
        # First alert should be sent
        alert1 = manager.check_metric(MetricType.CPU_PERCENT, 75.0)
        assert alert1 is not None
        assert len(mock_backend.sent_alerts) == 1
        
        # Second alert within deduplication window should be suppressed
        alert2 = manager.check_metric(MetricType.CPU_PERCENT, 76.0)
        assert alert2 is None
        assert len(mock_backend.sent_alerts) == 1
    
    def test_alert_deduplication_different_severity(self):
        """Test that alerts with different severity are not deduplicated."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0,
            critical_threshold=90.0
        )
        mock_backend = MockNotificationBackend()
        manager = AlertManager(
            thresholds=[threshold],
            notification_backends=[mock_backend],
            deduplication_window=60
        )
        
        # Warning alert
        alert1 = manager.check_metric(MetricType.CPU_PERCENT, 75.0)
        assert alert1 is not None
        assert alert1.severity == AlertSeverity.WARNING
        
        # Critical alert should not be deduplicated (different severity)
        alert2 = manager.check_metric(MetricType.CPU_PERCENT, 95.0)
        assert alert2 is not None
        assert alert2.severity == AlertSeverity.CRITICAL
        assert len(mock_backend.sent_alerts) == 2
    
    def test_alert_with_metadata(self):
        """Test that alert includes metadata."""
        threshold = ThresholdConfig(
            metric_type=MetricType.RESPONSE_TIME,
            warning_threshold=2.0
        )
        mock_backend = MockNotificationBackend()
        manager = AlertManager(
            thresholds=[threshold],
            notification_backends=[mock_backend]
        )
        
        metadata = {"endpoint": "/api/fir", "method": "POST"}
        alert = manager.check_metric(MetricType.RESPONSE_TIME, 3.5, metadata=metadata)
        
        assert alert is not None
        assert alert.metadata == metadata
        assert mock_backend.sent_alerts[0].metadata == metadata
    
    def test_multiple_notification_backends(self):
        """Test sending alerts to multiple backends."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0
        )
        backend1 = MockNotificationBackend()
        backend2 = MockNotificationBackend()
        manager = AlertManager(
            thresholds=[threshold],
            notification_backends=[backend1, backend2]
        )
        
        alert = manager.check_metric(MetricType.CPU_PERCENT, 75.0)
        
        assert alert is not None
        assert len(backend1.sent_alerts) == 1
        assert len(backend2.sent_alerts) == 1
    
    def test_notification_backend_failure_handling(self):
        """Test that backend failures don't prevent other backends from receiving alerts."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0
        )
        failing_backend = MockNotificationBackend()
        failing_backend.should_fail = True
        working_backend = MockNotificationBackend()
        
        manager = AlertManager(
            thresholds=[threshold],
            notification_backends=[failing_backend, working_backend]
        )
        
        alert = manager.check_metric(MetricType.CPU_PERCENT, 75.0)
        
        assert alert is not None
        # Working backend should still receive the alert
        assert len(working_backend.sent_alerts) == 1
    
    def test_get_alert_history(self):
        """Test retrieving alert history."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0,
            critical_threshold=90.0
        )
        manager = AlertManager(thresholds=[threshold])
        
        # Generate some alerts
        manager.check_metric(MetricType.CPU_PERCENT, 75.0)
        manager.clear_alert_history()  # Clear to reset deduplication
        manager.check_metric(MetricType.CPU_PERCENT, 95.0)
        
        history = manager.get_alert_history()
        assert len(history) == 1  # Only the second one (first was cleared)
    
    def test_get_alert_history_filtered_by_metric_type(self):
        """Test filtering alert history by metric type."""
        thresholds = [
            ThresholdConfig(metric_type=MetricType.CPU_PERCENT, warning_threshold=70.0),
            ThresholdConfig(metric_type=MetricType.MEMORY_PERCENT, warning_threshold=75.0)
        ]
        manager = AlertManager(thresholds=thresholds)
        
        manager.check_metric(MetricType.CPU_PERCENT, 80.0)
        manager.clear_alert_history()
        manager.check_metric(MetricType.MEMORY_PERCENT, 85.0)
        
        cpu_alerts = manager.get_alert_history(metric_type=MetricType.CPU_PERCENT)
        memory_alerts = manager.get_alert_history(metric_type=MetricType.MEMORY_PERCENT)
        
        assert len(cpu_alerts) == 0
        assert len(memory_alerts) == 1
    
    def test_get_alert_history_filtered_by_severity(self):
        """Test filtering alert history by severity."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0,
            critical_threshold=90.0
        )
        manager = AlertManager(thresholds=[threshold])
        
        manager.check_metric(MetricType.CPU_PERCENT, 75.0)
        manager.clear_alert_history()
        manager.check_metric(MetricType.CPU_PERCENT, 95.0)
        
        critical_alerts = manager.get_alert_history(severity=AlertSeverity.CRITICAL)
        warning_alerts = manager.get_alert_history(severity=AlertSeverity.WARNING)
        
        assert len(critical_alerts) == 1
        assert len(warning_alerts) == 0
    
    def test_clear_alert_history(self):
        """Test clearing alert history."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0
        )
        manager = AlertManager(thresholds=[threshold])
        
        manager.check_metric(MetricType.CPU_PERCENT, 75.0)
        assert len(manager.get_alert_history()) == 1
        
        manager.clear_alert_history()
        assert len(manager.get_alert_history()) == 0


class TestDefaultAlertManager:
    """Test default alert manager creation."""
    
    def test_create_default_alert_manager(self):
        """Test creating default alert manager with common thresholds."""
        manager = create_default_alert_manager()
        
        # Check that default thresholds are configured
        assert MetricType.CPU_PERCENT in manager.thresholds
        assert MetricType.MEMORY_PERCENT in manager.thresholds
        assert MetricType.RESPONSE_TIME in manager.thresholds
        assert MetricType.ERROR_RATE in manager.thresholds
        assert MetricType.CACHE_HIT_RATE in manager.thresholds
        assert MetricType.DB_POOL_UTILIZATION in manager.thresholds
        assert MetricType.MODEL_SERVER_LATENCY in manager.thresholds
    
    def test_default_thresholds_have_warning_and_critical(self):
        """Test that default thresholds have both warning and critical levels."""
        manager = create_default_alert_manager()
        
        cpu_threshold = manager.thresholds[MetricType.CPU_PERCENT]
        assert cpu_threshold.warning_threshold == 70.0
        assert cpu_threshold.critical_threshold == 90.0
        
        memory_threshold = manager.thresholds[MetricType.MEMORY_PERCENT]
        assert memory_threshold.warning_threshold == 75.0
        assert memory_threshold.critical_threshold == 90.0


class TestLogNotificationBackend:
    """Test log notification backend."""
    
    def test_log_backend_sends_alert(self):
        """Test that log backend successfully logs alerts."""
        backend = LogNotificationBackend()
        alert = Alert(
            metric_type=MetricType.CPU_PERCENT,
            severity=AlertSeverity.WARNING,
            current_value=75.0,
            threshold_value=70.0,
            message="CPU warning"
        )
        
        result = backend.send_alert(alert)
        assert result is True


class TestAlertMessageGeneration:
    """Test alert message generation."""
    
    def test_alert_message_greater_than(self):
        """Test alert message for greater_than comparison."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0,
            comparison="greater_than"
        )
        manager = AlertManager(thresholds=[threshold])
        
        alert = manager.check_metric(MetricType.CPU_PERCENT, 75.0)
        assert "exceeded" in alert.message.lower()
        assert "75.00" in alert.message
        assert "70.00" in alert.message
    
    def test_alert_message_less_than(self):
        """Test alert message for less_than comparison."""
        threshold = ThresholdConfig(
            metric_type=MetricType.CACHE_HIT_RATE,
            warning_threshold=70.0,
            comparison="less_than"
        )
        manager = AlertManager(thresholds=[threshold])
        
        alert = manager.check_metric(MetricType.CACHE_HIT_RATE, 65.0)
        assert "fell below" in alert.message.lower()
        assert "65.00" in alert.message
        assert "70.00" in alert.message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
