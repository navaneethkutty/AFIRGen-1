"""
BedrockClient for legal text processing using Claude 3 Sonnet.
Implements rate limiting, retry logic, and token usage tracking.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


@dataclass
class FormalNarrative:
    """Formal legal narrative result."""
    narrative: str
    input_tokens: int
    output_tokens: int


@dataclass
class ComplaintMetadata:
    """Extracted complaint metadata."""
    incident_type: str
    incident_date: Optional[str]
    location: str
    complainant_name: str
    accused_name: Optional[str]
    description: str


@dataclass
class IPCSection:
    """IPC section information."""
    section_number: str
    description: str
    penalty: str


@dataclass
class FIR:
    """Complete FIR document."""
    fir_number: str
    narrative: str
    metadata: ComplaintMetadata
    ipc_sections: List[str]
    legal_analysis: str
    input_tokens: int
    output_tokens: int


class BedrockError(Exception):
    """Exception raised for Bedrock errors."""
    pass


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class BedrockClient:
    """
    Manages legal text processing using Claude 3 Sonnet via Bedrock.
    Implements rate limiting, retry logic, and token usage tracking.
    """
    
    def __init__(
        self,
        region: str,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        max_concurrent: int = 10,
        max_retries: int = 3
    ):
        """
        Initialize BedrockClient.
        
        Args:
            region: AWS region
            model_id: Bedrock model ID
            max_concurrent: Maximum concurrent API calls
            max_retries: Maximum retry attempts
        """
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
        self.max_retries = max_retries
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.region = region
    
    async def generate_formal_narrative(
        self,
        complaint_text: str
    ) -> FormalNarrative:
        """
        Convert raw complaint text to formal legal narrative.
        
        Args:
            complaint_text: Raw complaint text from user
        
        Returns:
            FormalNarrative with formatted legal text (max 3 sentences)
        
        Raises:
            BedrockError: Generation failed after retries
        """
        prompt = f"""Convert the following complaint into a formal legal narrative. 
Use professional legal language and keep it concise (maximum 3 sentences).

Complaint: {complaint_text}

Formal Narrative:"""
        
        response = await self._invoke_model(
            prompt=prompt,
            max_tokens=500,
            temperature=0.3
        )
        
        narrative = response['content'][0]['text'].strip()
        
        return FormalNarrative(
            narrative=narrative,
            input_tokens=response['usage']['input_tokens'],
            output_tokens=response['usage']['output_tokens']
        )
    
    async def extract_metadata(
        self,
        narrative: str
    ) -> ComplaintMetadata:
        """
        Extract structured metadata from formal narrative.
        
        Args:
            narrative: Formal legal narrative
        
        Returns:
            ComplaintMetadata with incident type, date, location, parties
        
        Raises:
            BedrockError: Extraction failed after retries
            ValidationError: Missing required fields
        """
        prompt = f"""Extract the following information from this legal narrative and return as JSON:
- incident_type: Type of incident (e.g., theft, assault, fraud)
- incident_date: Date of incident (YYYY-MM-DD format, or null if not mentioned)
- location: Location where incident occurred
- complainant_name: Name of complainant
- accused_name: Name of accused (or null if not mentioned)
- description: Brief description of incident

Narrative: {narrative}

