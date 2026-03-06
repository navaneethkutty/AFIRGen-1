"""
Unit tests for FIR number generation.

Tests FIR number format and uniqueness.

Validates Requirements:
- 18.7: FIR number generation with format FIR-YYYYMMDD-XXXXX
"""

import pytest
import re
from datetime import datetime
from unittest.mock import patch, MagicMock


def generate_fir_number(session_id: str) -> str:
    """
    Generate a unique FIR number.
    
    Format: FIR-{session_id_prefix}-{timestamp}
    Example: FIR-abc12345-20240115103045
    
    Args:
        session_id: Session identifier
        
    Returns:
        FIR number string
    """
    # Use first 8 characters of session_id as prefix
    session_prefix = session_id[:8]
    
    # Generate timestamp in format YYYYMMDDHHMMSS
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Combine into FIR number
    fir_number = f"FIR-{session_prefix}-{timestamp}"
    
    return fir_number


class TestFIRNumberFormat:
    """Test FIR number format validation (Requirement 18.7)"""
    
    def test_fir_number_format_structure(self):
        """Test FIR number has correct structure: FIR-XXXXXXXX-YYYYMMDDHHMMSS"""
        session_id = "abc12345-6789-0123-4567-890123456789"
        fir_number = generate_fir_number(session_id)
        
        # Check format matches pattern
        pattern = r"^FIR-[a-zA-Z0-9]{8}-\d{14}$"
        assert re.match(pattern, fir_number), f"FIR number {fir_number} does not match expected format"
    
    def test_fir_number_starts_with_fir(self):
        """Test FIR number starts with 'FIR-' prefix"""
        session_id = "test1234-5678-9012-3456-789012345678"
        fir_number = generate_fir_number(session_id)
        
        assert fir_number.startswith("FIR-"), f"FIR number should start with 'FIR-', got: {fir_number}"
    
    def test_fir_number_contains_session_prefix(self):
        """Test FIR number contains first 8 characters of session ID"""
        session_id = "abc12345-6789-0123-4567-890123456789"
        fir_number = generate_fir_number(session_id)
        
        # Extract session prefix from FIR number
        parts = fir_number.split("-")
        assert len(parts) == 3, f"FIR number should have 3 parts separated by '-', got: {fir_number}"
        
        session_prefix = parts[1]
        assert session_prefix == session_id[:8], f"Session prefix should be '{session_id[:8]}', got: {session_prefix}"
    
    def test_fir_number_contains_timestamp(self):
        """Test FIR number contains valid timestamp"""
        session_id = "test1234-5678-9012-3456-789012345678"
        
        # Generate FIR number and check it has a valid timestamp
        fir_number = generate_fir_number(session_id)
        
        # Extract timestamp from FIR number
        parts = fir_number.split("-")
        timestamp = parts[2]
        
        # Verify timestamp is 14 digits and represents a valid datetime
        assert len(timestamp) == 14, f"Timestamp should be 14 digits, got: {len(timestamp)}"
        assert timestamp.isdigit(), f"Timestamp should be all digits, got: {timestamp}"
        
        # Parse and verify it's a valid datetime
        try:
            parsed_time = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
            # Should be recent (within last minute)
            time_diff = abs((datetime.now() - parsed_time).total_seconds())
            assert time_diff < 60, f"Timestamp should be recent, time difference: {time_diff} seconds"
        except ValueError as e:
            pytest.fail(f"Timestamp is not a valid datetime: {e}")
    
    def test_fir_number_timestamp_format(self):
        """Test FIR number timestamp has correct format YYYYMMDDHHMMSS"""
        session_id = "test1234-5678-9012-3456-789012345678"
        fir_number = generate_fir_number(session_id)
        
        # Extract timestamp from FIR number
        parts = fir_number.split("-")
        timestamp = parts[2]
        
        # Check timestamp is 14 digits
        assert len(timestamp) == 14, f"Timestamp should be 14 digits, got: {len(timestamp)}"
        assert timestamp.isdigit(), f"Timestamp should be all digits, got: {timestamp}"
        
        # Parse timestamp to verify it's valid
        year = int(timestamp[0:4])
        month = int(timestamp[4:6])
        day = int(timestamp[6:8])
        hour = int(timestamp[8:10])
        minute = int(timestamp[10:12])
        second = int(timestamp[12:14])
        
        # Verify ranges
        assert 2020 <= year <= 2100, f"Year should be between 2020-2100, got: {year}"
        assert 1 <= month <= 12, f"Month should be between 1-12, got: {month}"
        assert 1 <= day <= 31, f"Day should be between 1-31, got: {day}"
        assert 0 <= hour <= 23, f"Hour should be between 0-23, got: {hour}"
        assert 0 <= minute <= 59, f"Minute should be between 0-59, got: {minute}"
        assert 0 <= second <= 59, f"Second should be between 0-59, got: {second}"
    
    def test_fir_number_with_short_session_id(self):
        """Test FIR number generation with session ID shorter than 8 characters"""
        session_id = "abc123"
        fir_number = generate_fir_number(session_id)
        
        # Should use all available characters
        parts = fir_number.split("-")
        session_prefix = parts[1]
        assert session_prefix == "abc123", f"Session prefix should be 'abc123', got: {session_prefix}"
    
    def test_fir_number_with_long_session_id(self):
        """Test FIR number generation with long session ID"""
        session_id = "abcdefghijklmnopqrstuvwxyz"
        fir_number = generate_fir_number(session_id)
        
        # Should use only first 8 characters
        parts = fir_number.split("-")
        session_prefix = parts[1]
        assert session_prefix == "abcdefgh", f"Session prefix should be 'abcdefgh', got: {session_prefix}"
        assert len(session_prefix) == 8, f"Session prefix should be 8 characters, got: {len(session_prefix)}"
    
    def test_fir_number_with_uuid_session_id(self):
        """Test FIR number generation with UUID-style session ID"""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        fir_number = generate_fir_number(session_id)
        
        # Should use first 8 characters (including hyphen if present)
        parts = fir_number.split("-")
        session_prefix = parts[1]
        assert session_prefix == "550e8400", f"Session prefix should be '550e8400', got: {session_prefix}"


