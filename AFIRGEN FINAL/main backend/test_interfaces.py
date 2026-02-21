"""
Tests for interface implementations.

This module tests that concrete implementations properly implement
the defined interfaces and follow the interface contracts.

Requirements: 8.3
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Optional, List, Dict, Any

# Import interfaces
from interfaces.repository import IRepository, PaginatedResult
from interfaces.cache import ICacheManager
from interfaces.external_service import (
    IExternalService,
    IModelServer,
    ILLMModelServer,
    ServiceStatus
)

# Import concrete implementations
from repositories.base_repository import BaseRepository
from infrastructure.cache_manager import CacheManager
from services.gguf_model_server import GGUFModelServer


class TestRepositoryInterface:
    """Test that BaseRepository implements IRepository interface."""
    
    def test_base_repository_implements_interface(self):
        """Verify BaseRepository implements IRepository."""
        # BaseRepository is abstract, so we can't instantiate it directly
        # But we can verify it has the required methods
        assert hasattr(BaseRepository, 'table_name')
        assert hasattr(BaseRepository, 'primary_key')
        assert hasattr(BaseRepository, 'find_by_id')
        assert hasattr(BaseRepository, 'find_all')
        assert hasattr(BaseRepository, 'find_paginated')
        assert hasattr(BaseRepository, 'count')
        assert hasattr(BaseRepository, 'create')
        assert hasattr(BaseRepository, 'update')
        assert hasattr(BaseRepository, 'delete')
        assert hasattr(BaseRepository, 'aggregate')
    
    def test_repository_interface_contract(self):
        """Test that IRepository defines the expected contract."""
        # Verify interface has all required abstract methods
        abstract_methods = IRepository.__abstractmethods__
        
        expected_methods = {
            'table_name',
            'primary_key',
            'find_by_id',
            'find_all',
            'find_paginated',
            'count',
            'create',
            'update',
            'delete',
            'aggregate'
        }
        
        assert expected_methods.issubset(abstract_methods)
    
    def test_paginated_result_structure(self):
        """Test PaginatedResult data structure."""
        result = PaginatedResult(
            items=[1, 2, 3],
            total_count=10,
            page_size=3,
            next_cursor="abc123",
            has_more=True
        )
        
        assert result.items == [1, 2, 3]
        assert result.total_count == 10
        assert result.page_size == 3
        assert result.next_cursor == "abc123"
        assert result.has_more is True


class TestCacheInterface:
    """Test that CacheManager implements ICacheManager interface."""
    
    def test_cache_manager_implements_interface(self):
        """Verify CacheManager implements ICacheManager."""
        # Verify CacheManager has all required methods
        assert hasattr(CacheManager, 'get')
        assert hasattr(CacheManager, 'set')
        assert hasattr(CacheManager, 'delete')
        assert hasattr(CacheManager, 'exists')
        assert hasattr(CacheManager, 'get_ttl')
        assert hasattr(CacheManager, 'invalidate_pattern')
        assert hasattr(CacheManager, 'get_or_fetch')
        assert hasattr(CacheManager, 'generate_key')
        assert hasattr(CacheManager, 'get_multiple')
        assert hasattr(CacheManager, 'set_multiple')
        assert hasattr(CacheManager, 'flush_namespace')
        assert hasattr(CacheManager, 'ping')
    
    def test_cache_interface_contract(self):
        """Test that ICacheManager defines the expected contract."""
        abstract_methods = ICacheManager.__abstractmethods__
        
        expected_methods = {
            'get',
            'set',
            'delete',
            'exists',
            'get_ttl',
            'invalidate_pattern',
            'get_or_fetch',
            'generate_key',
            'get_multiple',
            'set_multiple',
            'flush_namespace',
            'ping'
        }
        
        assert expected_methods.issubset(abstract_methods)
    
    def test_cache_manager_with_mock_redis(self):
        """Test CacheManager with mock Redis client."""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.ping.return_value = True
        
        cache = CacheManager(redis_client=mock_redis)
        
        # Test that cache manager can be used through interface
        assert isinstance(cache, ICacheManager)
        assert cache.ping() is True


class TestExternalServiceInterface:
    """Test that model server implements IExternalService interfaces."""
    
    def test_gguf_model_server_implements_interface(self):
        """Verify GGUFModelServer implements ILLMModelServer."""
        # Verify GGUFModelServer has all required methods
        assert hasattr(GGUFModelServer, 'service_name')
        assert hasattr(GGUFModelServer, 'health_check')
        assert hasattr(GGUFModelServer, 'get_status')
        assert hasattr(GGUFModelServer, 'get_metrics')
        assert hasattr(GGUFModelServer, 'call')
        assert hasattr(GGUFModelServer, 'call_with_retry')
        assert hasattr(GGUFModelServer, 'get_circuit_breaker_status')
        assert hasattr(GGUFModelServer, 'reset_circuit_breaker')
        assert hasattr(GGUFModelServer, 'generate_text')
        assert hasattr(GGUFModelServer, 'generate_completion')
    
    def test_external_service_interface_contract(self):
        """Test that IExternalService defines the expected contract."""
        abstract_methods = IExternalService.__abstractmethods__
        
        expected_methods = {
            'service_name',
            'health_check',
            'get_status',
            'get_metrics'
        }
        
        assert expected_methods.issubset(abstract_methods)
    
    def test_model_server_interface_contract(self):
        """Test that IModelServer extends IExternalService."""
        abstract_methods = IModelServer.__abstractmethods__
        
        expected_methods = {
            'service_name',
            'health_check',
            'get_status',
            'get_metrics',
            'call',
            'call_with_retry',
            'get_circuit_breaker_status',
            'reset_circuit_breaker'
        }
        
        assert expected_methods.issubset(abstract_methods)
    
    def test_llm_model_server_interface_contract(self):
        """Test that ILLMModelServer extends IModelServer."""
        abstract_methods = ILLMModelServer.__abstractmethods__
        
        expected_methods = {
            'generate_text',
            'generate_completion'
        }
        
        # These should be in addition to IModelServer methods
        assert expected_methods.issubset(abstract_methods)
    
    def test_service_status_enum(self):
        """Test ServiceStatus enum values."""
        assert ServiceStatus.AVAILABLE == "available"
        assert ServiceStatus.UNAVAILABLE == "unavailable"
        assert ServiceStatus.DEGRADED == "degraded"
        assert ServiceStatus.UNKNOWN == "unknown"
    
    def test_gguf_model_server_instantiation(self):
        """Test that GGUFModelServer can be instantiated."""
        server = GGUFModelServer(url="http://localhost:8000")
        
        # Test that it implements the interface
        assert isinstance(server, ILLMModelServer)
        assert isinstance(server, IModelServer)
        assert isinstance(server, IExternalService)
        
        # Test service name property
        assert server.service_name == "gguf_llm_server"


class TestInterfacePolymorphism:
    """Test that interfaces enable polymorphism and dependency injection."""
    
    def test_repository_polymorphism(self):
        """Test that different repository implementations can be used interchangeably."""
        # Create a mock repository that implements IRepository
        mock_repo = Mock(spec=IRepository)
        mock_repo.find_by_id.return_value = {"id": "123", "name": "Test"}
        mock_repo.count.return_value = 10
        
        # Function that accepts any IRepository implementation
        def get_entity_count(repo: IRepository) -> int:
            return repo.count()
        
        # Should work with any IRepository implementation
        count = get_entity_count(mock_repo)
        assert count == 10
        mock_repo.count.assert_called_once()
    
    def test_cache_polymorphism(self):
        """Test that different cache implementations can be used interchangeably."""
        # Create a mock cache that implements ICacheManager
        mock_cache = Mock(spec=ICacheManager)
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        
        # Function that accepts any ICacheManager implementation
        def cache_value(cache: ICacheManager, key: str, value: Any) -> bool:
            return cache.set(key, value, ttl=3600)
        
        # Should work with any ICacheManager implementation
        result = cache_value(mock_cache, "test_key", "test_value")
        assert result is True
        mock_cache.set.assert_called_once_with("test_key", "test_value", ttl=3600)
    
    def test_external_service_polymorphism(self):
        """Test that different external service implementations can be used interchangeably."""
        # Create a mock service that implements IExternalService
        mock_service = Mock(spec=IExternalService)
        mock_service.health_check.return_value = True
        mock_service.get_status.return_value = ServiceStatus.AVAILABLE
        
        # Function that accepts any IExternalService implementation
        def check_service_health(service: IExternalService) -> bool:
            return service.health_check()
        
        # Should work with any IExternalService implementation
        is_healthy = check_service_health(mock_service)
        assert is_healthy is True
        mock_service.health_check.assert_called_once()


class TestInterfaceDocumentation:
    """Test that interfaces are properly documented."""
    
    def test_repository_interface_has_docstring(self):
        """Test that IRepository has documentation."""
        assert IRepository.__doc__ is not None
        assert "Abstract base class for repository implementations" in IRepository.__doc__
    
    def test_cache_interface_has_docstring(self):
        """Test that ICacheManager has documentation."""
        assert ICacheManager.__doc__ is not None
        assert "Abstract base class for cache manager implementations" in ICacheManager.__doc__
    
    def test_external_service_interface_has_docstring(self):
        """Test that IExternalService has documentation."""
        assert IExternalService.__doc__ is not None
        assert "Abstract base class for external service integrations" in IExternalService.__doc__
    
    def test_method_signatures_have_type_hints(self):
        """Test that interface methods have proper type hints."""
        # Check IRepository.find_by_id signature
        import inspect
        sig = inspect.signature(IRepository.find_by_id)
        
        # Should have type hints for parameters and return value
        assert 'entity_id' in sig.parameters
        assert 'fields' in sig.parameters
        assert sig.return_annotation is not inspect.Signature.empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
