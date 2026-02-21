"""
Unit tests for field filtering functionality.

Tests field validation, filtering, and parsing operations.
Requirements: 3.4
"""

import pytest
from utils.field_filter import FieldFilter


class TestFieldValidation:
    """Test field validation against allowed fields."""
    
    def test_validate_fields_all_allowed(self):
        """Test validation when all requested fields are allowed."""
        fields = ['id', 'name', 'email']
        allowed = ['id', 'name', 'email', 'age', 'address']
        
        assert FieldFilter.validate_fields(fields, allowed) is True
    
    def test_validate_fields_some_invalid(self):
        """Test validation when some requested fields are not allowed."""
        fields = ['id', 'name', 'password']
        allowed = ['id', 'name', 'email']
        
        assert FieldFilter.validate_fields(fields, allowed) is False
    
    def test_validate_fields_empty_request(self):
        """Test validation with empty fields list."""
        fields = []
        allowed = ['id', 'name']
        
        assert FieldFilter.validate_fields(fields, allowed) is True
    
    def test_validate_fields_exact_match(self):
        """Test validation when fields exactly match allowed."""
        fields = ['id', 'name']
        allowed = ['id', 'name']
        
        assert FieldFilter.validate_fields(fields, allowed) is True


class TestFieldFiltering:
    """Test field filtering operations."""
    
    def test_filter_dict_basic(self):
        """Test filtering a single dictionary."""
        data = {'id': 1, 'name': 'John', 'email': 'john@example.com', 'password': 'secret'}
        fields = ['id', 'name']
        
        result = FieldFilter.filter_fields(data, fields)
        
        assert result == {'id': 1, 'name': 'John'}
        assert 'email' not in result
        assert 'password' not in result
    
    def test_filter_list_of_dicts(self):
        """Test filtering a list of dictionaries."""
        data = [
            {'id': 1, 'name': 'John', 'email': 'john@example.com'},
            {'id': 2, 'name': 'Jane', 'email': 'jane@example.com'}
        ]
        fields = ['id', 'name']
        
        result = FieldFilter.filter_fields(data, fields)
        
        assert len(result) == 2
        assert result[0] == {'id': 1, 'name': 'John'}
        assert result[1] == {'id': 2, 'name': 'Jane'}
    
    def test_filter_none_fields(self):
        """Test filtering with None fields returns all data."""
        data = {'id': 1, 'name': 'John', 'email': 'john@example.com'}
        
        result = FieldFilter.filter_fields(data, None)
        
        assert result == data
    
    def test_filter_empty_fields(self):
        """Test filtering with empty fields list returns all data."""
        data = {'id': 1, 'name': 'John'}
        
        result = FieldFilter.filter_fields(data, [])
        
        assert result == data
    
    def test_filter_nonexistent_fields(self):
        """Test filtering with fields that don't exist in data."""
        data = {'id': 1, 'name': 'John'}
        fields = ['id', 'email', 'age']
        
        result = FieldFilter.filter_fields(data, fields)
        
        # Should only include fields that exist in data
        assert result == {'id': 1}
    
    def test_filter_empty_dict(self):
        """Test filtering an empty dictionary."""
        data = {}
        fields = ['id', 'name']
        
        result = FieldFilter.filter_fields(data, fields)
        
        assert result == {}
    
    def test_filter_empty_list(self):
        """Test filtering an empty list."""
        data = []
        fields = ['id', 'name']
        
        result = FieldFilter.filter_fields(data, fields)
        
        assert result == []


class TestFieldParsing:
    """Test field parameter parsing."""
    
    def test_parse_fields_comma_separated(self):
        """Test parsing comma-separated fields."""
        fields_param = "id,name,email"
        
        result = FieldFilter.parse_fields_param(fields_param)
        
        assert result == ['id', 'name', 'email']
    
    def test_parse_fields_with_spaces(self):
        """Test parsing fields with spaces."""
        fields_param = "id, name, email"
        
        result = FieldFilter.parse_fields_param(fields_param)
        
        assert result == ['id', 'name', 'email']
    
    def test_parse_fields_single_field(self):
        """Test parsing a single field."""
        fields_param = "id"
        
        result = FieldFilter.parse_fields_param(fields_param)
        
        assert result == ['id']
    
    def test_parse_fields_none(self):
        """Test parsing None returns None."""
        result = FieldFilter.parse_fields_param(None)
        
        assert result is None
    
    def test_parse_fields_empty_string(self):
        """Test parsing empty string returns None."""
        result = FieldFilter.parse_fields_param("")
        
        assert result is None
    
    def test_parse_fields_only_commas(self):
        """Test parsing string with only commas returns None."""
        result = FieldFilter.parse_fields_param(",,,")
        
        assert result is None


