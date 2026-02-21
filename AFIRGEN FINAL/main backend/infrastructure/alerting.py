"""
Alerting system for monitoring metrics and emitting alerts.

This module provides threshold-based alerting for system metrics,
with support for different severity levels, deduplication, and
pluggable notification backends.

Validates: Requirements 5.6
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import structlog
from collections import defaultdict


logger = structlog.get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    WARNING = "warning"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics that can be monitored."""
    CPU_PERCENT = "cpu_percent"
    MEMORY_PERCENT = "memory_percent"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    DB_POOL_UTILIZATION = "db_pool_utilization"
    MODEL_SERVER_LATENCY = "model_server_latency"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"


@dataclass
class ThresholdConfig:
    """Configuration for a metric threshold."""
    metric_type: MetricType
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    comparison: str = "greater_than"  # greater_than, less_than, equals
    
    def __post_init__(self):
        """Validate threshold configuration."""
        if self.warning_threshold is None and self.critical_threshold is None:
            raise ValueError("At least one threshold (warning or critical) must be set")
        
        if self.comparison not in ["greater_than", "less_than", "equals"]:
            raise ValueError(f"Invalid comparison: {self.comparison}")


@dataclass
class Alert:
    """Represents an alert event."""
    metric_type: MetricType
    severity: AlertSeverity
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for logging/serialization."""
        return {
            "metric_type": self.metric_type.value,
            "severity": self.severity.value,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class AlertNotificationBackend:
    """Base class for alert notification backends."""
    
    def send_alert(self, alert: Alert) -> bool:
        """
        Send an alert notification.
        
        Args:
            alert: The alert to send
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        raise NotImplementedError


class LogNotificationBackend(AlertNotificationBackend):
    """Notification backend that logs alerts."""
    
    def send_alert(self, alert: Alert) -> bool:
        """Log the alert."""
        try:
            if alert.severity == AlertSeverity.CRITICAL:
                logger.critical(
                    "Alert triggered",
                    **alert.to_dict()
                )
            else:
                logger.warning(
                    "Alert triggered",
                    **alert.to_dict()
                )
            return True
        except Exception as e:
            logger.error("Failed to log alert", error=str(e), alert=alert.to_dict())
            return False


