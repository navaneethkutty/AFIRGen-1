"""
Prompt templates for Claude interactions.
Defines prompts for legal narrative generation, metadata extraction, and FIR generation.
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class PromptConfig:
    """Configuration for a prompt template."""
    template: str
    temperature: float
    max_tokens: int
    required_placeholders: List[str]


class PromptTemplates:
    """Collection of prompt templates for legal text processing."""
    
    LEGAL_NARRATIVE = PromptConfig(
        template="""Convert the following complaint into a formal legal narrative.
Use professional legal language and keep it concise (maximum 3 sentences).
Focus on the key facts: what happened, when, where, and who was involved.

Complaint: {complaint_text}

Formal Legal Narrative:""",
        temperature=0.3,
        max_tokens=500,
        required_placeholders=['complaint_text']
    )
    
    METADATA_EXTRACTION = PromptConfig(
        template="""Extract the following information from this legal narrative and return as JSON:
- incident_type: Type of incident (e.g., theft, assault, fraud, robbery, burglary, cheating, harassment)
- incident_date: Date of incident in YYYY-MM-DD format (or null if not mentioned)
- location: Location where incident occurred (city, area, or address)
- complainant_name: Name of the person filing the complaint
- accused_name: Name of the accused person (or null if not mentioned or unknown)
- description: Brief description of the incident (1-2 sentences)

Legal Narrative: {narrative}

Return only valid JSON with these exact field names. Do not include any explanation or markdown formatting:""",
        temperature=0.1,
        max_tokens=300,
        required_placeholders=['narrative']
    )
    
    FIR_GENERATION = PromptConfig(
        template="""Generate a complete First Information Report (FIR) based on the following information.
The FIR should be formal, legally sound, and follow Indian legal standards.

FORMAL NARRATIVE:
{narrative}

INCIDENT DETAILS:
- Type: {incident_type}
- Date: {incident_date}
- Location: {location}
- Complainant: {complainant_name}
- Accused: {accused_name}
- Description: {description}

RELEVANT IPC SECTIONS:
{ipc_sections}

Generate a comprehensive FIR document that includes:
1. A detailed legal analysis of the incident
2. Application and explanation of the relevant IPC sections
3. Assessment of evidence and circumstances
4. Recommended charges based on the facts and applicable law
5. Any additional legal considerations

FIR Document:""",
        temperature=0.5,
        max_tokens=2048,
        required_placeholders=[
            'narrative', 'incident_type', 'incident_date', 'location',
            'complainant_name', 'accused_name', 'description', 'ipc_sections'
        ]
    )
    
    @classmethod
    def format_legal_narrative_prompt(cls, complaint_text: str) -> Dict[str, Any]:
        """
        Format prompt for legal narrative generation.
        
        Args:
            complaint_text: Raw complaint text
        
        Returns:
            Dictionary with prompt, temperature, and max_tokens
        """
        prompt = cls.LEGAL_NARRATIVE.template.format(complaint_text=complaint_text)
        return {
            'prompt': prompt,
            'temperature': cls.LEGAL_NARRATIVE.temperature,
            'max_tokens': cls.LEGAL_NARRATIVE.max_tokens
        }
    
    @classmethod
    def format_metadata_extraction_prompt(cls, narrative: str) -> Dict[str, Any]:
        """
        Format prompt for metadata extraction.
        
        Args:
            narrative: Formal legal narrative
        
        Returns:
            Dictionary with prompt, temperature, and max_tokens
        """
        prompt = cls.METADATA_EXTRACTION.template.format(narrative=narrative)
        return {
            'prompt': prompt,
            'temperature': cls.METADATA_EXTRACTION.temperature,
            'max_tokens': cls.METADATA_EXTRACTION.max_tokens
        }
    
    @classmethod
    def format_fir_generation_prompt(
        cls,
        narrative: str,
        incident_type: str,
        incident_date: str,
        location: str,
        complainant_name: str,
        accused_name: str,
        description: str,
        ipc_sections: str
    ) -> Dict[str, Any]:
        """
        Format prompt for FIR generation.
        
        Args:
            narrative: Formal legal narrative
            incident_type: Type of incident
            incident_date: Date of incident
            location: Location of incident
            complainant_name: Name of complainant
            accused_name: Name of accused
            description: Incident description
            ipc_sections: Formatted IPC sections text
        
        Returns:
            Dictionary with prompt, temperature, and max_tokens
        """
        prompt = cls.FIR_GENERATION.template.format(
            narrative=narrative,
            incident_type=incident_type,
            incident_date=incident_date or 'Not specified',
            location=location,
            complainant_name=complainant_name,
            accused_name=accused_name or 'Unknown',
            description=description,
            ipc_sections=ipc_sections
        )
        return {
            'prompt': prompt,
            'temperature': cls.FIR_GENERATION.temperature,
            'max_tokens': cls.FIR_GENERATION.max_tokens
        }
