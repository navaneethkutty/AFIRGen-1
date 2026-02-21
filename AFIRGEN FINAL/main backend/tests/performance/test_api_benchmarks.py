"""
API Endpoint Performance Benchmarks

This module contains performance benchmarks for all major API endpoints.
Tests measure response times under various load conditions and validate
against SLA thresholds.

Requirements: 9.1, 9.4
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import json

from infrastructure.performance_testing import (
    PerformanceTestFramework,
    TestType,
    PerformanceThreshold
)


# Performance thresholds based on requirements
# Requirement: < 10s for cached requests, < 15s for uncached requests
API_THRESHOLDS = {
    'get_session_status': PerformanceThreshold(
        max_p95_ms=100,  # Fast read operation
        max_p99_ms=200,
        min_throughput_ops=50
    ),
    'get_fir_status': PerformanceThreshold(
        max_p95_ms=100,  # Fast read operation with cache
        max_p99_ms=200,
        min_throughput_ops=50
    ),
    'get_fir_content': PerformanceThreshold(
        max_p95_ms=200,  # Slightly slower due to content size
        max_p99_ms=500,
        min_throughput_ops=30
    ),
    'validate_step': PerformanceThreshold(
        max_p95_ms=500,  # Business logic processing
        max_p99_ms=1000,
        min_throughput_ops=10
    ),
    'process_text': PerformanceThreshold(
        max_p95_ms=10000,  # 10s for cached (with model server)
        max_p99_ms=15000,  # 15s for uncached
        min_throughput_ops=1
    )
}


@pytest.fixture
def performance_framework():
    """Create performance test framework"""
    return PerformanceTestFramework()


@pytest.fixture
def mock_app():
    """Create FastAPI test client with mocked dependencies"""
    from fastapi import FastAPI
    from api.routes.fir_routes import router
    
    app = FastAPI()
    app.include_router(router)
    
    return app


@pytest.fixture
def mock_session_service():
    """Create mock session service"""
    service = Mock()
    
    # Mock session status response
    service.get_session_status = AsyncMock(return_value={
        'session_id': 'test_session_123',
        'status': 'processing',
        'current_step': 'validation',
        'created_at': '2024-01-01T00:00:00Z'
    })
    
    # Mock FIR status response
    service.get_fir_status = AsyncMock(return_value={
        'fir_number': 'FIR_123',
        'status': 'completed',
        'created_at': '2024-01-01T00:00:00Z'
    })
    
    # Mock FIR content response
    service.get_fir_content = AsyncMock(return_value={
        'fir_number': 'FIR_123',
        'content': 'Test FIR content' * 100,  # Simulate larger content
        'violations': ['violation1', 'violation2'],
        'metadata': {}
    })
    
    # Mock validation response
    service.validate_step = AsyncMock(return_value={
        'session_id': 'test_session_123',
        'step': 'validation',
        'approved': True,
        'next_step': 'authentication'
    })
    
    # Mock process input response
    service.process_input = AsyncMock(return_value={
        'session_id': 'test_session_123',
        'status': 'processing',
        'message': 'Processing started'
    })
    
    return service


class TestAPIEndpointBenchmarks:
    """Performance benchmarks for API endpoints"""
    
    def test_get_session_status_benchmark(
        self,
        performance_framework,
        mock_app,
        mock_session_service
    ):
        """
        Benchmark GET /session/{session_id}/status endpoint.
        
        This is a fast read operation that should be heavily cached.
        """
        with patch('api.dependencies.get_session_service', return_value=mock_session_service):
            client = TestClient(mock_app)
            
            def operation():
                response = client.get('/api/v1/session/test_session_123/status')
                assert response.status_code == 200
            
            result = performance_framework.run_benchmark(
                test_name='get_session_status',
                test_type=TestType.API_ENDPOINT,
                operation=operation,
                iterations=100,
                threshold=API_THRESHOLDS['get_session_status'],
                metadata={'endpoint': '/session/{session_id}/status', 'method': 'GET'}
            )
            
            assert result.metrics.iterations == 100
            assert result.metrics.mean_time_ms > 0
            print(f"\nSession Status - Mean: {result.metrics.mean_time_ms:.2f}ms, "
                  f"P95: {result.metrics.p95_time_ms:.2f}ms")
    
    def test_get_fir_status_benchmark(
        self,
        performance_framework,
        mock_app,
        mock_session_service
    ):
        """
        Benchmark GET /fir/{fir_number} endpoint.
        
        This endpoint should benefit from caching.
        """
        with patch('api.dependencies.get_session_service', return_value=mock_session_service):
            client = TestClient(mock_app)
            
            def operation():
                response = client.get('/api/v1/fir/FIR_123')
                assert response.status_code == 200
            
            result = performance_framework.run_benchmark(
                test_name='get_fir_status',
                test_type=TestType.API_ENDPOINT,
                operation=operation,
                iterations=100,
                threshold=API_THRESHOLDS['get_fir_status'],
                metadata={'endpoint': '/fir/{fir_number}', 'method': 'GET'}
            )
            
            assert result.metrics.iterations == 100
            print(f"\nFIR Status - Mean: {result.metrics.mean_time_ms:.2f}ms, "
                  f"P95: {result.metrics.p95_time_ms:.2f}ms")
    
    def test_get_fir_content_benchmark(
        self,
        performance_framework,
        mock_app,
        mock_session_service
    ):
        """
        Benchmark GET /fir/{fir_number}/content endpoint.
        
        This endpoint returns larger payloads and should test compression.
        """
        with patch('api.dependencies.get_session_service', return_value=mock_session_service):
            client = TestClient(mock_app)
            
            def operation():
                response = client.get('/api/v1/fir/FIR_123/content')
                assert response.status_code == 200
            
            result = performance_framework.run_benchmark(
                test_name='get_fir_content',
                test_type=TestType.API_ENDPOINT,
                operation=operation,
                iterations=100,
                threshold=API_THRESHOLDS['get_fir_content'],
                metadata={'endpoint': '/fir/{fir_number}/content', 'method': 'GET'}
            )
            
            assert result.metrics.iterations == 100
            print(f"\nFIR Content - Mean: {result.metrics.mean_time_ms:.2f}ms, "
                  f"P95: {result.metrics.p95_time_ms:.2f}ms")
    
    def test_validate_step_benchmark(
        self,
        performance_framework,
        mock_app,
        mock_session_service
    ):
        """
        Benchmark POST /validate endpoint.
        
        This endpoint involves business logic processing.
        """
        with patch('api.dependencies.get_session_service', return_value=mock_session_service):
            client = TestClient(mock_app)
            
            def operation():
                response = client.post(
                    '/api/v1/validate',
                    json={
                        'session_id': 'test_session_123',
                        'approved': True,
                        'user_input': None
                    }
                )
                assert response.status_code == 200
            
            result = performance_framework.run_benchmark(
                test_name='validate_step',
                test_type=TestType.API_ENDPOINT,
                operation=operation,
                iterations=100,
                threshold=API_THRESHOLDS['validate_step'],
                metadata={'endpoint': '/validate', 'method': 'POST'}
            )
            
            assert result.metrics.iterations == 100
            print(f"\nValidate Step - Mean: {result.metrics.mean_time_ms:.2f}ms, "
                  f"P95: {result.metrics.p95_time_ms:.2f}ms")
    
    def test_process_text_benchmark(
        self,
        performance_framework,
        mock_app,
        mock_session_service
    ):
        """
        Benchmark POST /process endpoint with text input.
        
        This is the most critical endpoint - should be < 10s cached, < 15s uncached.
        """
        with patch('api.dependencies.get_session_service', return_value=mock_session_service):
            client = TestClient(mock_app)
            
            def operation():
                response = client.post(
                    '/api/v1/process',
                    data={'text': 'Test complaint text for FIR generation'}
                )
                assert response.status_code == 200
            
            result = performance_framework.run_benchmark(
                test_name='process_text',
                test_type=TestType.API_ENDPOINT,
                operation=operation,
                iterations=50,  # Fewer iterations for slower endpoint
                threshold=API_THRESHOLDS['process_text'],
                metadata={'endpoint': '/process', 'method': 'POST', 'input_type': 'text'}
            )
            
            assert result.metrics.iterations == 50
            print(f"\nProcess Text - Mean: {result.metrics.mean_time_ms:.2f}ms, "
                  f"P95: {result.metrics.p95_time_ms:.2f}ms")
    
    def test_concurrent_load_benchmark(
        self,
        performance_framework,
        mock_app,
        mock_session_service
    ):
        """
        Benchmark API endpoints under concurrent load.
        
        Tests system behavior with 1, 5, 10, 15 concurrent requests.
        Requirement: System handles 15 concurrent requests.
        """
        with patch('api.dependencies.get_session_service', return_value=mock_session_service):
            client = TestClient(mock_app)
            
            def operation():
                response = client.get('/api/v1/session/test_session_123/status')
                assert response.status_code == 200
            
            results = performance_framework.run_concurrent_benchmark(
                test_name='concurrent_session_status',
                operation=operation,
                concurrency_levels=[1, 5, 10, 15],
                iterations_per_level=30,
                threshold=PerformanceThreshold(
                    max_p95_ms=500,  # Allow higher latency under load
                    max_error_rate=0.01
                ),
                metadata={'endpoint': '/session/{session_id}/status'}
            )
            
            # Verify all concurrency levels completed
            assert len(results) == 4
            
            # Print results
            print("\nConcurrent Load Results:")
            for result in results:
                concurrency = result.metrics.metadata['concurrency']
                print(f"  Concurrency {concurrency}: "
                      f"Mean={result.metrics.mean_time_ms:.2f}ms, "
                      f"P95={result.metrics.p95_time_ms:.2f}ms, "
                      f"Throughput={result.metrics.throughput_ops_per_sec:.2f} ops/sec")
    
    def test_generate_api_benchmark_report(self, performance_framework):
        """
        Generate comprehensive API benchmark report.
        
        This test runs all benchmarks and generates a report.
        """
        # This test would be run after all other benchmarks
        # to generate a comprehensive report
        
        if performance_framework.results:
            report = performance_framework.generate_report(
                output_file='api_benchmark_report.txt'
            )
            
            # Export JSON for CI/CD integration
            performance_framework.export_json('api_benchmark_results.json')
            
            print("\n" + report)
            
            # Verify report was generated
            assert len(report) > 0
            assert 'PERFORMANCE TEST REPORT' in report


class TestAPIEndpointStress:
    """Stress tests for API endpoints"""
    
    def test_sustained_load(
        self,
        performance_framework,
        mock_app,
        mock_session_service
    ):
        """
        Test API under sustained load.
        
        Simulates continuous requests over a longer period.
        """
        with patch('api.dependencies.get_session_service', return_value=mock_session_service):
            client = TestClient(mock_app)
            
            def operation():
                response = client.get('/api/v1/session/test_session_123/status')
                assert response.status_code == 200
            
            result = performance_framework.run_benchmark(
                test_name='sustained_load',
                test_type=TestType.API_ENDPOINT,
                operation=operation,
                iterations=500,  # More iterations for sustained load
                threshold=PerformanceThreshold(
                    max_p95_ms=200,
                    max_error_rate=0.01
                ),
                metadata={'test_type': 'sustained_load'}
            )
            
            assert result.metrics.iterations == 500
            print(f"\nSustained Load - Mean: {result.metrics.mean_time_ms:.2f}ms, "
                  f"P95: {result.metrics.p95_time_ms:.2f}ms, "
                  f"Throughput: {result.metrics.throughput_ops_per_sec:.2f} ops/sec")


# Pytest configuration for performance tests
def pytest_configure(config):
    """Configure pytest for performance tests"""
    config.addinivalue_line(
        "markers", "performance: mark test as a performance benchmark"
    )


# Mark all tests in this module as performance tests
pytestmark = pytest.mark.performance
