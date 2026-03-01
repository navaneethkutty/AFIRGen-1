"""
TitanEmbeddingsClient for generating embeddings using Amazon Titan.
Supports batch processing with retry logic.
"""

import asyncio
import json
import logging
from typing import List
import numpy as np
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class TitanEmbeddingsError(Exception):
    """Exception raised for Titan Embeddings errors."""
    pass


class TitanEmbeddingsClient:
    """
    Manages embedding generation using Amazon Titan Embeddings.
    Generates 1536-dimensional embeddings with batch support.
    """
    
    EMBEDDING_DIMENSION = 1536
    BATCH_SIZE = 25
    
    def __init__(
        self,
        region: str,
        model_id: str = "amazon.titan-embed-text-v1",
        max_retries: int = 3
    ):
        """
        Initialize TitanEmbeddingsClient.
        
        Args:
            region: AWS region
            model_id: Titan embeddings model ID
            max_retries: Maximum retry attempts
        """
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
        self.max_retries = max_retries
        self.region = region
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for single text.
        
        Args:
            text: Input text
        
        Returns:
            1536-dimensional numpy array
        
        Raises:
            TitanEmbeddingsError: Generation failed after retries
        """
        if not text or not text.strip():
            raise TitanEmbeddingsError("Input text cannot be empty")
        
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                # Prepare request body
                body = json.dumps({
                    "inputText": text.strip()
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
                embedding = np.array(response_body['embedding'], dtype=np.float32)
                
                # Validate dimensionality
                if len(embedding) != self.EMBEDDING_DIMENSION:
                    raise TitanEmbeddingsError(
                        f"Invalid embedding dimension: {len(embedding)}, expected {self.EMBEDDING_DIMENSION}"
                    )
                
                logger.info(f"Generated embedding for text (length: {len(text)})")
                return embedding
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                # Check if error is retryable
                if error_code in ['ThrottlingException', 'ServiceUnavailable', 'InternalServerError']:
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        raise TitanEmbeddingsError(f"Max retries exceeded: {str(e)}")
                    
                    # Exponential backoff
                    wait_time = min(2 ** retry_count, 30)
                    logger.warning(f"Retrying embedding generation after {wait_time}s (attempt {retry_count})")
                    await asyncio.sleep(wait_time)
                else:
                    raise TitanEmbeddingsError(f"Embedding generation failed: {str(e)}")
            
            except Exception as e:
                logger.error(f"Unexpected error during embedding generation: {e}")
                raise TitanEmbeddingsError(f"Embedding generation failed: {str(e)}")
        
        raise TitanEmbeddingsError("Max retries exceeded")
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of input texts
        
        Returns:
            List of 1536-dimensional numpy arrays
        
        Raises:
            TitanEmbeddingsError: Generation failed for any text
        """
        if not texts:
            return []
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i:i + self.BATCH_SIZE]
            logger.info(f"Processing batch {i // self.BATCH_SIZE + 1} ({len(batch)} texts)")
            
            # Generate embeddings concurrently within batch
            tasks = [self.generate_embedding(text) for text in batch]
            batch_embeddings = await asyncio.gather(*tasks)
            embeddings.extend(batch_embeddings)
        
        logger.info(f"Generated {len(embeddings)} embeddings in total")
        return embeddings
    
    def validate_embedding(self, embedding: np.ndarray) -> bool:
        """
        Validate embedding dimensionality and values.
        
        Args:
            embedding: Embedding array to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(embedding, np.ndarray):
            return False
        
        if len(embedding) != self.EMBEDDING_DIMENSION:
            return False
        
        if not np.isfinite(embedding).all():
            return False
        
        return True
