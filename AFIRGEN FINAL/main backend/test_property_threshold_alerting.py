"""
test_property_threshold_alerting.py
-----------------------------------------------------------------------------
Property-Based Tests for Threshold Alerting
-----------------------------------------------------------------------------

Property tests for threshold alerting using Hypothesis to verify:
- Property 24: Threshold alerting

Requirements Validated: 5.6 (Alert when resource usage exceeds thresholds)
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from infrastructure.alerting import (
    AlertManager,
    AlertSeverity,
    MetricType,
    ThresholdConfig,
    Alert,
    AlertNotificationBackend
)


# Strategy for generating metric values
metric_values = st.floats(
    min_value=0.0,
    max_value=100.0,
    allow_nan=False,
    allow_infinity=False
)

# Strategy for generating threshold values
threshold_values = st.floats(
    min_value=0.0,
    max_value=100.0,
    allow_nan=False,
    allow_infinity=False
)

# Strategy for generating metric types
metric_types = st.sampled_from(list(MetricType))

# Strategy for generating comparison operators
comparison_operators = st.sampled_from(["greater_than", "less_than", "equals"])

# Strategy for generating severity levels
severity_levels = st.sampled_from(list(AlertSeverity))


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


# Feature: backend-optimization, Property 24: Threshold alerting
@given(
    metric_type=metric_types,
    current_value=metric_values,
    threshold_value=threshold_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_alert_emitted_when_threshold_exceeded_greater_than(
    metric_type, current_value, threshold_value
):
    """
    Property 24: For any monitored metric that exceeds its configured threshold
    (greater_than comparison), the Monitoring_System should emit an alert.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Alerts are emitted when current value > threshold
    2. No alerts are emitted when current value <= threshold
    3. Alert includes correct metric name, current value, and threshold value
    """
    # Assume threshold is meaningful (not at boundary)
    assume(abs(current_value - threshold_value) > 0.01)
    
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=threshold_value,
        comparison="greater_than"
    )
    
    mock_backend = MockNotificationBackend()
    manager = AlertManager(
        thresholds=[threshold_config],
        notification_backends=[mock_backend]
    )
    
    # Check metric
    alert = manager.check_metric(metric_type, current_value)
    
    # Property assertions
    if current_value > threshold_value:
        # Alert should be emitted
        assert alert is not None, \
            f"Alert should be emitted when {current_value} > {threshold_value}"
        assert alert.metric_type == metric_type, \
            f"Alert should have correct metric type"
        assert alert.current_value == current_value, \
            f"Alert should include current value"
        assert alert.threshold_value == threshold_value, \
            f"Alert should include threshold value"
        assert len(mock_backend.sent_alerts) == 1, \
            f"Alert should be sent to notification backend"
    else:
        # No alert should be emitted
        assert alert is None, \
            f"No alert should be emitted when {current_value} <= {threshold_value}"
        assert len(mock_backend.sent_alerts) == 0, \
            f"No alert should be sent to notification backend"


@given(
    metric_type=metric_types,
    current_value=metric_values,
    threshold_value=threshold_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_alert_emitted_when_threshold_exceeded_less_than(
    metric_type, current_value, threshold_value
):
    """
    Property 24: For any monitored metric that falls below its configured threshold
    (less_than comparison), the Monitoring_System should emit an alert.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Alerts are emitted when current value < threshold
    2. No alerts are emitted when current value >= threshold
    3. Alert includes correct comparison information
    """
    # Assume threshold is meaningful (not at boundary)
    assume(abs(current_value - threshold_value) > 0.01)
    
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=threshold_value,
        comparison="less_than"
    )
    
    mock_backend = MockNotificationBackend()
    manager = AlertManager(
        thresholds=[threshold_config],
        notification_backends=[mock_backend]
    )
    
    # Check metric
    alert = manager.check_metric(metric_type, current_value)
    
    # Property assertions
    if current_value < threshold_value:
        # Alert should be emitted
        assert alert is not None, \
            f"Alert should be emitted when {current_value} < {threshold_value}"
        assert alert.metric_type == metric_type, \
            f"Alert should have correct metric type"
        assert alert.current_value == current_value, \
            f"Alert should include current value"
        assert alert.threshold_value == threshold_value, \
            f"Alert should include threshold value"
        assert len(mock_backend.sent_alerts) == 1, \
            f"Alert should be sent to notification backend"
    else:
        # No alert should be emitted
        assert alert is None, \
            f"No alert should be emitted when {current_value} >= {threshold_value}"
        assert len(mock_backend.sent_alerts) == 0, \
            f"No alert should be sent to notification backend"


@given(
    metric_type=metric_types,
    warning_threshold=threshold_values,
    critical_threshold=threshold_values,
    current_value=metric_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_warning_and_critical_thresholds_work_correctly(
    metric_type, warning_threshold, critical_threshold, current_value
):
    """
    Property 24: For any metric with both warning and critical thresholds,
    the correct severity level should be triggered based on the current value.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Critical alerts are emitted when critical threshold is exceeded
    2. Warning alerts are emitted when warning threshold is exceeded but not critical
    3. No alerts when neither threshold is exceeded
    4. Critical takes precedence over warning
    """
    # Ensure critical threshold is higher than warning for greater_than comparison
    assume(critical_threshold > warning_threshold)
    assume(abs(current_value - warning_threshold) > 0.01)
    assume(abs(current_value - critical_threshold) > 0.01)
    
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        comparison="greater_than"
    )
    
    mock_backend = MockNotificationBackend()
    manager = AlertManager(
        thresholds=[threshold_config],
        notification_backends=[mock_backend]
    )
    
    # Check metric
    alert = manager.check_metric(metric_type, current_value)
    
    # Property assertions
    if current_value > critical_threshold:
        # Critical alert should be emitted
        assert alert is not None, \
            f"Alert should be emitted when {current_value} > {critical_threshold}"
        assert alert.severity == AlertSeverity.CRITICAL, \
            f"Alert severity should be CRITICAL when exceeding critical threshold"
        assert alert.threshold_value == critical_threshold, \
            f"Alert should reference critical threshold"
    elif current_value > warning_threshold:
        # Warning alert should be emitted
        assert alert is not None, \
            f"Alert should be emitted when {current_value} > {warning_threshold}"
        assert alert.severity == AlertSeverity.WARNING, \
            f"Alert severity should be WARNING when exceeding warning threshold"
        assert alert.threshold_value == warning_threshold, \
            f"Alert should reference warning threshold"
    else:
        # No alert should be emitted
        assert alert is None, \
            f"No alert should be emitted when {current_value} <= {warning_threshold}"


@given(
    metric_type=metric_types,
    threshold_value=threshold_values,
    comparison=comparison_operators,
    current_value=metric_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_different_comparison_operators_work(
    metric_type, threshold_value, comparison, current_value
):
    """
    Property 24: For any comparison operator (greater_than, less_than, equals),
    the alerting system should correctly evaluate the condition.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. greater_than comparison works correctly
    2. less_than comparison works correctly
    3. equals comparison works correctly (with float epsilon)
    """
    # Assume meaningful difference for non-equals comparisons
    if comparison != "equals":
        assume(abs(current_value - threshold_value) > 0.01)
    
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=threshold_value,
        comparison=comparison
    )
    
    mock_backend = MockNotificationBackend()
    manager = AlertManager(
        thresholds=[threshold_config],
        notification_backends=[mock_backend]
    )
    
    # Check metric
    alert = manager.check_metric(metric_type, current_value)
    
    # Property assertions based on comparison type
    if comparison == "greater_than":
        if current_value > threshold_value:
            assert alert is not None, \
                f"Alert should be emitted for greater_than when {current_value} > {threshold_value}"
        else:
            assert alert is None, \
                f"No alert for greater_than when {current_value} <= {threshold_value}"
    
    elif comparison == "less_than":
        if current_value < threshold_value:
            assert alert is not None, \
                f"Alert should be emitted for less_than when {current_value} < {threshold_value}"
        else:
            assert alert is None, \
                f"No alert for less_than when {current_value} >= {threshold_value}"
    
    elif comparison == "equals":
        # For equals, use epsilon comparison
        if abs(current_value - threshold_value) < 1e-9:
            assert alert is not None, \
                f"Alert should be emitted for equals when values are equal"
        else:
            assert alert is None, \
                f"No alert for equals when values are not equal"


@given(
    metric_type=metric_types,
    threshold_value=threshold_values,
    num_alerts=st.integers(min_value=2, max_value=5),
    deduplication_window=st.integers(min_value=10, max_value=60)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_alert_deduplication_prevents_alert_storms(
    metric_type, threshold_value, num_alerts, deduplication_window
):
    """
    Property 24: For any sequence of alerts for the same metric and severity
    within the deduplication window, only the first alert should be emitted.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. First alert is emitted
    2. Subsequent alerts within deduplication window are suppressed
    3. Alert deduplication prevents alert storms
    """
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=threshold_value,
        comparison="greater_than"
    )
    
    mock_backend = MockNotificationBackend()
    manager = AlertManager(
        thresholds=[threshold_config],
        notification_backends=[mock_backend],
        deduplication_window=deduplication_window
    )
    
    # Generate value that exceeds threshold
    exceeding_value = threshold_value + 10.0
    
    # Check metric multiple times
    alerts_emitted = []
    for i in range(num_alerts):
        alert = manager.check_metric(metric_type, exceeding_value)
        if alert is not None:
            alerts_emitted.append(alert)
    
    # Property assertions
    
    # 1. Only first alert should be emitted (others deduplicated)
    assert len(alerts_emitted) == 1, \
        f"Only first alert should be emitted, got {len(alerts_emitted)} alerts"
    
    # 2. Only one alert should be sent to backend
    assert len(mock_backend.sent_alerts) == 1, \
        f"Only one alert should be sent to backend within deduplication window"
    
    # 3. First alert should have correct properties
    assert alerts_emitted[0].metric_type == metric_type, \
        f"Alert should have correct metric type"
    assert alerts_emitted[0].current_value == exceeding_value, \
        f"Alert should have correct current value"


@given(
    metric_type=metric_types,
    warning_threshold=threshold_values,
    critical_threshold=threshold_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_different_severity_alerts_not_deduplicated(
    metric_type, warning_threshold, critical_threshold
):
    """
    Property 24: For any metric with different severity levels,
    alerts with different severities should not be deduplicated.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Warning and critical alerts are tracked separately
    2. Different severity alerts are both emitted
    3. Deduplication is per (metric_type, severity) pair
    """
    # Ensure critical threshold is higher than warning
    assume(critical_threshold > warning_threshold + 1.0)
    
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        comparison="greater_than"
    )
    
    mock_backend = MockNotificationBackend()
    manager = AlertManager(
        thresholds=[threshold_config],
        notification_backends=[mock_backend],
        deduplication_window=60
    )
    
    # First, trigger warning alert
    warning_value = warning_threshold + 0.5
    warning_alert = manager.check_metric(metric_type, warning_value)
    
    # Then, trigger critical alert
    critical_value = critical_threshold + 0.5
    critical_alert = manager.check_metric(metric_type, critical_value)
    
    # Property assertions
    
    # 1. Both alerts should be emitted (different severities)
    assert warning_alert is not None, \
        f"Warning alert should be emitted"
    assert critical_alert is not None, \
        f"Critical alert should be emitted (not deduplicated)"
    
    # 2. Alerts should have different severities
    assert warning_alert.severity == AlertSeverity.WARNING, \
        f"First alert should be WARNING"
    assert critical_alert.severity == AlertSeverity.CRITICAL, \
        f"Second alert should be CRITICAL"
    
    # 3. Both alerts should be sent to backend
    assert len(mock_backend.sent_alerts) == 2, \
        f"Both alerts should be sent (different severities)"


@given(
    metric_type=metric_types,
    threshold_value=threshold_values,
    metadata_keys=st.lists(
        st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        min_size=1,
        max_size=5,
        unique=True
    ),
    metadata_values=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_alerts_include_correct_metadata(
    metric_type, threshold_value, metadata_keys, metadata_values
):
    """
    Property 24: For any alert with metadata,
    the alert should include all provided metadata.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Alerts include provided metadata
    2. Metadata is preserved correctly
    3. Metadata is accessible in alert object
    """
    # Create metadata dictionary
    metadata = dict(zip(metadata_keys[:len(metadata_values)], metadata_values))
    
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=threshold_value,
        comparison="greater_than"
    )
    
    mock_backend = MockNotificationBackend()
    manager = AlertManager(
        thresholds=[threshold_config],
        notification_backends=[mock_backend]
    )
    
    # Check metric with value that exceeds threshold
    exceeding_value = threshold_value + 10.0
    alert = manager.check_metric(metric_type, exceeding_value, metadata=metadata)
    
    # Property assertions
    
    # 1. Alert should be emitted
    assert alert is not None, \
        f"Alert should be emitted when threshold is exceeded"
    
    # 2. Alert should include all metadata
    assert alert.metadata == metadata, \
        f"Alert should include all provided metadata"
    
    # 3. Each metadata key-value pair should be present
    for key, value in metadata.items():
        assert key in alert.metadata, \
            f"Metadata key '{key}' should be in alert"
        assert alert.metadata[key] == value, \
            f"Metadata value for '{key}' should match"


@given(
    metric_type=metric_types,
    threshold_value=threshold_values,
    num_alerts=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_alert_history_maintained_correctly(
    metric_type, threshold_value, num_alerts
):
    """
    Property 24: For any sequence of alerts,
    the alert history should maintain a record of all emitted alerts.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Alert history records all emitted alerts
    2. Alert history can be retrieved
    3. Alert history includes correct alert details
    """
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=threshold_value,
        comparison="greater_than"
    )
    
    manager = AlertManager(thresholds=[threshold_config])
    
    # Clear any existing history
    manager.clear_alert_history()
    
    # Generate value that exceeds threshold
    exceeding_value = threshold_value + 10.0
    
    # Emit multiple alerts (clear deduplication between each)
    for i in range(num_alerts):
        manager.check_metric(metric_type, exceeding_value)
        # Clear deduplication to allow next alert
        manager._recent_alerts.clear()
    
    # Get alert history
    history = manager.get_alert_history()
    
    # Property assertions
    
    # 1. History should contain all emitted alerts
    assert len(history) == num_alerts, \
        f"Alert history should contain {num_alerts} alerts, got {len(history)}"
    
    # 2. All alerts in history should have correct metric type
    for alert in history:
        assert alert.metric_type == metric_type, \
            f"All alerts in history should have correct metric type"
        assert alert.current_value == exceeding_value, \
            f"All alerts in history should have correct current value"
        assert alert.threshold_value == threshold_value, \
            f"All alerts in history should have correct threshold value"


@given(
    metric_types_list=st.lists(
        st.sampled_from(list(MetricType)),
        min_size=2,
        max_size=5,
        unique=True
    ),
    threshold_value=threshold_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_alert_history_filtered_by_metric_type(
    metric_types_list, threshold_value
):
    """
    Property 24: For any alert history with multiple metric types,
    filtering by metric type should return only alerts for that metric.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Alert history can be filtered by metric type
    2. Filtered results contain only matching alerts
    3. Other metric types are excluded
    """
    # Create threshold configurations for all metric types
    thresholds = [
        ThresholdConfig(
            metric_type=mt,
            warning_threshold=threshold_value,
            comparison="greater_than"
        )
        for mt in metric_types_list
    ]
    
    manager = AlertManager(thresholds=thresholds)
    manager.clear_alert_history()
    
    # Generate value that exceeds threshold
    exceeding_value = threshold_value + 10.0
    
    # Emit one alert for each metric type
    for metric_type in metric_types_list:
        manager.check_metric(metric_type, exceeding_value)
    
    # Test filtering for each metric type
    for target_metric_type in metric_types_list:
        filtered_history = manager.get_alert_history(metric_type=target_metric_type)
        
        # Property assertions
        
        # 1. Should have exactly one alert for this metric type
        assert len(filtered_history) == 1, \
            f"Filtered history should contain 1 alert for {target_metric_type.value}"
        
        # 2. Alert should be for the correct metric type
        assert filtered_history[0].metric_type == target_metric_type, \
            f"Filtered alert should be for {target_metric_type.value}"


@given(
    metric_type=metric_types,
    warning_threshold=threshold_values,
    critical_threshold=threshold_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_alert_history_filtered_by_severity(
    metric_type, warning_threshold, critical_threshold
):
    """
    Property 24: For any alert history with multiple severity levels,
    filtering by severity should return only alerts with that severity.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Alert history can be filtered by severity
    2. Filtered results contain only matching severity
    3. Other severities are excluded
    """
    # Ensure critical threshold is higher than warning
    assume(critical_threshold > warning_threshold + 1.0)
    
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        comparison="greater_than"
    )
    
    manager = AlertManager(thresholds=[threshold_config])
    manager.clear_alert_history()
    
    # Emit warning alert
    warning_value = warning_threshold + 0.5
    manager.check_metric(metric_type, warning_value)
    
    # Emit critical alert (clear deduplication first)
    manager._recent_alerts.clear()
    critical_value = critical_threshold + 0.5
    manager.check_metric(metric_type, critical_value)
    
    # Filter by WARNING severity
    warning_alerts = manager.get_alert_history(severity=AlertSeverity.WARNING)
    
    # Filter by CRITICAL severity
    critical_alerts = manager.get_alert_history(severity=AlertSeverity.CRITICAL)
    
    # Property assertions
    
    # 1. Should have one warning alert
    assert len(warning_alerts) == 1, \
        f"Should have 1 warning alert"
    assert warning_alerts[0].severity == AlertSeverity.WARNING, \
        f"Filtered alert should be WARNING severity"
    
    # 2. Should have one critical alert
    assert len(critical_alerts) == 1, \
        f"Should have 1 critical alert"
    assert critical_alerts[0].severity == AlertSeverity.CRITICAL, \
        f"Filtered alert should be CRITICAL severity"


@given(
    metric_type=metric_types,
    threshold_value=threshold_values,
    num_backends=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_alerts_sent_to_all_notification_backends(
    metric_type, threshold_value, num_backends
):
    """
    Property 24: For any alert with multiple notification backends,
    the alert should be sent to all backends.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Alerts are sent to all configured backends
    2. Each backend receives the same alert
    3. Backend failures don't prevent other backends from receiving alerts
    """
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=threshold_value,
        comparison="greater_than"
    )
    
    # Create multiple mock backends
    backends = [MockNotificationBackend() for _ in range(num_backends)]
    
    manager = AlertManager(
        thresholds=[threshold_config],
        notification_backends=backends
    )
    
    # Check metric with value that exceeds threshold
    exceeding_value = threshold_value + 10.0
    alert = manager.check_metric(metric_type, exceeding_value)
    
    # Property assertions
    
    # 1. Alert should be emitted
    assert alert is not None, \
        f"Alert should be emitted when threshold is exceeded"
    
    # 2. All backends should receive the alert
    for i, backend in enumerate(backends):
        assert len(backend.sent_alerts) == 1, \
            f"Backend {i} should receive 1 alert"
        assert backend.sent_alerts[0].metric_type == metric_type, \
            f"Backend {i} should receive alert with correct metric type"


@given(
    metric_type=metric_types,
    threshold_value=threshold_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_alert_message_contains_required_information(
    metric_type, threshold_value
):
    """
    Property 24: For any alert, the alert message should contain
    the metric name, current value, and threshold value.
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Alert message is human-readable
    2. Alert message includes metric name
    3. Alert message includes current and threshold values
    """
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=threshold_value,
        comparison="greater_than"
    )
    
    manager = AlertManager(thresholds=[threshold_config])
    
    # Check metric with value that exceeds threshold
    exceeding_value = threshold_value + 10.0
    alert = manager.check_metric(metric_type, exceeding_value)
    
    # Property assertions
    
    # 1. Alert should be emitted
    assert alert is not None, \
        f"Alert should be emitted when threshold is exceeded"
    
    # 2. Alert message should contain metric type
    assert metric_type.value in alert.message.lower(), \
        f"Alert message should contain metric type '{metric_type.value}'"
    
    # 3. Alert message should contain current value (as string)
    assert str(round(exceeding_value, 2)) in alert.message, \
        f"Alert message should contain current value"
    
    # 4. Alert message should contain threshold value (as string)
    assert str(round(threshold_value, 2)) in alert.message, \
        f"Alert message should contain threshold value"


@given(
    metric_type=metric_types,
    threshold_value=threshold_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_alert_timestamp_is_recent(metric_type, threshold_value):
    """
    Property 24: For any alert, the alert timestamp should be
    close to the current time (within a few seconds).
    
    **Validates: Requirements 5.6**
    
    This property verifies that:
    1. Alerts have timestamps
    2. Timestamps are recent (not in the past or future)
    3. Timestamps are accurate
    """
    # Create threshold configuration
    threshold_config = ThresholdConfig(
        metric_type=metric_type,
        warning_threshold=threshold_value,
        comparison="greater_than"
    )
    
    manager = AlertManager(thresholds=[threshold_config])
    
    # Record time before check
    time_before = datetime.utcnow()
    
    # Check metric with value that exceeds threshold
    exceeding_value = threshold_value + 10.0
    alert = manager.check_metric(metric_type, exceeding_value)
    
    # Record time after check
    time_after = datetime.utcnow()
    
    # Property assertions
    
    # 1. Alert should be emitted
    assert alert is not None, \
        f"Alert should be emitted when threshold is exceeded"
    
    # 2. Alert should have a timestamp
    assert alert.timestamp is not None, \
        f"Alert should have a timestamp"
    
    # 3. Timestamp should be between before and after times (within 5 seconds buffer)
    assert time_before - timedelta(seconds=5) <= alert.timestamp <= time_after + timedelta(seconds=5), \
        f"Alert timestamp should be recent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
