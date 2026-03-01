"""
Integration tests for Vector Database and Titan Embeddings.
Tests embedding generation and vector database operations with real AWS services.
"""

import pytest
import asyncio
import numpy as np
from services.aws.titan_embeddings_client import TitanEmbeddingsClient
from services.vector_db.factory import VectorDBFactory
from services.vector_db.interface import VectorDatabaseInterface


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_embedding(aws_region, embeddings_model_id):
    """Test embedding generation with Titan."""
    client = TitanEmbeddingsClient(
        region=aws_region,
        model_id=embeddings_model_id
    )
    
    text = "This is a test complaint about theft of property."
    
    embedding = await client.generate_embedding(text)
    
    # Verify embedding
    assert isinstance(embedding, np.ndarray)
    assert len(embedding) == 1536
    assert embedding.dtype == np.float32
    assert np.isfinite(embedding).all()
    
    # Verify embedding has reasonable values
    assert np.abs(embedding).max() < 10.0  # Reasonable magnitude


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_batch_embeddings(aws_region, embeddings_model_id):
    """Test batch embedding generation."""
    client = TitanEmbeddingsClient(
        region=aws_region,
        model_id=embeddings_model_id
    )
    
    texts = [
        "Theft of mobile phone",
        "Assault and battery",
        "Fraud and cheating",
        "Property damage",
        "Trespassing"
    ]
    
    embeddings = await client.generate_batch_embeddings(texts)
    
    # Verify embeddings
    assert len(embeddings) == 5
    for embedding in embeddings:
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == 1536
        assert np.isfinite(embedding).all()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_embedding_similarity(aws_region, embeddings_model_id):
    """Test that similar texts have similar embeddings."""
    client = TitanEmbeddingsClient(
        region=aws_region,
        model_id=embeddings_model_id
    )
    
    similar_texts = [
        "Theft of mobile phone from bag",
        "Mobile phone stolen from purse"
    ]
    
    different_text = "Traffic accident on highway"
    
    # Generate embeddings
    similar_emb1 = await client.generate_embedding(similar_texts[0])
    similar_emb2 = await client.generate_embedding(similar_texts[1])
    different_emb = await client.generate_embedding(different_text)
    
    # Calculate cosine similarities
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    similar_score = cosine_similarity(similar_emb1, similar_emb2)
    different_score = cosine_similarity(similar_emb1, different_emb)
    
    # Similar texts should have higher similarity
    assert similar_score > different_score
    assert similar_score > 0.7  # High similarity threshold


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vector_db_insert_and_search(
    aws_region,
    embeddings_model_id,
    vector_db_type,
    opensearch_endpoint,
    aurora_config
):
    """Test vector database insert and similarity search."""
    # Skip if vector DB not configured
    if vector_db_type == "opensearch" and not opensearch_endpoint:
        pytest.skip("OpenSearch endpoint not configured")
    if vector_db_type == "aurora_pgvector" and not aurora_config["host"]:
        pytest.skip("Aurora configuration not set")
    
    # Create clients
    embeddings_client = TitanEmbeddingsClient(
        region=aws_region,
        model_id=embeddings_model_id
    )
    
    from services.vector_db.factory import VectorDBFactory
    
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
    
    try:
        # Connect to database
        await vector_db.connect()
        
        # Create test index/table
        test_index = f"test_ipc_sections_{asyncio.get_event_loop().time()}"
        await vector_db.create_index(test_index, dimension=1536)
        
        # Prepare test data
        ipc_sections = [
            {
                "section": "IPC 379",
                "description": "Whoever commits theft shall be punished",
                "penalty": "Imprisonment up to 3 years"
            },
            {
                "section": "IPC 420",
                "description": "Whoever cheats and thereby dishonestly induces",
                "penalty": "Imprisonment up to 7 years"
            },
            {
                "section": "IPC 323",
                "description": "Whoever voluntarily causes hurt",
                "penalty": "Imprisonment up to 1 year"
            }
        ]
        
        # Generate embeddings
        texts = [sec["description"] for sec in ipc_sections]
        embeddings = await embeddings_client.generate_batch_embeddings(texts)
        
        # Insert into vector database
        await vector_db.insert_vectors(
            index_name=test_index,
            vectors=embeddings,
            metadata=ipc_sections
        )
        
        # Wait for indexing
        await asyncio.sleep(2)
        
        # Search for theft-related sections
        query_text = "Someone stole my property"
        query_embedding = await embeddings_client.generate_embedding(query_text)
        
        results = await vector_db.similarity_search(
            index_name=test_index,
            query_vector=query_embedding,
            top_k=2
        )
        
        # Verify results
        assert len(results) > 0
        assert len(results) <= 2
        
        # Top result should be IPC 379 (theft)
        assert "379" in results[0].section_number
        assert results[0].score > 0.5
        
    finally:
        # Cleanup
        await vector_db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vector_db_multiple_searches(
    aws_region,
    embeddings_model_id,
    vector_db_type,
    opensearch_endpoint,
    aurora_config
):
    """Test multiple similarity searches."""
    if vector_db_type == "opensearch" and not opensearch_endpoint:
        pytest.skip("OpenSearch endpoint not configured")
    if vector_db_type == "aurora_pgvector" and not aurora_config["host"]:
        pytest.skip("Aurora configuration not set")
    
    embeddings_client = TitanEmbeddingsClient(
        region=aws_region,
        model_id=embeddings_model_id
    )
    
    from services.vector_db.factory import VectorDBFactory
    
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
    
    try:
        await vector_db.connect()
        
        # Use existing index or create new one
        test_index = "test_ipc_sections"
        
        # Perform multiple searches
        queries = [
            "Theft of property",
            "Physical assault",
            "Fraud and cheating"
        ]
        
        for query in queries:
            query_embedding = await embeddings_client.generate_embedding(query)
            results = await vector_db.similarity_search(
                index_name=test_index,
                query_vector=query_embedding,
                top_k=3
            )
            
            # Each search should return results
            assert len(results) > 0
            
    finally:
        await vector_db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_embedding_empty_text(aws_region, embeddings_model_id):
    """Test embedding generation with empty text."""
    client = TitanEmbeddingsClient(
        region=aws_region,
        model_id=embeddings_model_id
    )
    
    with pytest.raises(Exception) as exc_info:
        await client.generate_embedding("")
    
    assert "empty" in str(exc_info.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_embedding_long_text(aws_region, embeddings_model_id):
    """Test embedding generation with very long text."""
    client = TitanEmbeddingsClient(
        region=aws_region,
        model_id=embeddings_model_id
    )
    
    # Create long text (but within model limits)
    long_text = " ".join(["This is a test sentence."] * 100)
    
    embedding = await client.generate_embedding(long_text)
    
    # Should still generate valid embedding
    assert isinstance(embedding, np.ndarray)
    assert len(embedding) == 1536


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vector_db_top_k_parameter(
    aws_region,
    embeddings_model_id,
    vector_db_type,
    opensearch_endpoint,
    aurora_config
):
    """Test that top_k parameter correctly limits results."""
    if vector_db_type == "opensearch" and not opensearch_endpoint:
        pytest.skip("OpenSearch endpoint not configured")
    if vector_db_type == "aurora_pgvector" and not aurora_config["host"]:
        pytest.skip("Aurora configuration not set")
    
    embeddings_client = TitanEmbeddingsClient(
        region=aws_region,
        model_id=embeddings_model_id
    )
    
    from services.vector_db.factory import VectorDBFactory
    
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
    
    try:
        await vector_db.connect()
        
        test_index = "test_ipc_sections"
        query_text = "Test query"
        query_embedding = await embeddings_client.generate_embedding(query_text)
        
        # Test different top_k values
        for k in [1, 3, 5]:
            results = await vector_db.similarity_search(
                index_name=test_index,
                query_vector=query_embedding,
                top_k=k
            )
            
            # Should return at most k results
            assert len(results) <= k
            
    finally:
        await vector_db.close()
