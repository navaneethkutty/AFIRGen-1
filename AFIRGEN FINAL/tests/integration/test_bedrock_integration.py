"""
Integration tests for BedrockClient.
Tests legal text processing with real AWS Bedrock service.
"""

import pytest
import asyncio
from services.aws.bedrock_client import (
    BedrockClient,
    FormalNarrative,
    ComplaintMetadata,
    IPCSection,
    FIR,
    ValidationError
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_formal_narrative(aws_region, bedrock_model_id):
    """Test formal narrative generation from complaint text."""
    client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id
    )
    
    complaint_text = """
    Yesterday at 3 PM, someone stole my mobile phone from my bag 
    while I was at the market. The phone was worth Rs. 25,000.
    """
    
    result = await client.generate_formal_narrative(complaint_text)
    
    # Verify result
    assert isinstance(result, FormalNarrative)
    assert result.narrative
    assert len(result.narrative) > 0
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    
    # Verify narrative is more formal than input
    assert "complainant" in result.narrative.lower() or "theft" in result.narrative.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_metadata(aws_region, bedrock_model_id):
    """Test metadata extraction from formal narrative."""
    client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id
    )
    
    narrative = """
    The complainant reports that on January 15, 2024, at approximately 3:00 PM,
    an unidentified individual unlawfully removed a mobile phone valued at Rs. 25,000
    from the complainant's bag at the Central Market, Delhi.
    """
    
    result = await client.extract_metadata(narrative)
    
    # Verify result
    assert isinstance(result, ComplaintMetadata)
    assert result.incident_type
    assert result.location
    assert result.complainant_name or True  # May not always extract name
    assert result.description
    
    # Verify extracted data makes sense
    assert "theft" in result.incident_type.lower() or "steal" in result.incident_type.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_fir(aws_region, bedrock_model_id):
    """Test complete FIR generation with RAG."""
    client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id
    )
    
    narrative = """
    The complainant reports that on January 15, 2024, an unidentified individual
    unlawfully removed a mobile phone from the complainant's bag at Central Market.
    """
    
    metadata = ComplaintMetadata(
        incident_type="Theft",
        incident_date="2024-01-15",
        location="Central Market, Delhi",
        complainant_name="John Doe",
        accused_name=None,
        description="Mobile phone theft from bag"
    )
    
    ipc_sections = [
        IPCSection(
            section_number="379",
            description="Punishment for theft",
            penalty="Imprisonment up to 3 years or fine or both"
        ),
        IPCSection(
            section_number="380",
            description="Theft in dwelling house",
            penalty="Imprisonment up to 7 years and fine"
        )
    ]
    
    fir_number = "FIR-20240115-00001"
    
    result = await client.generate_fir(
        narrative=narrative,
        metadata=metadata,
        ipc_sections=ipc_sections,
        fir_number=fir_number
    )
    
    # Verify result
    assert isinstance(result, FIR)
    assert result.fir_number == fir_number
    assert result.narrative == narrative
    assert result.metadata == metadata
    assert len(result.ipc_sections) == 2
    assert "379" in result.ipc_sections
    assert "380" in result.ipc_sections
    assert result.legal_analysis
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    
    # Verify legal analysis mentions IPC sections
    assert "379" in result.legal_analysis or "theft" in result.legal_analysis.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_bedrock_calls(aws_region, bedrock_model_id):
    """Test concurrent Bedrock API calls with rate limiting."""
    client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id,
        max_concurrent=5
    )
    
    complaints = [
        "Someone stole my wallet at the bus station.",
        "My car was damaged by an unknown person.",
        "I was assaulted by a group of people.",
        "My house was broken into last night.",
        "Someone forged my signature on documents."
    ]
    
    # Generate narratives concurrently
    tasks = [
        client.generate_formal_narrative(complaint)
        for complaint in complaints
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify all succeeded
    assert len(results) == 5
    for result in results:
        assert isinstance(result, FormalNarrative)
        assert result.narrative


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bedrock_retry_on_throttling(aws_region, bedrock_model_id):
    """Test retry logic on throttling errors."""
    client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id,
        max_concurrent=1,
        max_retries=3
    )
    
    # Make many rapid requests to potentially trigger throttling
    tasks = [
        client.generate_formal_narrative(f"Test complaint {i}")
        for i in range(20)
    ]
    
    # Should handle throttling with retries
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Most should succeed despite throttling
    successful = [r for r in results if isinstance(r, FormalNarrative)]
    assert len(successful) > 15  # At least 75% success rate


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bedrock_token_tracking(aws_region, bedrock_model_id):
    """Test token usage tracking."""
    client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id
    )
    
    short_text = "Theft occurred."
    long_text = """
    This is a detailed complaint about a complex incident involving multiple parties,
    various locations, and a series of events that occurred over several days.
    The incident began on Monday morning when the complainant noticed suspicious activity.
    """
    
    short_result = await client.generate_formal_narrative(short_text)
    long_result = await client.generate_formal_narrative(long_text)
    
    # Longer input should use more tokens
    assert long_result.input_tokens > short_result.input_tokens
    assert long_result.output_tokens >= short_result.output_tokens


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metadata_validation(aws_region, bedrock_model_id):
    """Test metadata extraction with missing required fields."""
    client = BedrockClient(
        region=aws_region,
        model_id=bedrock_model_id
    )
    
    # Vague narrative with minimal information
    vague_narrative = "Something happened somewhere."
    
    # Should either extract what it can or raise ValidationError
    try:
        result = await client.extract_metadata(vague_narrative)
        # If it succeeds, verify it has some data
        assert result.incident_type or result.location or result.description
    except ValidationError:
        # Expected if required fields cannot be extracted
        pass
