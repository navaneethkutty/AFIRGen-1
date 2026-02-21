# Performance Testing Suite

## Overview

This directory contains comprehensive performance benchmarks for the AFIRGen backend system. The test suite validates that the system meets performance SLA requirements and detects performance regressions.

## Performance Requirements

Based on the backend optimization requirements:

- **API Response Time**: < 10s for cached requests, < 15s for uncached requests
- **Database Queries**: P95 < 100ms for indexed queries
- **Cache Operations**: P95 < 10ms for cache hits
- **Concurrent Load**: Handle 15 concurrent requests
- **Error Rate**: < 1% under normal load

## Test Structure

```
tests/performance/
├── test_api_benchmarks.py       # API endpoint performance tests
├── test_database_benchmarks.py  # Database query performance tests
├── test_cache_benchmarks.py     # Cache operation performance tests
└── README.md                    # This file
```

## Running Tests

### Quick Start

```bash
# Run all performance tests
make -f Makefile.performance perf-test

# Run specific test categories
make -f Makefile.performance perf-api      # API tests only
make -f Makefile.performance perf-db       # Database tests only
make -f Makefile.performance perf-cache    # Cache tests only

# Generate reports
make -f Makefile.performance perf-report
```

### Using pytest directly

```bash
# Run all performance tests
pytest -c pytest.performance.ini tests/performance/

# Run specific test file
pytest -c pytest.performance.ini tests/performance/test_api_benchmarks.py

# Run tests with specific marker
pytest -c pytest.performance.ini -m "performance and api"

# Run with verbose output
pytest -c pytest.performance.ini -v tests/performance/
```

### Using the report generator script

```bash
# Run tests and generate reports
python scripts/generate_performance_report.py --run-tests

# Compare to baseline
python scripts/generate_performance_report.py \
    --run-tests \
    --baseline performance_baseline.json \
    --fail-on-regression

# Save new baseline
python scripts/generate_performance_report.py \
    --run-tests \
    --save-baseline
```

## Test Categories

### API Endpoint Benchmarks

Tests in `test_api_benchmarks.py`:

- **GET /session/{session_id}/status**: Fast read operation (target: P95 < 100ms)
- **GET /fir/{fir_number}**: Cached FIR retrieval (target: P95 < 100ms)
- **GET /fir/{fir_number}/content**: Large payload with compression (target: P95 < 200ms)
- **POST /validate**: Business logic processing (target: P95 < 500ms)
- **POST /process**: Full FIR generation (target: P95 < 10s cached, < 15s uncached)
- **Concurrent Load**: 1, 5, 10, 15 concurrent requests

### Database Query Benchmarks

Tests in `test_database_benchmarks.py`:

- **Simple SELECT by ID**: Primary key lookup (target: P95 < 50ms)
- **SELECT with WHERE**: Indexed column filtering (target: P95 < 50ms)
- **JOIN queries**: Multi-table joins with indexes (target: P95 < 100ms)
- **Aggregation**: COUNT, SUM, AVG operations (target: P95 < 150ms)
- **Cursor pagination**: Optimized pagination (target: P95 < 100ms)
- **Full-text search**: Text search with indexes (target: P95 < 200ms)
- **Bulk insert**: Batch insert operations (target: P95 < 200ms)

### Cache Operation Benchmarks

Tests in `test_cache_benchmarks.py`:

- **Cache GET (hit)**: Retrieve cached value (target: P95 < 5ms)
- **Cache GET (miss)**: Cache miss handling (target: P95 < 10ms)
- **Cache SET**: Write to cache (target: P95 < 10ms)
- **Cache DELETE**: Invalidate cache entry (target: P95 < 10ms)
- **get_or_fetch (hit)**: Cache-aside pattern with hit (target: P95 < 5ms)
- **get_or_fetch (miss)**: Cache-aside pattern with miss (target: P95 < 50ms)
- **Hit rate measurement**: Verify 80%+ cache hit rate
- **Concurrent operations**: Cache under concurrent load

## Baseline Comparison

The test suite supports baseline comparison to detect performance regressions:

1. **Create baseline**: Run tests and save results as baseline
   ```bash
   make -f Makefile.performance perf-baseline
   ```

2. **Compare to baseline**: Run tests and compare to baseline
   ```bash
   make -f Makefile.performance perf-compare
   ```

3. **View changes**: Reports show percentage changes from baseline
   - Improvements: > 5% faster than baseline (green)
   - Regressions: > 5% slower than baseline (red)
   - Stable: Within 5% of baseline

## CI/CD Integration

Performance tests are integrated into the CI/CD pipeline:

### GitHub Actions Workflow

The `.github/workflows/performance-tests.yml` workflow:

- Runs on every push to main/develop
- Runs on pull requests
- Runs daily via cron schedule
- Compares results to baseline
- Fails build if SLA thresholds exceeded
- Uploads reports as artifacts
- Comments on PRs with results

