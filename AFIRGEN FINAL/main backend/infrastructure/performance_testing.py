"""
Performance Testing Framework

This module provides a comprehensive framework for performance testing and benchmarking
of the AFIRGen backend system. It supports API endpoint benchmarks, database query
benchmarks, cache performance tests, and report generation.

Requirements: 9.1-9.7
"""

import time
import statistics
import json
from typing import Dict, List, Any, Callable, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import psutil


class TestType(Enum):
    """Types of performance tests"""
    API_ENDPOINT = "api_endpoint"
    DATABASE_QUERY = "database_query"
    CACHE_OPERATION = "cache_operation"
    CONCURRENT_LOAD = "concurrent_load"


class TestStatus(Enum):
    """Status of performance test execution"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class PerformanceMetrics:
    """Performance metrics collected during a test"""
    test_name: str
    test_type: TestType
    iterations: int
    min_time_ms: float
    max_time_ms: float
    mean_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    std_dev_ms: float
    throughput_ops_per_sec: float
    total_duration_sec: float
    timestamp: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        result = asdict(self)
        result['test_type'] = self.test_type.value
        return result


@dataclass
class PerformanceThreshold:
    """Performance thresholds for test validation"""
    max_p95_ms: Optional[float] = None
    max_p99_ms: Optional[float] = None
    max_mean_ms: Optional[float] = None
    min_throughput_ops: Optional[float] = None
    max_error_rate: Optional[float] = None


@dataclass
class TestResult:
    """Result of a performance test"""
    metrics: PerformanceMetrics
    status: TestStatus
    threshold: Optional[PerformanceThreshold]
    violations: List[str]
    system_metrics: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'metrics': self.metrics.to_dict(),
            'status': self.status.value,
            'threshold': asdict(self.threshold) if self.threshold else None,
            'violations': self.violations,
            'system_metrics': self.system_metrics
        }


class PerformanceTestFramework:
    """
    Framework for running performance tests and collecting metrics.
    
    This framework provides utilities for:
    - Running timed operations with multiple iterations
    - Collecting detailed performance metrics
    - Validating against performance thresholds
    - Generating performance reports
    """
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.baseline_metrics: Dict[str, PerformanceMetrics] = {}
    
    def run_benchmark(
        self,
        test_name: str,
        test_type: TestType,
        operation: Callable[[], Any],
        iterations: int = 100,
        warmup_iterations: int = 10,
        threshold: Optional[PerformanceThreshold] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TestResult:
        """
        Run a performance benchmark on an operation.
        
        Args:
            test_name: Name of the test
            test_type: Type of test being run
            operation: Callable to benchmark
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations before measurement
            threshold: Performance thresholds to validate against
            metadata: Additional metadata to include in results
            
        Returns:
            TestResult with metrics and validation status
        """
        # Warmup phase
        for _ in range(warmup_iterations):
            try:
                operation()
            except Exception:
                pass  # Ignore warmup errors
        
        # Measurement phase
        timings: List[float] = []
        errors = 0
        
        start_time = time.time()
        
        for _ in range(iterations):
            try:
                op_start = time.perf_counter()
                operation()
                op_end = time.perf_counter()
                timings.append((op_end - op_start) * 1000)  # Convert to ms
            except Exception:
                errors += 1
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Calculate metrics
        if not timings:
            # All operations failed
            metrics = PerformanceMetrics(
                test_name=test_name,
                test_type=test_type,
                iterations=iterations,
                min_time_ms=0,
                max_time_ms=0,
                mean_time_ms=0,
                median_time_ms=0,
                p95_time_ms=0,
                p99_time_ms=0,
                std_dev_ms=0,
                throughput_ops_per_sec=0,
                total_duration_sec=total_duration,
                timestamp=datetime.utcnow().isoformat(),
                metadata=metadata or {}
            )
            status = TestStatus.FAILED
            violations = [f"All {iterations} operations failed"]
        else:
            sorted_timings = sorted(timings)
            
            metrics = PerformanceMetrics(
                test_name=test_name,
                test_type=test_type,
                iterations=len(timings),
                min_time_ms=min(timings),
                max_time_ms=max(timings),
                mean_time_ms=statistics.mean(timings),
                median_time_ms=statistics.median(timings),
                p95_time_ms=self._percentile(sorted_timings, 95),
                p99_time_ms=self._percentile(sorted_timings, 99),
                std_dev_ms=statistics.stdev(timings) if len(timings) > 1 else 0,
                throughput_ops_per_sec=len(timings) / total_duration,
                total_duration_sec=total_duration,
                timestamp=datetime.utcnow().isoformat(),
                metadata=metadata or {}
            )
            
            # Validate against thresholds
            status, violations = self._validate_thresholds(metrics, threshold, errors, iterations)
        
        # Collect system metrics
        system_metrics = self._collect_system_metrics()
        
        result = TestResult(
            metrics=metrics,
            status=status,
            threshold=threshold,
            violations=violations,
            system_metrics=system_metrics
        )
        
        self.results.append(result)
        return result
    
    def run_concurrent_benchmark(
        self,
        test_name: str,
        operation: Callable[[], Any],
        concurrency_levels: List[int],
        iterations_per_level: int = 50,
        threshold: Optional[PerformanceThreshold] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TestResult]:
        """
        Run a benchmark with different concurrency levels.
        
        Args:
            test_name: Name of the test
            operation: Callable to benchmark
            concurrency_levels: List of concurrency levels to test
            iterations_per_level: Iterations per concurrency level
            threshold: Performance thresholds
            metadata: Additional metadata
            
        Returns:
            List of TestResult for each concurrency level
        """
        import concurrent.futures
        
        results = []
        
        for concurrency in concurrency_levels:
            test_metadata = {
                **(metadata or {}),
                'concurrency': concurrency
            }
            
            def run_concurrent():
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                    futures = [executor.submit(operation) for _ in range(concurrency)]
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            future.result()
                        except Exception:
                            pass
            
            result = self.run_benchmark(
                test_name=f"{test_name}_concurrency_{concurrency}",
                test_type=TestType.CONCURRENT_LOAD,
                operation=run_concurrent,
                iterations=iterations_per_level,
                threshold=threshold,
                metadata=test_metadata
            )
            results.append(result)
        
        return results
    
    def load_baseline(self, baseline_file: str) -> None:
        """Load baseline metrics from a file"""
        try:
            with open(baseline_file, 'r') as f:
                data = json.load(f)
                for test_name, metrics_dict in data.items():
                    # Reconstruct TestType enum
                    metrics_dict['test_type'] = TestType(metrics_dict['test_type'])
                    self.baseline_metrics[test_name] = PerformanceMetrics(**metrics_dict)
        except FileNotFoundError:
            pass  # No baseline exists yet
    
    def save_baseline(self, baseline_file: str) -> None:
        """Save current results as baseline metrics"""
        baseline_data = {}
        for result in self.results:
            baseline_data[result.metrics.test_name] = result.metrics.to_dict()
        
        with open(baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
    
    def compare_to_baseline(self, test_name: str) -> Optional[Dict[str, float]]:
        """
        Compare current test results to baseline.
        
        Returns:
            Dictionary with percentage changes, or None if no baseline exists
        """
        if test_name not in self.baseline_metrics:
            return None
        
        baseline = self.baseline_metrics[test_name]
        current = next((r.metrics for r in self.results if r.metrics.test_name == test_name), None)
        
        if not current:
            return None
        
        def pct_change(old: float, new: float) -> float:
            if old == 0:
                return 0
            return ((new - old) / old) * 100
        
        return {
            'mean_change_pct': pct_change(baseline.mean_time_ms, current.mean_time_ms),
            'p95_change_pct': pct_change(baseline.p95_time_ms, current.p95_time_ms),
            'p99_change_pct': pct_change(baseline.p99_time_ms, current.p99_time_ms),
            'throughput_change_pct': pct_change(baseline.throughput_ops_per_sec, current.throughput_ops_per_sec)
        }
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate a performance test report.
        
        Args:
            output_file: Optional file path to save report
            
        Returns:
            Report as string
        """
        report_lines = [
            "=" * 80,
            "PERFORMANCE TEST REPORT",
            "=" * 80,
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Total Tests: {len(self.results)}",
            ""
        ]
        
        # Summary statistics
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        warnings = sum(1 for r in self.results if r.status == TestStatus.WARNING)
        
        report_lines.extend([
            "SUMMARY",
            "-" * 80,
            f"Passed: {passed}",
            f"Failed: {failed}",
            f"Warnings: {warnings}",
            ""
        ])
        
        # Detailed results
        report_lines.extend([
            "DETAILED RESULTS",
            "-" * 80,
            ""
        ])
        
        for result in self.results:
            m = result.metrics
            report_lines.extend([
                f"Test: {m.test_name}",
                f"Type: {m.test_type.value}",
                f"Status: {result.status.value.upper()}",
                f"Iterations: {m.iterations}",
                f"Mean: {m.mean_time_ms:.2f} ms",
                f"Median: {m.median_time_ms:.2f} ms",
                f"P95: {m.p95_time_ms:.2f} ms",
                f"P99: {m.p99_time_ms:.2f} ms",
                f"Min: {m.min_time_ms:.2f} ms",
                f"Max: {m.max_time_ms:.2f} ms",
                f"Std Dev: {m.std_dev_ms:.2f} ms",
                f"Throughput: {m.throughput_ops_per_sec:.2f} ops/sec",
            ])
            
            # Baseline comparison
            comparison = self.compare_to_baseline(m.test_name)
            if comparison:
                report_lines.extend([
                    "Baseline Comparison:",
                    f"  Mean: {comparison['mean_change_pct']:+.2f}%",
                    f"  P95: {comparison['p95_change_pct']:+.2f}%",
                    f"  P99: {comparison['p99_change_pct']:+.2f}%",
                    f"  Throughput: {comparison['throughput_change_pct']:+.2f}%",
                ])
            
            # Violations
            if result.violations:
                report_lines.append("Violations:")
                for violation in result.violations:
                    report_lines.append(f"  - {violation}")
            
            # System metrics
            report_lines.extend([
                "System Metrics:",
                f"  CPU: {result.system_metrics.get('cpu_percent', 0):.1f}%",
                f"  Memory: {result.system_metrics.get('memory_percent', 0):.1f}%",
                ""
            ])
        
        report_lines.append("=" * 80)
        
        report = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
        
        return report
    
    def export_json(self, output_file: str) -> None:
        """Export results as JSON"""
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            'results': [r.to_dict() for r in self.results]
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    @staticmethod
    def _percentile(sorted_data: List[float], percentile: float) -> float:
        """Calculate percentile from sorted data"""
        if not sorted_data:
            return 0
        
        index = (percentile / 100) * (len(sorted_data) - 1)
        lower = int(index)
        upper = min(lower + 1, len(sorted_data) - 1)
        weight = index - lower
        
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight
    
    @staticmethod
    def _validate_thresholds(
        metrics: PerformanceMetrics,
        threshold: Optional[PerformanceThreshold],
        errors: int,
        total_iterations: int
    ) -> Tuple[TestStatus, List[str]]:
        """Validate metrics against thresholds"""
        if not threshold:
            return TestStatus.PASSED, []
        
        violations = []
        
        if threshold.max_p95_ms and metrics.p95_time_ms > threshold.max_p95_ms:
            violations.append(
                f"P95 latency {metrics.p95_time_ms:.2f}ms exceeds threshold {threshold.max_p95_ms}ms"
            )
        
        if threshold.max_p99_ms and metrics.p99_time_ms > threshold.max_p99_ms:
            violations.append(
                f"P99 latency {metrics.p99_time_ms:.2f}ms exceeds threshold {threshold.max_p99_ms}ms"
            )
        
        if threshold.max_mean_ms and metrics.mean_time_ms > threshold.max_mean_ms:
            violations.append(
                f"Mean latency {metrics.mean_time_ms:.2f}ms exceeds threshold {threshold.max_mean_ms}ms"
            )
        
        if threshold.min_throughput_ops and metrics.throughput_ops_per_sec < threshold.min_throughput_ops:
            violations.append(
                f"Throughput {metrics.throughput_ops_per_sec:.2f} ops/sec below threshold {threshold.min_throughput_ops} ops/sec"
            )
        
        if threshold.max_error_rate:
            error_rate = errors / total_iterations
            if error_rate > threshold.max_error_rate:
                violations.append(
                    f"Error rate {error_rate:.2%} exceeds threshold {threshold.max_error_rate:.2%}"
                )
        
        if violations:
            return TestStatus.FAILED, violations
        
        return TestStatus.PASSED, []
    
    @staticmethod
    def _collect_system_metrics() -> Dict[str, float]:
        """Collect current system metrics"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_io_read_mb': psutil.disk_io_counters().read_bytes / (1024 * 1024) if psutil.disk_io_counters() else 0,
            'disk_io_write_mb': psutil.disk_io_counters().write_bytes / (1024 * 1024) if psutil.disk_io_counters() else 0,
        }
