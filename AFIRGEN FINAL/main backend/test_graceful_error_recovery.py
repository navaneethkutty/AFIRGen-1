"""
Unit tests for graceful error recovery in FIR generation workflow.

Tests verify that the system:
1. Continues workflow with empty IPC sections if retrieval fails
2. Uses basic defaults if metadata extraction fails
3. Cleans up S3 files even on failure
4. Marks session as failed and stores error message
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Mock the database and AWS connections before importing the module
with patch('mysql.connector.pooling.MySQLConnectionPool'):
    with patch('sqlite3.connect'):
        with patch('boto3.client'):
            from agentv5_clean import FIRGenerator, AWSServiceClients, DatabaseManager


class TestGracefulErrorRecovery:
    """Test graceful error recovery in FIR generation workflow"""
    
    @pytest.fixture
    def mock_aws_clients(self):
        """Create mock AWS clients"""
        mock = Mock(spec=AWSServiceClients)
        return mock
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager"""
        mock = Mock(spec=DatabaseManager)
        return mock
    
    @pytest.fixture
    def fir_generator(self, mock_aws_clients, mock_db_manager):
        """Create FIR generator with mocked dependencies"""
        return FIRGenerator(mock_aws_clients, mock_db_manager)
    
    def test_continue_with_empty_ipc_sections_on_retrieval_failure(self, fir_generator, mock_db_manager):
        """Test that workflow continues with empty IPC sections if retrieval fails"""
        # Arrange
        metadata = {
            "complainant_name": "John Doe",
            "incident_date": "2024-01-15",
            "incident_time": "10:00",
            "incident_location": "Mumbai",
            "incident_type": "theft",
            "keywords": ["theft", "property"]
        }
        
        # Simulate database failure
        mock_db_manager.get_ipc_sections.side_effect = Exception("Database connection failed")
        
        # Act
        result = fir_generator._retrieve_ipc_sections(metadata)
        
        # Assert
        assert result == []
        assert mock_db_manager.get_ipc_sections.called
    
    def test_use_basic_defaults_on_metadata_extraction_failure(self, fir_generator, mock_aws_clients):
        """Test that basic defaults are used if metadata extraction fails"""
        # Arrange
        narrative = "This is a formal narrative about an incident."
        
        # Simulate Claude returning invalid JSON
        mock_aws_clients.invoke_claude.return_value = "Invalid JSON response"
        
        # Act
        result = fir_generator._extract_metadata(narrative)
        
        # Assert
        assert result == {
            "complainant_name": "Unknown",
            "incident_date": "Unknown",
            "incident_time": "Unknown",
            "incident_location": "Unknown",
            "incident_type": "Unknown",
            "keywords": []
        }
        assert mock_aws_clients.invoke_claude.called
    
    def test_use_basic_defaults_on_claude_invocation_failure(self, fir_generator, mock_aws_clients):
        """Test that basic defaults are used if Claude invocation fails"""
        # Arrange
        narrative = "This is a formal narrative about an incident."
        
        # Simulate Claude invocation failure
        mock_aws_clients.invoke_claude.side_effect = Exception("Bedrock service unavailable")
        
        # Act
        result = fir_generator._extract_metadata(narrative)
        
        # Assert
        assert result == {
            "complainant_name": "Unknown",
            "incident_date": "Unknown",
            "incident_time": "Unknown",
            "incident_location": "Unknown",
            "incident_type": "Unknown",
            "keywords": []
        }
        assert mock_aws_clients.invoke_claude.called
    
    def test_cleanup_s3_audio_file_on_failure(self, fir_generator, mock_aws_clients, mock_db_manager):
        """Test that S3 audio file is cleaned up even on failure"""
        # Arrange
        audio_bytes = b"fake audio data"
        language = "en-IN"
        session_id = "test-session-123"
        
        # Simulate transcription failure
        mock_aws_clients.upload_to_s3.return_value = "s3://bucket/audio/test.mp3"
        mock_aws_clients.transcribe_audio.side_effect = Exception("Transcription failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Transcription failed"):
            fir_generator.generate_from_audio(audio_bytes, language, session_id)
        
        # Verify S3 cleanup was attempted
        assert mock_aws_clients.delete_from_s3.called
        assert mock_db_manager.update_session.called
        
        # Verify session was marked as failed
        update_calls = mock_db_manager.update_session.call_args_list
        failed_call = [call for call in update_calls if call[0][1].get("status") == "failed"]
        assert len(failed_call) > 0
        assert "error" in failed_call[0][0][1]
    
    def test_cleanup_s3_image_file_on_failure(self, fir_generator, mock_aws_clients, mock_db_manager):
        """Test that S3 image file is cleaned up even on failure"""
        # Arrange
        image_bytes = b"fake image data"
        session_id = "test-session-456"
        
        # Simulate text extraction failure
        mock_aws_clients.upload_to_s3.return_value = "s3://bucket/images/test.jpg"
        mock_aws_clients.extract_text_from_image.side_effect = Exception("Textract failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Textract failed"):
            fir_generator.generate_from_image(image_bytes, session_id)
        
        # Verify S3 cleanup was attempted
        assert mock_aws_clients.delete_from_s3.called
        assert mock_db_manager.update_session.called
        
        # Verify session was marked as failed
        update_calls = mock_db_manager.update_session.call_args_list
        failed_call = [call for call in update_calls if call[0][1].get("status") == "failed"]
        assert len(failed_call) > 0
        assert "error" in failed_call[0][0][1]
    
    def test_mark_session_as_failed_with_error_message(self, fir_generator, mock_aws_clients, mock_db_manager):
        """Test that session is marked as failed with error message stored"""
        # Arrange
        text = "This is a complaint text."
        session_id = "test-session-789"
        error_message = "FIR generation failed due to invalid response"
        
        # Simulate failure in formal narrative generation
        mock_aws_clients.invoke_claude.side_effect = Exception(error_message)
        
        # Act & Assert
        with pytest.raises(Exception, match=error_message):
            fir_generator.generate_from_text(text, session_id)
        
        # Verify session was marked as failed with error message
        update_calls = mock_db_manager.update_session.call_args_list
        failed_call = [call for call in update_calls if call[0][1].get("status") == "failed"]
        assert len(failed_call) > 0
        assert failed_call[0][0][1]["error"] == error_message
    
    def test_generate_fir_with_empty_ipc_sections(self, fir_generator, mock_aws_clients):
        """Test that FIR generation continues with empty IPC sections"""
        # Arrange
        narrative = "Formal narrative about an incident."
        metadata = {
            "complainant_name": "John Doe",
            "incident_date": "2024-01-15",
            "incident_time": "10:00",
            "incident_location": "Mumbai",
            "incident_type": "theft",
            "keywords": ["theft"]
        }
        ipc_sections = []  # Empty IPC sections
        
        # Mock Claude to return valid FIR JSON
        fir_json = {
            "complainant_name": "John Doe",
            "complainant_dob": "01/01/1990",
            "complainant_nationality": "Indian",
            "complainant_father_husband_name": "Father Name",
            "complainant_address": "Address",
            "complainant_contact": "1234567890",
            "complainant_passport": "N/A",
            "complainant_occupation": "Engineer",
            "incident_date_from": "15/01/2024",
            "incident_date_to": "15/01/2024",
            "incident_time_from": "10:00",
            "incident_time_to": "11:00",
            "incident_location": "Mumbai",
            "incident_address": "Incident Address",
            "incident_description": "Description",
            "delayed_reporting_reasons": "N/A",
            "incident_summary": "Summary",
            "legal_acts": "IPC",
            "legal_sections": "General sections",
            "suspect_details": "Unknown",
            "investigating_officer_name": "",
            "investigating_officer_rank": "",
            "witnesses": "None",
            "action_taken": "FIR filed",
            "investigation_status": "Pending",
            "date_of_despatch": "15/01/2024",
            "investigating_officer_signature": "Placeholder",
            "investigating_officer_date": "15/01/2024",
            "complainant_signature": "Placeholder",
            "complainant_date": "15/01/2024"
        }
        mock_aws_clients.invoke_claude.return_value = json.dumps(fir_json)
        
        # Act
        result = fir_generator._generate_complete_fir(narrative, metadata, ipc_sections)
        
        # Assert
        assert result is not None
        assert "complainant_name" in result
        assert mock_aws_clients.invoke_claude.called
        
        # Verify the prompt includes message about empty IPC sections
        call_args = mock_aws_clients.invoke_claude.call_args
        prompt = call_args[0][0]
        assert "No specific IPC sections retrieved" in prompt or "general applicable sections" in prompt.lower()
    
    def test_s3_cleanup_continues_even_if_cleanup_fails(self, fir_generator, mock_aws_clients, mock_db_manager):
        """Test that workflow continues even if S3 cleanup fails"""
        # Arrange
        audio_bytes = b"fake audio data"
        language = "en-IN"
        session_id = "test-session-cleanup"
        
        # Simulate transcription failure and cleanup failure
        mock_aws_clients.upload_to_s3.return_value = "s3://bucket/audio/test.mp3"
        mock_aws_clients.transcribe_audio.side_effect = Exception("Transcription failed")
        mock_aws_clients.delete_from_s3.side_effect = Exception("S3 delete failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Transcription failed"):
            fir_generator.generate_from_audio(audio_bytes, language, session_id)
        
        # Verify cleanup was attempted (even though it failed)
        assert mock_aws_clients.delete_from_s3.called
        
        # Verify session was still marked as failed with original error
        update_calls = mock_db_manager.update_session.call_args_list
        failed_call = [call for call in update_calls if call[0][1].get("status") == "failed"]
        assert len(failed_call) > 0
        assert "Transcription failed" in failed_call[0][0][1]["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
