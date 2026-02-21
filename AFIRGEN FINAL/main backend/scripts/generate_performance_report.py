#!/usr/bin/env python3
"""
Performance Report Generator

This script runs all performance benchmarks and generates comprehensive reports
comparing current results to baseline metrics. It can be used in CI/CD pipelines
to detect performance regressions.

Requirements: 9.5
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.performance_testing import (
    PerformanceTestFramework,
    TestStatus
)


class PerformanceReportGenerator:
    """
    Generates comprehensive performance reports with baseline comparison,
    graphs, and statistics.
    """
    
    def __init__(self, baseline_file: Optional[str] = None):
        self.framework = PerformanceTestFramework()
        self.baseline_file = baseline_file or 'performance_baseline.json'
        
        # Load baseline if exists
        if os.path.exists(self.baseline_file):
            self.framework.load_baseline(self.baseline_file)
            print(f"Loaded baseline from {self.baseline_file}")
        else:
            print(f"No baseline found at {self.baseline_file}")
    
    def run_all_benchmarks(self) -> bool:
        """
        Run all performance benchmarks.
        
        Returns:
            True if all tests passed, False otherwise
        """
        print("=" * 80)
        print("RUNNING PERFORMANCE BENCHMARKS")
        print("=" * 80)
        print()
        
        # Run pytest with performance markers
        import pytest
        
        # Run API benchmarks
        print("Running API endpoint benchmarks...")
        api_result = pytest.main([
            '-v',
            '-m', 'performance',
            'tests/performance/test_api_benchmarks.py',
            '--tb=short'
        ])
        
        # Run database benchmarks
        print("\nRunning database query benchmarks...")
        db_result = pytest.main([
            '-v',
            '-m', 'performance',
            'tests/performance/test_database_benchmarks.py',
            '--tb=short'
        ])
        
        # Run cache benchmarks
        print("\nRunning cache performance benchmarks...")
        cache_result = pytest.main([
            '-v',
            '-m', 'performance',
            'tests/performance/test_cache_benchmarks.py',
            '--tb=short'
        ])
        
        # Check if all tests passed
        all_passed = all(result == 0 for result in [api_result, db_result, cache_result])
        
        return all_passed
    
    def generate_summary_report(self, output_file: str = 'performance_summary.txt') -> str:
        """
        Generate summary performance report.
        
        Args:
            output_file: Output file path
            
        Returns:
            Report content as string
        """
        lines = [
            "=" * 80,
            "PERFORMANCE BENCHMARK SUMMARY",
            "=" * 80,
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Total Tests: {len(self.framework.results)}",
            ""
        ]
        
        # Overall statistics
        passed = sum(1 for r in self.framework.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.framework.results if r.status == TestStatus.FAILED)
        warnings = sum(1 for r in self.framework.results if r.status == TestStatus.WARNING)
        
        lines.extend([
            "OVERALL STATUS",
            "-" * 80,
            f"✓ Passed: {passed}",
            f"✗ Failed: {failed}",
            f"⚠ Warnings: {warnings}",
            f"Success Rate: {(passed / len(self.framework.results) * 100):.1f}%" if self.framework.results else "N/A",
            ""
        ])
        
        # Group results by test type
        api_tests = [r for r in self.framework.results if 'api' in r.metrics.test_name.lower()]
        db_tests = [r for r in self.framework.results if 'query' in r.metrics.test_name.lower() or 'database' in r.metrics.test_name.lower()]
        cache_tests = [r for r in self.framework.results if 'cache' in r.metrics.test_name.lower()]
        
        # API Endpoint Summary
        if api_tests:
            lines.extend([
                "API ENDPOINT PERFORMANCE",
                "-" * 80,
            ])
            for result in api_tests:
                m = result.metrics
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                lines.append(
                    f"{status_icon} {m.test_name}: "
                    f"Mean={m.mean_time_ms:.2f}ms, "
                    f"P95={m.p95_time_ms:.2f}ms, "
                    f"P99={m.p99_time_ms:.2f}ms"
                )
            lines.append("")
        
        # Database Query Summary
        if db_tests:
            lines.extend([
                "DATABASE QUERY PERFORMANCE",
                "-" * 80,
            ])
            for result in db_tests:
                m = result.metrics
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                lines.append(
                    f"{status_icon} {m.test_name}: "
                    f"Mean={m.mean_time_ms:.2f}ms, "
                    f"P95={m.p95_time_ms:.2f}ms"
                )
            lines.append("")
        
        # Cache Performance Summary
        if cache_tests:
            lines.extend([
                "CACHE PERFORMANCE",
                "-" * 80,
            ])
            for result in cache_tests:
                m = result.metrics
                status_icon = "✓" if result.status == TestStatus.PASSED else "✗"
                lines.append(
                    f"{status_icon} {m.test_name}: "
                    f"Mean={m.mean_time_ms:.2f}ms, "
                    f"Throughput={m.throughput_ops_per_sec:.0f} ops/sec"
                )
            lines.append("")
        
        # Baseline Comparison
        if self.framework.baseline_metrics:
            lines.extend([
                "BASELINE COMPARISON",
                "-" * 80,
            ])
            
            improvements = []
            regressions = []
            
            for result in self.framework.results:
                comparison = self.framework.compare_to_baseline(result.metrics.test_name)
                if comparison:
                    mean_change = comparison['mean_change_pct']
                    p95_change = comparison['p95_change_pct']
                    
                    if mean_change < -5:  # >5% improvement
                        improvements.append((result.metrics.test_name, mean_change, p95_change))
                    elif mean_change > 5:  # >5% regression
                        regressions.append((result.metrics.test_name, mean_change, p95_change))
            
            if improvements:
                lines.append("Improvements:")
                for name, mean_change, p95_change in improvements:
                    lines.append(f"  ✓ {name}: Mean {mean_change:+.1f}%, P95 {p95_change:+.1f}%")
            
            if regressions:
                lines.append("Regressions:")
                for name, mean_change, p95_change in regressions:
                    lines.append(f"  ✗ {name}: Mean {mean_change:+.1f}%, P95 {p95_change:+.1f}%")
            
            if not improvements and not regressions:
                lines.append("No significant changes from baseline")
            
            lines.append("")
        
        # Threshold Violations
        violations = [r for r in self.framework.results if r.violations]
        if violations:
            lines.extend([
                "THRESHOLD VIOLATIONS",
                "-" * 80,
            ])
            for result in violations:
                lines.append(f"✗ {result.metrics.test_name}:")
                for violation in result.violations:
                    lines.append(f"  - {violation}")
            lines.append("")
        
        # System Resource Usage
        if self.framework.results:
            avg_cpu = sum(r.system_metrics.get('cpu_percent', 0) for r in self.framework.results) / len(self.framework.results)
            avg_memory = sum(r.system_metrics.get('memory_percent', 0) for r in self.framework.results) / len(self.framework.results)
            
            lines.extend([
                "SYSTEM RESOURCE USAGE",
                "-" * 80,
                f"Average CPU: {avg_cpu:.1f}%",
                f"Average Memory: {avg_memory:.1f}%",
                ""
            ])
        
        lines.append("=" * 80)
        
        report = "\n".join(lines)
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write(report)
        
        print(f"\nSummary report saved to {output_file}")
        
        return report
    
    def generate_detailed_report(self, output_file: str = 'performance_detailed.txt') -> str:
        """
        Generate detailed performance report with all metrics.
        
        Args:
            output_file: Output file path
            
        Returns:
            Report content as string
        """
        report = self.framework.generate_report(output_file)
        print(f"Detailed report saved to {output_file}")
        return report
    
    def export_json_results(self, output_file: str = 'performance_results.json') -> None:
        """
        Export results as JSON for CI/CD integration.
        
        Args:
            output_file: Output file path
        """
        self.framework.export_json(output_file)
        print(f"JSON results saved to {output_file}")
    
    def save_as_baseline(self) -> None:
        """Save current results as new baseline"""
        self.framework.save_baseline(self.baseline_file)
        print(f"Baseline saved to {self.baseline_file}")
    
    def check_sla_compliance(self) -> bool:
        """
        Check if all tests meet SLA requirements.
        
        Returns:
            True if all tests passed, False otherwise
        """
        failed_tests = [r for r in self.framework.results if r.status == TestStatus.FAILED]
        
        if failed_tests:
            print("\n" + "=" * 80)
            print("SLA COMPLIANCE CHECK: FAILED")
            print("=" * 80)
            print(f"\n{len(failed_tests)} test(s) failed to meet SLA requirements:\n")
            
            for result in failed_tests:
                print(f"✗ {result.metrics.test_name}")
                for violation in result.violations:
                    print(f"  - {violation}")
                print()
            
            return False
        else:
            print("\n" + "=" * 80)
            print("SLA COMPLIANCE CHECK: PASSED")
            print("=" * 80)
            print(f"\nAll {len(self.framework.results)} tests met SLA requirements ✓\n")
            return True


def main():
    """Main entry point for performance report generator"""
    parser = argparse.ArgumentParser(
        description='Generate performance benchmark reports'
    )
    parser.add_argument(
        '--baseline',
        type=str,
        default='performance_baseline.json',
        help='Path to baseline metrics file'
    )
    parser.add_argument(
        '--save-baseline',
        action='store_true',
        help='Save current results as new baseline'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help='Output directory for reports'
    )
    parser.add_argument(
        '--run-tests',
        action='store_true',
        help='Run all performance tests before generating report'
    )
    parser.add_argument(
        '--fail-on-regression',
        action='store_true',
        help='Exit with error code if any tests fail'
    )
    
    args = parser.parse_args()
    
    # Create output directory if needed
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize generator
    generator = PerformanceReportGenerator(baseline_file=args.baseline)
    
    # Run tests if requested
    if args.run_tests:
        tests_passed = generator.run_all_benchmarks()
        if not tests_passed and args.fail_on_regression:
            print("\n✗ Some performance tests failed")
            sys.exit(1)
    
    # Generate reports
    print("\nGenerating performance reports...")
    
    summary_file = os.path.join(args.output_dir, 'performance_summary.txt')
    detailed_file = os.path.join(args.output_dir, 'performance_detailed.txt')
    json_file = os.path.join(args.output_dir, 'performance_results.json')
    
    summary = generator.generate_summary_report(summary_file)
    generator.generate_detailed_report(detailed_file)
    generator.export_json_results(json_file)
    
    # Print summary to console
    print("\n" + summary)
    
    # Check SLA compliance
    sla_passed = generator.check_sla_compliance()
    
    # Save baseline if requested
    if args.save_baseline:
        baseline_file = os.path.join(args.output_dir, args.baseline)
        generator.framework.save_baseline(baseline_file)
        print(f"\n✓ Baseline saved to {baseline_file}")
    
    # Exit with appropriate code
    if args.fail_on_regression and not sla_passed:
        sys.exit(1)
    
    print("\n✓ Performance report generation complete")
    sys.exit(0)


if __name__ == '__main__':
    main()
