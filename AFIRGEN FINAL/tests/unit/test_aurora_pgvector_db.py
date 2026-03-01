"""Unit tests for AuroraPgVectorDB."""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, 'AFIRGEN FINAL')

from services.vector_db.aurora_pgvector_db import AuroraPgVectorDB
from services.vector_db.interface import VectorSearchResult


@pytest.fixture
def aurora_db():
    """Create AuroraPgVectorDB instance for testing."""
    db = AuroraPgVectorDB(
        host='test-host',
        port=5432,
        database='test_db',
        user='test_user',
        password='test_pass'
    )
    db.pool = MagicMock()
    return db


class TestAuroraPgVectorDB:
    """Test suite for AuroraPgVectorDB."""
    
    def test_init(self):
        """Test initialization."""
        db = AuroraPgVectorDB(
            host='localhost',
            port=5432,
            database='afirgen',
            user='admin',
            password='secret'
        )
        assert db.host == 'localhost'
        assert db.port == 5432
        assert db.database == 'afirgen'
    
    @pytest.mark.asyncio
    async def test_create_index_success(self, aurora_db):
        """Test successful index creation."""
        mock_conn = AsyncMock()
        aurora_db.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        await aurora_db.create_index('test_table', 1536, 'cosine')
        
        assert mock_conn.execute.call_count >= 2  # CREATE TABLE + CREATE INDEX
    
    @pytest.mark.asyncio
    async def test_insert_vectors_success(self, aurora_db):
        """Test successful vector insertion."""
        vectors = [np.random.rand(1536).astype(np.float32) for _ in range(2)]
        metadata = [
            {'section_number': '379', 'description': 'Theft', 'penalty': '3 years'},
            {'section_number': '380', 'description': 'Theft in dwelling', 'penalty': '7 years'}
        ]
        
        mock_conn = AsyncMock()
        aurora_db.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        ids = await aurora_db.insert_vectors('test_table', vectors, metadata)
        
        assert len(ids) == 2
        assert mock_conn.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_similarity_search_success(self, aurora_db):
        """Test successful similarity search."""
        query_vector = np.random.rand(1536).astype(np.float32)
        
        mock_rows = [
            {
                'id': 'uuid1',
                'section_number': '379',
                'description': 'Theft',
                'penalty': '3 years',
                'score': 0.95,
                'metadata': {'category': 'property'}
            }
        ]
        
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_rows
        aurora_db.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        results = await aurora_db.similarity_search('test_table', query_vector, top_k=5)
        
        assert len(results) == 1
        assert isinstance(results[0], VectorSearchResult)
        assert results[0].section_number == '379'
    
    @pytest.mark.asyncio
    async def test_delete_vectors_success(self, aurora_db):
        """Test successful vector deletion."""
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = 'DELETE 2'
        aurora_db.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        deleted = await aurora_db.delete_vectors('test_table', ['id1', 'id2'])
        
        assert deleted == 2
    
    @pytest.mark.asyncio
    async def test_index_exists_true(self, aurora_db):
        """Test table existence check (exists)."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = True
        aurora_db.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        exists = await aurora_db.index_exists('test_table')
        
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_get_index_stats_success(self, aurora_db):
        """Test getting table statistics."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = [100, 1024000]  # count, size
        aurora_db.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        stats = await aurora_db.get_index_stats('test_table')
        
        assert stats['vector_count'] == 100
        assert stats['size_bytes'] == 1024000
