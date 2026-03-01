"""
Aurora PostgreSQL with pgvector extension implementation.
Uses IVFFlat index for vector similarity search.
"""

import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional
import numpy as np
import asyncpg

from .interface import VectorDatabaseInterface, VectorSearchResult


logger = logging.getLogger(__name__)


class AuroraPgVectorDB(VectorDatabaseInterface):
    """
    Aurora PostgreSQL with pgvector implementation.
    Uses IVFFlat index for efficient similarity search.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        table_name: str = 'ipc_sections',
        max_retries: int = 3,
        pool_size: int = 10
    ):
        """
        Initialize Aurora pgvector client.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            table_name: Table name for vectors
            max_retries: Maximum retry attempts
            pool_size: Connection pool size
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.table_name = table_name
        self.max_retries = max_retries
        self.pool_size = pool_size
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Establish connection pool to Aurora PostgreSQL."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=1,
                max_size=self.pool_size,
                ssl='require'
            )
            
            # Enable pgvector extension
            async with self.pool.acquire() as conn:
                await conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
            
            logger.info(f"Connected to Aurora PostgreSQL at {self.host}")
        except Exception as e:
            logger.error(f"Failed to connect to Aurora: {e}")
            raise ConnectionError(f"Aurora connection failed: {str(e)}")
    
    async def close(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Closed Aurora PostgreSQL connection")
    
    async def create_index(
        self,
        index_name: str,
        dimension: int,
        metric: str = 'cosine'
    ) -> None:
        """Create table with vector column and IVFFlat index."""
        if not self.pool:
            raise RuntimeError("Not connected to Aurora")
        
        # Map metric names to pgvector operators
        metric_map = {
            'cosine': 'vector_cosine_ops',
            'euclidean': 'vector_l2_ops',
            'dot_product': 'vector_ip_ops'
        }
        
        if metric not in metric_map:
            raise ValueError(f"Unsupported metric: {metric}")
        
        async with self.pool.acquire() as conn:
            # Create table
            await conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {index_name} (
                    id UUID PRIMARY KEY,
                    embedding vector({dimension}),
                    section_number TEXT NOT NULL,
                    description TEXT NOT NULL,
                    penalty TEXT NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create IVFFlat index
            # lists = rows / 1000 for up to 1M rows
            lists = 100  # Default for small datasets
            await conn.execute(f'''
                CREATE INDEX IF NOT EXISTS {index_name}_embedding_idx
                ON {index_name}
                USING ivfflat (embedding {metric_map[metric]})
                WITH (lists = {lists})
            ''')
            
            logger.info(f"Created Aurora table and index: {index_name}")
    
    async def insert_vectors(
        self,
        index_name: str,
        vectors: List[np.ndarray],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert vectors with metadata."""
        if not self.pool:
            raise RuntimeError("Not connected to Aurora")
        
        if len(vectors) != len(metadata):
            raise ValueError("Vectors and metadata must have same length")
        
        ids = []
        
        async with self.pool.acquire() as conn:
            for vector, meta in zip(vectors, metadata):
                doc_id = str(uuid.uuid4())
                
                retry_count = 0
                while retry_count < self.max_retries:
                    try:
                        await conn.execute(f'''
                            INSERT INTO {index_name}
                            (id, embedding, section_number, description, penalty, metadata)
                            VALUES ($1, $2, $3, $4, $5, $6)
                        ''',
                            doc_id,
                            vector.tolist(),
                            meta.get('section_number', ''),
                            meta.get('description', ''),
                            meta.get('penalty', ''),
                            meta
                        )
                        ids.append(doc_id)
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count >= self.max_retries:
                            raise RuntimeError(f"Failed to insert vector: {str(e)}")
                        await asyncio.sleep(2 ** retry_count)
        
        logger.info(f"Inserted {len(ids)} vectors into {index_name}")
        return ids
    
    async def similarity_search(
        self,
        index_name: str,
        query_vector: np.ndarray,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Perform cosine similarity search using pgvector."""
        if not self.pool:
            raise RuntimeError("Not connected to Aurora")
        
        # Build query with optional filters
        where_clause = ""
        params = [query_vector.tolist(), top_k]
        
        if filters:
            conditions = []
            for key, value in filters.items():
                params.append(value)
                conditions.append(f"{key} = ${len(params)}")
            where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f'''
            SELECT id, section_number, description, penalty, metadata,
                   1 - (embedding <=> $1) AS score
            FROM {index_name}
            {where_clause}
            ORDER BY embedding <=> $1
            LIMIT $2
        '''
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                
                results = []
                for row in rows:
                    results.append(VectorSearchResult(
                        id=str(row['id']),
                        section_number=row['section_number'],
                        description=row['description'],
                        penalty=row['penalty'],
                        score=float(row['score']),
                        metadata=dict(row['metadata']) if row['metadata'] else {}
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
        if not self.pool:
            raise RuntimeError("Not connected to Aurora")
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(f'''
                    DELETE FROM {index_name}
                    WHERE id = ANY($1::uuid[])
                ''', ids)
                
                # Extract count from result string "DELETE N"
                deleted_count = int(result.split()[-1]) if result else 0
                
                logger.info(f"Deleted {deleted_count} vectors from {index_name}")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise RuntimeError(f"Deletion failed: {str(e)}")
    
    async def index_exists(self, index_name: str) -> bool:
        """Check if table exists."""
        if not self.pool:
            raise RuntimeError("Not connected to Aurora")
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval('''
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = $1
                    )
                ''', index_name)
                return result
        except Exception as e:
            logger.error(f"Failed to check table existence: {e}")
            return False
    
    async def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get table statistics."""
        if not self.pool:
            raise RuntimeError("Not connected to Aurora")
        
        try:
            async with self.pool.acquire() as conn:
                # Get row count
                count = await conn.fetchval(f'SELECT COUNT(*) FROM {index_name}')
                
                # Get table size
                size_query = '''
                    SELECT pg_total_relation_size($1) AS size_bytes
                '''
                size = await conn.fetchval(size_query, index_name)
                
                return {
                    'vector_count': count,
                    'size_bytes': size,
                    'index_name': index_name
                }
        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            raise RuntimeError(f"Failed to get stats: {str(e)}")