Return only valid JSON with these exact field names:"""
        
        response = await self._invoke_model(
            prompt=prompt,
            max_tokens=300,
            temperature=0.1
        )
        
        # Parse JSON response
        try:
            content = response['content'][0]['text'].strip()
            # Extract JSON from response (may have markdown code blocks)
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            metadata_dict = json.loads(content)
            
            # Validate required fields
            required_fields = ['incident_type', 'location', 'complainant_name', 'description']
            missing_fields = [f for f in required_fields if not metadata_dict.get(f)]
            if missing_fields:
                raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
            
            return ComplaintMetadata(
                incident_type=metadata_dict['incident_type'],
                incident_date=metadata_dict.get('incident_date'),
                location=metadata_dict['location'],
                complainant_name=metadata_dict['complainant_name'],
                accused_name=metadata_dict.get('accused_name'),
                description=metadata_dict['description']
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse metadata JSON: {e}")
            raise BedrockError(f"Invalid JSON response from model: {str(e)}")
    
    async def generate_fir(
        self,
        narrative: str,
        metadata: ComplaintMetadata,
        ipc_sections: List[IPCSection],
        fir_number: str
    ) -> FIR:
        """
        Generate complete FIR using RAG with IPC sections.
        
        Args:
            narrative: Formal legal narrative
            metadata: Extracted complaint metadata
            ipc_sections: Relevant IPC sections from vector search
            fir_number: FIR number to assign
        
        Returns:
            Complete FIR in standard format
        
        Raises:
            BedrockError: Generation failed after retries
        """
        # Format IPC sections for context
        ipc_context = "\n\n".join([
            f"Section {sec.section_number}: {sec.description}\nPenalty: {sec.penalty}"
            for sec in ipc_sections
        ])
        
        prompt = f"""Generate a complete First Information Report (FIR) based on the following information:

NARRATIVE:
{narrative}

INCIDENT DETAILS:
- Type: {metadata.incident_type}
- Date: {metadata.incident_date or 'Not specified'}
- Location: {metadata.location}
- Complainant: {metadata.complainant_name}
- Accused: {metadata.accused_name or 'Unknown'}

RELEVANT IPC SECTIONS:
{ipc_context}

Generate a formal FIR document that includes:
1. A detailed legal analysis of the incident
2. Application of the relevant IPC sections
3. Recommended charges based on the evidence

FIR Document:"""
        
        response = await self._invoke_model(
            prompt=prompt,
            max_tokens=2048,
            temperature=0.5
        )
        
        legal_analysis = response['content'][0]['text'].strip()
        
        return FIR(
            fir_number=fir_number,
            narrative=narrative,
            metadata=metadata,
            ipc_sections=[sec.section_number for sec in ipc_sections],
            legal_analysis=legal_analysis,
            input_tokens=response['usage']['input_tokens'],
            output_tokens=response['usage']['output_tokens']
        )
    
    async def _invoke_model(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """
        Invoke Bedrock model with retry logic and rate limiting.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
        
        Returns:
            Model response dictionary
        
        Raises:
            BedrockError: Invocation failed after retries
        """
        async with self.semaphore:
            retry_count = 0
            
            while retry_count < self.max_retries:
                try:
                    # Prepare request body for Claude
                    body = json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    })
                    
                    # Invoke model
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.bedrock_client.invoke_model(
                            modelId=self.model_id,
                            body=body,
                            contentType='application/json',
                            accept='application/json'
                        )
                    )
                    
                    # Parse response
                    response_body = json.loads(response['body'].read())
                    
                    # Log token usage
                    logger.info(
                        f"Bedrock invocation - Input tokens: {response_body['usage']['input_tokens']}, "
                        f"Output tokens: {response_body['usage']['output_tokens']}"
                    )
                    
                    return response_body
                    
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    
                    # Check if error is retryable
                    if error_code in ['ThrottlingException', 'ServiceUnavailable', 'InternalServerError']:
                        retry_count += 1
                        if retry_count >= self.max_retries:
                            raise BedrockError(f"Max retries exceeded: {str(e)}")
                        
                        # Exponential backoff with jitter
                        wait_time = min(2 ** retry_count + (asyncio.get_event_loop().time() % 1), 30)
                        logger.warning(f"Retrying Bedrock call after {wait_time}s (attempt {retry_count})")
                        await asyncio.sleep(wait_time)
                    else:
                        # Non-retryable error
                        raise BedrockError(f"Bedrock invocation failed: {str(e)}")
                
                except Exception as e:
                    logger.error(f"Unexpected error during Bedrock invocation: {e}")
                    raise BedrockError(f"Bedrock invocation failed: {str(e)}")
            
            raise BedrockError("Max retries exceeded")
