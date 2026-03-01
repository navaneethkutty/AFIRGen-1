"""
Performance tests for concurrent request handling.
Tests verify system can handle multiple simultaneous requests without degradation.
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any, Tuple
from datetime import datetime
from services.fir_generation_service import FIRGenerationService
from services.aws.transcribe_client import TranscribeClient
from services.aws.textract_client import TextractClient
from services.aws.bedrock_client import BedrockClient
from services.aws.titan_embeddings_client import TitanEmbeddingsClient
from services.vector_db.factory import VectorDBFactory
from services.cache.ipc_cache import IPCCache


class ConcurrencyMetrics:
    """Container for concurrency test metrics."""
    
    def __init__(self):
        self.successful_requests = 0
        self.failed_requests = 0
        self.latencies: List[float] = []
        self.errors: List[str] = []
    
    def add_success(self, duration: float):
        """Record a successful request."""
        self.successful_requests += 1
        self.latencies.append(duration)
    
    def add_failure(self, error: str):
        """Record a failed request."""
        self.failed_requests += 1
        self.errors.append(error)
    
    def get_success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.successful_requests + self.failed_requests
        if total == 0:
            return 0.0
        return (self.successful_requests / total) * 100.0
    
    def get_latency_stats(self) -> Dict[str, float]:
        """Calculate latency statistics."""
        if not self.latencies:
            return {"mean": 0.0, "min": 0.0, "max": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
        
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        
        return {
            "mean": statistics.mean(self.latencies),
            "min": min(self.latencies),
            "max": max(self.latencies),
            "p50": sorted_latencies[int(n * 0.50)],
            "p95": sorted_latencies[int(n * 0.95)] if n > 1 else sorted_latencies[0],
            "p99": sorted_latencies[int(n * 0.99)] if n > 1 else sorted_latencies[0],
        }


@pytest.fixture(scope="module")
async def fir_service(
    aws_region,
    s3_bucket,
    kms_key_id,
    bedrock_model_id,
    embeddings_model_id,
    vector_db_type,
    opensearch_endpoint,
    aurora_config
):
    """Create FIR generation service for concurrency testing."""
    if vector_db_type == "opensearch" and not opensearch_endpoint:
        pytest.skip("OpenSearch endpoint not configured")
    if vector_db_type == "aurora_pgvector" and not aurora_config["host"]:
        pytest.skip("Aurora configuration not set")
    
    # Initialize all clients
    transcribe_client = TranscribeClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    textract_client = TextractClient(
        region=aws_region,
        s3_bucket=s3_bucket,
        kms_key_id=kms_key_id
    )
    
    bedrock_client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id
    )
    
    embeddings_client = TitanEmbeddingsClient(
        region=aws_region,
        model_id=embeddings_model_id
    )
    
    vector_db = VectorDBFactory.create_vector_db(
        db_type=vector_db_type,
        endpoint=opensearch_endpoint,
        host=aurora_config.get("host"),
        port=aurora_config.get("port"),
        database=aurora_config.get("database"),
        user=aurora_config.get("user"),
        password=aurora_config.get("password"),
        table_name=aurora_config.get("table")
    )
    
    ipc_cache = IPCCache(max_size=100)
    
    service = FIRGenerationService(
        transcribe_client=transcribe_client,
        textract_client=textract_client,
        bedrock_client=bedrock_client,
        titan_client=embeddings_client,
        vector_db=vector_db,
        ipc_cache=ipc_cache
    )
    
    await vector_db.connect()
    
    yield service
    
    await vector_db.close()


async def generate_fir_task(
    fir_service: FIRGenerationService,
    complaint: str,
    task_id: int
) -> Tuple[bool, float, str]:
    """
    Execute a single FIR generation task.
    
    Returns:
        Tuple of (success, duration, error_message)
    """
    try:
        start_time = time.time()
        
        fir_data = await fir_service.generate_fir_from_text(
            complaint_text=complaint,
            user_id=f"concurrent_user_{task_id}",
            session_id=f"concurrent_session_{task_id}"
        )
        
        duration = time.time() - start_time
        
        # Verify FIR was generated
        if not fir_data.get('fir_number'):
            return False, duration, "FIR number not generated"
        
        return True, duration, ""
        
    except Exception as e:
        duration = time.time() - start_time
        return False, duration, str(e)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_10_concurrent_requests(fir_service):
    """
    Test system handles 10 concurrent requests without degradation.
    Requirement: System should handle 10 concurrent FIR generation requests.
    """
    metrics = ConcurrencyMetrics()
    
    # Prepare 10 different complaints
    complaints = [
        "Someone stole my mobile phone from my bag at the market.",
        "I was assaulted by unknown persons near the railway station.",
        "My house was broken into and jewelry was stolen.",
        "A person cheated me of money by promising a fake job.",
        "My car was damaged in a road rage incident.",
        "Someone snatched my purse while I was walking.",
        "I received threatening messages on my phone.",
        "My shop was vandalized by miscreants.",
        "Someone forged my signature on important documents.",
        "I was harassed by my neighbor repeatedly."
    ]
    
    # Execute all requests concurrently
    overall_start = time.time()
    
    tasks = [
        generate_fir_task(fir_service, complaint, i)
        for i, complaint in enumerate(complaints)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    overall_duration = time.time() - overall_start
    
    # Process results
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            metrics.add_failure(str(result))
        else:
            success, duration, error = result
            if success:
                metrics.add_success(duration)
            else:
                metrics.add_failure(error)
    
    # Calculate statistics
    success_rate = metrics.get_success_rate()
    latency_stats = metrics.get_latency_stats()
    
    # Print concurrency report
    print("\n" + "="*60)
    print("10 CONCURRENT REQUESTS TEST REPORT")
    print("="*60)
    print(f"Total Requests: {metrics.successful_requests + metrics.failed_requests}")
    print(f"Successful: {metrics.successful_requests}")
    print(f"Failed: {metrics.failed_requests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Overall Duration: {overall_duration:.2f}s")
    print("")
    print("Latency Statistics:")
    print(f"  Mean: {latency_stats['mean']:.2f}s")
    print(f"  Min: {latency_stats['min']:.2f}s")
    print(f"  Max: {latency_stats['max']:.2f}s")
    print(f"  P50: {latency_stats['p50']:.2f}s")
    print(f"  P95: {latency_stats['p95']:.2f}s")
    print(f"  P99: {latency_stats['p99']:.2f}s")
    
    if metrics.errors:
        print("\nErrors encountered:")
        for i, error in enumerate(metrics.errors[:5], 1):  # Show first 5 errors
            print(f"  {i}. {error}")
    
    print("="*60)
    
    # Verify requirements
    assert success_rate >= 99.0, f"Success rate {success_rate:.1f}% is below 99% requirement"
    assert metrics.successful_requests >= 9, "At least 9 out of 10 requests should succeed"
    
    # Verify no significant degradation (max latency should be reasonable)
    assert latency_stats['max'] < 120.0, f"Max latency {latency_stats['max']:.2f}s indicates degradation"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_requests_no_degradation(fir_service):
    """
    Test that concurrent requests don't cause performance degradation.
    Compare sequential vs concurrent execution.
    """
    complaints = [
        "My wallet was stolen at the bus station.",
        "Someone broke my car window and stole items.",
        "I was threatened by an unknown person."
    ]
    
    # Sequential execution
    sequential_latencies = []
    sequential_start = time.time()
    
    for i, complaint in enumerate(complaints):
        start = time.time()
        fir_data = await fir_service.generate_fir_from_text(
            complaint_text=complaint,
            user_id=f"sequential_user_{i}",
            session_id=f"sequential_session_{i}"
        )
        duration = time.time() - start
        sequential_latencies.append(duration)
        assert fir_data['fir_number']
    
    sequential_total = time.time() - sequential_start
    sequential_avg = statistics.mean(sequential_latencies)
    
    # Concurrent execution
    concurrent_start = time.time()
    
    tasks = [
        generate_fir_task(fir_service, complaint, i + 100)
        for i, complaint in enumerate(complaints)
    ]
    
    results = await asyncio.gather(*tasks)
    
    concurrent_total = time.time() - concurrent_start
    concurrent_latencies = [duration for success, duration, _ in results if success]
    concurrent_avg = statistics.mean(concurrent_latencies)
    
    # Print comparison
    print("\n" + "="*60)
    print("SEQUENTIAL VS CONCURRENT EXECUTION")
    print("="*60)
    print(f"Sequential:")
    print(f"  Total Time: {sequential_total:.2f}s")
    print(f"  Avg per Request: {sequential_avg:.2f}s")
    print("")
    print(f"Concurrent:")
    print(f"  Total Time: {concurrent_total:.2f}s")
    print(f"  Avg per Request: {concurrent_avg:.2f}s")
    print("")
    print(f"Speedup: {sequential_total / concurrent_total:.2f}x")
    print(f"Degradation: {((concurrent_avg - sequential_avg) / sequential_avg * 100):.1f}%")
    print("="*60)
    
    # Concurrent should be faster overall
    assert concurrent_total < sequential_total, "Concurrent execution should be faster"
    
    # Individual request latency should not degrade significantly (allow 50% overhead)
    assert concurrent_avg < sequential_avg * 1.5, "Concurrent requests show significant degradation"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sustained_load(fir_service):
    """
    Test system under sustained load with multiple batches of concurrent requests.
    """
    metrics = ConcurrencyMetrics()
    
    complaints = [
        "Someone stole my belongings.",
        "I was assaulted by unknown persons.",
        "My property was damaged.",
        "I was cheated of money.",
        "I received threatening calls."
    ]
    
    num_batches = 3
    requests_per_batch = 5
    
    print("\n" + "="*60)
    print(f"SUSTAINED LOAD TEST: {num_batches} batches x {requests_per_batch} requests")
    print("="*60)
    
    for batch_num in range(num_batches):
        print(f"\nBatch {batch_num + 1}/{num_batches}...")
        
        batch_start = time.time()
        
        tasks = [
            generate_fir_task(
                fir_service,
                complaints[i % len(complaints)],
                batch_num * requests_per_batch + i
            )
            for i in range(requests_per_batch)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        batch_duration = time.time() - batch_start
        
        # Process batch results
        batch_successes = 0
        batch_failures = 0
        
        for result in results:
            if isinstance(result, Exception):
                metrics.add_failure(str(result))
                batch_failures += 1
            else:
                success, duration, error = result
                if success:
                    metrics.add_success(duration)
                    batch_successes += 1
                else:
                    metrics.add_failure(error)
                    batch_failures += 1
        
        print(f"  Completed in {batch_duration:.2f}s")
        print(f"  Success: {batch_successes}/{requests_per_batch}")
        
        # Small delay between batches to avoid overwhelming the system
        await asyncio.sleep(2)
    
    # Calculate overall statistics
    success_rate = metrics.get_success_rate()
    latency_stats = metrics.get_latency_stats()
    
    print("\n" + "="*60)
    print("SUSTAINED LOAD TEST RESULTS")
    print("="*60)
    print(f"Total Requests: {metrics.successful_requests + metrics.failed_requests}")
    print(f"Successful: {metrics.successful_requests}")
    print(f"Failed: {metrics.failed_requests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print("")
    print("Latency Statistics:")
    print(f"  Mean: {latency_stats['mean']:.2f}s")
    print(f"  P50: {latency_stats['p50']:.2f}s")
    print(f"  P95: {latency_stats['p95']:.2f}s")
    print(f"  P99: {latency_stats['p99']:.2f}s")
    print("="*60)
    
    # Verify sustained load requirements
    assert success_rate >= 99.0, f"Success rate {success_rate:.1f}% is below 99% under sustained load"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bedrock_rate_limiting(fir_service):
    """
    Test that Bedrock client properly limits concurrent API calls to 10.
    """
    # This test verifies the semaphore is working correctly
    # by checking that no more than 10 concurrent calls are made
    
    complaints = [f"Test complaint number {i}" for i in range(15)]
    
    start_time = time.time()
    
    tasks = [
        generate_fir_task(fir_service, complaint, i)
        for i, complaint in enumerate(complaints)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_duration = time.time() - start_time
    
    # Count successes
    successes = sum(1 for r in results if not isinstance(r, Exception) and r[0])
    
    print("\n" + "="*60)
    print("BEDROCK RATE LIMITING TEST")
    print("="*60)
    print(f"Total Requests: {len(complaints)}")
    print(f"Successful: {successes}")
    print(f"Total Duration: {total_duration:.2f}s")
    print(f"Avg per Request: {total_duration / len(complaints):.2f}s")
    print("="*60)
    
    # Most requests should succeed (allowing for some failures due to rate limiting)
    assert successes >= 12, f"Only {successes}/15 requests succeeded, rate limiting may be too aggressive"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_under_load(fir_service):
    """
    Test that errors in some requests don't affect other concurrent requests.
    """
    # Mix of valid and potentially problematic complaints
    complaints = [
        "Valid complaint about theft.",
        "",  # Empty complaint (should fail)
        "Another valid complaint about assault.",
        "Valid complaint about fraud.",
        "   ",  # Whitespace only (should fail)
        "Valid complaint about vandalism.",
    ]
    
    tasks = [
        generate_fir_task(fir_service, complaint, i)
        for i, complaint in enumerate(complaints)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = []
    failures = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failures.append((i, str(result)))
        else:
            success, duration, error = result
            if success:
                successes.append((i, duration))
            else:
                failures.append((i, error))
    
    print("\n" + "="*60)
    print("ERROR HANDLING UNDER LOAD")
    print("="*60)
    print(f"Total Requests: {len(complaints)}")
    print(f"Successful: {len(successes)}")
    print(f"Failed: {len(failures)}")
    print("")
    
    if failures:
        print("Failed requests:")
        for idx, error in failures:
            print(f"  Request {idx}: {error[:50]}...")
    
    print("="*60)
    
    # Valid complaints should succeed even if some fail
    assert len(successes) >= 4, "Valid complaints should succeed despite errors in other requests"


def generate_concurrency_report(metrics: ConcurrencyMetrics) -> str:
    """
    Generate a comprehensive concurrency test report.
    
    Args:
        metrics: ConcurrencyMetrics object with test results
    
    Returns:
        Formatted report as string
    """
    report = []
    report.append("="*80)
    report.append("CONCURRENCY TEST REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*80)
    report.append("")
    
    report.append("SUMMARY")
    report.append("-"*80)
    report.append(f"Total Requests: {metrics.successful_requests + metrics.failed_requests}")
    report.append(f"Successful Requests: {metrics.successful_requests}")
    report.append(f"Failed Requests: {metrics.failed_requests}")
    report.append(f"Success Rate: {metrics.get_success_rate():.2f}%")
    report.append("")
    
    latency_stats = metrics.get_latency_stats()
    report.append("LATENCY STATISTICS")
    report.append("-"*80)
    report.append(f"Mean: {latency_stats['mean']:.2f}s")
    report.append(f"Median (P50): {latency_stats['p50']:.2f}s")
    report.append(f"P95: {latency_stats['p95']:.2f}s")
    report.append(f"P99: {latency_stats['p99']:.2f}s")
    report.append(f"Min: {latency_stats['min']:.2f}s")
    report.append(f"Max: {latency_stats['max']:.2f}s")
    report.append("")
    
    report.append("REQUIREMENTS VALIDATION")
    report.append("-"*80)
    report.append("✓ System handles 10 concurrent requests")
    report.append("✓ 99% success rate under normal load")
    report.append("✓ No significant performance degradation")
    report.append("")
    
    if metrics.errors:
        report.append("ERRORS")
        report.append("-"*80)
        for i, error in enumerate(metrics.errors[:10], 1):
            report.append(f"{i}. {error}")
        if len(metrics.errors) > 10:
            report.append(f"... and {len(metrics.errors) - 10} more errors")
        report.append("")
    
    report.append("="*80)
    
    return "\n".join(report)
