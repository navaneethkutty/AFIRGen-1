"""
Unit tests for BedrockClient.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from io import BytesIO

import sys
sys.path.insert(0, 'AFIRGEN FINAL')

from services.aws.bedrock_client import (
    BedrockClient,
    FormalNarrative,
    ComplaintMetadata,
    IPCSection,
    FIR,
    BedrockError,
    ValidationError
)


@pytest.fixture
def bedrock_client():
    """Create BedrockClient instance for testing."""
    with patch('boto3.client'):
        client = BedrockClient(
            region='us-east-1',
            model_id='anthropic.claude-3-sonnet-20240229-v1:0'
        )
        return client


@pytest.fixture
def mock_bedrock_response():
    """Create mock Bedrock response."""
    return {
        'content': [{'text': 'Generated text response'}],
        'usage': {
            'input_tokens': 100,
            'output_tokens': 50
        }
    }


class TestBedrockClient:
    """Test suite for BedrockClient."""
    
    def test_init(self, bedrock_client):
        """Test client initialization."""
        assert bedrock_client.model_id == 'anthropic.claude-3-sonnet-20240229-v1:0'
        assert bedrock_client.region == 'us-east-1'
        assert bedrock_client.max_retries == 3
        assert bedrock_client.semaphore._value == 10
    
    @pytest.mark.asyncio
    async def test_generate_formal_narrative_success(self, bedrock_client):
        """Test successful formal narrative generation."""
        mock_response = {
            'content': [{'text': 'On the date of incident, the complainant reported theft of property.'}],
            'usage': {'input_tokens': 120, 'output_tokens': 45}
        }
        
        bedrock_client._invoke_model = AsyncMock(return_value=mock_response)
        
        result = await bedrock_client.generate_formal_narrative(
            "Someone stole my phone yesterday"
        )
        
        assert isinstance(result, FormalNarrative)
        assert len(result.narrative) > 0
        assert result.input_tokens == 120
        assert result.output_tokens == 45
    
    
    @pytest.mark.asyncio
    async def test_extract_metadata_success(self, bedrock_client):
        """Test successful metadata extraction."""
        metadata_json = {
            'incident_type': 'theft',
            'incident_date': '2024-01-15',
            'location': 'Mumbai',
            'complainant_name': 'John Doe',
            'accused_name': 'Jane Smith',
            'description': 'Mobile phone theft'
        }
        
        mock_response = {
            'content': [{'text': json.dumps(metadata_json)}],
            'usage': {'input_tokens': 80, 'output_tokens': 60}
        }
        
        bedrock_client._invoke_model = AsyncMock(return_value=mock_response)
        
        result = await bedrock_client.extract_metadata(
            "Formal narrative about theft incident"
        )
        
        assert isinstance(result, ComplaintMetadata)
        assert result.incident_type == 'theft'
        assert result.location == 'Mumbai'
        assert result.complainant_name == 'John Doe'
    
    @pytest.mark.asyncio
    async def test_extract_metadata_with_markdown(self, bedrock_client):
        """Test metadata extraction with markdown code blocks."""
        metadata_json = {
            'incident_type': 'assault',
            'incident_date': None,
            'location': 'Delhi',
            'complainant_name': 'Test User',
            'accused_name': None,
            'description': 'Physical assault'
        }
        
        mock_response = {
            'content': [{'text': f'```json\n{json.dumps(metadata_json)}\n```'}],
            'usage': {'input_tokens': 80, 'output_tokens': 60}
        }
        
        bedrock_client._invoke_model = AsyncMock(return_value=mock_response)
        
        result = await bedrock_client.extract_metadata("Narrative")
        
        assert result.incident_type == 'assault'
        assert result.incident_date is None
        assert result.accused_name is None
    
    @pytest.mark.asyncio
    async def test_extract_metadata_missing_fields(self, bedrock_client):
        """Test metadata extraction with missing required fields."""
        incomplete_json = {
            'incident_type': 'theft',
            'location': 'Mumbai'
            # Missing complainant_name and description
        }
        
        mock_response = {
            'content': [{'text': json.dumps(incomplete_json)}],
            'usage': {'input_tokens': 80, 'output_tokens': 60}
        }
        
        bedrock_client._invoke_model = AsyncMock(return_value=mock_response)
        
        with pytest.raises(ValidationError) as exc_info:
            await bedrock_client.extract_metadata("Narrative")
        
        assert "Missing required fields" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_fir_success(self, bedrock_client):
        """Test successful FIR generation."""
        metadata = ComplaintMetadata(
            incident_type='theft',
            incident_date='2024-01-15',
            location='Mumbai',
            complainant_name='John Doe',
            accused_name='Jane Smith',
            description='Mobile phone theft'
        )
        
        ipc_sections = [
            IPCSection(
                section_number='379',
                description='Punishment for theft',
                penalty='Imprisonment up to 3 years'
            )
        ]
        
        mock_response = {
            'content': [{'text': 'Complete FIR document with legal analysis...'}],
            'usage': {'input_tokens': 500, 'output_tokens': 800}
        }
        
        bedrock_client._invoke_model = AsyncMock(return_value=mock_response)
        
        result = await bedrock_client.generate_fir(
            narrative="Formal narrative",
            metadata=metadata,
            ipc_sections=ipc_sections,
            fir_number='FIR-2024-001'
        )
        
        assert isinstance(result, FIR)
        assert result.fir_number == 'FIR-2024-001'
        assert result.metadata == metadata
        assert '379' in result.ipc_sections
        assert len(result.legal_analysis) > 0
        assert result.input_tokens == 500
        assert result.output_tokens == 800
    
    @pytest.mark.asyncio
    async def test_invoke_model_success(self, bedrock_client):
        """Test successful model invocation."""
        mock_bedrock = MagicMock()
        mock_response_body = {
            'content': [{'text': 'Response text'}],
            'usage': {'input_tokens': 100, 'output_tokens': 50}
        }
        
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: json.dumps(mock_response_body).encode())
        }
        
        bedrock_client.bedrock_client = mock_bedrock
        
        result = await bedrock_client._invoke_model(
            prompt="Test prompt",
            max_tokens=500,
            temperature=0.3
        )
        
        assert result['content'][0]['text'] == 'Response text'
        assert result['usage']['input_tokens'] == 100
        assert result['usage']['output_tokens'] == 50
    
    @pytest.mark.asyncio
    async def test_invoke_model_throttling_retry(self, bedrock_client):
        """Test retry logic on throttling."""
        from botocore.exceptions import ClientError
        
        mock_bedrock = MagicMock()
        
        # First call raises throttling error, second succeeds
        throttling_error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'invoke_model'
        )
        
        success_response = {
            'body': Mock(read=lambda: json.dumps({
                'content': [{'text': 'Success'}],
                'usage': {'input_tokens': 100, 'output_tokens': 50}
            }).encode())
        }
        
        mock_bedrock.invoke_model.side_effect = [throttling_error, success_response]
        bedrock_client.bedrock_client = mock_bedrock
        
        result = await bedrock_client._invoke_model(
            prompt="Test",
            max_tokens=500,
            temperature=0.3
        )
        
        assert result['content'][0]['text'] == 'Success'
        assert mock_bedrock.invoke_model.call_count == 2
    
    @pytest.mark.asyncio
    async def test_invoke_model_max_retries_exceeded(self, bedrock_client):
        """Test max retries exceeded."""
        from botocore.exceptions import ClientError
        
        mock_bedrock = MagicMock()
        throttling_error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'invoke_model'
        )
        
        mock_bedrock.invoke_model.side_effect = throttling_error
        bedrock_client.bedrock_client = mock_bedrock
        
        with pytest.raises(BedrockError) as exc_info:
            await bedrock_client._invoke_model(
                prompt="Test",
                max_tokens=500,
                temperature=0.3
            )
        
        assert "Max retries exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_invoke_model_non_retryable_error(self, bedrock_client):
        """Test non-retryable error handling."""
        from botocore.exceptions import ClientError
        
        mock_bedrock = MagicMock()
        validation_error = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}},
            'invoke_model'
        )
        
        mock_bedrock.invoke_model.side_effect = validation_error
        bedrock_client.bedrock_client = mock_bedrock
        
        with pytest.raises(BedrockError) as exc_info:
            await bedrock_client._invoke_model(
                prompt="Test",
                max_tokens=500,
                temperature=0.3
            )
        
        assert "Bedrock invocation failed" in str(exc_info.value)
        assert mock_bedrock.invoke_model.call_count == 1  # No retries
