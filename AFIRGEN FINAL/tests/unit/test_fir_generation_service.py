"""
Unit tests for FIRGenerationService.
Tests orchestration of FIR generation workflow with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
from io import BytesIO

import sys
sys.path.insert(0, 'AFIRGEN FINAL')

from services.fir_generation_service import FIRGenerationService
from services.aws.transcribe_client import TranscriptionResult
from services.aws.textract_client import ExtractionResult
from services.aws.bedrock_client import FormalNarrative, ComplaintMetadata, IPCSection, FIR
from services.cache.ipc_cache import IPCCache


@pytest.fixture
def mock_transcribe_client():
    """Create mock TranscribeClient."""
    client = AsyncMock()
    client.transcribe_audio = AsyncMock(return_value=TranscriptionResult(
        transcript="Transcribed complaint text",
        language_code="hi-IN",
        confidence=0.95,
        job_name="test-job-123",
        duration_seconds=120.0
    ))
    return client


@pytest.fixture
def mock_textract_client():
    """Create mock TextractClient."""
    client = AsyncMock()
    client.extract_text = AsyncMock(return_value=ExtractionResult(
        text="Extracted complaint text from document",
        confidence=0.98,
        page_count=1,
        form_fields={}
    ))
    return client


@pytest.fixture
def mock_bedrock_client():
    """Create mock BedrockClient."""
    client = AsyncMock()
    
    # Mock generate_formal_narrative
    client.generate_formal_narrative = AsyncMock(return_value=FormalNarrative(
        narrative="On the date of incident, the complainant reported theft of mobile phone.",
        input_tokens=100,
        output_tokens=50
    ))
    
    # Mock extract_metadata
    mock_metadata = ComplaintMetadata(
        incident_type="theft",
        incident_date="2024-01-15",
        location="Mumbai",
        complainant_name="John Doe",
        accused_name="Jane Smith",
        description="Mobile phone theft"
    )
    client.extract_metadata = AsyncMock(return_value=mock_metadata)
    
    # Mock generate_fir
    client.generate_fir = AsyncMock(return_value=FIR(
        fir_number="FIR-2024-TEST1234",
        narrative="Formal legal narrative",
        metadata=mock_metadata,
        ipc_sections=["IPC 379", "IPC 420"],
        legal_analysis="Legal analysis text",
        input_tokens=200,
        output_tokens=150
    ))
    
    return client


@pytest.fixture
def mock_titan_client():
    """Create mock TitanEmbeddingsClient."""
    import numpy as np
    client = AsyncMock()
    client.generate_embedding = AsyncMock(return_value=np.random.rand(1536))
    return client


@pytest.fixture
def mock_vector_db():
    """Create mock VectorDatabase."""
    db = AsyncMock()
    
    # Mock search result
    search_result = Mock()
    search_result.section_number = "IPC 379"
    search_result.description = "Theft"
    search_result.penalty = "3 years"
    
    db.similarity_search = AsyncMock(return_value=[search_result])
    return db


@pytest.fixture
def mock_ipc_cache():
    """Create mock IPCCache."""
    cache = Mock(spec=IPCCache)
    cache.get = Mock(return_value=None)  # Default: cache miss
    cache.put = Mock()
    cache.get_stats = Mock(return_value={
        'size': 0,
        'hits': 0,
        'misses': 0,
        'hit_rate': 0.0
    })
    cache.clear = Mock()
    return cache


@pytest.fixture
def fir_service(
    mock_transcribe_client,
    mock_textract_client,
    mock_bedrock_client,
    mock_titan_client,
    mock_vector_db,
    mock_ipc_cache
):
    """Create FIRGenerationService with mocked dependencies."""
    return FIRGenerationService(
        transcribe_client=mock_transcribe_client,
        textract_client=mock_textract_client,
        bedrock_client=mock_bedrock_client,
        titan_client=mock_titan_client,
        vector_db=mock_vector_db,
        ipc_cache=mock_ipc_cache,
        top_k_sections=5
    )


class TestFIRGenerationService:
    """Test suite for FIRGenerationService."""
    
    def test_initialization(self, fir_service):
        """Test service initializes correctly."""
        assert fir_service.top_k_sections == 5
        assert fir_service.transcribe_client is not None
        assert fir_service.textract_client is not None
        assert fir_service.bedrock_client is not None
        assert fir_service.titan_client is not None
        assert fir_service.vector_db is not None
        assert fir_service.ipc_cache is not None
    
    @pytest.mark.asyncio
    async def test_generate_fir_from_text_success(self, fir_service, mock_bedrock_client):
        """Test successful FIR generation from text."""
        result = await fir_service.generate_fir_from_text(
            complaint_text="Someone stole my phone",
            user_id="user-123",
            session_id="session-456"
        )
        
        # Verify result structure
        assert 'fir_number' in result
        assert 'narrative' in result
        assert 'metadata' in result
        assert 'ipc_sections' in result
        assert 'legal_analysis' in result
        assert 'user_id' in result
        assert 'session_id' in result
        assert 'created_at' in result
        assert 'token_usage' in result
        
        # Verify values
        assert result['user_id'] == "user-123"
        assert result['session_id'] == "session-456"
        assert isinstance(result['ipc_sections'], list)
        
        # Verify Bedrock client was called
        mock_bedrock_client.generate_formal_narrative.assert_called_once()
        mock_bedrock_client.extract_metadata.assert_called_once()
        mock_bedrock_client.generate_fir.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_fir_from_text_workflow(self, fir_service, mock_bedrock_client, mock_titan_client, mock_vector_db):
        """Test complete workflow for text-based FIR generation."""
        result = await fir_service.generate_fir_from_text(
            complaint_text="Theft complaint",
            user_id="user-123",
            session_id="session-456"
        )
        
        # Verify workflow steps
        # 1. Generate narrative
        mock_bedrock_client.generate_formal_narrative.assert_called_once_with("Theft complaint")
        
        # 2. Extract metadata
        mock_bedrock_client.extract_metadata.assert_called_once()
        
        # 3. Generate embedding and search
        mock_titan_client.generate_embedding.assert_called_once()
        mock_vector_db.similarity_search.assert_called_once()
        
        # 4. Generate FIR
        mock_bedrock_client.generate_fir.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_fir_from_audio_success(self, fir_service, mock_transcribe_client, mock_bedrock_client):
        """Test successful FIR generation from audio."""
        # Create mock audio file
        audio_file = Mock()
        audio_file.filename = "complaint.mp3"
        
        result = await fir_service.generate_fir_from_audio(
            audio_file=audio_file,
            language_code="hi-IN",
            user_id="user-123",
            session_id="session-456"
        )
        
        # Verify transcription was called
        mock_transcribe_client.transcribe_audio.assert_called_once_with(audio_file, "hi-IN")
        
        # Verify result includes transcription metadata
        assert 'transcription' in result
        assert result['transcription']['language_code'] == "hi-IN"
        assert result['transcription']['confidence'] == 0.95
        assert result['transcription']['duration_seconds'] == 120.0
        
        # Verify FIR was generated
        assert 'fir_number' in result
        assert 'narrative' in result
    
    @pytest.mark.asyncio
    async def test_generate_fir_from_image_success(self, fir_service, mock_textract_client, mock_bedrock_client):
        """Test successful FIR generation from image."""
        # Create mock image file
        image_file = Mock()
        image_file.filename = "complaint.jpg"
        
        result = await fir_service.generate_fir_from_image(
            image_file=image_file,
            user_id="user-123",
            session_id="session-456"
        )
        
        # Verify extraction was called
        mock_textract_client.extract_text.assert_called_once_with(image_file, extract_forms=True)
        
        # Verify result includes extraction metadata
        assert 'extraction' in result
        assert result['extraction']['confidence'] == 0.98
        assert result['extraction']['page_count'] == 1
        
        # Verify FIR was generated
        assert 'fir_number' in result
        assert 'narrative' in result
    
    @pytest.mark.asyncio
    async def test_retrieve_ipc_sections_cache_hit(self, fir_service, mock_ipc_cache, mock_titan_client, mock_vector_db):
        """Test IPC section retrieval with cache hit."""
        # Configure cache to return cached data
        cached_sections = [
            {'section_number': 'IPC 379', 'description': 'Theft', 'penalty': '3 years'}
        ]
        mock_ipc_cache.get.return_value = cached_sections
        
        result = await fir_service._retrieve_relevant_ipc_sections("theft narrative")
        
        # Verify cache was checked
        mock_ipc_cache.get.assert_called_once()
        
        # Verify embedding and search were NOT called (cache hit)
        mock_titan_client.generate_embedding.assert_not_called()
        mock_vector_db.similarity_search.assert_not_called()
        
        # Verify result
        assert len(result) == 1
        assert result[0].section_number == 'IPC 379'
    
    @pytest.mark.asyncio
    async def test_retrieve_ipc_sections_cache_miss(self, fir_service, mock_ipc_cache, mock_titan_client, mock_vector_db):
        """Test IPC section retrieval with cache miss."""
        # Configure cache to return None (cache miss)
        mock_ipc_cache.get.return_value = None
        
        result = await fir_service._retrieve_relevant_ipc_sections("theft narrative")
        
        # Verify cache was checked
        mock_ipc_cache.get.assert_called_once()
        
        # Verify embedding and search were called (cache miss)
        mock_titan_client.generate_embedding.assert_called_once_with("theft narrative")
        mock_vector_db.similarity_search.assert_called_once()
        
        # Verify result was cached
        mock_ipc_cache.put.assert_called_once()
        
        # Verify result
        assert len(result) == 1
        assert result[0].section_number == 'IPC 379'
    
    @pytest.mark.asyncio
    async def test_generate_fir_number_format(self, fir_service):
        """Test FIR number generation format."""
        fir_number = fir_service._generate_fir_number()
        
        # Verify format: FIR-YYYY-XXXXXXXX
        assert fir_number.startswith("FIR-")
        parts = fir_number.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 4  # Year
        assert len(parts[2]) == 8  # Unique ID
        assert parts[2].isupper()  # Uppercase
    
    @pytest.mark.asyncio
    async def test_generate_fir_number_uniqueness(self, fir_service):
        """Test FIR numbers are unique."""
        fir_numbers = set()
        
        for _ in range(100):
            fir_number = fir_service._generate_fir_number()
            fir_numbers.add(fir_number)
        
        # All should be unique
        assert len(fir_numbers) == 100
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, fir_service, mock_ipc_cache):
        """Test getting cache statistics."""
        stats = await fir_service.get_cache_stats()
        
        mock_ipc_cache.get_stats.assert_called_once()
        assert 'size' in stats
        assert 'hits' in stats
        assert 'misses' in stats
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, fir_service, mock_ipc_cache):
        """Test clearing cache."""
        await fir_service.clear_cache()
        
        mock_ipc_cache.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_token_usage_tracking(self, fir_service, mock_bedrock_client):
        """Test token usage is tracked in result."""
        result = await fir_service.generate_fir_from_text(
            complaint_text="Test complaint",
            user_id="user-123",
            session_id="session-456"
        )
        
        # Verify token usage is included
        assert 'token_usage' in result
        assert 'narrative_input' in result['token_usage']
        assert 'narrative_output' in result['token_usage']
        assert 'fir_input' in result['token_usage']
        assert 'fir_output' in result['token_usage']
        
        # Verify values
        assert result['token_usage']['narrative_input'] == 100
        assert result['token_usage']['narrative_output'] == 50
        assert result['token_usage']['fir_input'] == 200
        assert result['token_usage']['fir_output'] == 150
    
    @pytest.mark.asyncio
    async def test_metadata_structure(self, fir_service):
        """Test metadata structure in result."""
        result = await fir_service.generate_fir_from_text(
            complaint_text="Test complaint",
            user_id="user-123",
            session_id="session-456"
        )
        
        # Verify metadata structure
        metadata = result['metadata']
        assert 'incident_type' in metadata
        assert 'incident_date' in metadata
        assert 'location' in metadata
        assert 'complainant_name' in metadata
        assert 'accused_name' in metadata
        assert 'description' in metadata
        
        # Verify values
        assert metadata['incident_type'] == "theft"
        assert metadata['location'] == "Mumbai"
    
    @pytest.mark.asyncio
    async def test_error_propagation_from_transcribe(self, fir_service, mock_transcribe_client):
        """Test error propagation from transcribe client."""
        mock_transcribe_client.transcribe_audio.side_effect = Exception("Transcription failed")
        
        audio_file = Mock()
        
        with pytest.raises(Exception) as exc_info:
            await fir_service.generate_fir_from_audio(
                audio_file=audio_file,
                language_code="hi-IN",
                user_id="user-123",
                session_id="session-456"
            )
        
        assert "Transcription failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_error_propagation_from_textract(self, fir_service, mock_textract_client):
        """Test error propagation from textract client."""
        mock_textract_client.extract_text.side_effect = Exception("Extraction failed")
        
        image_file = Mock()
        
        with pytest.raises(Exception) as exc_info:
            await fir_service.generate_fir_from_image(
                image_file=image_file,
                user_id="user-123",
                session_id="session-456"
            )
        
        assert "Extraction failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_error_propagation_from_bedrock(self, fir_service, mock_bedrock_client):
        """Test error propagation from bedrock client."""
        mock_bedrock_client.generate_formal_narrative.side_effect = Exception("Bedrock failed")
        
        with pytest.raises(Exception) as exc_info:
            await fir_service.generate_fir_from_text(
                complaint_text="Test complaint",
                user_id="user-123",
                session_id="session-456"
            )
        
        assert "Bedrock failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_vector_search_with_top_k(self, fir_service, mock_vector_db, mock_ipc_cache):
        """Test vector search uses correct top_k parameter."""
        mock_ipc_cache.get.return_value = None  # Force cache miss
        
        await fir_service._retrieve_relevant_ipc_sections("test narrative")
        
        # Verify similarity_search was called with correct top_k
        call_args = mock_vector_db.similarity_search.call_args
        assert call_args[1]['top_k'] == 5
    
    @pytest.mark.asyncio
    async def test_created_at_timestamp(self, fir_service):
        """Test created_at timestamp is included."""
        result = await fir_service.generate_fir_from_text(
            complaint_text="Test complaint",
            user_id="user-123",
            session_id="session-456"
        )
        
        assert 'created_at' in result
        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(result['created_at'].replace('Z', '+00:00'))
    
    @pytest.mark.asyncio
    async def test_ipc_sections_in_result(self, fir_service):
        """Test IPC sections are included in result."""
        result = await fir_service.generate_fir_from_text(
            complaint_text="Test complaint",
            user_id="user-123",
            session_id="session-456"
        )
        
        assert 'ipc_sections' in result
        assert isinstance(result['ipc_sections'], list)
        assert len(result['ipc_sections']) > 0
