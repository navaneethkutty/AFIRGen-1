# Script to remove obsolete test files from old implementation
# These tests are for infrastructure that was removed in Task 1

Write-Host "Removing obsolete test files..." -ForegroundColor Yellow

$obsoleteTests = @(
    "test_alerting.py",
    "test_alerting_integration.py",
    "test_background_task_manager.py",
    "test_cache_header_middleware.py",
    "test_cache_invalidation.py",
    "test_cache_invalidation_properties.py",
    "test_cache_manager.py",
    "test_celery_config.py",
    "test_circuit_breaker.py",
    "test_circuit_breaker_property.py",
    "test_compression_middleware.py",
    "test_connection_retry.py",
    "test_connection_retry_integration.py",
    "test_connection_retry_property.py",
    "test_correlation_id_integration.py",
    "test_correlation_id_middleware.py",
    "test_correlation_id_property.py",
    "test_dependency_injection.py",
    "test_error_classification.py",
    "test_error_classification_property.py",
    "test_error_response.py",
    "test_error_response_integration.py",
    "test_error_response_logging_property.py",
    "test_field_filter.py",
    "test_fir_repository_caching.py",
    "test_fir_service_integration.py",
    "test_interfaces.py",
    "test_log_format_property.py",
    "test_logger_enhancements.py",
    "test_metrics_cache_db.py",
    "test_metrics_middleware.py",
    "test_metrics_middleware_integration.py",
    "test_model_server_monitoring.py",
    "test_model_server_monitoring_integration.py",
    "test_performance_testing.py",
    "test_prometheus_endpoint.py",
    "test_redis_client.py",
    "test_redis_connection_pool.py",
    "test_redis_connection_pool_property.py",
    "test_redis_integration.py",
    "test_reliability.py",
    "test_reliability_integration.py",
    "test_reliability_property.py",
    "test_request_id_middleware.py",
    "test_request_id_property.py",
    "test_request_logging_middleware.py",
    "test_request_logging_property.py",
    "test_structured_logging.py",
    "test_structured_logging_integration.py",
    "test_structured_logging_property.py",
    "test_timeout_middleware.py",
    "test_timeout_property.py",
    "test_tracing.py",
    "test_tracing_integration.py",
    "test_tracing_property.py",
    "test_xray_tracing.py",
    "test_xray_tracing_integration.py"
)

$removed = 0
$notFound = 0

foreach ($test in $obsoleteTests) {
    if (Test-Path $test) {
        Remove-Item $test -Force
        Write-Host "  ✓ Removed: $test" -ForegroundColor Green
        $removed++
    } else {
        $notFound++
    }
}

Write-Host ""
Write-Host "Cleanup complete!" -ForegroundColor Cyan
Write-Host "  Removed: $removed files" -ForegroundColor Green
Write-Host "  Not found: $notFound files" -ForegroundColor Yellow
Write-Host ""
Write-Host "Run 'pytest -v' to verify tests now work" -ForegroundColor Cyan
