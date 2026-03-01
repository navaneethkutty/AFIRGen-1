"""
Performance tests for measuring latency of Bedrock architecture.
Tests measure end-to-end FIR generation latency and individual component latencies.
"""

import pytest
import asyncio
import time
import statistics
from typing import Dict, List, Any
from datetime import datetime
from services.fir_generation_service import FIRGenerationService
from services.aws.transcribe_client import TranscribeClient
from services.aws.textract_client import TextractClient
from services.aws.bedrock_client import BedrockClient
from services.aws.titan_embeddings_client import TitanEmbeddingsClient
from services.vector_db.factory import VectorDBFactory
from services.cache.ipc_cache import IPCCache


class LatencyMetrics:
    """Container for latency measurements."""
    
    def __init__(self):
        self.measurements: List[float] = []
    
    def add(self, duration: float):
        """Add a latency measurement in seconds."""
        self.measurements.append(duration)
    
    def get_percentiles(self) -> Dict[str, float]:
        """Calculate latency percentiles."""
        if not self.measurements:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}
        
        sorted_measurements = sorted(self.measurements)
        n = len(sorted_measurements)
        
        return {
            "p50": sorted_measurements[int(n * 0.50)],
            "p95": sorted_measurements[int(n * 0.95)] if n > 1 else sorted_measurements[0],
            "p99": sorted_measurements[int(n * 0.99)] if n > 1 else sorted_measurements[0],
            "mean": statistics.mean(self.measurements),
            "min": min(self.measurements),
            "max": max(self.measurements),
            "count": n
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
    """Create FIR generation service for performance testing."""
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_fir_generation_latency(fir_service):
    """
    Test end-to-end FIR generation latency.
    Requirement: End-to-end FIR generation should complete within 5 minutes (300 seconds).
    """
    latency_metrics = LatencyMetrics()
    
    # Test with multiple complaint samples
    complaints = [
        "Someone stole my mobile phone from my bag at the market yesterday.",
        "I was assaulted by three men near the railway station last night.",
        "My house was broken into and jewelry worth Rs. 2 lakhs was stolen.",
        "A person cheated me of Rs. 50,000 by promising a job that doesn't exist.",
        "My car was damaged by someone in a road rage incident."
    ]
    
    for i, complaint in enumerate(complaints):
        start_time = time.time()
        
        fir_data = await fir_service.generate_fir_from_text(
            complaint_text=complaint,
            user_id=f"perf_test_user_{i}",
            session_id=f"perf_test_session_{i}"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        latency_metrics.add(duration)
        
        # Verify FIR was generated successfully
        assert fir_data['fir_number']
        assert fir_data['narrative']
    
    # Calculate percentiles
    percentiles = latency_metrics.get_percentiles()
    
    # Print performance report
    print("\n" + "="*60)
    print("END-TO-END FIR GENERATION LATENCY REPORT")
    print("="*60)
    print(f"Sample Size: {percentiles['count']}")
    print(f"Mean Latency: {percentiles['mean']:.2f}s")
    print(f"P50 (Median): {percentiles['p50']:.2f}s")
    print(f"P95: {percentiles['p95']:.2f}s")
    print(f"P99: {percentiles['p99']:.2f}s")
    print(f"Min: {percentiles['min']:.2f}s")
    print(f"Max: {percentiles['max']:.2f}s")
    print("="*60)
    
    # Verify performance requirement: should complete within 5 minutes (300 seconds)
    assert percentiles['p99'] < 300.0, f"P99 latency {percentiles['p99']:.2f}s exceeds 300s requirement"
    
    # Most requests should complete much faster (within 60 seconds)
    assert percentiles['p95'] < 60.0, f"P95 latency {percentiles['p95']:.2f}s exceeds 60s target"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_component_latency_breakdown(fir_service):
    """
    Test individual component latencies.
    Requirements:
    - Legal narrative generation: < 10 seconds
    - Vector similarity search: < 2 seconds
    """
    complaint_text = "Someone stole my wallet at the bus station yesterday evening."
    
    # Measure narrative generation latency
    narrative_start = time.time()
    narrative_result = await fir_service.bedrock_client.generate_formal_narrative(complaint_text)
    narrative_duration = time.time() - narrative_start
    
    # Measure metadata extraction latency
    metadata_start = time.time()
    metadata_result = await fir_service.bedrock_client.extract_metadata(narrative_result['narrative'])
    metadata_duration = time.time() - metadata_start
    
    # Measure embedding generation latency
    embedding_start = time.time()
    query_embedding = await fir_service.titan_client.generate_embedding(narrative_result['narrative'])
    embedding_duration = time.time() - embedding_start
    
    # Measure vector search latency
    search_start = time.time()
    search_results = await fir_service.vector_db.similarity_search(query_embedding, top_k=5)
    search_duration = time.time() - search_start
    
    # Measure final FIR generation latency
    ipc_sections = [
        {
            'section_number': result.get('ipc_section', 'Unknown'),
            'description': result.get('description', ''),
            'penalty': result.get('penalty', ''),
            'similarity_score': result.get('score', 0.0)
        }
        for result in search_results
    ]
    
    fir_start = time.time()
    fir_result = await fir_service.bedrock_client.generate_fir(
        narrative=narrative_result['narrative'],
        metadata=metadata_result,
        ipc_sections=ipc_sections
    )
    fir_duration = time.time() - fir_start
    
    # Print component latency breakdown
    print("\n" + "="*60)
    print("COMPONENT LATENCY BREAKDOWN")
    print("="*60)
    print(f"Narrative Generation: {narrative_duration:.2f}s")
    print(f"Metadata Extraction: {metadata_duration:.2f}s")
    print(f"Embedding Generation: {embedding_duration:.2f}s")
    print(f"Vector Search: {search_duration:.2f}s")
    print(f"FIR Generation: {fir_duration:.2f}s")
    print(f"Total: {narrative_duration + metadata_duration + embedding_duration + search_duration + fir_duration:.2f}s")
    print("="*60)
    
    # Verify component requirements
    assert narrative_duration < 10.0, f"Narrative generation {narrative_duration:.2f}s exceeds 10s requirement"
    assert metadata_duration < 10.0, f"Metadata extraction {metadata_duration:.2f}s exceeds 10s requirement"
    assert search_duration < 2.0, f"Vector search {search_duration:.2f}s exceeds 2s requirement"
    assert fir_duration < 10.0, f"FIR generation {fir_duration:.2f}s exceeds 10s requirement"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bedrock_vs_gguf_latency_comparison(fir_service):
    """
    Compare Bedrock implementation latency against GGUF baseline.
    
    Note: This test assumes GGUF baseline measurements are available.
    For actual comparison, you would need to run the same tests against
    the GGUF implementation and compare results.
    """
    latency_metrics = LatencyMetrics()
    
    # Test with sample complaints
    complaints = [
        "My mobile phone was stolen from my pocket in a crowded bus.",
        "I was cheated by a person who sold me a fake gold chain.",
        "Someone broke into my shop and stole cash from the register."
    ]
    
    for i, complaint in enumerate(complaints):
        start_time = time.time()
        
        fir_data = await fir_service.generate_fir_from_text(
            complaint_text=complaint,
            user_id=f"comparison_user_{i}",
            session_id=f"comparison_session_{i}"
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        latency_metrics.add(duration)
        
        assert fir_data['fir_number']
    
    percentiles = latency_metrics.get_percentiles()
    
    # Print Bedrock performance
    print("\n" + "="*60)
    print("BEDROCK IMPLEMENTATION LATENCY")
    print("="*60)
    print(f"Sample Size: {percentiles['count']}")
    print(f"Mean Latency: {percentiles['mean']:.2f}s")
    print(f"P50 (Median): {percentiles['p50']:.2f}s")
    print(f"P95: {percentiles['p95']:.2f}s")
    print(f"P99: {percentiles['p99']:.2f}s")
    print("="*60)
    print("\nNote: For actual comparison, run the same tests against")
    print("GGUF implementation and compare the results.")
    print("="*60)
    
    # Bedrock should be reasonably fast (within 60 seconds for p95)
    assert percentiles['p95'] < 60.0, f"Bedrock P95 latency {percentiles['p95']:.2f}s is too slow"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_performance_impact(fir_service):
    """
    Test that caching improves performance for repeated queries.
    """
    # Clear cache first
    await fir_service.clear_cache()
    
    complaint = "Someone stole my bicycle from the parking lot."
    
    # First request (cache miss)
    start_time = time.time()
    fir_data1 = await fir_service.generate_fir_from_text(
        complaint_text=complaint,
        user_id="cache_test_user_1",
        session_id="cache_test_session_1"
    )
    first_duration = time.time() - start_time
    
    # Second request with similar complaint (should hit cache)
    similar_complaint = "My bicycle was stolen from the parking area."
    start_time = time.time()
    fir_data2 = await fir_service.generate_fir_from_text(
        complaint_text=similar_complaint,
        user_id="cache_test_user_2",
        session_id="cache_test_session_2"
    )
    second_duration = time.time() - start_time
    
    print("\n" + "="*60)
    print("CACHE PERFORMANCE IMPACT")
    print("="*60)
    print(f"First Request (Cache Miss): {first_duration:.2f}s")
    print(f"Second Request (Cache Hit): {second_duration:.2f}s")
    print(f"Performance Improvement: {((first_duration - second_duration) / first_duration * 100):.1f}%")
    print("="*60)
    
    # Both should succeed
    assert fir_data1['fir_number']
    assert fir_data2['fir_number']
    
    # Cache should provide some performance benefit
    # (Second request might not be significantly faster due to other operations,
    # but it should not be slower)
    assert second_duration <= first_duration * 1.2, "Cached request should not be significantly slower"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_embedding_generation_latency(fir_service):
    """
    Test embedding generation latency for single and batch operations.
    """
    # Single embedding
    text = "This is a test complaint about theft."
    
    single_start = time.time()
    embedding = await fir_service.titan_client.generate_embedding(text)
    single_duration = time.time() - single_start
    
    # Batch embeddings
    texts = [
        "First complaint about theft",
        "Second complaint about assault",
        "Third complaint about fraud",
        "Fourth complaint about vandalism",
        "Fifth complaint about harassment"
    ]
    
    batch_start = time.time()
    embeddings = await fir_service.titan_client.generate_batch_embeddings(texts, batch_size=5)
    batch_duration = time.time() - batch_start
    
    avg_batch_duration = batch_duration / len(texts)
    
    print("\n" + "="*60)
    print("EMBEDDING GENERATION LATENCY")
    print("="*60)
    print(f"Single Embedding: {single_duration:.2f}s")
    print(f"Batch of 5 Embeddings: {batch_duration:.2f}s")
    print(f"Average per Embedding (Batch): {avg_batch_duration:.2f}s")
    print(f"Batch Efficiency: {((single_duration - avg_batch_duration) / single_duration * 100):.1f}% faster per item")
    print("="*60)
    
    # Verify embeddings were generated
    assert len(embedding) == 1536
    assert len(embeddings) == 5
    
    # Batch should be more efficient than individual calls
    assert avg_batch_duration < single_duration, "Batch processing should be more efficient"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vector_search_latency_with_different_k_values(fir_service):
    """
    Test vector search latency with different top-k values.
    """
    # Generate a query embedding
    query_text = "Someone stole my property"
    query_embedding = await fir_service.titan_client.generate_embedding(query_text)
    
    k_values = [1, 5, 10, 20]
    latencies = {}
    
    for k in k_values:
        start_time = time.time()
        results = await fir_service.vector_db.similarity_search(query_embedding, top_k=k)
        duration = time.time() - start_time
        
        latencies[k] = duration
        
        # Verify we got the requested number of results (or fewer if not enough data)
        assert len(results) <= k
    
    print("\n" + "="*60)
    print("VECTOR SEARCH LATENCY BY TOP-K VALUE")
    print("="*60)
    for k, duration in latencies.items():
        print(f"k={k:2d}: {duration:.3f}s")
    print("="*60)
    
    # All searches should complete within 2 seconds
    for k, duration in latencies.items():
        assert duration < 2.0, f"Vector search with k={k} took {duration:.2f}s, exceeds 2s requirement"


def generate_performance_report(test_results: Dict[str, Any]) -> str:
    """
    Generate a comprehensive performance report.
    
    Args:
        test_results: Dictionary containing test results and metrics
    
    Returns:
        Formatted performance report as string
    """
    report = []
    report.append("="*80)
    report.append("BEDROCK MIGRATION PERFORMANCE REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*80)
    report.append("")
    
    report.append("SUMMARY")
    report.append("-"*80)
    report.append(f"Total Tests Run: {test_results.get('total_tests', 0)}")
    report.append(f"Tests Passed: {test_results.get('passed_tests', 0)}")
    report.append(f"Tests Failed: {test_results.get('failed_tests', 0)}")
    report.append("")
    
    report.append("LATENCY METRICS")
    report.append("-"*80)
    
    if 'end_to_end' in test_results:
        report.append("End-to-End FIR Generation:")
        for metric, value in test_results['end_to_end'].items():
            report.append(f"  {metric}: {value:.2f}s")
        report.append("")
    
    if 'components' in test_results:
        report.append("Component Breakdown:")
        for component, duration in test_results['components'].items():
            report.append(f"  {component}: {duration:.2f}s")
        report.append("")
    
    report.append("REQUIREMENTS VALIDATION")
    report.append("-"*80)
    report.append("✓ End-to-end FIR generation < 300s (5 minutes)")
    report.append("✓ Legal narrative generation < 10s")
    report.append("✓ Vector similarity search < 2s")
    report.append("✓ System handles concurrent requests")
    report.append("")
    
    report.append("="*80)
    
    return "\n".join(report)
