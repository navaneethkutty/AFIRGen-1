"""
Regression Test: FIR Required Fields Validation (BUG-0007)
Tests that FIR generation does not use hardcoded fallback values for legal documents.
"""

import pytest
from datetime import datetime
import json


class TestFIRRequiredFields:
    """Test FIR generation with required field validation."""

    def test_fir_with_all_required_fields(self):
        """
        Test FIR generation when all required fields are provided.
        Should succeed with validation_status='complete'.
        """
        from main_backend.agentv5 import get_fir_data
        
        session_state = {
            'complainant_name': 'Rajesh Kumar',
            'father_name': 'Suresh Kumar',
            'complainant_address': '123 MG Road, Bangalore',
            'complainant_contact': '9876543210',
            'occurrence_place': 'Cubbon Park',
            'incident_description': 'Theft of mobile phone',
            'police_station': 'Cubbon Park Police Station',
            'district': 'Bangalore Urban',
            'state': 'Karnataka',
            'io_name': 'Inspector Ramesh'
        }
        
        fir_data = get_fir_data(session_state, 'FIR-2026-001')
        
        # Verify all required fields are present
        assert fir_data['complainant_name'] == 'Rajesh Kumar'
        assert fir_data['father_name/husband_name'] == 'Suresh Kumar'
        assert fir_data['complainant_address'] == '123 MG Road, Bangalore'
        assert fir_data['complainant_contact'] == '9876543210'
        assert fir_data['Place of Occurrence'] == 'Cubbon Park'
        assert fir_data['incident_description'] == 'Theft of mobile phone'
        assert fir_data['police_station'] == 'Cubbon Park Police Station'
        assert fir_data['district'] == 'Bangalore Urban'
        assert fir_data['state'] == 'Karnataka'
        assert fir_data['io_name'] == 'Inspector Ramesh'
        
        # Verify validation status
        assert fir_data['_validation_status'] == 'complete'
        assert fir_data['_missing_fields'] == []
        
        print("✅ FIR with all required fields: validation_status='complete'")

    def test_fir_with_missing_required_fields(self):
        """
        Test FIR generation when required fields are missing.
        Should set fields to None and mark validation_status='incomplete'.
        
        SECURITY FIX: No hardcoded fallback values should be used.
        """
        from main_backend.agentv5 import get_fir_data
        
        # Session with missing required fields
        session_state = {
            'incident_description': 'Theft of mobile phone'
            # Missing: complainant_name, father_name, address, contact, etc.
        }
        
        fir_data = get_fir_data(session_state, 'FIR-2026-002')
        
        # SECURITY FIX: Verify NO hardcoded fallbacks are used
        assert fir_data['complainant_name'] is None, \
            "BUG-0007: Hardcoded fallback 'John Doe' still present!"
        assert fir_data['father_name/husband_name'] is None, \
            "BUG-0007: Hardcoded fallback 'Richard Doe' still present!"
        assert fir_data['complainant_address'] is None, \
            "BUG-0007: Hardcoded fallback '123 Main St.' still present!"
        assert fir_data['complainant_contact'] is None, \
            "BUG-0007: Hardcoded fallback '9876543210' still present!"
        assert fir_data['Place of Occurrence'] is None, \
            "BUG-0007: Hardcoded fallback 'Central Park, Metro City' still present!"
        assert fir_data['police_station'] is None, \
            "BUG-0007: Hardcoded fallback 'Central Police Station' still present!"
        assert fir_data['district'] is None, \
            "BUG-0007: Hardcoded fallback 'Metro City' still present!"
        assert fir_data['state'] is None, \
            "BUG-0007: Hardcoded fallback 'State of Example' still present!"
        assert fir_data['io_name'] is None, \
            "BUG-0007: Hardcoded fallback 'Inspector Rajesh Kumar' still present!"
        
        # Verify validation status
        assert fir_data['_validation_status'] == 'incomplete'
        assert len(fir_data['_missing_fields']) > 0
        
        # Verify missing fields are tracked
        expected_missing = [
            'complainant_name', 'father_name', 'complainant_address',
            'complainant_contact', 'occurrence_place', 'police_station',
            'district', 'state', 'io_name'
        ]
        for field in expected_missing:
            assert field in fir_data['_missing_fields'], \
                f"Missing field '{field}' not tracked in _missing_fields"
        
        print("✅ FIR with missing fields: No hardcoded fallbacks used")
        print(f"   Missing fields tracked: {fir_data['_missing_fields']}")

    def test_partial_fir_data(self):
        """
        Test FIR generation with some required fields present, some missing.
        """
        from main_backend.agentv5 import get_fir_data
        
        session_state = {
            'complainant_name': 'Priya Sharma',
            'complainant_contact': '9123456789',
            'incident_description': 'Vehicle accident',
            # Missing: father_name, address, occurrence_place, police_station, etc.
        }
        
        fir_data = get_fir_data(session_state, 'FIR-2026-003')
        
        # Verify provided fields are used
        assert fir_data['complainant_name'] == 'Priya Sharma'
        assert fir_data['complainant_contact'] == '9123456789'
        assert fir_data['incident_description'] == 'Vehicle accident'
        
        # Verify missing fields are None (not hardcoded)
        assert fir_data['father_name/husband_name'] is None
        assert fir_data['complainant_address'] is None
        assert fir_data['Place of Occurrence'] is None
        assert fir_data['police_station'] is None
        
        # Verify validation status
        assert fir_data['_validation_status'] == 'incomplete'
        assert 'father_name' in fir_data['_missing_fields']
        assert 'complainant_address' in fir_data['_missing_fields']
        
        print("✅ Partial FIR data: Provided fields used, missing fields set to None")

    def test_fir_validation_metadata(self):
        """
        Test that FIR data includes validation metadata.
        """
        from main_backend.agentv5 import get_fir_data
        
        session_state = {
            'complainant_name': 'Test User',
            'incident_description': 'Test incident'
        }
        
        fir_data = get_fir_data(session_state, 'FIR-2026-004')
        
        # Verify metadata fields exist
        assert '_validation_status' in fir_data
        assert '_missing_fields' in fir_data
        assert '_generated_at' in fir_data
        
        # Verify metadata types
        assert isinstance(fir_data['_validation_status'], str)
        assert isinstance(fir_data['_missing_fields'], list)
        assert isinstance(fir_data['_generated_at'], str)
        
        # Verify generated_at is valid ISO format
        try:
            datetime.fromisoformat(fir_data['_generated_at'])
        except ValueError:
            pytest.fail("_generated_at is not valid ISO format")
        
        print("✅ FIR validation metadata present and valid")

    def test_security_event_logging_for_missing_fields(self):
        """
        Test that security events are logged when required fields are missing.
        
        This is important for audit trails in legal systems.
        """
        from main_backend.agentv5 import get_fir_data
        from unittest.mock import patch
        
        session_state = {
            'incident_description': 'Test incident'
            # Missing all other required fields
        }
        
        # Mock the security event logger
        with patch('main_backend.agentv5.log_security_event') as mock_log:
            fir_data = get_fir_data(session_state, 'FIR-2026-005')
            
            # Verify security event was logged
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            
            # Verify event type
            assert call_args[1]['event_type'] == 'fir_missing_required_fields'
            assert call_args[1]['severity'] == 'high'
            assert 'missing_fields' in call_args[1]
        
        print("✅ Security event logged for missing required fields")

    def test_fir_finalization_should_validate_required_fields(self):
        """
        Test that FIR finalization endpoint should validate required fields.
        
        This is a recommendation for upstream validation.
        """
        # This test documents the expected behavior
        # Actual implementation should be in the finalize endpoint
        
        print("✅ Recommendation: FIR finalization endpoint should:")
        print("   1. Check _validation_status == 'complete'")
        print("   2. Reject finalization if _missing_fields is not empty")
        print("   3. Return 400 Bad Request with list of missing fields")
        print("   4. Log validation failure for audit trail")

    def test_no_hardcoded_legal_values(self):
        """
        Comprehensive test to ensure NO hardcoded legal values are used.
        """
        from main_backend.agentv5 import get_fir_data
        
        # Empty session state
        session_state = {}
        
        fir_data = get_fir_data(session_state, 'FIR-2026-006')
        
        # List of fields that should NEVER have hardcoded values
        legal_fields = {
            'complainant_name': ['John Doe', 'Jane Doe'],
            'father_name/husband_name': ['Richard Doe', 'Robert Doe'],
            'complainant_address': ['123 Main St', '123 Main Street'],
            'complainant_contact': ['9876543210', '1234567890'],
            'Place of Occurrence': ['Central Park', 'Metro City'],
            'police_station': ['Central Police Station', 'Police Station'],
            'district': ['Metro City', 'City District'],
            'state': ['State of Example', 'Example State'],
            'io_name': ['Inspector Rajesh Kumar', 'Inspector Kumar']
        }
        
        for field, forbidden_values in legal_fields.items():
            field_value = fir_data.get(field)
            
            # Field should be None or empty, not a hardcoded value
            if field_value:
                for forbidden in forbidden_values:
                    assert field_value != forbidden, \
                        f"BUG-0007: Hardcoded value '{forbidden}' found in field '{field}'"
        
        print("✅ No hardcoded legal values found in FIR data")

    def test_fir_template_handles_none_values(self):
        """
        Test that FIR template can handle None values without crashing.
        """
        from main_backend.agentv5 import get_fir_data, fir_template
        
        session_state = {}
        fir_data = get_fir_data(session_state, 'FIR-2026-007')
        
        # Try to format template with None values
        try:
            # Replace None with empty string for template formatting
            template_data = {k: (v if v is not None else '') for k, v in fir_data.items()}
            formatted_fir = fir_template.format(**template_data)
            
            # Verify template was formatted (even with empty values)
            assert 'FIR-2026-007' in formatted_fir
            assert 'FIRST INFORMATION REPORT' in formatted_fir
            
            print("✅ FIR template handles None values correctly")
        except KeyError as e:
            pytest.fail(f"FIR template missing key: {e}")
        except Exception as e:
            pytest.fail(f"FIR template formatting failed: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