### Running in CI/CD

```bash
# CI/CD mode - fails on regression
make -f Makefile.performance perf-ci

# Or using the script directly
python scripts/generate_performance_report.py \
    --run-tests \
    --baseline performance_baseline.json \
    --fail-on-regression
```

## Load Testing

Load tests use Locust to simulate realistic user traffic:

```bash
# Run load tests
make -f Makefile.performance perf-load

# Or run Locust directly
locust -f locustfile.py \
    --headless \
    --users 15 \
    --spawn-rate 5 \
    --run-time 5m \
    --host http://localhost:8000
```

Load test scenarios:
- 15 concurrent users (system requirement)
- Mixed workload: 60% reads, 30% validation, 10% processing
- 5-minute sustained load
- Measures throughput, response times, error rates

## Report Formats

### Summary Report

High-level overview with:
- Overall pass/fail status
- Test counts by category
- Key metrics (mean, P95, P99)
- Baseline comparison
- Threshold violations
- System resource usage

Example:
```
PERFORMANCE BENCHMARK SUMMARY
================================================================================
Generated: 2024-01-15T10:30:00Z
Total Tests: 25

OVERALL STATUS
--------------------------------------------------------------------------------
✓ Passed: 23
✗ Failed: 2
⚠ Warnings: 0
Success Rate: 92.0%
```

### Detailed Report

Comprehensive metrics for each test:
- All timing percentiles (min, max, mean, median, P95, P99)
- Standard deviation
- Throughput (ops/sec)
- System metrics during test
- Baseline comparison
- Threshold violations

### JSON Export

Machine-readable format for:
- CI/CD integration
- Trend analysis
- Custom reporting
- Data visualization

## Performance Thresholds

Thresholds are defined per test type:

```python
# API endpoints
API_THRESHOLDS = {
    'get_session_status': PerformanceThreshold(
        max_p95_ms=100,
        max_p99_ms=200,
        min_throughput_ops=50
    ),
    'process_text': PerformanceThreshold(
        max_p95_ms=10000,  # 10s
        max_p99_ms=15000,  # 15s
        min_throughput_ops=1
    )
}

# Database queries
DB_THRESHOLDS = {
    'simple_select': PerformanceThreshold(
        max_p95_ms=50,
        max_p99_ms=100,
        min_throughput_ops=100
    )
}

# Cache operations
CACHE_THRESHOLDS = {
    'cache_get_hit': PerformanceThreshold(
        max_p95_ms=5,
        max_p99_ms=10,
        min_throughput_ops=1000
    )
}
```

## Best Practices

1. **Run on isolated systems**: Performance tests should run on dedicated hardware
2. **Warm up**: Tests include warmup iterations to avoid cold start effects
3. **Sufficient iterations**: Minimum 100 iterations for stable statistics
4. **Baseline tracking**: Maintain baseline metrics to detect regressions
5. **Regular execution**: Run daily to catch performance issues early
6. **Resource monitoring**: Track CPU, memory, disk I/O during tests
7. **Realistic data**: Use production-like data volumes and patterns

## Troubleshooting

### Tests are slow

- Check system resources (CPU, memory, disk)
- Verify database indexes are created
- Ensure Redis is running and accessible
- Check for network latency

### High variance in results

- Run more iterations for stable statistics
- Ensure system is not under other load
- Check for background processes
- Use dedicated test environment

### Baseline comparison fails

- Verify baseline file exists and is valid JSON
- Check that test names match between runs
- Ensure same test configuration (iterations, etc.)

### CI/CD failures

- Check GitHub Actions logs for errors
- Verify services (Redis, MySQL) are healthy
- Check for timeout issues
- Review threshold violations in reports

## Metrics Glossary

- **Mean**: Average response time across all iterations
- **Median**: Middle value when sorted (50th percentile)
- **P95**: 95th percentile - 95% of requests faster than this
- **P99**: 99th percentile - 99% of requests faster than this
- **Throughput**: Operations per second
- **Hit Rate**: Percentage of cache hits vs total requests
- **Error Rate**: Percentage of failed requests

## Requirements Validation

This test suite validates:

- **Requirement 9.1**: API endpoint response time measurement ✓
- **Requirement 9.2**: Database query execution time measurement ✓
- **Requirement 9.3**: Cache hit rate and response time measurement ✓
- **Requirement 9.4**: Concurrent request handling testing ✓
- **Requirement 9.5**: Report generation with baseline comparison ✓
- **Requirement 9.6**: SLA threshold validation ✓
- **Requirement 9.7**: CI/CD pipeline integration ✓

## Support

For issues or questions:
1. Check this README
2. Review test output and reports
3. Check CI/CD workflow logs
4. Consult infrastructure/README_performance_testing.md
