# Performance Testing Framework

## Overview

The Performance Testing Framework provides comprehensive tools for benchmarking and validating the performance of the AFIRGen backend system. It supports API endpoint benchmarks, database query benchmarks, cache performance tests, and concurrent load testing.

## Features

- **Flexible Benchmarking**: Run performance tests on any callable operation
- **Detailed Metrics**: Collect min, max, mean, median, P95, P99, standard deviation, and throughput
- **Threshold Validation**: Define and validate against performance SLA thresholds
- **Baseline Comparison**: Compare current results against baseline metrics
- **Concurrent Load Testing**: Test performance under various concurrency levels
- **System Metrics**: Collect CPU, memory, and disk I/O during tests
- **Report Generation**: Generate human-readable and JSON reports

## Usage

### Basic Benchmark

```python
from infrastructure.performance_testing import (
    PerformanceTestFramework,
    TestType,
    PerformanceThreshold
)

# Create framework instance
framework = PerformanceTestFramework()

# Define operation to benchmark
def my_operation():
    # Your code here
    pass

# Define performance threshold
threshold = PerformanceThreshold(
    max_p95_ms=100,
    max_p99_ms=200,
    min_throughput_ops=10
)

# Run benchmark
result = framework.run_benchmark(
    test_name="my_test",
    test_type=TestType.API_ENDPOINT,
    operation=my_operation,
    iterations=100,
    threshold=threshold,
    metadata={'endpoint': '/api/v1/fir'}
)

# Check result
print(f"Status: {result.status.value}")
print(f"Mean: {result.metrics.mean_time_ms:.2f}ms")
print(f"P95: {result.metrics.p95_time_ms:.2f}ms")
```

### Concurrent Load Testing

```python
# Test with different concurrency levels
results = framework.run_concurrent_benchmark(
    test_name="concurrent_api_test",
    operation=my_operation,
    concurrency_levels=[1, 5, 10, 20, 50],
    iterations_per_level=50,
    threshold=threshold
)

# Analyze results
for result in results:
    concurrency = result.metrics.metadata['concurrency']
    print(f"Concurrency {concurrency}: {result.metrics.mean_time_ms:.2f}ms")
```

### Baseline Comparison

```python
# Load baseline from previous run
framework.load_baseline('baseline_metrics.json')

# Run tests
result = framework.run_benchmark(...)

# Compare to baseline
comparison = framework.compare_to_baseline('my_test')
if comparison:
    print(f"Mean change: {comparison['mean_change_pct']:+.2f}%")
    print(f"P95 change: {comparison['p95_change_pct']:+.2f}%")

# Save new baseline
framework.save_baseline('baseline_metrics.json')
```

### Generate Reports

```python
# Generate text report
report = framework.generate_report(output_file='performance_report.txt')
print(report)

# Export JSON
framework.export_json('performance_results.json')
```

## Performance Thresholds

Define thresholds to validate performance:

```python
threshold = PerformanceThreshold(
    max_p95_ms=2000,      # P95 latency must be < 2000ms
    max_p99_ms=5000,      # P99 latency must be < 5000ms
    max_mean_ms=1000,     # Mean latency must be < 1000ms
    min_throughput_ops=10, # Throughput must be >= 10 ops/sec
    max_error_rate=0.01   # Error rate must be < 1%
)
```

## Test Types

The framework supports different test types:

- `TestType.API_ENDPOINT`: API endpoint benchmarks
- `TestType.DATABASE_QUERY`: Database query benchmarks
- `TestType.CACHE_OPERATION`: Cache operation benchmarks
- `TestType.CONCURRENT_LOAD`: Concurrent load tests

## Metrics Collected

For each test, the framework collects:

- **Timing Metrics**: min, max, mean, median, P95, P99, standard deviation
- **Throughput**: Operations per second
- **System Metrics**: CPU usage, memory usage, disk I/O
- **Metadata**: Custom metadata for context

## Report Format

The framework generates reports with:

1. **Summary**: Total tests, passed, failed, warnings
2. **Detailed Results**: Metrics for each test
3. **Baseline Comparison**: Percentage changes from baseline
4. **Violations**: Any threshold violations
5. **System Metrics**: Resource usage during tests

## Integration with CI/CD

The framework can be integrated into CI/CD pipelines:

```python
# Run tests
framework.run_benchmark(...)

# Check for failures
failed_tests = [r for r in framework.results if r.status == TestStatus.FAILED]
if failed_tests:
    print("Performance tests failed!")
    sys.exit(1)
```

## Best Practices

1. **Warmup Iterations**: Always use warmup iterations to avoid cold start effects
2. **Sufficient Iterations**: Use at least 100 iterations for stable statistics
3. **Realistic Thresholds**: Set thresholds based on actual SLA requirements
4. **Baseline Tracking**: Maintain baseline metrics to detect regressions
5. **System Isolation**: Run performance tests on isolated systems when possible
6. **Metadata**: Include relevant metadata for context and debugging

## Requirements

Validates Requirements 9.1-9.7:
- 9.1: API endpoint response time measurement
- 9.2: Database query execution time measurement
- 9.3: Cache hit rate and response time measurement
- 9.4: Concurrent request handling testing
- 9.5: Report generation with baseline comparison
- 9.6: Threshold validation for SLA compliance
- 9.7: CI/CD pipeline integration support
