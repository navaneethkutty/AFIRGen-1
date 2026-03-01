"""
Factory for creating vector database instances.
Supports OpenSearch Serverless and Aurora pgvector.
"""

import os
import logging
from typing import Optional

from .interface import VectorDatabaseInterface
from .opensearch_db import OpenSearchVectorDB
from .aurora_pgvector_db import AuroraPgVectorDB


logger = logging.getLogger(__name__)


class VectorDBFactory:
    """Factory for creating vector database instances based on configuration."""
    
    @staticmethod
    def create_vector_db(
        db_type: Optional[str] = None,
        **kwargs
    ) -> VectorDatabaseInterface:
        """
        Create vector database instance based on type.
        
        Args:
            db_type: Database type ('opensearch' or 'aurora_pgvector').
                    If None, reads from VECTOR_DB_TYPE environment variable.
            **kwargs: Additional arguments for database initialization
        
        Returns:
            VectorDatabaseInterface implementation
        
        Raises:
            ValueError: If db_type is invalid or not provided
            RuntimeError: If required configuration is missing
        """
        # Get database type from parameter or environment
        db_type = db_type or os.getenv('VECTOR_DB_TYPE')
        
        if not db_type:
            raise ValueError(
                "Database type not specified. Set VECTOR_DB_TYPE environment variable "
                "or pass db_type parameter."
            )
        
        db_type = db_type.lower().strip()
        
        if db_type == 'opensearch':
            return VectorDBFactory._create_opensearch(**kwargs)
        elif db_type == 'aurora_pgvector':
            return VectorDBFactory._create_aurora_pgvector(**kwargs)
        else:
            raise ValueError(
                f"Unsupported database type: {db_type}. "
                "Supported types: 'opensearch', 'aurora_pgvector'"
            )
    
    @staticmethod
    def _create_opensearch(**kwargs) -> OpenSearchVectorDB:
        """Create OpenSearch Serverless instance."""
        # Get configuration from kwargs or environment
        endpoint = kwargs.get('endpoint') or os.getenv('OPENSEARCH_ENDPOINT')
        region = kwargs.get('region') or os.getenv('AWS_REGION', 'us-east-1')
        index_name = kwargs.get('index_name') or os.getenv('OPENSEARCH_INDEX_NAME', 'ipc_sections')
        
        if not endpoint:
            raise RuntimeError(
                "OpenSearch endpoint not configured. Set OPENSEARCH_ENDPOINT environment variable."
            )
        
        logger.info(f"Creating OpenSearch vector database: {endpoint}")
        
        return OpenSearchVectorDB(
            endpoint=endpoint,
            region=region,
            index_name=index_name,
            max_retries=kwargs.get('max_retries', 3)
        )
    
    @staticmethod
    def _create_aurora_pgvector(**kwargs) -> AuroraPgVectorDB:
        """Create Aurora PostgreSQL with pgvector instance."""
        # Get configuration from kwargs or environment
        host = kwargs.get('host') or os.getenv('AURORA_HOST')
        port = kwargs.get('port') or int(os.getenv('AURORA_PORT', '5432'))
        database = kwargs.get('database') or os.getenv('AURORA_DATABASE')
        user = kwargs.get('user') or os.getenv('AURORA_USER')
        password = kwargs.get('password') or os.getenv('AURORA_PASSWORD')
        table_name = kwargs.get('table_name') or os.getenv('AURORA_TABLE_NAME', 'ipc_sections')
        
        # Validate required parameters
        missing = []
        if not host:
            missing.append('AURORA_HOST')
        if not database:
            missing.append('AURORA_DATABASE')
        if not user:
            missing.append('AURORA_USER')
        if not password:
            missing.append('AURORA_PASSWORD')
        
        if missing:
            raise RuntimeError(
                f"Aurora configuration incomplete. Missing environment variables: {', '.join(missing)}"
            )
        
        logger.info(f"Creating Aurora pgvector database: {host}:{port}/{database}")
        
        return AuroraPgVectorDB(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            table_name=table_name,
            max_retries=kwargs.get('max_retries', 3),
            pool_size=kwargs.get('pool_size', 10)
        )
