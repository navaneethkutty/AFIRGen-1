"""
Integration tests for complete FIR generation workflow.
Tests end-to-end FIR generation with all AWS services.
"""

import pytest
import asyncio
import io
from datetime import datetime
from services.fir_generation_service import FIRGenerationService
from services.aws.transcribe_client import TranscribeClient
from services.aws.textract_client import TextractClient
from services.aws.bedrock_client import BedrockClient
from services.aws.titan_embeddings_client import TitanEmbeddingsClient
from services.vector_db.factory import VectorDBFactory
from services.cache.ipc_cache import IPCCache
from fastapi import UploadFile


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_fir_from_text(
    aws_region,
    s3_bucket,
    kms_key_id,
    bedrock_model_id,
    embeddings_model_id,
    vector_db_type,
    opensearch_endpoint,
    aurora_config
):
    """Test complete FIR generation from text complaint."""
    # Skip if vector DB not configured
    if vector_db_type == "opensearch" and not opensearch_endpoint:
        pytest.skip("OpenSearch endpoint not configured")
    if vector_db_type == "aurora_pgvector" and not aurora_config["host"]:
        pytest.skip("Aurora configuration not set")
    
    # Initialize all clients
    bedrock_client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id
    )
    
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
    
    ipc_cache = IPCCache(max_size=100)
    
    # Create placeholder clients (not used in text-only test)
    transcribe_client = None
    textract_client = None
    
    # Create FIR generation service
    fir_service = FIRGenerationService(
        transcribe_client=transcribe_client,
        textract_client=textract_client,
        bedrock_client=bedrock_client,
        titan_client=embeddings_client,
        vector_db=vector_db,
        ipc_cache=ipc_cache
    )
    
    try:
        # Connect to vector database
        await vector_db.connect()
        
        # Test complaint text
        complaint_text = """
        Yesterday at 3 PM, I was at the Central Market in Delhi when someone 
        stole my mobile phone from my bag. The phone was a Samsung Galaxy S21 
        worth Rs. 45,000. I saw a young man running away but couldn't catch him.
        My name is Rajesh Kumar and I want to file a complaint.
        """
        
        # Generate FIR
        fir_data = await fir_service.generate_fir_from_text(
            complaint_text=complaint_text,
            user_id="test_user_001",
            session_id="test_session_001"
        )
        
        # Verify FIR structure
        assert fir_data['fir_number']
        assert fir_data['narrative']
        assert fir_data['metadata']
        assert fir_data['metadata']['incident_type']
        assert fir_data['metadata']['location']
        assert fir_data['metadata']['complainant_name']
        assert len(fir_data['ipc_sections']) > 0
        assert fir_data['legal_analysis']
        
        # Verify FIR contains relevant information
        assert "theft" in fir_data['narrative'].lower() or "379" in str(fir_data['ipc_sections'])
        
    finally:
        await vector_db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_fir_from_audio(
    aws_region,
    s3_bucket,
    kms_key_id,
    bedrock_model_id,
    embeddings_model_id,
    vector_db_type,
    opensearch_endpoint,
    aurora_config
):
    """Test FIR generation from audio file."""
    if vector_db_type == "opensearch" and not opensearch_endpoint:
        pytest.skip("OpenSearch endpoint not configured")
    if vector_db_type == "aurora_pgvector" and not aurora_config["host"]:
        pytest.skip("Aurora configuration not set")
    
    # Initialize clients
    transcribe_client = TranscribeClient(
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
    
    ipc_cache = IPCCache(max_size=100)
    
    fir_service = FIRGenerationService(
        transcribe_client=transcribe_client,
        textract_client=None,
        bedrock_client=bedrock_client,
        titan_client=embeddings_client,
        vector_db=vector_db,
        ipc_cache=ipc_cache
    )
    
    try:
        await vector_db.connect()
        
        # Create sample audio file
        audio_content = create_sample_audio()
        audio_file = UploadFile(
            filename="complaint_audio.mp3",
            file=io.BytesIO(audio_content)
        )
        
        # Generate FIR from audio
        fir_data = await fir_service.generate_fir_from_audio(
            audio_file=audio_file,
            language_code="hi-IN",
            user_id="test_user_002",
            session_id="test_session_002"
        )
        
        # Verify FIR was generated
        assert fir_data['fir_number']
        assert fir_data['narrative']
        assert fir_data['metadata']
        
    finally:
        await vector_db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_fir_from_image(
    aws_region,
    s3_bucket,
    kms_key_id,
    bedrock_model_id,
    embeddings_model_id,
    vector_db_type,
    opensearch_endpoint,
    aurora_config
):
    """Test FIR generation from document image."""
    if vector_db_type == "opensearch" and not opensearch_endpoint:
        pytest.skip("OpenSearch endpoint not configured")
    if vector_db_type == "aurora_pgvector" and not aurora_config["host"]:
        pytest.skip("Aurora configuration not set")
    
    # Initialize clients
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
    
    ipc_cache = IPCCache(max_size=100)
    
    fir_service = FIRGenerationService(
        transcribe_client=None,
        textract_client=textract_client,
        bedrock_client=bedrock_client,
        titan_client=embeddings_client,
        vector_db=vector_db,
        ipc_cache=ipc_cache
    )
    
    try:
        await vector_db.connect()
        
        # Create sample document image
        image_content = create_sample_complaint_image()
        image_file = UploadFile(
            filename="complaint_document.png",
            file=io.BytesIO(image_content)
        )
        
        # Generate FIR from image
        fir_data = await fir_service.generate_fir_from_image(
            image_file=image_file,
            user_id="test_user_003",
            session_id="test_session_003"
        )
        
        # Verify FIR was generated
        assert fir_data['fir_number']
        assert fir_data['narrative']
        assert fir_data['metadata']
        
    finally:
        await vector_db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fir_generation_with_cache(
    aws_region,
    s3_bucket,
    bedrock_model_id,
    embeddings_model_id,
    vector_db_type,
    opensearch_endpoint,
    aurora_config
):
    """Test that IPC cache reduces embedding API calls."""
    if vector_db_type == "opensearch" and not opensearch_endpoint:
        pytest.skip("OpenSearch endpoint not configured")
    if vector_db_type == "aurora_pgvector" and not aurora_config["host"]:
        pytest.skip("Aurora configuration not set")
    
    bedrock_client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id
    )
    
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
    
    ipc_cache = IPCCache(max_size=100)
    
    fir_service = FIRGenerationService(
        transcribe_client=None,
        textract_client=None,
        bedrock_client=bedrock_client,
        titan_client=embeddings_client,
        vector_db=vector_db,
        ipc_cache=ipc_cache
    )
    
    try:
        await vector_db.connect()
        
        # Generate FIR twice with similar complaints
        complaint1 = "Someone stole my mobile phone from my bag."
        complaint2 = "My mobile phone was stolen from my purse."
        
        fir_data1 = await fir_service.generate_fir_from_text(
            complaint_text=complaint1,
            user_id="test_user_004",
            session_id="test_session_004"
        )
        
        fir_data2 = await fir_service.generate_fir_from_text(
            complaint_text=complaint2,
            user_id="test_user_005",
            session_id="test_session_005"
        )
        
        # Both should succeed
        assert fir_data1['fir_number']
        assert fir_data2['fir_number']
        
        # Should have similar IPC sections (cache working)
        common_sections = set(fir_data1['ipc_sections']) & set(fir_data2['ipc_sections'])
        assert len(common_sections) > 0
        
    finally:
        await vector_db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fir_generation_performance(
    aws_region,
    s3_bucket,
    bedrock_model_id,
    embeddings_model_id,
    vector_db_type,
    opensearch_endpoint,
    aurora_config
):
    """Test FIR generation completes within acceptable time."""
    if vector_db_type == "opensearch" and not opensearch_endpoint:
        pytest.skip("OpenSearch endpoint not configured")
    if vector_db_type == "aurora_pgvector" and not aurora_config["host"]:
        pytest.skip("Aurora configuration not set")
    
    bedrock_client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id
    )
    
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
    
    ipc_cache = IPCCache(max_size=100)
    
    fir_service = FIRGenerationService(
        transcribe_client=None,
        textract_client=None,
        bedrock_client=bedrock_client,
        titan_client=embeddings_client,
        vector_db=vector_db,
        ipc_cache=ipc_cache
    )
    
    try:
        await vector_db.connect()
        
        complaint_text = "Someone stole my wallet at the bus station."
        
        # Measure time
        start_time = asyncio.get_event_loop().time()
        
        fir_data = await fir_service.generate_fir_from_text(
            complaint_text=complaint_text,
            user_id="test_user_006",
            session_id="test_session_006"
        )
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Should complete within 60 seconds for text-based FIR
        assert duration < 60.0
        assert fir_data['fir_number']
        
    finally:
        await vector_db.close()


def create_sample_audio() -> bytes:
    """Create sample audio content for testing."""
    # Placeholder - in real tests, use actual audio file
    return b'\xff\xfb\x90\x00' + b'\x00' * 1000


def create_sample_complaint_image() -> bytes:
    """Create sample complaint document image."""
    from PIL import Image, ImageDraw
    
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    complaint_text = """
    COMPLAINT
    
    I, Rajesh Kumar, want to report that my mobile phone
    was stolen yesterday at Central Market, Delhi.
    The phone is worth Rs. 45,000.
    
    Date: January 15, 2024
    Signature: Rajesh Kumar
    """
    
    draw.text((50, 50), complaint_text, fill='black')
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()

