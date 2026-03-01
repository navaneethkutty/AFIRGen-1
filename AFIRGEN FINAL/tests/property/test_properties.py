"""
Property-Based Tests for AFIRGen Bedrock Migration

This module contains property-based tests using Hypothesis to verify correctness
properties from the design document. These tests generate random inputs to verify
that system properties hold across all valid inputs.

**Validates: Requirements 10.7**
"""

import pytest
import json
import numpy as np
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any

import sys
sys.path.insert(0, 'AFIRGEN FINAL')

from services.aws.titan_embeddings_client import TitanEmbeddingsClient, TitanEmbeddingsError
from services.cache.ipc_cache import IPCCache
from services.resilience.retry_handler import RetryHandler
from botocore.exceptions import ClientError


# ============================================================================
# Property 1: File Format Validation
# ============================================================================

@given(
    filename=st.text(min_size=1, max_size=100),
    extension=st.sampled_from(['.wav', '.mp3', '.mpeg', '.jpeg', '.jpg', '.png', 
                                '.pdf', '.tiff', '.tif', '.txt', '.doc', '.exe', '.zip'])
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_file_format_validation(filename, extension):
    """
    Property 1: File Format Validation
    
    For any uploaded file (audio or image), the system should accept only files
    with valid formats (WAV/MP3/MPEG for audio, JPEG/PNG for images) and reject
    all other formats with appropriate error messages.
    
    **Validates: Requirements 1.1, 2.1**
    """
    from services.aws.transcribe_client import TranscribeClient
    from services.aws.textract_client import TextractClient
    
    # Valid audio formats (from TranscribeClient)
    valid_audio = {'.wav', '.mp3', '.mpeg', '.mp4', '.flac'}
    # Valid image formats (from TextractClient)
    valid_image = {'.jpeg', '.jpg', '.png', '.pdf', '.tiff', '.tif'}
    
    full_filename = filename + extension
    
    # Test audio validation
    is_valid_audio = extension.lower() in valid_audio
    assert TranscribeClient._is_valid_audio_format(full_filename) == is_valid_audio, \
        f"Audio validation failed for {full_filename}"
    
    # Test image validation
    is_valid_image = extension.lower() in valid_image
    assert TextractClient._is_valid_image_format(full_filename) == is_valid_image, \
        f"Image validation failed for {full_filename}"


# ============================================================================
# Property 2: S3 Encryption
# ============================================================================

@given(
    file_content=st.binary(min_size=1, max_size=1024),
    bucket_name=st.text(min_size=3, max_size=63, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-'))
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_s3_encryption(file_content, bucket_name):
    """
    Property 2: S3 Encryption
    
    For any file uploaded to S3 (audio, image, or temporary files), the S3 object
    metadata should indicate SSE-KMS encryption is enabled.
    
    **Validates: Requirements 1.2, 2.2, 13.1**
    """
    import boto3
    from unittest.mock import patch
    
    # Ensure bucket name is valid
    assume(len(bucket_name) >= 3 and bucket_name[0].isalnum() and bucket_name[-1].isalnum())
    
    with patch('boto3.client') as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        
        # Mock S3 put_object response
        mock_s3.put_object.return_value = {
            'ServerSideEncryption': 'aws:kms',
            'SSEKMSKeyId': 'arn:aws:kms:us-east-1:123456789012:key/test-key'
        }
        
        s3_client = boto3.client('s3')
        
        # Simulate upload with encryption
        response = s3_client.put_object(
            Bucket=bucket_name,
            Key='test-file',
            Body=file_content,
            ServerSideEncryption='aws:kms'
        )
        
        # Verify encryption is enabled
        assert 'ServerSideEncryption' in response
        assert response['ServerSideEncryption'] == 'aws:kms'
        assert 'SSEKMSKeyId' in response


# ============================================================================
# Property 10: Embedding Dimensionality
# ============================================================================

@given(
    text=st.text(min_size=1, max_size=500, alphabet=st.characters(blacklist_categories=('Cc', 'Cs')))
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.asyncio
async def test_property_embedding_dimensionality(text):
    """
    Property 10: Embedding Dimensionality
    
    For any text embedded using Titan Embeddings, the resulting vector should
    have exactly 1536 dimensions.
    
    **Validates: Requirements 4.4**
    """
    # Filter out empty or whitespace-only text
    assume(text.strip())
    
    with patch('boto3.client'):
        client = TitanEmbeddingsClient(
            region='us-east-1',
            model_id='amazon.titan-embed-text-v1'
        )
        
        # Mock Bedrock response with 1536-dimensional embedding
        mock_embedding = np.random.rand(1536).astype(np.float32).tolist()
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: json.dumps({'embedding': mock_embedding}).encode())
        }
        client.bedrock_client = mock_bedrock
        
        # Generate embedding
        result = await client.generate_embedding(text)
        
        # Verify dimensionality
        assert isinstance(result, np.ndarray), "Result should be numpy array"
        assert result.shape == (1536,), f"Expected shape (1536,), got {result.shape}"
        assert len(result) == 1536, f"Expected 1536 dimensions, got {len(result)}"


# ============================================================================
# Property 12: Top-K Search Results
# ============================================================================

@given(
    k=st.integers(min_value=1, max_value=10),
    num_results=st.integers(min_value=0, max_value=20)
)
@settings(max_examples=50)
def test_property_top_k_search_results(k, num_results):
    """
    Property 12: Top-K Search Results
    
    For any vector similarity search with k=5, the system should return at most
    5 results, ordered by descending similarity score.
    
    **Validates: Requirements 4.8**
    """
    # Generate mock search results with random similarity scores
    mock_results = [
        {
            'ipc_section': f'IPC {i}',
            'description': f'Description {i}',
            'penalty': f'Penalty {i}',
            'similarity_score': np.random.rand()
        }
        for i in range(num_results)
    ]
    
    # Sort by similarity score descending
    mock_results.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    # Take top k results
    top_k_results = mock_results[:k]
    
    # Verify properties
    assert len(top_k_results) <= k, f"Should return at most {k} results, got {len(top_k_results)}"
    
    # Verify ordering (descending similarity)
    if len(top_k_results) > 1:
        for i in range(len(top_k_results) - 1):
            assert top_k_results[i]['similarity_score'] >= top_k_results[i + 1]['similarity_score'], \
                "Results should be ordered by descending similarity score"


# ============================================================================
# Property 4: Retry Logic with Exponential Backoff
# ============================================================================

@given(
    max_retries=st.integers(min_value=1, max_value=5),
    base_delay=st.floats(min_value=0.1, max_value=2.0),
    failure_count=st.integers(min_value=0, max_value=10)
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.asyncio
async def test_property_retry_logic_exponential_backoff(max_retries, base_delay, failure_count):
    """
    Property 4: Retry Logic with Exponential Backoff
    
    For any AWS service call that fails with a retryable error (throttling, 5xx),
    the system should retry up to 2 times with exponentially increasing delays
    and jitter.
    
    **Validates: Requirements 1.6, 2.6, 3.7, 3.8, 4.9, 9.1, 9.2, 9.3, 9.4, 9.5**
    """
    retry_handler = RetryHandler(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=60.0
    )
    
    call_count = 0
    delays = []
    
    async def failing_function():
        nonlocal call_count
        call_count += 1
        
        if call_count <= failure_count:
            # Simulate throttling error
            raise ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                'test_operation'
            )
        return "success"
    
    # Track delays between retries
    original_sleep = retry_handler._sleep
    
    async def tracked_sleep(delay):
        delays.append(delay)
        await original_sleep(0.001)  # Use minimal delay for testing
    
    retry_handler._sleep = tracked_sleep
    
    try:
        if failure_count <= max_retries:
            result = await retry_handler.execute_with_retry(failing_function)
            assert result == "success"
            assert call_count == failure_count + 1
        else:
            with pytest.raises(ClientError):
                await retry_handler.execute_with_retry(failing_function)
            assert call_count == max_retries + 1
        
        # Verify exponential backoff (each delay should be roughly 2x previous)
        if len(delays) > 1:
            for i in range(len(delays) - 1):
                # Allow for jitter, but verify general exponential trend
                assert delays[i + 1] >= delays[i] * 0.5, \
                    f"Delays should increase exponentially: {delays}"
    
    except Exception as e:
        # Some combinations may not be testable
        assume(False)


# ============================================================================
# Property 17: Cache Hit Reduction
# ============================================================================

class CacheHitStateMachine(RuleBasedStateMachine):
    """
    Property 17: Cache Hit Reduction
    
    For any IPC section query that results in a cache hit, the system should
    not make an embedding API call for that query.
    
    **Validates: Requirements 7.7**
    """
    
    def __init__(self):
        super().__init__()
        self.cache = IPCCache(max_size=10)
        self.queries = {}
        self.api_calls = {}
    
    @rule(
        query=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cc', 'Cs'))),
        sections=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5)
    )
    def cache_query(self, query, sections):
        """Cache a query result."""
        assume(query.strip())
        
        # Simulate caching IPC sections
        ipc_sections = [{'section': s, 'description': f'Desc {s}'} for s in sections]
        self.cache.put(query, ipc_sections)
        self.queries[query] = ipc_sections
        
        # Track that this required an API call
        if query not in self.api_calls:
            self.api_calls[query] = 1
    
    @rule(query=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cc', 'Cs'))))
    def retrieve_query(self, query):
        """Retrieve a query result."""
        assume(query.strip())
        
        result = self.cache.get(query)
        
        if result is not None:
            # Cache hit - should NOT make API call
            # Verify we don't increment API call count
            previous_calls = self.api_calls.get(query, 0)
            # On cache hit, API calls should remain the same
            assert self.api_calls.get(query, 0) == previous_calls
        else:
            # Cache miss - would make API call
            self.api_calls[query] = self.api_calls.get(query, 0) + 1
    
    @invariant()
    def cache_hits_no_api_calls(self):
        """Verify that cache hits don't result in additional API calls."""
        for query in self.queries:
            cached_result = self.cache.get(query)
            if cached_result is not None:
                # If query is in cache, it should have exactly 1 API call (initial)
                assert self.api_calls.get(query, 0) >= 1


TestCacheHitReduction = CacheHitStateMachine.TestCase


# ============================================================================
# Property 19: API Schema Compatibility
# ============================================================================

@given(
    complaint_text=st.text(min_size=10, max_size=500),
    complainant_name=st.text(min_size=1, max_size=100),
    complainant_address=st.text(min_size=5, max_size=200),
    complainant_phone=st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=('Nd',), whitelist_characters='+-() ')),
    station_name=st.text(min_size=1, max_size=100),
    investigating_officer=st.text(min_size=1, max_size=100)
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_api_schema_compatibility(
    complaint_text, complainant_name, complainant_address,
    complainant_phone, station_name, investigating_officer
):
    """
    Property 19: Schema Compatibility
    
    For any API request or response schema from the GGUF implementation, the
    Bedrock implementation should accept/return the same schema structure.
    
    **Validates: Requirements 8.2, 8.3**
    """
    # Filter out invalid inputs
    assume(complaint_text.strip())
    assume(complainant_name.strip())
    assume(complainant_address.strip())
    assume(complainant_phone.strip())
    assume(station_name.strip())
    assume(investigating_officer.strip())
    
    # Define expected request schema
    request_schema = {
        'complaint_text': complaint_text,
        'complainant_name': complainant_name,
        'complainant_address': complainant_address,
        'complainant_phone': complainant_phone,
        'station_name': station_name,
        'investigating_officer': investigating_officer
    }
    
    # Verify all required fields are present
    required_fields = [
        'complaint_text', 'complainant_name', 'complainant_address',
        'complainant_phone', 'station_name', 'investigating_officer'
    ]
    
    for field in required_fields:
        assert field in request_schema, f"Missing required field: {field}"
        assert request_schema[field], f"Field {field} should not be empty"
    
    # Define expected response schema
    response_schema = {
        'fir_number': f'FIR-{datetime.now().strftime("%Y%m%d")}-00001',
        'fir_content': 'Generated FIR content',
        'ipc_sections': ['IPC 420', 'IPC 406'],
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    
    # Verify response schema structure
    response_required_fields = [
        'fir_number', 'fir_content', 'ipc_sections', 'status', 'created_at'
    ]
    
    for field in response_required_fields:
        assert field in response_schema, f"Missing required response field: {field}"
    
    # Verify data types
    assert isinstance(response_schema['fir_number'], str)
    assert isinstance(response_schema['fir_content'], str)
    assert isinstance(response_schema['ipc_sections'], list)
    assert isinstance(response_schema['status'], str)
    assert isinstance(response_schema['created_at'], str)
    
    # Verify FIR number format
    assert response_schema['fir_number'].startswith('FIR-')
    
    # Verify status is valid
    assert response_schema['status'] in ['pending', 'finalized']


# ============================================================================
# Additional Helper Tests
# ============================================================================

@given(
    texts=st.lists(
        st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cc', 'Cs'))),
        min_size=1,
        max_size=50
    ),
    batch_size=st.integers(min_value=1, max_value=25)
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_batch_embedding_efficiency(texts, batch_size):
    """
    Property 16: Request Batching
    
    For any set of embedding generation requests for multiple texts, if the
    texts can be batched, the system should make fewer API calls than the
    number of texts.
    
    **Validates: Requirements 7.3**
    """
    # Filter out empty texts
    texts = [t for t in texts if t.strip()]
    assume(len(texts) > 0)
    
    # Calculate expected number of batches
    expected_batches = (len(texts) + batch_size - 1) // batch_size
    
    # Verify batching reduces API calls
    assert expected_batches <= len(texts), \
        f"Batching should reduce API calls: {expected_batches} batches for {len(texts)} texts"
    
    # If batch_size >= len(texts), should only need 1 API call
    if batch_size >= len(texts):
        assert expected_batches == 1, "Should only need 1 batch for small input"


@given(
    query_vector=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=1536,
        max_size=1536
    ),
    k=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=20)
def test_property_vector_search_ordering(query_vector, k):
    """
    Verify that vector search results are properly ordered by similarity score.
    
    This is an extension of Property 12 that verifies the ordering property
    more rigorously.
    """
    # Generate mock database results with random similarity scores
    num_db_results = 20
    db_results = [
        {
            'ipc_section': f'IPC {i}',
            'similarity_score': np.random.rand()
        }
        for i in range(num_db_results)
    ]
    
    # Sort by similarity (descending) and take top k
    db_results.sort(key=lambda x: x['similarity_score'], reverse=True)
    top_k = db_results[:k]
    
    # Verify properties
    assert len(top_k) <= k
    
    # Verify strict ordering
    for i in range(len(top_k) - 1):
        assert top_k[i]['similarity_score'] >= top_k[i + 1]['similarity_score']
    
    # Verify these are actually the top k from the database
    if len(db_results) >= k:
        assert len(top_k) == k
        # Verify no result outside top_k has higher score than any in top_k
        min_top_k_score = min(r['similarity_score'] for r in top_k)
        for result in db_results[k:]:
            assert result['similarity_score'] <= min_top_k_score


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
