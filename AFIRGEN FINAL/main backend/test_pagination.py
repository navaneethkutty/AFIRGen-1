"""
Unit tests for pagination handler.

Tests cursor encoding/decoding, paginated response creation, and edge cases.
Requirements: 3.2, 3.3
"""

import pytest
from utils.pagination import PaginationHandler, PaginatedResponse, CursorInfo


class TestCursorEncoding:
    """Test cursor encoding and decoding."""
    
    def test_encode_cursor_basic(self):
        """Test basic cursor encoding."""
        last_item = {'id': '123', 'created_at': '2024-01-15T10:30:00'}
        cursor = PaginationHandler.encode_cursor(last_item, sort_field='created_at')
        
        assert cursor is not None
        assert isinstance(cursor, str)
        assert len(cursor) > 0
    
    def test_decode_cursor_basic(self):
        """Test basic cursor decoding."""
        last_item = {'id': '123', 'created_at': '2024-01-15T10:30:00'}
        cursor = PaginationHandler.encode_cursor(last_item, sort_field='created_at')
        
        decoded = PaginationHandler.decode_cursor(cursor)
        
        assert decoded is not None
        assert decoded.last_id == '123'
        assert decoded.last_value == '2024-01-15T10:30:00'
    
    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding are inverse operations."""
        last_item = {'id': 'abc-123', 'created_at': '2024-01-15T10:30:00', 'status': 'active'}
        cursor = PaginationHandler.encode_cursor(last_item, sort_field='created_at')
        decoded = PaginationHandler.decode_cursor(cursor)
        
        assert decoded.last_id == 'abc-123'
        assert decoded.last_value == '2024-01-15T10:30:00'
    
    def test_decode_none_cursor(self):
        """Test decoding None cursor returns None."""
        result = PaginationHandler.decode_cursor(None)
        assert result is None
    
    def test_decode_empty_cursor(self):
        """Test decoding empty cursor returns None."""
        result = PaginationHandler.decode_cursor("")
        assert result is None
    
    def test_decode_invalid_cursor(self):
        """Test decoding invalid cursor returns None."""
        result = PaginationHandler.decode_cursor("invalid_base64_string!!!")
        assert result is None
    
    def test_encode_empty_item(self):
        """Test encoding empty item returns empty string."""
        cursor = PaginationHandler.encode_cursor({}, sort_field='id')
        assert cursor == ""
    
    def test_encode_none_item(self):
        """Test encoding None item returns empty string."""
        cursor = PaginationHandler.encode_cursor(None, sort_field='id')
        assert cursor == ""


class TestPaginatedResponse:
    """Test paginated response creation."""
    
    def test_create_paginated_response_no_more_pages(self):
        """Test creating paginated response when there are no more pages."""
        items = [
            {'id': '1', 'name': 'Item 1'},
            {'id': '2', 'name': 'Item 2'}
        ]
        
        response = PaginationHandler.create_paginated_response(
            items=items,
            total_count=2,
            limit=10
        )
        
        assert len(response.items) == 2
        assert response.total_count == 2
        assert response.page_size == 2
        assert response.next_cursor is None
        assert response.has_more is False
    
    def test_create_paginated_response_has_more_pages(self):
        """Test creating paginated response when there are more pages."""
        # Simulate fetching limit+1 items
        items = [
            {'id': '1', 'name': 'Item 1'},
            {'id': '2', 'name': 'Item 2'},
            {'id': '3', 'name': 'Item 3'}  # Extra item to indicate more pages
        ]
        
        response = PaginationHandler.create_paginated_response(
            items=items,
            total_count=10,
            limit=2
        )
        
        # Should only return limit items
        assert len(response.items) == 2
        assert response.total_count == 10
        assert response.page_size == 2
        assert response.next_cursor is not None
        assert response.has_more is True
    
    def test_create_paginated_response_empty_items(self):
        """Test creating paginated response with empty items."""
        response = PaginationHandler.create_paginated_response(
            items=[],
            total_count=0,
            limit=10
        )
        
        assert len(response.items) == 0
        assert response.total_count == 0
        assert response.page_size == 0
        assert response.next_cursor is None
        assert response.has_more is False
    
    def test_paginated_response_to_dict(self):
        """Test converting paginated response to dictionary."""
        items = [{'id': '1', 'name': 'Item 1'}]
        response = PaginationHandler.create_paginated_response(
            items=items,
            total_count=1,
            limit=10
        )
        
        result = response.to_dict()
        
        assert isinstance(result, dict)
        assert 'items' in result
        assert 'total_count' in result
        assert 'page_size' in result
        assert 'next_cursor' in result
        assert 'has_more' in result
        assert result['total_count'] == 1
        assert result['page_size'] == 1
        assert result['has_more'] is False


class TestCursorInfo:
    """Test CursorInfo dataclass."""
    
    def test_cursor_info_to_dict(self):
        """Test converting CursorInfo to dictionary."""
        cursor_info = CursorInfo(last_id='123', last_value='2024-01-15')
        result = cursor_info.to_dict()
        
        assert isinstance(result, dict)
        assert result['last_id'] == '123'
        assert result['last_value'] == '2024-01-15'


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_cursor_with_special_characters(self):
        """Test cursor encoding/decoding with special characters."""
        last_item = {
            'id': 'abc-123-xyz',
            'created_at': '2024-01-15T10:30:00+00:00',
            'name': 'Test Item with "quotes" and \'apostrophes\''
        }
        
        cursor = PaginationHandler.encode_cursor(last_item, sort_field='created_at')
        decoded = PaginationHandler.decode_cursor(cursor)
        
        assert decoded is not None
        assert decoded.last_id == 'abc-123-xyz'
        assert decoded.last_value == '2024-01-15T10:30:00+00:00'
    
    def test_cursor_with_numeric_values(self):
        """Test cursor encoding/decoding with numeric sort values."""
        last_item = {'id': '123', 'priority': 5}
        cursor = PaginationHandler.encode_cursor(last_item, sort_field='priority')
        decoded = PaginationHandler.decode_cursor(cursor)
        
        assert decoded is not None
        assert decoded.last_id == '123'
        assert decoded.last_value == 5
    
    def test_large_page_size(self):
        """Test pagination with large page size."""
        items = [{'id': str(i), 'name': f'Item {i}'} for i in range(101)]
        
        response = PaginationHandler.create_paginated_response(
            items=items,
            total_count=200,
            limit=100
        )
        
        assert len(response.items) == 100
        assert response.has_more is True
        assert response.next_cursor is not None
    
    def test_single_item_page(self):
        """Test pagination with single item per page."""
        items = [
            {'id': '1', 'name': 'Item 1'},
            {'id': '2', 'name': 'Item 2'}
        ]
        
        response = PaginationHandler.create_paginated_response(
            items=items,
            total_count=10,
            limit=1
        )
        
        assert len(response.items) == 1
        assert response.has_more is True
        assert response.next_cursor is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
