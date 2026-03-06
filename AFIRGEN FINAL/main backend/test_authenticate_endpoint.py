"""
Test for POST /authenticate endpoint

This test verifies that the authenticate endpoint:
1. Accepts session_id, complainant_signature, and officer_signature
2. Retrieves FIR from session
3. Generates PDF with signatures
4. Uploads PDF to S3
5. Updates FIR status to "finalized"
6. Returns fir_number and pdf_url
"""

import pytest
import json
import uuid
import os
from unittest.mock import Mock, patch, MagicMock

# Set environment variables before importing the app
os.environ['S3_BUCKET_NAME'] = 'test-bucket'
os.environ['DB_HOST'] = 'test-host'
os.environ['DB_PASSWORD'] = 'test-password'
os.environ['API_KEY'] = 'test-api-key'
os.environ['AWS_REGION'] = 'us-east-1'

from fastapi.testclient import TestClient

# Mock the database and AWS clients before importing the app
with patch('agentv5_clean.DatabaseManager'), \
     patch('agentv5_clean.AWSServiceClients'):
    from agentv5_clean import app, config


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_session_data():
    """Mock session data with completed FIR"""
    return {
        'session_id': str(uuid.uuid4()),
        'status': 'completed',
        'fir_number': 'FIR-20240115-00001',
        'fir_content': {
            'complainant_name': 'John Doe',
            'complainant_dob': '01/01/1990',
            'complainant_nationality': 'Indian',
            'complainant_father_husband_name': 'Father Name',
            'complainant_address': '123 Test St',
            'complainant_contact': '1234567890',
            'complainant_passport': 'N/A',
            'complainant_occupation': 'Engineer',
            'incident_date_from': '01/01/2024',
            'incident_date_to': '01/01/2024',
            'incident_time_from': '10:00',
            'incident_time_to': '11:00',
            'incident_location': 'Test Location',
            'incident_address': 'Test Address',
            'incident_description': 'Test incident',
            'delayed_reporting_reasons': 'N/A',
            'incident_summary': 'Test summary',
            'legal_acts': 'IPC',
            'legal_sections': '420',
            'suspect_details': 'Unknown',
            'investigating_officer_name': '',
            'investigating_officer_rank': '',
            'witnesses': 'None',
            'action_taken': 'FIR filed',
            'investigation_status': 'Pending',
            'date_of_despatch': '15/01/2024',
            'investigating_officer_signature': '',
            'investigating_officer_date': '15/01/2024',
            'complainant_signature': '',
            'complainant_date': '15/01/2024'
        }
    }


def test_authenticate_endpoint_success(client, mock_session_data):
    """Test successful FIR authentication"""
    
    session_id = mock_session_data['session_id']
    
    with patch('agentv5_clean.db_manager') as mock_db, \
         patch('agentv5_clean.pdf_generator') as mock_pdf, \
         patch('agentv5_clean.aws_clients') as mock_aws:
        
        # Mock database get_session
        mock_db.get_session.return_value = mock_session_data
        
        # Mock PDF generation
        mock_pdf.generate_fir_pdf.return_value = b'fake_pdf_content'
        
        # Mock S3 upload
        mock_aws.upload_to_s3.return_value = f"https://s3.amazonaws.com/bucket/pdfs/{mock_session_data['fir_number']}.pdf"
        
        # Mock update_fir_status
        mock_db.update_fir_status.return_value = None
        
        # Make request
        response = client.post(
            "/authenticate",
            json={
                "session_id": session_id,
                "complainant_signature": "John Doe Signature",
                "officer_signature": "Officer Signature"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data['fir_number'] == mock_session_data['fir_number']
        assert 'pdf_url' in data
        assert data['status'] == 'finalized'
        
        # Verify PDF was generated
        mock_pdf.generate_fir_pdf.assert_called_once()
        
        # Verify PDF was uploaded to S3
        mock_aws.upload_to_s3.assert_called_once()
        
        # Verify FIR status was updated
        mock_db.update_fir_status.assert_called_once_with(
            mock_session_data['fir_number'],
            'finalized'
        )


def test_authenticate_endpoint_missing_api_key(client):
    """Test authenticate endpoint without API key"""
    
    response = client.post(
        "/authenticate",
        json={
            "session_id": str(uuid.uuid4()),
            "complainant_signature": "Signature",
            "officer_signature": "Officer Signature"
        }
    )
    
    assert response.status_code == 422  # Missing required header


def test_authenticate_endpoint_invalid_api_key(client):
    """Test authenticate endpoint with invalid API key"""
    
    response = client.post(
        "/authenticate",
        json={
            "session_id": str(uuid.uuid4()),
            "complainant_signature": "Signature",
            "officer_signature": "Officer Signature"
        },
        headers={"X-API-Key": "invalid_key"}
    )
    
    assert response.status_code == 401


def test_authenticate_endpoint_session_not_found(client):
    """Test authenticate endpoint with non-existent session"""
    
    with patch('agentv5_clean.db_manager') as mock_db:
        mock_db.get_session.return_value = None
        
        response = client.post(
            "/authenticate",
            json={
                "session_id": str(uuid.uuid4()),
                "complainant_signature": "Signature",
                "officer_signature": "Officer Signature"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 404


def test_authenticate_endpoint_session_not_completed(client, mock_session_data):
    """Test authenticate endpoint with session that is not completed"""
    
    mock_session_data['status'] = 'processing'
    
    with patch('agentv5_clean.db_manager') as mock_db:
        mock_db.get_session.return_value = mock_session_data
        
        response = client.post(
            "/authenticate",
            json={
                "session_id": mock_session_data['session_id'],
                "complainant_signature": "Signature",
                "officer_signature": "Officer Signature"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 400
        assert 'not completed' in response.json()['detail'].lower()


def test_authenticate_endpoint_missing_fir_content(client, mock_session_data):
    """Test authenticate endpoint with session missing FIR content"""
    
    mock_session_data['fir_content'] = None
    
    with patch('agentv5_clean.db_manager') as mock_db:
        mock_db.get_session.return_value = mock_session_data
        
        response = client.post(
            "/authenticate",
            json={
                "session_id": mock_session_data['session_id'],
                "complainant_signature": "Signature",
                "officer_signature": "Officer Signature"
            },
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 400
        assert 'not found' in response.json()['detail'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

