"""
Unit tests for utility modules.

Tests the validators, constants, and common utility functions.
"""

import pytest
from datetime import datetime
from utils.validators import (
    ValidationError,
    sanitize_text,
    validate_text_length,
    validate_uuid,
    validate_fir_number,
    validate_positive_integer,
    validate_range,
)
from utils.constants import (
    TextLimits,
    HTTPStatus,
    CacheTTL,
    TaskPriority,
    ValidationStep,
)
from utils.common import (
    truncate_string,
    normalize_whitespace,
    to_snake_case,
    mask_sensitive_data,
    generate_uuid,
    generate_fir_number,
    deep_merge,
    chunk_list,
    to_bool,
    to_int,
)


class TestValidators:
    """Test validation functions."""
    
    def test_sanitize_text_removes_dangerous_content(self):
        """Test that sanitize_text removes dangerous patterns."""
        with pytest.raises(ValidationError):
            sanitize_text("<script>alert('xss')</script>")
    
    def test_sanitize_text_escapes_html(self):
        """Test that sanitize_text escapes HTML by default."""
        result = sanitize_text("<div>Hello</div>")
        assert "&lt;div&gt;" in result
        assert "&lt;/div&gt;" in result
    
    def test_validate_text_length_min(self):
        """Test minimum text length validation."""
        with pytest.raises(ValidationError):
            validate_text_length("short", min_length=10)
    
    def test_validate_text_length_max(self):
        """Test maximum text length validation."""
        with pytest.raises(ValidationError):
            validate_text_length("x" * 100, max_length=50)
    
    def test_validate_uuid_valid(self):
        """Test valid UUID validation."""
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = validate_uuid(uuid)
        assert result == uuid.lower()
    
    def test_validate_uuid_invalid(self):
        """Test invalid UUID validation."""
        with pytest.raises(ValidationError):
            validate_uuid("invalid-uuid")
    
    def test_validate_fir_number_valid(self):
        """Test valid FIR number validation."""
        fir = "FIR-12345678-20240101120000"
        result = validate_fir_number(fir)
        assert result == fir
    
    def test_validate_fir_number_invalid(self):
        """Test invalid FIR number validation."""
        with pytest.raises(ValidationError):
            validate_fir_number("INVALID-FIR")
    
    def test_validate_positive_integer(self):
        """Test positive integer validation."""
        assert validate_positive_integer(5) == 5
        
        with pytest.raises(ValidationError):
            validate_positive_integer(0)
    
    def test_validate_range(self):
        """Test range validation."""
        assert validate_range(5.0, min_value=0.0, max_value=10.0) == 5.0
        
        with pytest.raises(ValidationError):
            validate_range(15.0, min_value=0.0, max_value=10.0)


class TestConstants:
    """Test constant definitions."""
    
    def test_text_limits(self):
        """Test text limit constants."""
        assert TextLimits.MAX_TEXT_LENGTH == 50_000
        assert TextLimits.MIN_TEXT_LENGTH == 10
    
    def test_http_status(self):
        """Test HTTP status constants."""
        assert HTTPStatus.OK == 200
        assert HTTPStatus.NOT_FOUND == 404
        assert HTTPStatus.INTERNAL_SERVER_ERROR == 500
    
    def test_cache_ttl(self):
        """Test cache TTL constants."""
        assert CacheTTL.FIR_RECORD == 3600
        assert CacheTTL.SHORT == 60
    
    def test_task_priority(self):
        """Test task priority constants."""
        assert TaskPriority.LOW == 3
        assert TaskPriority.MEDIUM == 5
        assert TaskPriority.HIGH == 7
    
    def test_validation_step_enum(self):
        """Test ValidationStep enum."""
        assert ValidationStep.TRANSCRIPT_REVIEW == "transcript_review"
        assert ValidationStep.FINAL_REVIEW == "final_review"


class TestCommonUtilities:
    """Test common utility functions."""
    
    def test_truncate_string(self):
        """Test string truncation."""
        result = truncate_string("Hello World", max_length=8)
        assert result == "Hello..."
        assert len(result) == 8
    
    def test_truncate_string_no_truncation(self):
        """Test string truncation when not needed."""
        text = "Short"
        result = truncate_string(text, max_length=10)
        assert result == text
    
    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        result = normalize_whitespace("Hello    World  \n  Test")
        assert result == "Hello World Test"
    
    def test_to_snake_case(self):
        """Test camelCase to snake_case conversion."""
        assert to_snake_case("camelCase") == "camel_case"
        assert to_snake_case("PascalCase") == "pascal_case"
    
    def test_mask_sensitive_data(self):
        """Test sensitive data masking."""
        result = mask_sensitive_data("secret123456", visible_chars=4)
        assert result == "********3456"
        assert len(result) == len("secret123456")
    
    def test_generate_uuid(self):
        """Test UUID generation."""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        
        assert len(uuid1) == 36
        assert uuid1 != uuid2
        assert "-" in uuid1
    
    def test_generate_fir_number(self):
        """Test FIR number generation."""
        fir = generate_fir_number()
        
        assert fir.startswith("FIR-")
        assert len(fir.split("-")) == 3
        
        # Validate format
        validate_fir_number(fir)
    
    def test_deep_merge(self):
        """Test deep dictionary merge."""
        dict1 = {"a": 1, "b": {"c": 2}}
        dict2 = {"b": {"d": 3}, "e": 4}
        
        result = deep_merge(dict1, dict2)
        
        assert result["a"] == 1
        assert result["b"]["c"] == 2
        assert result["b"]["d"] == 3
        assert result["e"] == 4
    
    def test_chunk_list(self):
        """Test list chunking."""
        lst = [1, 2, 3, 4, 5, 6, 7]
        chunks = chunk_list(lst, chunk_size=3)
        
        assert len(chunks) == 3
        assert chunks[0] == [1, 2, 3]
        assert chunks[1] == [4, 5, 6]
        assert chunks[2] == [7]
    
    def test_to_bool(self):
        """Test boolean conversion."""
        assert to_bool("true") is True
        assert to_bool("false") is False
        assert to_bool("1") is True
        assert to_bool("0") is False
        assert to_bool(1) is True
        assert to_bool(0) is False
    
    def test_to_int(self):
        """Test integer conversion."""
        assert to_int("123") == 123
        assert to_int("invalid", default=0) == 0
        assert to_int(45.7) == 45


class TestIntegration:
    """Integration tests for utility modules."""
    
    def test_validate_and_sanitize_workflow(self):
        """Test validation and sanitization workflow."""
        # User input
        user_input = "  Hello <b>World</b>  "
        
        # Sanitize
        sanitized = sanitize_text(user_input)
        
        # Validate length
        validate_text_length(sanitized, min_length=5, max_length=100)
        
        # Should succeed
        assert "&lt;b&gt;" in sanitized
    
    def test_generate_and_validate_ids(self):
        """Test ID generation and validation workflow."""
        # Generate UUID
        uuid = generate_uuid()
        
        # Validate it
        validated_uuid = validate_uuid(uuid)
        assert validated_uuid == uuid.lower()
        
        # Generate FIR number
        fir = generate_fir_number()
        
        # Validate it
        validated_fir = validate_fir_number(fir)
        assert validated_fir == fir
    
    def test_constants_usage(self):
        """Test using constants in validation."""
        # Use text limits
        text = "x" * TextLimits.MAX_TEXT_LENGTH
        validate_text_length(text, max_length=TextLimits.MAX_TEXT_LENGTH)
        
        # Use task priority
        priority = TaskPriority.HIGH
        assert priority > TaskPriority.LOW


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
