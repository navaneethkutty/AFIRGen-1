"""
Pagination Handler for API Response Optimization.

This module provides utilities for cursor-based pagination in API endpoints:
- Cursor encoding/decoding for secure pagination state
- Paginated response model with metadata
- Helper functions for building paginated API responses

Requirements: 3.2, 3.3
"""

import base64
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Generic, TypeVar
from infrastructure.logging import get_logger


logger = get_logger(__name__)


T = TypeVar('T')


@dataclass
class CursorInfo:
    """
    Information for cursor-based pagination.
    
    Encapsulates the state needed to continue pagination from a specific point.
    Uses base64 encoding for security and URL-safety.
    """
    last_id: str
    last_value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cursor info to dictionary."""
        return {
            'last_id': self.last_id,
            'last_value': self.last_value
        }


@dataclass
class PaginatedResponse(Generic[T]):
    """
    Paginated response model with metadata.
    
    Provides complete pagination information including items, counts, and navigation.
    Requirements: 3.2, 3.3
    """
    items: List[T]
    total_count: int
    page_size: int
    next_cursor: Optional[str]
    has_more: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert paginated response to dictionary."""
        return {
            'items': self.items,
            'total_count': self.total_count,
            'page_size': self.page_size,
            'next_cursor': self.next_cursor,
            'has_more': self.has_more
        }


class PaginationHandler:
    """
    Handler for cursor-based pagination operations.
    
    Provides encoding/decoding of cursors and building paginated responses.
    """
    
    @staticmethod
    def encode_cursor(last_item: Dict[str, Any], sort_field: str = 'id') -> str:
        """
        Encode cursor from the last item in the current page.
        
        Args:
            last_item: The last item in the current page
            sort_field: The field used for sorting (default: 'id')
            
        Returns:
            Base64-encoded cursor string
            
        Requirements: 3.2
        """
        if not last_item:
            return ""
        
        cursor_info = CursorInfo(
            last_id=str(last_item.get('id', '')),
            last_value=last_item.get(sort_field)
        )
        
        cursor_json = json.dumps(cursor_info.to_dict())
        cursor_bytes = cursor_json.encode('utf-8')
        encoded = base64.urlsafe_b64encode(cursor_bytes).decode('utf-8')
        
        logger.debug("Encoded cursor", cursor=encoded, sort_field=sort_field)
        return encoded
    
    @staticmethod
    def decode_cursor(cursor: Optional[str]) -> Optional[CursorInfo]:
        """
        Decode cursor to extract pagination state.
        
        Args:
            cursor: Base64-encoded cursor string
            
        Returns:
            CursorInfo object or None if cursor is invalid
            
        Requirements: 3.2
        """
        if not cursor:
            return None
        
        try:
            cursor_bytes = base64.urlsafe_b64decode(cursor.encode('utf-8'))
            cursor_json = cursor_bytes.decode('utf-8')
            cursor_dict = json.loads(cursor_json)
            
            cursor_info = CursorInfo(
                last_id=cursor_dict['last_id'],
                last_value=cursor_dict['last_value']
            )
            
            logger.debug("Decoded cursor", last_id=cursor_info.last_id, last_value=cursor_info.last_value)
            return cursor_info
            
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            logger.warning("Failed to decode cursor", error=str(e), cursor=cursor)
            return None
    
    @staticmethod
    def create_paginated_response(
        items: List[T],
        total_count: int,
        limit: int,
        sort_field: str = 'id'
    ) -> PaginatedResponse[T]:
        """
        Create a paginated response with metadata.
        
        Args:
            items: List of items for the current page
            total_count: Total number of items across all pages
            limit: Maximum number of items per page
            sort_field: Field used for sorting (default: 'id')
            
        Returns:
            PaginatedResponse with items and metadata
            
        Requirements: 3.2, 3.3
        """
        has_more = len(items) > limit
        
        # If we have more items than the limit, remove the extra item
        # (we fetched limit+1 to check if there are more pages)
        if has_more:
            items = items[:limit]
        
        # Generate next cursor from the last item
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            # Convert item to dict if it's not already
            if hasattr(last_item, '__dict__'):
                last_item_dict = last_item.__dict__
            elif isinstance(last_item, dict):
                last_item_dict = last_item
            else:
                last_item_dict = asdict(last_item) if hasattr(last_item, '__dataclass_fields__') else {}
            
            next_cursor = PaginationHandler.encode_cursor(last_item_dict, sort_field)
        
        return PaginatedResponse(
            items=items,
            total_count=total_count,
            page_size=len(items),
            next_cursor=next_cursor,
            has_more=has_more
        )
