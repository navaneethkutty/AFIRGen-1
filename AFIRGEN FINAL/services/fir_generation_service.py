"""
FIR Generation Service - Orchestrates complete FIR generation workflow.
Coordinates AWS services, vector search, and caching for end-to-end FIR creation.
"""

import asyncio
import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import UploadFile

from services.aws.transcribe_client import TranscribeClient, TranscriptionResult
from services.aws.textract_client import TextractClient, ExtractionResult
from services.aws.bedrock_client import BedrockClient, FormalNarrative, ComplaintMetadata, IPCSection, FIR
from services.aws.titan_embeddings_client import TitanEmbeddingsClient
from services.vector_db.interface import VectorDatabaseInterface
from services.cache.ipc_cache import IPCCache


logger = logging.getLogger(__name__)


class FIRGenerationService:
    """
    Orchestrates complete FIR generation workflow with RAG.
    Coordinates all AWS services and implements caching.
    """
    
    def __init__(
        self,
        transcribe_client: TranscribeClient,
        textract_client: TextractClient,
        bedrock_client: BedrockClient,
        titan_client: TitanEmbeddingsClient,
        vector_db: VectorDatabaseInterface,
        ipc_cache: Optional[IPCCache] = None,
        top_k_sections: int = 5
    ):
        """
        Initialize FIR Generation Service.
        
        Args:
            transcribe_client: Client for audio transcription
            textract_client: Client for document OCR
            bedrock_client: Client for legal text processing
            titan_client: Client for embeddings generation
            vector_db: Vector database for IPC section retrieval
            ipc_cache: Optional cache for IPC sections
            top_k_sections: Number of IPC sections to retrieve
        """
        self.transcribe_client = transcribe_client
        self.textract_client = textract_client
        self.bedrock_client = bedrock_client
        self.titan_client = titan_client
        self.vector_db = vector_db
        self.ipc_cache = ipc_cache or IPCCache()
        self.top_k_sections = top_k_sections
    
    async def generate_fir_from_text(
        self,
        complaint_text: str,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Generate FIR from text complaint.
        
        Args:
            complaint_text: Raw complaint text
            user_id: User ID for RBAC
            session_id: Session ID for tracking
        
        Returns:
            Dictionary with FIR data and metadata
        """
        logger.info(f"Starting FIR generation from text for user {user_id}")
        
        try:
            # Step 1: Generate formal narrative
            narrative_result = await self.bedrock_client.generate_formal_narrative(
                complaint_text
            )
            logger.info("Generated formal narrative")
            
            # Step 2: Extract metadata
            metadata = await self.bedrock_client.extract_metadata(
                narrative_result.narrative
            )
            logger.info(f"Extracted metadata: {metadata.incident_type}")
            
            # Step 3: Retrieve relevant IPC sections
            ipc_sections = await self._retrieve_relevant_ipc_sections(
                narrative_result.narrative
            )
            logger.info(f"Retrieved {len(ipc_sections)} relevant IPC sections")
            
            # Step 4: Generate complete FIR
            fir_number = self._generate_fir_number()
            fir = await self.bedrock_client.generate_fir(
                narrative=narrative_result.narrative,
                metadata=metadata,
                ipc_sections=ipc_sections,
                fir_number=fir_number
            )
            logger.info(f"Generated FIR: {fir_number}")
            
            # Prepare response
            return {
                'fir_number': fir.fir_number,
                'narrative': fir.narrative,
                'metadata': {
                    'incident_type': metadata.incident_type,
                    'incident_date': metadata.incident_date,
                    'location': metadata.location,
                    'complainant_name': metadata.complainant_name,
                    'accused_name': metadata.accused_name,
                    'description': metadata.description
                },
                'ipc_sections': fir.ipc_sections,
                'legal_analysis': fir.legal_analysis,
                'user_id': user_id,
                'session_id': session_id,
                'created_at': datetime.utcnow().isoformat(),
                'token_usage': {
                    'narrative_input': narrative_result.input_tokens,
                    'narrative_output': narrative_result.output_tokens,
                    'fir_input': fir.input_tokens,
                    'fir_output': fir.output_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"FIR generation from text failed: {e}")
            raise
    
    async def generate_fir_from_audio(
        self,
        audio_file: UploadFile,
        language_code: Optional[str],
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Generate FIR from audio complaint.
        
        Args:
            audio_file: Audio file to transcribe
            language_code: Optional language code
            user_id: User ID for RBAC
            session_id: Session ID for tracking
        
        Returns:
            Dictionary with FIR data and metadata
        """
        logger.info(f"Starting FIR generation from audio for user {user_id}")
        
        try:
            # Step 1: Transcribe audio
            transcription = await self.transcribe_client.transcribe_audio(
                audio_file,
                language_code
            )
            logger.info(f"Transcribed audio: {len(transcription.transcript)} chars")
            
            # Step 2: Generate FIR from transcribed text
            fir_data = await self.generate_fir_from_text(
                complaint_text=transcription.transcript,
                user_id=user_id,
                session_id=session_id
            )
            
            # Add transcription metadata
            fir_data['transcription'] = {
                'language_code': transcription.language_code,
                'confidence': transcription.confidence,
                'duration_seconds': transcription.duration_seconds
            }
            
            return fir_data
            
        except Exception as e:
            logger.error(f"FIR generation from audio failed: {e}")
            raise
    
    async def generate_fir_from_image(
        self,
        image_file: UploadFile,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Generate FIR from document image.
        
        Args:
            image_file: Document image file
            user_id: User ID for RBAC
            session_id: Session ID for tracking
        
        Returns:
            Dictionary with FIR data and metadata
        """
        logger.info(f"Starting FIR generation from image for user {user_id}")
        
        try:
            # Step 1: Extract text from image
            extraction = await self.textract_client.extract_text(
                image_file,
                extract_forms=True
            )
            logger.info(f"Extracted text: {len(extraction.text)} chars")
            
            # Step 2: Generate FIR from extracted text
            fir_data = await self.generate_fir_from_text(
                complaint_text=extraction.text,
                user_id=user_id,
                session_id=session_id
            )
            
            # Add extraction metadata
            fir_data['extraction'] = {
                'confidence': extraction.confidence,
                'page_count': extraction.page_count,
                'form_fields_count': len(extraction.form_fields)
            }
            
            return fir_data
            
        except Exception as e:
            logger.error(f"FIR generation from image failed: {e}")
            raise
    
    async def _retrieve_relevant_ipc_sections(
        self,
        narrative: str
    ) -> List[IPCSection]:
        """
        Retrieve relevant IPC sections using RAG with caching.
        
        Args:
            narrative: Formal legal narrative
        
        Returns:
            List of relevant IPC sections
        """
        # Check cache first
        cached_sections = self.ipc_cache.get(narrative)
        if cached_sections:
            logger.info("Retrieved IPC sections from cache")
            return [
                IPCSection(
                    section_number=sec['section_number'],
                    description=sec['description'],
                    penalty=sec['penalty']
                )
                for sec in cached_sections
            ]
        
        # Generate embedding for narrative
        embedding = await self.titan_client.generate_embedding(narrative)
        
        # Perform vector similarity search
        search_results = await self.vector_db.similarity_search(
            index_name='ipc_sections',
            query_vector=embedding,
            top_k=self.top_k_sections
        )
        
        # Convert to IPCSection objects
        ipc_sections = [
            IPCSection(
                section_number=result.section_number,
                description=result.description,
                penalty=result.penalty
            )
            for result in search_results
        ]
        
        # Cache results
        cached_data = [
            {
                'section_number': sec.section_number,
                'description': sec.description,
                'penalty': sec.penalty
            }
            for sec in ipc_sections
        ]
        self.ipc_cache.put(narrative, cached_data)
        
        logger.info(f"Retrieved and cached {len(ipc_sections)} IPC sections")
        return ipc_sections
    
    def _generate_fir_number(self) -> str:
        """
        Generate unique FIR number.
        
        Returns:
            FIR number in format FIR-YYYY-XXXXXXXX
        """
        year = datetime.utcnow().year
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"FIR-{year}-{unique_id}"
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get IPC cache statistics.
        
        Returns:
            Cache statistics dictionary
        """
        return self.ipc_cache.get_stats()
    
    async def clear_cache(self) -> None:
        """Clear IPC cache."""
        self.ipc_cache.clear()
        logger.info("Cleared IPC cache")
