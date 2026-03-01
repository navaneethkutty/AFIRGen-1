"""
Abstract interface for vector database operations.
Supports both OpenSearch Serverless and Aurora pgvector implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""
    id: str
    section_number: str
    description: str
    penalty: str
    score: float
    metadata: Dict[str, Any]


class VectorDatabaseInterface(ABC):
    """
    Abstract interface for vector database operations.
    Implementations must support both OpenSearch and Aurora pgvector.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to vector database.
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        Close connection to vector database.
        """
        pass
    
    @abstractmethod
    async def create_index(
        self,
        index_name: str,
        dimension: int,
        metric: str = 'cosine'
    ) -> None:
        """
        Create vector index for similarity search.
        
        Args:
            index_name: Name of the index
            dimension: Dimensionality of vectors
            metric: Distance metric ('cosine', 'euclidean', 'dot_product')
        
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If index creation fails
        """
        pass
    
    @abstractmethod
    async def insert_vectors(
        self,
        index_name: str,
        vectors: List[np.ndarray],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Insert vectors with metadata into index.
        
        Args:
            index_name: Name of the index
            vectors: List of embedding vectors
            metadata: List of metadata dictionaries (must include section_number, description, penalty)
        
        Returns:
            List of inserted document IDs
        
        Raises:
            ValueError: If vectors and metadata lengths don't match
            RuntimeError: If insertion fails
        """
        pass
    
    @abstractmethod
    async def similarity_search(
        self,
        index_name: str,
        query_vector: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """
        Perform similarity search to find nearest vectors.
        
        Args:
            index_name: Name of the index
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters
        
        Returns:
            List of search results ordered by similarity score
        
        Raises:
            ValueError: If query_vector dimension doesn't match index
            RuntimeError: If search fails
        """
        pass
    
    @abstractmethod
    async def delete_vectors(
        self,
        index_name: str,
        ids: List[str]
    ) -> int:
        """
        Delete vectors by IDs.
        
        Args:
            index_name: Name of the index
            ids: List of document IDs to delete
        
        Returns:
            Number of vectors deleted
        
        Raises:
            RuntimeError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def index_exists(self, index_name: str) -> bool:
        """
        Check if index exists.
        
        Args:
            index_name: Name of the index
        
        Returns:
            True if index exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """
        Get statistics about the index.
        
        Args:
            index_name: Name of the index
        
        Returns:
            Dictionary with index statistics (vector_count, dimension, etc.)
        
        Raises:
            RuntimeError: If index doesn't exist
        """
        pass
