"""
OpenSearch Serverless vector database implementation.
Uses k-NN plugin with HNSW algorithm and cosine similarity.
"""

import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional
import numpy as np
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

from .interface import VectorDatabaseInterface, VectorSearchResult


logger = logging.getLogger(__name__)


class OpenSearchVectorDB(VectorDatabaseInterface):
    """
    OpenSearch Serverless implementation of vector database.
    Uses k-NN plugin with HNSW algorithm for similarity search.
    """
    
    def __init__(
        self,
        endpoint: str,
        region: str,
        index_name: str = 'ipc_sections',
        max_retries: int = 3
    ):
        """
        Initialize OpenSearch client.
        
        Args:
            endpoint: OpenSearch endpoint URL
            region: AWS region
            index_name: Default index name
            max_retries: Maximum retry attempts
        """
        self.endpoint = endpoint
        self.region = region
        self.index_name = index_name
        self.max_retries = max_retries
        self.client: Optional[OpenSearch] = None
    
    async def connect(self) -> None:
        """Establish connection to OpenSearch."""
        try:
            # Get AWS credentials for SigV4 authentication
            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region,
                'aoss',  # OpenSearch Serverless service name
                session_token=credentials.token
            )
            
            # Create OpenSearch client
            loop = asyncio.get_event_loop()
            self.client = await loop.run_in_executor(
                None,
                lambda: OpenSearch(
                    hosts=[{'host': self.endpoint, 'port': 443}],
                    http_auth=awsauth,
                    use_ssl=True,
                    verify_certs=True,
                    connection_class=RequestsHttpConnection,
                    timeout=30
                )
            )
            
            logger.info(f"Connected to OpenSearch at {self.endpoint}")
        except Exception as e:
            logger.error(f"Failed to connect to OpenSearch: {e}")
            raise ConnectionError(f"OpenSearch connection failed: {str(e)}")
    
    async def close(self) -> None:
        """Close OpenSearch connection."""
        if self.client:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.client.close)
            logger.info("Closed OpenSearch connection")
    
    async def create_index(
        self,
        index_name: str,
        dimension: int,
        metric: str = 'cosine'
    ) -> None:
        """Create k-NN index with HNSW algorithm."""
        if not self.client:
            raise RuntimeError("Not connected to OpenSearch")
        
        # Map metric names
        metric_map = {
            'cosine': 'cosinesimil',
            'euclidean': 'l2',
            'dot_product': 'innerproduct'
        }
        
        if metric not in metric_map:
            raise ValueError(f"Unsupported metric: {metric}")
        
        index_body = {
            'settings': {
                'index': {
                    'knn': True,
                    'knn.algo_param.ef_search': 512
                }
            },
            'mappings': {
                'properties': {
                    'embedding': {
                        'type': 'knn_vector',
                        'dimension': dimension,
                        'method': {
                            'name': 'hnsw',
                            'space_type': metric_map[metric],
                            'engine': 'nmslib',
                            'parameters': {
                                'ef_construction': 512,
                                'm': 16
                            }
                        }
                    },
                    'section_number': {'type': 'keyword'},
                    'description': {'type': 'text'},
                    'penalty': {'type': 'text'},
                    'metadata': {'type': 'object', 'enabled': True}
                }
            }
        }
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.indices.create(index=index_name, body=index_body)
            )
            logger.info(f"Created OpenSearch index: {index_name}")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise RuntimeError(f"Index creation failed: {str(e)}")
    
    async def insert_vectors(
        self,
        index_name: str,
        vectors: List[np.ndarray],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert vectors with metadata."""
        if not self.client:
            raise RuntimeError("Not connected to OpenSearch")
        
        if len(vectors) != len(metadata):
            raise ValueError("Vectors and metadata must have same length")
        
        ids = []
        
        for vector, meta in zip(vectors, metadata):
            doc_id = str(uuid.uuid4())
            
            document = {
                'embedding': vector.tolist(),
                'section_number': meta.get('section_number', ''),
                'description': meta.get('description', ''),
                'penalty': meta.get('penalty', ''),
                'metadata': meta
            }
            
            retry_count = 0
            while retry_count < self.max_retries:
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: self.client.index(
                            index=index_name,
                            id=doc_id,
                            body=document
                        )
                    )
                    ids.append(doc_id)
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count >= self.max_retries:
                        raise RuntimeError(f"Failed to insert vector: {str(e)}")
                    await asyncio.sleep(2 ** retry_count)
        
        # Refresh index to make documents searchable
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.indices.refresh(index=index_name)
        )
        
        logger.info(f"Inserted {len(ids)} vectors into {index_name}")
        return ids
    
    async def similarity_search(
        self,
        index_name: str,
        query_vector: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Perform k-NN similarity search."""
        if not self.client:
            raise RuntimeError("Not connected to OpenSearch")
        
        query = {
            'size': top_k,
            'query': {
                'knn': {
                    'embedding': {
                        'vector': query_vector.tolist(),
                        'k': top_k
                    }
                }
            }
        }
        
        # Add filters if provided
        if filters:
            query['query'] = {
                'bool': {
                    'must': [query['query']],
                    'filter': [
                        {'term': {k: v}} for k, v in filters.items()
                    ]
                }
            }
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.search(index=index_name, body=query)
            )
            
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                results.append(VectorSearchResult(
                    id=hit['_id'],
                    section_number=source.get('section_number', ''),
                    description=source.get('description', ''),
                    penalty=source.get('penalty', ''),
                    score=hit['_score'],
                    metadata=source.get('metadata', {})
                ))
            
            logger.info(f"Found {len(results)} results for similarity search")
            return results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            raise RuntimeError(f"Search failed: {str(e)}")
    
    async def delete_vectors(
        self,
        index_name: str,
        ids: List[str]
    ) -> int:
        """Delete vectors by IDs."""
        if not self.client:
            raise RuntimeError("Not connected to OpenSearch")
        
        deleted_count = 0
        
        for doc_id in ids:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.client.delete(index=index_name, id=doc_id)
                )
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete document {doc_id}: {e}")
        
        logger.info(f"Deleted {deleted_count} vectors from {index_name}")
        return deleted_count
    
    async def index_exists(self, index_name: str) -> bool:
        """Check if index exists."""
        if not self.client:
            raise RuntimeError("Not connected to OpenSearch")
        
        try:
            loop = asyncio.get_event_loop()
            exists = await loop.run_in_executor(
                None,
                lambda: self.client.indices.exists(index=index_name)
            )
            return exists
        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False
    
    async def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get index statistics."""
        if not self.client:
            raise RuntimeError("Not connected to OpenSearch")
        
        try:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None,
                lambda: self.client.indices.stats(index=index_name)
            )
            
            index_stats = stats['indices'][index_name]
            
            return {
                'vector_count': index_stats['total']['docs']['count'],
                'size_bytes': index_stats['total']['store']['size_in_bytes'],
                'index_name': index_name
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            raise RuntimeError(f"Failed to get stats: {str(e)}")
