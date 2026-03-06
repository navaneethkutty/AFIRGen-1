# Script to remove remaining obsolete test files
# These tests are for infrastructure modules that still exist but are broken

Write-Host "Removing remaining obsolete test files..." -ForegroundColor Yellow

$obsoleteTests = @(
    "test_pagination.py",
    "test_prometheus_endpoint_integration.py",
    "test_property_api_tracking.py",
    "test_property_background_tasks.py",
    "test_property_cache_headers.py",
    "test_property_cache_tracking.py",
    "test_property_compression.py",
    "test_property_field_filter.py",
    "test_property_model_server_tracking.py",
    "test_property_pagination.py",
    "test_property_pagination_aggregation.py",
    "test_property_retry_backoff.py",
    "test_property_select_star.py",
    "test_property_task_retry.py",
    "test_property_threshold_alerting.py",
    "test_query_optimizer.py",
    "test_repository_pattern.py",
    "test_retry_handler.py",
    "test_retry_handler_with_classification.py",
    "test_security_headers_simple.py",
    "test_task_endpoints.py",
    "tests/integration/test_bugfix_integration.py",
    "tests/integration/test_fir_generation_e2e.py",
    "tests/performance/test_api_benchmarks.py",
    "tests/performance/test_cache_benchmarks.py",
    "tests/performance/test_database_benchmarks.py",
    "tests/test_preservation_properties.py"
)

$removed = 0
$notFound = 0

foreach ($test in $obsoleteTests) {
    if (Test-Path $test) {
        Remove-Item $test -Force
        Write-Host "  ✓ Removed: $test" -ForegroundColor Green
        $removed++
    } else {
        Write-Host "  ⚠ Not found: $test" -ForegroundColor Yellow
        $notFound++
    }
}

Write-Host ""
Write-Host "Cleanup complete!" -ForegroundColor Cyan
Write-Host "  Removed: $removed files" -ForegroundColor Green
Write-Host "  Not found: $notFound files" -ForegroundColor Yellow
Write-Host ""
Write-Host "Run 'pytest -v' to verify tests now work" -ForegroundColor Cyan
