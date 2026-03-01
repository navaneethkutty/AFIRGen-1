"""
Unit tests for TitanEmbeddingsClient.
"""

import pytest
import json
import numpy as np
from unittest.mock import Mock, AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, 'AFIRGEN FINAL')

from services.aws.titan_embeddings_client import (
    TitanEmbeddingsClient,
    TitanEmbeddingsError
)


@pytest.fixture
def titan_client():
    """Create TitanEmbeddingsClient instance for testing."""
    with patch('boto3.client'):
        client = TitanEmbeddingsClient(
            region='us-east-1',
            model_id='amazon.titan-embed-text-v1'
        )
        return client


@pytest.fixture
def mock_embedding():
    """Create mock 1536-dimensional embedding."""
    return np.random.rand(1536).astype(np.float32).tolist()


class TestTitanEmbeddingsClient:
    """Test suite for TitanEmbeddingsClient."""
    
    def test_init(self, titan_client):
        """Test client initialization."""
        assert titan_client.model_id == 'amazon.titan-embed-text-v1'
        assert titan_client.region == 'us-east-1'
        assert titan_client.max_retries == 3
        assert titan_client.EMBEDDING_DIMENSION == 1536
        assert titan_client.BATCH_SIZE == 25
    
    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, titan_client, mock_embedding):
        """Test successful embedding generation."""
        mock_bedrock = MagicMock()
        mock_response_body = {'embedding': mock_embedding}
        
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: json.dumps(mock_response_body).encode())
        }
        
        titan_client.bedrock_client = mock_bedrock
        
        result = await titan_client.generate_embedding("Test text for embedding")
        
        assert isinstance(result, np.ndarray)
        assert len(result) == 1536
        assert result.dtype == np.float32
    
    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, titan_client):
        """Test embedding generation with empty text."""
        with pytest.raises(TitanEmbeddingsError) as exc_info:
            await titan_client.generate_embedding("")
        
        assert "cannot be empty" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_embedding_invalid_dimension(self, titan_client):
        """Test embedding with invalid dimension."""
        mock_bedrock = MagicMock()
        invalid_embedding = [0.1] * 512  # Wrong dimension
        
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: json.dumps({'embedding': invalid_embedding}).encode())
        }
        
        titan_client.bedrock_client = mock_bedrock
        
        with pytest.raises(TitanEmbeddingsError) as exc_info:
            await titan_client.generate_embedding("Test")
        
        assert "Invalid embedding dimension" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_embedding_throttling_retry(self, titan_client, mock_embedding):
        """Test retry logic on throttling."""
        from botocore.exceptions import ClientError
        
        mock_bedrock = MagicMock()
        
        throttling_error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'invoke_model'
        )
        
        success_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': mock_embedding}).encode())
        }
        
        mock_bedrock.invoke_model.side_effect = [throttling_error, success_response]
        titan_client.bedrock_client = mock_bedrock
        
        result = await titan_client.generate_embedding("Test")
        
        assert isinstance(result, np.ndarray)
        assert len(result) == 1536
        assert mock_bedrock.invoke_model.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_success(self, titan_client, mock_embedding):
        """Test successful batch embedding generation."""
        texts = ["Text 1", "Text 2", "Text 3"]
        
        # Mock generate_embedding to return valid embeddings
        async def mock_generate(text):
            return np.array(mock_embedding, dtype=np.float32)
        
        titan_client.generate_embedding = mock_generate
        
        results = await titan_client.generate_batch_embeddings(texts)
        
        assert len(results) == 3
        assert all(isinstance(emb, np.ndarray) for emb in results)
        assert all(len(emb) == 1536 for emb in results)
    
    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_empty_list(self, titan_client):
        """Test batch generation with empty list."""
        results = await titan_client.generate_batch_embeddings([])
        assert results == []
    
    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_large_batch(self, titan_client, mock_embedding):
        """Test batch generation with more than batch size."""
        texts = [f"Text {i}" for i in range(30)]  # More than BATCH_SIZE (25)
        
        async def mock_generate(text):
            return np.array(mock_embedding, dtype=np.float32)
        
        titan_client.generate_embedding = mock_generate
        
        results = await titan_client.generate_batch_embeddings(texts)
        
        assert len(results) == 30
    
    def test_validate_embedding_valid(self, titan_client):
        """Test validation of valid embedding."""
        valid_embedding = np.random.rand(1536).astype(np.float32)
        assert titan_client.validate_embedding(valid_embedding) is True
    
    def test_validate_embedding_wrong_dimension(self, titan_client):
        """Test validation of wrong dimension."""
        invalid_embedding = np.random.rand(512).astype(np.float32)
        assert titan_client.validate_embedding(invalid_embedding) is False
    
    def test_validate_embedding_not_numpy(self, titan_client):
        """Test validation of non-numpy array."""
        invalid_embedding = [0.1] * 1536
        assert titan_client.validate_embedding(invalid_embedding) is False
    
    def test_validate_embedding_with_nan(self, titan_client):
        """Test validation with NaN values."""
        invalid_embedding = np.random.rand(1536).astype(np.float32)
        invalid_embedding[0] = np.nan
        assert titan_client.validate_embedding(invalid_embedding) is False
    
    def test_validate_embedding_with_inf(self, titan_client):
        """Test validation with infinite values."""
        invalid_embedding = np.random.rand(1536).astype(np.float32)
        invalid_embedding[0] = np.inf
        assert titan_client.validate_embedding(invalid_embedding) is False
