"""
Unit tests for OpenSearchVectorDB.
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, 'AFIRGEN FINAL')

from services.vector_db.opensearch_db import OpenSearchVectorDB
from services.vector_db.interface import VectorSearchResult


@pytest.fixture
def opensearch_db():
    """Create OpenSearchVectorDB instance for testing."""
    db = OpenSearchVectorDB(
        endpoint='test-endpoint.us-east-1.aoss.amazonaws.com',
        region='us-east-1',
        index_name='test_index'
    )
    db.client = MagicMock()
    return db


@pytest.fixture
def mock_vector():
    """Create mock embedding vector."""
    return np.random.rand(1536).astype(np.float32)


class TestOpenSearchVectorDB:
    """Test suite for OpenSearchVectorDB."""
    
    def test_init(self):
        """Test initialization."""
        db = OpenSearchVectorDB(
            endpoint='test-endpoint',
            region='us-east-1'
        )
        assert db.endpoint == 'test-endpoint'
        assert db.region == 'us-east-1'
        assert db.max_retries == 3
    
    @pytest.mark.asyncio
    async def test_create_index_success(self, opensearch_db):
        """Test successful index creation."""
        opensearch_db.client.indices.create = Mock()
        
        await opensearch_db.create_index('test_index', 1536, 'cosine')
        
        opensearch_db.client.indices.create.assert_called_once()
        call_args = opensearch_db.client.indices.create.call_args
        assert call_args[1]['index'] == 'test_index'
        assert 'knn_vector' in str(call_args[1]['body'])
    
    @pytest.mark.asyncio
    async def test_create_index_invalid_metric(self, opensearch_db):
        """Test index creation with invalid metric."""
        with pytest.raises(ValueError) as exc_info:
            await opensearch_db.create_index('test_index', 1536, 'invalid_metric')
        
        assert "Unsupported metric" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_insert_vectors_success(self, opensearch_db, mock_vector):
        """Test successful vector insertion."""
        vectors = [mock_vector, mock_vector]
        metadata = [
            {'section_number': '379', 'description': 'Theft', 'penalty': '3 years'},
            {'section_number': '380', 'description': 'Theft in dwelling', 'penalty': '7 years'}
        ]
        
        opensearch_db.client.index = Mock()
        opensearch_db.client.indices.refresh = Mock()
        
        ids = await opensearch_db.insert_vectors('test_index', vectors, metadata)
        
        assert len(ids) == 2
        assert opensearch_db.client.index.call_count == 2
        opensearch_db.client.indices.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_insert_vectors_length_mismatch(self, opensearch_db, mock_vector):
        """Test vector insertion with mismatched lengths."""
        vectors = [mock_vector]
        metadata = [{'section_number': '379'}, {'section_number': '380'}]
        
        with pytest.raises(ValueError) as exc_info:
            await opensearch_db.insert_vectors('test_index', vectors, metadata)
        
        assert "same length" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_similarity_search_success(self, opensearch_db, mock_vector):
        """Test successful similarity search."""
        mock_response = {
            'hits': {
                'hits': [
                    {
                        '_id': 'doc1',
                        '_score': 0.95,
                        '_source': {
                            'section_number': '379',
                            'description': 'Theft',
                            'penalty': '3 years',
                            'metadata': {'category': 'property'}
                        }
                    },
                    {
                        '_id': 'doc2',
                        '_score': 0.90,
                        '_source': {
                            'section_number': '380',
                            'description': 'Theft in dwelling',
                            'penalty': '7 years',
                            'metadata': {'category': 'property'}
                        }
                    }
                ]
            }
        }
        
        opensearch_db.client.search = Mock(return_value=mock_response)
        
        results = await opensearch_db.similarity_search('test_index', mock_vector, top_k=2)
        
        assert len(results) == 2
        assert all(isinstance(r, VectorSearchResult) for r in results)
        assert results[0].section_number == '379'
        assert results[0].score == 0.95
        assert results[1].section_number == '380'
    
    @pytest.mark.asyncio
    async def test_similarity_search_with_filters(self, opensearch_db, mock_vector):
        """Test similarity search with filters."""
        opensearch_db.client.search = Mock(return_value={'hits': {'hits': []}})
        
        filters = {'category': 'property'}
        await opensearch_db.similarity_search('test_index', mock_vector, top_k=5, filters=filters)
        
        call_args = opensearch_db.client.search.call_args[1]
        assert 'filter' in str(call_args['body'])
    
    @pytest.mark.asyncio
    async def test_delete_vectors_success(self, opensearch_db):
        """Test successful vector deletion."""
        opensearch_db.client.delete = Mock()
        
        deleted = await opensearch_db.delete_vectors('test_index', ['doc1', 'doc2'])
        
        assert deleted == 2
        assert opensearch_db.client.delete.call_count == 2
    
    @pytest.mark.asyncio
    async def test_index_exists_true(self, opensearch_db):
        """Test index existence check (exists)."""
        opensearch_db.client.indices.exists = Mock(return_value=True)
        
        exists = await opensearch_db.index_exists('test_index')
        
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_index_exists_false(self, opensearch_db):
        """Test index existence check (doesn't exist)."""
        opensearch_db.client.indices.exists = Mock(return_value=False)
        
        exists = await opensearch_db.index_exists('test_index')
        
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_get_index_stats_success(self, opensearch_db):
        """Test getting index statistics."""
        mock_stats = {
            'indices': {
                'test_index': {
                    'total': {
                        'docs': {'count': 100},
                        'store': {'size_in_bytes': 1024000}
                    }
                }
            }
        }
        
        opensearch_db.client.indices.stats = Mock(return_value=mock_stats)
        
        stats = await opensearch_db.get_index_stats('test_index')
        
        assert stats['vector_count'] == 100
        assert stats['size_bytes'] == 1024000
        assert stats['index_name'] == 'test_index'
