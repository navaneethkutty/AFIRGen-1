"""
Property-based tests for field filtering functionality.

Tests universal properties that should hold for all field filtering operations:
- Property 15: Field filtering

Requirements: 3.4
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from utils.field_filter import FieldFilter


# Strategy for generating valid field names
field_name_strategy = st.text(
    min_size=1, 
    max_size=20,
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_')
)


# Feature: backend-optimization, Property 15: Field filtering
@given(
    data=st.dictionaries(
        keys=field_name_strategy,
        values=st.one_of(st.integers(), st.text(), st.floats(allow_nan=False), st.none()),
        min_size=1,
        max_size=20
    ),
    num_fields_to_request=st.integers(min_value=0, max_value=10)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_15_field_filtering(data, num_fields_to_request):
    """
    Property 15: For any API request with a fields parameter, the response 
    should include only the requested fields and exclude all others.
    
    Validates: Requirements 3.4
    """
    # Get available fields from data
    available_fields = list(data.keys())
    
    # Select random subset of fields to request
    num_to_request = min(num_fields_to_request, len(available_fields))
    if num_to_request > 0:
        import random
        requested_fields = random.sample(available_fields, num_to_request)
    else:
        requested_fields = []
    
    # Filter the data
    result = FieldFilter.filter_fields(data, requested_fields if requested_fields else None)
    
    if not requested_fields:
        # Property: If no fields requested, all fields should be returned
        assert result == data
    else:
        # Property: Result should only contain requested fields
        assert set(result.keys()) == set(requested_fields)
        
        # Property: Values for requested fields should match original
        for field in requested_fields:
            assert result[field] == data[field]
        
        # Property: Non-requested fields should not be in result
        non_requested = set(available_fields) - set(requested_fields)
        for field in non_requested:
            assert field not in result


# Feature: backend-optimization, Property 15: Field filtering for lists
@given(
    num_items=st.integers(min_value=0, max_value=20),
    num_fields=st.integers(min_value=1, max_value=10),
    num_requested=st.integers(min_value=0, max_value=10)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_15_list_filtering(num_items, num_fields, num_requested):
    """
    Property 15: Field filtering should work consistently for lists of dictionaries.
    
    Validates: Requirements 3.4
    """
    # Generate field names
    field_names = [f'field_{i}' for i in range(num_fields)]
    
    # Generate list of dictionaries
    data = [
        {field: f'value_{item}_{field}' for field in field_names}
        for item in range(num_items)
    ]
    
    # Select fields to request
    num_to_request = min(num_requested, num_fields)
    requested_fields = field_names[:num_to_request] if num_to_request > 0 else None
    
    # Filter the data
    result = FieldFilter.filter_fields(data, requested_fields)
    
    # Property: Result should have same number of items
    assert len(result) == len(data)
    
    if requested_fields:
        # Property: Each item should only have requested fields
        for item in result:
            assert set(item.keys()) == set(requested_fields)
    else:
        # Property: If no fields requested, items should be unchanged
        assert result == data


# Feature: backend-optimization, Property 15: Field validation
@given(
    num_allowed=st.integers(min_value=1, max_value=20),
    num_requested=st.integers(min_value=0, max_value=10),
    num_invalid=st.integers(min_value=0, max_value=5)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_15_field_validation(num_allowed, num_requested, num_invalid):
    """
    Property 15: Field validation should correctly identify invalid fields.
    
    Validates: Requirements 3.4
    """
    # Generate allowed fields
    allowed_fields = [f'allowed_{i}' for i in range(num_allowed)]
    
    # Generate requested fields (mix of valid and invalid)
    num_valid = min(num_requested, num_allowed)
    valid_requested = allowed_fields[:num_valid]
    invalid_requested = [f'invalid_{i}' for i in range(num_invalid)]
    requested_fields = valid_requested + invalid_requested
    
    # Validate fields
    is_valid = FieldFilter.validate_fields(requested_fields, allowed_fields)
    
    # Property: Validation should pass only if no invalid fields
    if num_invalid == 0:
        assert is_valid is True
    else:
        assert is_valid is False


# Feature: backend-optimization, Property 15: Empty fields handling
@given(
    data=st.dictionaries(
        keys=field_name_strategy,
        values=st.integers(),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_15_empty_fields(data):
    """
    Property 15: Empty or None fields parameter should return all data.
    
    Validates: Requirements 3.4
    """
    # Test with None
    result_none = FieldFilter.filter_fields(data, None)
    assert result_none == data
    
    # Test with empty list
    result_empty = FieldFilter.filter_fields(data, [])
    assert result_empty == data


# Feature: backend-optimization, Property 15: Field parsing
@given(
    num_fields=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_15_field_parsing(num_fields):
    """
    Property 15: Field parameter parsing should correctly split comma-separated values.
    
    Validates: Requirements 3.4
    """
    # Generate field names
    field_names = [f'field_{i}' for i in range(num_fields)]
    
    # Create comma-separated string
    fields_param = ','.join(field_names)
    
    # Parse fields
    result = FieldFilter.parse_fields_param(fields_param)
    
    # Property: Parsed fields should match original
    assert result == field_names
    assert len(result) == num_fields


# Feature: backend-optimization, Property 15: Idempotence
@given(
    data=st.dictionaries(
        keys=field_name_strategy,
        values=st.integers(),
        min_size=1,
        max_size=10
    ),
    num_requested=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_15_filtering_idempotence(data, num_requested):
    """
    Property 15: Filtering the same data twice should produce the same result.
    
    Validates: Requirements 3.4
    """
    # Select fields to request
    available_fields = list(data.keys())
    num_to_request = min(num_requested, len(available_fields))
    
    if num_to_request > 0:
        import random
        requested_fields = random.sample(available_fields, num_to_request)
    else:
        requested_fields = available_fields[:1]  # At least one field
    
    # Filter twice
    result1 = FieldFilter.filter_fields(data, requested_fields)
    result2 = FieldFilter.filter_fields(data, requested_fields)
    
    # Property: Results should be identical
    assert result1 == result2


# Feature: backend-optimization, Property 15: Subset property
@given(
    data=st.dictionaries(
        keys=field_name_strategy,
        values=st.integers(),
        min_size=2,
        max_size=20
    )
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_15_subset_property(data):
    """
    Property 15: Filtered result should always be a subset of original data.
    
    Validates: Requirements 3.4
    """
    available_fields = list(data.keys())
    
    # Request subset of fields
    import random
    num_to_request = random.randint(1, len(available_fields))
    requested_fields = random.sample(available_fields, num_to_request)
    
    # Filter data
    result = FieldFilter.filter_fields(data, requested_fields)
    
    # Property: Result keys should be subset of original keys
    assert set(result.keys()).issubset(set(data.keys()))
    
    # Property: Result should have at most as many fields as original
    assert len(result) <= len(data)


# Feature: backend-optimization, Property 15: Non-existent fields
@given(
    data=st.dictionaries(
        keys=field_name_strategy,
        values=st.integers(),
        min_size=1,
        max_size=10
    ),
    num_nonexistent=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_15_nonexistent_fields(data, num_nonexistent):
    """
    Property 15: Requesting non-existent fields should not cause errors.
    
    Validates: Requirements 3.4
    """
    # Generate non-existent field names
    existing_fields = set(data.keys())
    nonexistent_fields = []
    for i in range(num_nonexistent):
        field = f'nonexistent_{i}'
        # Ensure it doesn't exist in data
        while field in existing_fields:
            field = f'nonexistent_{i}_{i}'
        nonexistent_fields.append(field)
    
    # Request non-existent fields
    result = FieldFilter.filter_fields(data, nonexistent_fields)
    
    # Property: Result should be empty (no matching fields)
    assert result == {}


# Feature: backend-optimization, Property 15: Complete workflow
@given(
    num_fields=st.integers(min_value=2, max_value=15),
    num_requested=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_15_complete_workflow(num_fields, num_requested):
    """
    Property 15: Complete filtering workflow with validation should work correctly.
    
    Validates: Requirements 3.4
    """
    # Generate data and allowed fields
    field_names = [f'field_{i}' for i in range(num_fields)]
    data = {field: f'value_{field}' for field in field_names}
    allowed_fields = field_names
    
    # Select fields to request
    num_to_request = min(num_requested, num_fields)
    import random
    requested_fields = random.sample(field_names, num_to_request)
    
    # Use complete workflow
    result = FieldFilter.filter_response(data, requested_fields, allowed_fields)
    
    # Property: Result should only contain requested fields
    assert set(result.keys()) == set(requested_fields)
    
    # Property: Values should match original
    for field in requested_fields:
        assert result[field] == data[field]


# Feature: backend-optimization, Property 15: Duplicate fields handling
@given(
    data=st.dictionaries(
        keys=field_name_strategy,
        values=st.integers(),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_property_15_duplicate_fields(data):
    """
    Property 15: Duplicate field names in request should be handled gracefully.
    
    Validates: Requirements 3.4
    """
    available_fields = list(data.keys())
    
    if len(available_fields) > 0:
        # Create list with duplicates
        import random
        field = random.choice(available_fields)
        requested_fields = [field, field, field]  # Duplicates
        
        # Filter data
        result = FieldFilter.filter_fields(data, requested_fields)
        
        # Property: Result should contain field only once
        assert field in result
        assert result[field] == data[field]
        
        # Property: Result should have correct number of unique fields
        assert len(result) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