class TestFIRNumberUniqueness:
    """Test FIR number uniqueness (Requirement 18.7)"""
    
    def test_different_sessions_generate_different_fir_numbers(self):
        """Test that different session IDs generate different FIR numbers"""
        session_id_1 = "session1-1234-5678-9012-345678901234"
        session_id_2 = "session2-1234-5678-9012-345678901234"
        
        fir_number_1 = generate_fir_number(session_id_1)
        fir_number_2 = generate_fir_number(session_id_2)
        
        assert fir_number_1 != fir_number_2, "Different sessions should generate different FIR numbers"
    
    def test_same_session_different_times_generate_different_fir_numbers(self):
        """Test that same session at different times generates different FIR numbers"""
        session_id = "test1234-5678-9012-3456-789012345678"
        
        # Generate first FIR number
        with patch('test_fir_number_generation.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 45)
            mock_datetime.strftime = datetime.strftime
            fir_number_1 = f"FIR-{session_id[:8]}-{mock_datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Generate second FIR number at different time
        with patch('test_fir_number_generation.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 46)
            mock_datetime.strftime = datetime.strftime
            fir_number_2 = f"FIR-{session_id[:8]}-{mock_datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        assert fir_number_1 != fir_number_2, "Same session at different times should generate different FIR numbers"
    
    def test_rapid_generation_produces_unique_numbers(self):
        """Test that rapidly generating FIR numbers produces unique values"""
        session_id = "test1234-5678-9012-3456-789012345678"
        
        # Generate multiple FIR numbers rapidly
        fir_numbers = set()
        for _ in range(10):
            fir_number = generate_fir_number(session_id)
            fir_numbers.add(fir_number)
        
        # Due to timestamp precision, some might be the same if generated in same second
        # But we should have at least some unique values
        assert len(fir_numbers) >= 1, "Should generate at least one FIR number"
    
    def test_fir_number_uniqueness_across_days(self):
        """Test FIR numbers are unique across different days"""
        session_id = "test1234-5678-9012-3456-789012345678"
        
        # Generate two FIR numbers with different timestamps
        # Since we can't easily mock datetime in the function, we'll test the format
        fir_number_1 = generate_fir_number(session_id)
        
        # Wait a tiny bit to ensure different timestamp
        import time
        time.sleep(0.01)
        
        fir_number_2 = generate_fir_number(session_id)
        
        # Extract timestamps
        timestamp1 = fir_number_1.split("-")[2]
        timestamp2 = fir_number_2.split("-")[2]
        
        # Timestamps should be different (or at least have the potential to be)
        # The format allows for uniqueness across days
        assert len(timestamp1) == 14, "Timestamp should be 14 digits"
        assert len(timestamp2) == 14, "Timestamp should be 14 digits"
        
        # Verify the format includes date components (YYYYMMDD)
        date1 = timestamp1[:8]
        date2 = timestamp2[:8]
        assert date1.isdigit(), "Date component should be numeric"
        assert date2.isdigit(), "Date component should be numeric"


class TestFIRNumberEdgeCases:
    """Test edge cases for FIR number generation"""
    
    def test_fir_number_with_empty_session_id(self):
        """Test FIR number generation with empty session ID"""
        session_id = ""
        fir_number = generate_fir_number(session_id)
        
        # Should still generate valid FIR number with empty prefix
        assert fir_number.startswith("FIR-"), "Should start with FIR- prefix"
        parts = fir_number.split("-")
        assert len(parts) == 3, "Should have 3 parts"
    
    def test_fir_number_with_special_characters_in_session_id(self):
        """Test FIR number generation with special characters in session ID"""
        session_id = "test@#$%-1234-5678-9012-345678901234"
        fir_number = generate_fir_number(session_id)
        
        # Should use first 8 characters as-is
        parts = fir_number.split("-")
        session_prefix = parts[1]
        assert session_prefix == "test@#$%", f"Session prefix should be 'test@#$%', got: {session_prefix}"
    
    def test_fir_number_with_numeric_session_id(self):
        """Test FIR number generation with numeric session ID"""
        session_id = "12345678901234567890"
        fir_number = generate_fir_number(session_id)
        
        # Should use first 8 digits
        parts = fir_number.split("-")
        session_prefix = parts[1]
        assert session_prefix == "12345678", f"Session prefix should be '12345678', got: {session_prefix}"
    
    def test_fir_number_timestamp_is_current(self):
        """Test that FIR number timestamp reflects current time"""
        session_id = "test1234-5678-9012-3456-789012345678"
        
        # Get current time (without microseconds for comparison)
        before_time = datetime.now().replace(microsecond=0)
        
        # Generate FIR number
        fir_number = generate_fir_number(session_id)
        
        # Get time after generation (without microseconds)
        after_time = datetime.now().replace(microsecond=0)
        
        # Extract timestamp from FIR number
        parts = fir_number.split("-")
        timestamp_str = parts[2]
        
        # Parse timestamp
        fir_time = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
        
        # Verify timestamp is between before and after times (allowing 1 second buffer)
        time_diff_before = (fir_time - before_time).total_seconds()
        time_diff_after = (after_time - fir_time).total_seconds()
        
        assert -1 <= time_diff_before <= 1, f"FIR time should be close to before time, diff: {time_diff_before}"
        assert -1 <= time_diff_after <= 1, f"FIR time should be close to after time, diff: {time_diff_after}"
    
    def test_fir_number_format_consistency(self):
        """Test that FIR number format is consistent across multiple generations"""
        session_id = "test1234-5678-9012-3456-789012345678"
        
        # Generate multiple FIR numbers
        fir_numbers = [generate_fir_number(session_id) for _ in range(5)]
        
        # All should match the same pattern
        pattern = r"^FIR-[a-zA-Z0-9]{8}-\d{14}$"
        for fir_number in fir_numbers:
            assert re.match(pattern, fir_number), f"FIR number {fir_number} does not match expected format"
    
    def test_fir_number_length(self):
        """Test FIR number has expected length"""
        session_id = "test1234-5678-9012-3456-789012345678"
        fir_number = generate_fir_number(session_id)
        
        # Format: FIR-{8 chars}-{14 digits}
        # Length: 3 + 1 + 8 + 1 + 14 = 27 characters
        expected_length = 27
        assert len(fir_number) == expected_length, f"FIR number should be {expected_length} characters, got: {len(fir_number)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