class AlertManager:
    """
    Manages alert thresholds, monitoring, and notifications.
    
    Validates: Requirements 5.6
    """
    
    def __init__(
        self,
        thresholds: Optional[List[ThresholdConfig]] = None,
        notification_backends: Optional[List[AlertNotificationBackend]] = None,
        deduplication_window: int = 300  # 5 minutes in seconds
    ):
        """
        Initialize the alert manager.
        
        Args:
            thresholds: List of threshold configurations
            notification_backends: List of notification backends
            deduplication_window: Time window in seconds for alert deduplication
        """
        self.thresholds: Dict[MetricType, ThresholdConfig] = {}
        if thresholds:
            for threshold in thresholds:
                self.thresholds[threshold.metric_type] = threshold
        
        self.notification_backends = notification_backends or [LogNotificationBackend()]
        self.deduplication_window = deduplication_window
        
        # Track recent alerts for deduplication
        # Key: (metric_type, severity), Value: timestamp of last alert
        self._recent_alerts: Dict[tuple, datetime] = {}
        
        # Track alert history for audit trail
        self._alert_history: List[Alert] = []
    
    def add_threshold(self, threshold: ThresholdConfig):
        """Add or update a threshold configuration."""
        self.thresholds[threshold.metric_type] = threshold
    
    def remove_threshold(self, metric_type: MetricType):
        """Remove a threshold configuration."""
        if metric_type in self.thresholds:
            del self.thresholds[metric_type]
    
    def check_metric(
        self,
        metric_type: MetricType,
        current_value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Alert]:
        """
        Check a metric value against configured thresholds.
        
        Args:
            metric_type: Type of metric being checked
            current_value: Current value of the metric
            metadata: Additional metadata to include in alert
            
        Returns:
            Alert object if threshold is exceeded, None otherwise
            
        Validates: Requirements 5.6
        """
        if metric_type not in self.thresholds:
            return None
        
        threshold = self.thresholds[metric_type]
        alert = self._evaluate_threshold(
            metric_type,
            current_value,
            threshold,
            metadata or {}
        )
        
        if alert:
            # Check deduplication
            if not self._is_duplicate(alert):
                self._emit_alert(alert)
                return alert
        
        return None
    
    def _evaluate_threshold(
        self,
        metric_type: MetricType,
        current_value: float,
        threshold: ThresholdConfig,
        metadata: Dict[str, Any]
    ) -> Optional[Alert]:
        """Evaluate if a metric value exceeds thresholds."""
        severity = None
        threshold_value = None
        
        # Check critical threshold first
        if threshold.critical_threshold is not None:
            if self._compare_value(current_value, threshold.critical_threshold, threshold.comparison):
                severity = AlertSeverity.CRITICAL
                threshold_value = threshold.critical_threshold
        
        # Check warning threshold if critical not triggered
        if severity is None and threshold.warning_threshold is not None:
            if self._compare_value(current_value, threshold.warning_threshold, threshold.comparison):
                severity = AlertSeverity.WARNING
                threshold_value = threshold.warning_threshold
        
        if severity is None:
            return None
        
        # Create alert message
        message = self._create_alert_message(
            metric_type,
            severity,
            current_value,
            threshold_value,
            threshold.comparison
        )
        
        return Alert(
            metric_type=metric_type,
            severity=severity,
            current_value=current_value,
            threshold_value=threshold_value,
            message=message,
            metadata=metadata
        )
    
    def _compare_value(self, current: float, threshold: float, comparison: str) -> bool:
        """Compare current value against threshold."""
        if comparison == "greater_than":
            return current > threshold
        elif comparison == "less_than":
            return current < threshold
        elif comparison == "equals":
            return abs(current - threshold) < 1e-9  # Float comparison with epsilon
        return False
    
    def _create_alert_message(
        self,
        metric_type: MetricType,
        severity: AlertSeverity,
        current_value: float,
        threshold_value: float,
        comparison: str
    ) -> str:
        """Create a human-readable alert message."""
        comparison_text = {
            "greater_than": "exceeded",
            "less_than": "fell below",
            "equals": "equals"
        }.get(comparison, "violated")
        
        return (
            f"{severity.value.upper()}: {metric_type.value} {comparison_text} threshold. "
            f"Current: {current_value:.2f}, Threshold: {threshold_value:.2f}"
        )
    
    def _is_duplicate(self, alert: Alert) -> bool:
        """
        Check if alert is a duplicate within the deduplication window.
        
        Implements alert deduplication to prevent alert storms.
        """
        key = (alert.metric_type, alert.severity)
        
        if key in self._recent_alerts:
            last_alert_time = self._recent_alerts[key]
            time_since_last = (alert.timestamp - last_alert_time).total_seconds()
            
            if time_since_last < self.deduplication_window:
                logger.debug(
                    "Alert deduplicated",
                    metric_type=alert.metric_type.value,
                    severity=alert.severity.value,
                    time_since_last=time_since_last
                )
                return True
        
        # Update recent alerts tracking
        self._recent_alerts[key] = alert.timestamp
        return False
    
    def _emit_alert(self, alert: Alert):
        """
        Emit an alert to all configured notification backends.
        
        Validates: Requirements 5.6
        """
        # Add to alert history for audit trail
        self._alert_history.append(alert)
        
        # Send to all notification backends
        for backend in self.notification_backends:
            try:
                backend.send_alert(alert)
            except Exception as e:
                logger.error(
                    "Failed to send alert via backend",
                    backend=backend.__class__.__name__,
                    error=str(e),
                    alert=alert.to_dict()
                )
    
    def get_alert_history(
        self,
        metric_type: Optional[MetricType] = None,
        severity: Optional[AlertSeverity] = None,
        since: Optional[datetime] = None
    ) -> List[Alert]:
        """
        Get alert history with optional filtering.
        
        Args:
            metric_type: Filter by metric type
            severity: Filter by severity
            since: Filter alerts since this timestamp
            
        Returns:
            List of alerts matching the filters
        """
        filtered = self._alert_history
        
        if metric_type:
            filtered = [a for a in filtered if a.metric_type == metric_type]
        
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        
        if since:
            filtered = [a for a in filtered if a.timestamp >= since]
        
        return filtered
    
    def clear_alert_history(self):
        """Clear the alert history (useful for testing)."""
        self._alert_history.clear()
        self._recent_alerts.clear()


# Default alert manager instance with common thresholds
def create_default_alert_manager() -> AlertManager:
    """
    Create an alert manager with default threshold configurations.
    
    Returns:
        AlertManager with default thresholds
    """
    default_thresholds = [
        # CPU usage thresholds
        ThresholdConfig(
            metric_type=MetricType.CPU_PERCENT,
            warning_threshold=70.0,
            critical_threshold=90.0,
            comparison="greater_than"
        ),
        # Memory usage thresholds
        ThresholdConfig(
            metric_type=MetricType.MEMORY_PERCENT,
            warning_threshold=75.0,
            critical_threshold=90.0,
            comparison="greater_than"
        ),
        # Response time thresholds (in seconds)
        ThresholdConfig(
            metric_type=MetricType.RESPONSE_TIME,
            warning_threshold=2.0,
            critical_threshold=5.0,
            comparison="greater_than"
        ),
        # Error rate thresholds (percentage)
        ThresholdConfig(
            metric_type=MetricType.ERROR_RATE,
            warning_threshold=5.0,
            critical_threshold=10.0,
            comparison="greater_than"
        ),
        # Cache hit rate thresholds (percentage)
        ThresholdConfig(
            metric_type=MetricType.CACHE_HIT_RATE,
            warning_threshold=70.0,
            critical_threshold=50.0,
            comparison="less_than"
        ),
        # Database pool utilization thresholds (percentage)
        ThresholdConfig(
            metric_type=MetricType.DB_POOL_UTILIZATION,
            warning_threshold=80.0,
            critical_threshold=95.0,
            comparison="greater_than"
        ),
        # Model server latency thresholds (in seconds)
        ThresholdConfig(
            metric_type=MetricType.MODEL_SERVER_LATENCY,
            warning_threshold=10.0,
            critical_threshold=30.0,
            comparison="greater_than"
        )
    ]
    
    return AlertManager(thresholds=default_thresholds)


# Global alert manager instance
alert_manager = create_default_alert_manager()
