"""Property-Based Tests for FIR Generation (Properties 1-2)"""
import json
import pytest
from hypothesis import given, strategies as st, settings

# All 30 required FIR fields
FIR_FIELDS = [
    "complainant_name", "complainant_dob", "complainant_nationality",
    "complainant_father_husband_name", "complainant_address",
    "complainant_contact", "complainant_passport", "complainant_occupation",
    "incident_date_from", "incident_date_to", "incident_time_from",
    "incident_time_to", "incident_location", "incident_address",
    "incident_description", "delayed_reporting_reasons", "incident_summary",
    "legal_acts", "legal_sections", "suspect_details",
    "investigating_officer_name", "investigating_officer_rank",
    "witnesses", "action_taken", "investigation_status",
    "date_of_despatch", "investigating_officer_signature",
    "investigating_officer_date", "complainant_signature", "complainant_date"
]

# Strategy for complaint text
complaint_text_strategy = st.text(min_size=50, max_size=500)


@pytest.mark.property
@given(complaint_text=complaint_text_strategy)
@settings(max_examples=50, deadline=None)
def test_property_1_fir_field_completeness(complaint_text):
    """
    Property 1: FIR field completeness
    For any valid complaint text, generated FIR contains all 30 required fields
    with non-empty values.
    Validates: Requirements 5.1-5.30, 6.7, 18.5
    """
    # Mock FIR generation (replace with actual implementation)
    fir_data = _mock_generate_fir(complaint_text)
    
    # Check all 30 fields are present
    for field in FIR_FIELDS:
        assert field in fir_data, f"Missing required field: {field}"
        assert fir_data[field], f"Field {field} is empty"
        assert isinstance(fir_data[field], str), f"Field {field} is not a string"


@pytest.mark.proper