class TestFilterResponse:
    """Test complete filtering workflow."""
    
    def test_filter_response_with_validation(self):
        """Test filtering with field validation."""
        data = {'id': 1, 'name': 'John', 'email': 'john@example.com'}
        fields = ['id', 'name']
        allowed = ['id', 'name', 'email']
        
        result = FieldFilter.filter_response(data, fields, allowed)
        
        assert result == {'id': 1, 'name': 'John'}
    
    def test_filter_response_invalid_fields(self):
        """Test filtering with invalid fields raises error."""
        data = {'id': 1, 'name': 'John'}
        fields = ['id', 'password']
        allowed = ['id', 'name']
        
        with pytest.raises(ValueError) as exc_info:
            FieldFilter.filter_response(data, fields, allowed)
        
        assert 'Invalid fields' in str(exc_info.value)
    
    def test_filter_response_no_validation(self):
        """Test filtering without validation."""
        data = {'id': 1, 'name': 'John', 'email': 'john@example.com'}
        fields = ['id', 'name']
        
        result = FieldFilter.filter_response(data, fields, None)
        
        assert result == {'id': 1, 'name': 'John'}
    
    def test_filter_response_no_fields(self):
        """Test filtering with no fields returns all data."""
        data = {'id': 1, 'name': 'John'}
        
        result = FieldFilter.filter_response(data, None, ['id', 'name'])
        
        assert result == data


class TestGetAllowedFields:
    """Test extracting allowed fields from models."""
    
    def test_get_allowed_fields_dict(self):
        """Test getting allowed fields from dictionary."""
        model = {'id': 1, 'name': 'test', 'email': 'test@example.com'}
        
        result = FieldFilter.get_allowed_fields(model)
        
        assert set(result) == {'id', 'name', 'email'}
    
    def test_get_allowed_fields_empty_dict(self):
        """Test getting allowed fields from empty dictionary."""
        model = {}
        
        result = FieldFilter.get_allowed_fields(model)
        
        assert result == []


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_filter_with_duplicate_fields(self):
        """Test filtering with duplicate field names."""
        data = {'id': 1, 'name': 'John', 'email': 'john@example.com'}
        fields = ['id', 'name', 'id', 'name']  # Duplicates
        
        result = FieldFilter.filter_fields(data, fields)
        
        # Should handle duplicates gracefully
        assert result == {'id': 1, 'name': 'John'}
    
    def test_filter_nested_dict(self):
        """Test filtering doesn't affect nested dictionaries."""
        data = {
            'id': 1,
            'name': 'John',
            'address': {'street': '123 Main St', 'city': 'NYC'}
        }
        fields = ['id', 'address']
        
        result = FieldFilter.filter_fields(data, fields)
        
        # Nested dict should be preserved as-is
        assert result == {
            'id': 1,
            'address': {'street': '123 Main St', 'city': 'NYC'}
        }
    
    def test_filter_with_none_values(self):
        """Test filtering preserves None values."""
        data = {'id': 1, 'name': None, 'email': 'john@example.com'}
        fields = ['id', 'name']
        
        result = FieldFilter.filter_fields(data, fields)
        
        assert result == {'id': 1, 'name': None}
    
    def test_filter_list_with_mixed_types(self):
        """Test filtering list with non-dict items."""
        data = [
            {'id': 1, 'name': 'John'},
            'not a dict',
            {'id': 2, 'name': 'Jane'}
        ]
        fields = ['id']
        
        result = FieldFilter.filter_fields(data, fields)
        
        # Should only filter dict items
        assert len(result) == 2
        assert result[0] == {'id': 1}
        assert result[1] == {'id': 2}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
