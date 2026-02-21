"""
Property-based tests for pagination functionality.

Tests universal properties that should hold for all pagination operations:
- Property 13: Pagination support for list endpoints
- Property 14: Pagination metadata completeness

Requirements: 3.2, 3.3
"""

import pytest
from hypothesis import given, strategies as st, settings
from utils.pagination import PaginationHandler, PaginatedResponse, CursorInfo


# Feature: backend-optimization, Property 13: Pagination support for list endpoints
@given(
    total_items=st.integers(min_value=0, max_value=1000),
    limit=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_13_pagination_support(total_items, limit):
    """
    Property 13: For any list endpoint request, the API should accept pagination 
    parameters (cursor, limit) and return a paginated response.
    
    Validates: Requirements 3.2
    """
    # Generate mock items
    items = [{'id': str(i), 'name': f'Item {i}', 'created_at': f'2024-01-{i%28+1:02d}'} 
             for i in range(min(total_items, limit + 1))]
    
    # Test first page (no cursor)
    response = PaginationHandler.create_paginated_response(
        items=items,
        total_count=total_items,
        limit=limit
    )
    
    # Property: Response must be a PaginatedResponse
    assert isinstance(response, PaginatedResponse)
    
    # Property: Response must have all required fields
    assert hasattr(response, 'items')
    assert hasattr(response, 'total_count')
    assert hasattr(response, 'page_size')
    assert hasattr(response, 'next_cursor')
    assert hasattr(response, 'has_more')
    
    # Property: Items returned should not exceed limit
    assert len(response.items) <= limit
    
    # Property: If there are more items than limit, has_more should be True
    if len(items) > limit:
        assert response.has_more is True
        assert response.next_cursor is not None
    
    # Property: If items <= limit, has_more should be False
    if len(items) <= limit:
        assert response.has_more is False


# Feature: backend-optimization, Property 13: Cursor-based pagination
@given(
    num_items=st.integers(min_value=2, max_value=50),
    limit=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_13_cursor_based_pagination(num_items, limit):
    """
    Property 13: Pagination should use cursor-based approach (not offset-based).
    
    Validates: Requirements 3.2
    """
    # Generate items
    items = [{'id': str(i), 'name': f'Item {i}', 'value': i} 
             for i in range(min(num_items, limit + 1))]
    
    response = PaginationHandler.create_paginated_response(
        items=items,
        total_count=num_items,
        limit=limit,
        sort_field='value'
    )
    
    # Property: If there's a next page, cursor must be decodable
    if response.next_cursor:
        decoded = PaginationHandler.decode_cursor(response.next_cursor)
        assert decoded is not None
        assert isinstance(decoded, CursorInfo)
        
        # Property: Cursor should contain last item's information
        if response.items:
            last_item = response.items[-1]
            assert decoded.last_id == str(last_item['id'])
            assert decoded.last_value == last_item['value']


# Feature: backend-optimization, Property 14: Pagination metadata completeness
@given(
    total_count=st.integers(min_value=0, max_value=1000),
    num_items=st.integers(min_value=0, max_value=100),
    limit=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_14_metadata_completeness(total_count, num_items, limit):
    """
    Property 14: For any paginated API response, the response should include 
    metadata fields: total_count, page_size, next_cursor, and has_more.
    
    Validates: Requirements 3.3
    """
    # Generate items (simulate fetching limit+1 to check for more pages)
    actual_items = min(num_items, limit + 1)
    items = [{'id': str(i), 'name': f'Item {i}'} for i in range(actual_items)]
    
    response = PaginationHandler.create_paginated_response(
        items=items,
        total_count=total_count,
        limit=limit
    )
    
    # Property: Response must include total_count
    assert hasattr(response, 'total_count')
    assert response.total_count == total_count
    assert isinstance(response.total_count, int)
    assert response.total_count >= 0
    
    # Property: Response must include page_size
    assert hasattr(response, 'page_size')
    assert isinstance(response.page_size, int)
    assert response.page_size >= 0
    assert response.page_size <= limit
    
    # Property: Response must include next_cursor
    assert hasattr(response, 'next_cursor')
    assert response.next_cursor is None or isinstance(response.next_cursor, str)
    
    # Property: Response must include has_more
    assert hasattr(response, 'has_more')
    assert isinstance(response.has_more, bool)
    
    # Property: page_size should equal the number of items returned
    assert response.page_size == len(response.items)


# Feature: backend-optimization, Property 14: Metadata consistency
@given(
    items_count=st.integers(min_value=0, max_value=100),
    limit=st.integers(min_value=1, max_value=50)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_14_metadata_consistency(items_count, limit):
    """
    Property 14: Metadata fields should be consistent with each other.
    
    Validates: Requirements 3.3
    """
    # Simulate fetching limit+1 items
    fetch_count = min(items_count, limit + 1)
    items = [{'id': str(i), 'data': f'Data {i}'} for i in range(fetch_count)]
    
    response = PaginationHandler.create_paginated_response(
        items=items,
        total_count=items_count,
        limit=limit
    )
    
    # Property: If has_more is True, next_cursor must not be None
    if response.has_more:
        assert response.next_cursor is not None
        assert len(response.next_cursor) > 0
    
    # Property: If has_more is False, next_cursor should be None
    if not response.has_more:
        assert response.next_cursor is None
    
    # Property: page_size should never exceed limit
    assert response.page_size <= limit
    
    # Property: If items were fetched, page_size should match items length
    assert response.page_size == len(response.items)


# Feature: backend-optimization, Property 14: to_dict conversion
@given(
    num_items=st.integers(min_value=0, max_value=50),
    limit=st.integers(min_value=1, max_value=20),
    total=st.integers(min_value=0, max_value=1000)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_14_to_dict_completeness(num_items, limit, total):
    """
    Property 14: The to_dict() method should include all required metadata fields.
    
    Validates: Requirements 3.3
    """
    items = [{'id': str(i)} for i in range(min(num_items, limit + 1))]
    
    response = PaginationHandler.create_paginated_response(
        items=items,
        total_count=total,
        limit=limit
    )
    
    result_dict = response.to_dict()
    
    # Property: to_dict must return a dictionary
    assert isinstance(result_dict, dict)
    
    # Property: Dictionary must contain all required keys
    required_keys = {'items', 'total_count', 'page_size', 'next_cursor', 'has_more'}
    assert required_keys.issubset(result_dict.keys())
    
    # Property: Values in dict should match response attributes
    assert result_dict['items'] == response.items
    assert result_dict['total_count'] == response.total_count
    assert result_dict['page_size'] == response.page_size
    assert result_dict['next_cursor'] == response.next_cursor
    assert result_dict['has_more'] == response.has_more


# Feature: backend-optimization, Property 13 & 14: Cursor encoding/decoding roundtrip
@given(
    item_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), 
        whitelist_characters='-_'
    )),
    sort_value=st.one_of(
        st.text(min_size=1, max_size=100),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.none()
    )
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_13_cursor_roundtrip(item_id, sort_value):
    """
    Property 13: Cursor encoding and decoding should be inverse operations.
    
    Validates: Requirements 3.2
    """
    item = {'id': item_id, 'sort_field': sort_value}
    
    # Encode cursor
    encoded = PaginationHandler.encode_cursor(item, sort_field='sort_field')
    
    # Property: Encoded cursor should be a non-empty string
    assert isinstance(encoded, str)
    assert len(encoded) > 0
    
    # Decode cursor
    decoded = PaginationHandler.decode_cursor(encoded)
    
    # Property: Decoded cursor should not be None
    assert decoded is not None
    
    # Property: Decoded values should match original
    assert decoded.last_id == item_id
    assert decoded.last_value == sort_value


# Feature: backend-optimization, Property 13: Empty results handling
@given(
    limit=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_13_empty_results(limit):
    """
    Property 13: Pagination should handle empty result sets correctly.
    
    Validates: Requirements 3.2
    """
    response = PaginationHandler.create_paginated_response(
        items=[],
        total_count=0,
        limit=limit
    )
    
    # Property: Empty results should have no items
    assert len(response.items) == 0
    assert response.page_size == 0
    
    # Property: Empty results should have no next page
    assert response.has_more is False
    assert response.next_cursor is None
    
    # Property: Total count should be 0
    assert response.total_count == 0


# Feature: backend-optimization, Property 14: Boundary conditions
@given(
    limit=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_14_exact_limit_boundary(limit):
    """
    Property 14: When items exactly equal limit, metadata should be correct.
    
    Validates: Requirements 3.3
    """
    # Create exactly 'limit' items (no extra item)
    items = [{'id': str(i), 'name': f'Item {i}'} for i in range(limit)]
    
    response = PaginationHandler.create_paginated_response(
        items=items,
        total_count=limit,
        limit=limit
    )
    
    # Property: Should return all items
    assert len(response.items) == limit
    assert response.page_size == limit
    
    # Property: Should indicate no more pages
    assert response.has_more is False
    assert response.next_cursor is None
    
    # Property: Total count should match
    assert response.total_count == limit


# Feature: backend-optimization, Property 13: Large dataset handling
@given(
    total_count=st.integers(min_value=100, max_value=10000),
    limit=st.integers(min_value=1, max_value=100)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_13_large_dataset(total_count, limit):
    """
    Property 13: Pagination should handle large datasets efficiently.
    
    Validates: Requirements 3.2
    """
    # Simulate first page of large dataset
    items = [{'id': str(i), 'value': i} for i in range(limit + 1)]
    
    response = PaginationHandler.create_paginated_response(
        items=items,
        total_count=total_count,
        limit=limit
    )
    
    # Property: Should return exactly limit items
    assert len(response.items) == limit
    assert response.page_size == limit
    
    # Property: Should indicate more pages exist
    assert response.has_more is True
    assert response.next_cursor is not None
    
    # Property: Total count should be preserved
    assert response.total_count == total_count


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
