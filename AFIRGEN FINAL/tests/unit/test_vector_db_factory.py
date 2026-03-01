"""Unit tests for VectorDBFactory."""

import pytest
import os
from unittest.mock import patch

import sys
sys.path.insert(0, 'AFIRGEN FINAL')

from services.vector_db.factory import VectorDBFactory
from services.vector_db.opensearch_db import OpenSearchVectorDB
from services.vector_db.aurora_pgvector_db import AuroraPgVectorDB


class TestVectorDBFactory:
    """Test suite for VectorDBFactory."""
    
    def test_create_opensearch_with_type_parameter(self):
        """Test creating OpenSearch instance with type parameter."""
        db = VectorDBFactory.create_vector_db(
            db_type='opensearch',
            endpoint='test-endpoint.aoss.amazonaws.com',
            region='us-east-1'
        )
        
        assert isinstance(db, OpenSearchVectorDB)
        assert db.endpoint == 'test-endpoint.aoss.amazonaws.com'
    
    def test_create_aurora_with_type_parameter(self):
        """Test creating Aurora instance with type parameter."""
        db = VectorDBFactory.create_vector_db(
            db_type='aurora_pgvector',
            host='test-host',
            port=5432,
            database='test_db',
            user='test_user',
            password='test_pass'
        )
        
        assert isinstance(db, AuroraPgVectorDB)
        assert db.host == 'test-host'
    
    @patch.dict(os.environ, {'VECTOR_DB_TYPE': 'opensearch', 'OPENSEARCH_ENDPOINT': 'env-endpoint'})
    def test_create_from_environment(self):
        """Test creating instance from environment variables."""
        db = VectorDBFactory.create_vector_db()
        
        assert isinstance(db, OpenSearchVectorDB)
        assert db.endpoint == 'env-endpoint'
    
    def test_create_invalid_type(self):
        """Test creating with invalid database type."""
        with pytest.raises(ValueError) as exc_info:
            VectorDBFactory.create_vector_db(db_type='invalid_type')
        
        assert "Unsupported database type" in str(exc_info.value)
    
    def test_create_no_type_specified(self):
        """Test creating without specifying type."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                VectorDBFactory.create_vector_db()
            
            assert "not specified" in str(exc_info.value)
    
    def test_create_opensearch_missing_endpoint(self):
        """Test creating OpenSearch without endpoint."""
        with pytest.raises(RuntimeError) as exc_info:
            VectorDBFactory.create_vector_db(db_type='opensearch')
        
        assert "endpoint not configured" in str(exc_info.value).lower()
    
    def test_create_aurora_missing_config(self):
        """Test creating Aurora with missing configuration."""
        with pytest.raises(RuntimeError) as exc_info:
            VectorDBFactory.create_vector_db(
                db_type='aurora_pgvector',
                host='test-host'
                # Missing database, user, password
            )
        
        assert "configuration incomplete" in str(exc_info.value).lower()
    
    @patch.dict(os.environ, {
        'VECTOR_DB_TYPE': 'aurora_pgvector',
        'AURORA_HOST': 'env-host',
        'AURORA_DATABASE': 'env-db',
        'AURORA_USER': 'env-user',
        'AURORA_PASSWORD': 'env-pass'
    })
    def test_create_aurora_from_environment(self):
        """Test creating Aurora from environment variables."""
        db = VectorDBFactory.create_vector_db()
        
        assert isinstance(db, AuroraPgVectorDB)
        assert db.host == 'env-host'
        assert db.database == 'env-db'
