"""
Repository Interface

Defines the abstract base class for repository implementations.
All repository classes should inherit from this interface to ensure
consistent data access patterns across the application.

Requirements: 8.3 - Define clear interfaces for database interactions
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Generic, TypeVar
from dataclasses import dataclass


T = TypeVar('T')


@dataclass
class PaginatedResult(Generic[T]):
    """
    Result of a paginated query.
    
    Attributes:
        items: List of items in the current page
        total_count: Total number of items across all pages
        page_size: Number of items per page
        next_cursor: Cursor for the next page (None if no more pages)
        has_more: Whether there are more pages available
    """
    items: List[T]
    total_count: int
    page_size: int
    next_cursor: Optional[str]
    has_more: bool


class IRepository(ABC, Generic[T]):
    """
    Abstract base class for repository implementations.
    
    This interface defines the contract for data access operations including:
    - CRUD operations (Create, Read, Update, Delete)
    - Querying with filters
    - Pagination support
    - Aggregation operations
    
    All concrete repository implementations must implement these methods
    to ensure consistent data access patterns.
    
    Type Parameters:
        T: The entity type managed by this repository
    
    Requirements: 8.3
    """
    
    @property
    @abstractmethod
    def table_name(self) -> str:
        """
        Get the primary table name for this repository.
        
        Returns:
            Table name as string
        """
        pass
    
    @property
    @abstractmethod
    def primary_key(self) -> str:
        """
        Get the primary key column name.
        
        Returns:
            Primary key column name as string
        """
        pass
    
    @abstractmethod
    def find_by_id(
        self,
        entity_id: Any,
        fields: Optional[List[str]] = None
    ) -> Optional[T]:
        """
        Find entity by primary key.
        
        Args:
            entity_id: Primary key value
            fields: Optional list of specific fields to retrieve
        
        Returns:
            Entity object if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_all(
        self,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[T]:
        """
        Find all entities matching filters.
        
        Args:
            fields: Optional list of specific fields to retrieve
            filters: Optional dictionary of column=value filters
            order_by: Optional ORDER BY clause
        
        Returns:
            List of entity objects
        """
        pass
    
    @abstractmethod
    def find_paginated(
        self,
        cursor: Optional[str] = None,
        limit: int = 20,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        sort_column: Optional[str] = None
    ) -> PaginatedResult[T]:
        """
        Find entities with cursor-based pagination.
        
        Args:
            cursor: Optional cursor from previous page
            limit: Number of items per page
            fields: Optional list of specific fields to retrieve
            filters: Optional dictionary of column=value filters
            order_by: Optional ORDER BY clause
            sort_column: Column used for cursor sorting
        
        Returns:
            PaginatedResult with items and pagination metadata
        """
        pass
    
    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities matching filters.
        
        Args:
            filters: Optional dictionary of column=value filters
        
        Returns:
            Count of matching entities
        """
        pass
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """
        Create a new entity.
        
        Args:
            entity: Entity object to create
        
        Returns:
            Created entity with any generated fields populated
        """
        pass
    
    @abstractmethod
    def update(self, entity_id: Any, updates: Dict[str, Any]) -> Optional[T]:
        """
        Update an entity.
        
        Args:
            entity_id: Primary key value
            updates: Dictionary of column=value updates
        
        Returns:
            Updated entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: Any) -> bool:
        """
        Delete an entity.
        
        Args:
            entity_id: Primary key value
        
        Returns:
            True if entity was deleted, False if not found
        """
        pass
    
    @abstractmethod
    def aggregate(
        self,
        function: str,
        column: str,
        filters: Optional[Dict[str, Any]] = None,
        group_by: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute database-level aggregation query.
        
        Args:
            function: Aggregate function (COUNT, SUM, AVG, MAX, MIN)
            column: Column to aggregate
            filters: Optional dictionary of column=value filters
            group_by: Optional list of columns to group by
        
        Returns:
            List of dictionaries with aggregation results
        """
        pass


class IRepositoryFactory(ABC):
    """
    Abstract factory for creating repository instances.
    
    This interface allows for dependency injection of repository factories,
    making it easier to swap implementations or create mock repositories
    for testing.
    
    Requirements: 8.3
    """
    
    @abstractmethod
    def create_repository(self, entity_type: type) -> IRepository:
        """
        Create a repository instance for the given entity type.
        
        Args:
            entity_type: The entity class type
        
        Returns:
            Repository instance for the entity type
        """
        pass
