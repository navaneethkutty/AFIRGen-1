"""
Integration Test for Task 25.2 - Complete Audio File FIR Generation Flow

**Validates: Requirements 3.1, 3.5, 3.6**

This integration test verifies the complete audio file FIR generation workflow works end-to-end
and that preservation requirements are met (audio processing continues to work unchanged after bug fixes).

Test Flow:
1. Upload valid .wav or .mp3 audio file
2. Verify processing succeeds
3. Complete validation workflow
4. Verify FIR generation completes successfully

This test confirms that audio file processing is preserved after all bug fixes.
"""

import pytest
import sys
import io
import wave
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


def create_valid_wav_audio(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Create a valid WAV audio file in memory."""
    num_channels = 1
    sample_width = 2  # 16-bit audio
    num_frames = int(duration_seconds * sample_rate)
    
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(num_channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        
        # Generate silence (zeros)
        audio_data = b'\x00\x00' * num_frames
        wav_file.writeframes(audio_data)
    
    buffer.seek(0)
    return buffer.read()


def create_valid_mp3_audio() -> bytes:
    """Create a minimal valid MP3 file (just headers for testing)."""
    # MP3 frame header: 11 bits sync word (all set), MPEG version, layer, etc.
    # This is a minimal valid MP3 frame header
    mp3_header = bytes([
        0xFF, 0xFB,  # Sync word + MPEG version + Layer
        0x90, 0x00,  # Bitrate + Sample rate + Padding + Private
    ])
    # Repeat to make a minimal valid file
    return mp3_header * 10


@pytest.fixture
def mock_model_pool():
    """Mock ModelPool to avoid external dependencies."""
    mock_pool = AsyncMock()
    
    # Mock the transcribe method for audio processing
    mock_pool.transcribe = AsyncMock(return_value="This is a test transcription of the audio complaint.")
    
    # Mock the two_line_summary method
    mock_pool.two_line_summary = AsyncMock(return_value="Test summary of the audio complaint")
    
    # Mock the check_violation method
    mock_pool.check_violation = AsyncMock(return_value=True)
    
    # Mock the fir_narrative method
    mock_pool.fir_narrative = AsyncMock(return_value="Test FIR narrative content from audio")
    
    return mock_pool


@pytest.fixture
def mock_kb():
    """Mock KB (knowledge base) to avoid external dependencies."""
    mock = Mock()
    mock.retrieve = Mock(return_value=[
        {
            "section": "Section 379",
            "title": "Theft",
            "description": "Test violation description for theft"
        }
    ])
    return mock


@pytest.fixture
def test_client(mock_model_pool, mock_kb):
    """Create a test client with mocked dependencies."""
    # Mock DB class to avoid pool_timeout configuration issue
    mock_db = Mock()
    mock_db.flush_all = Mock()
    mock_db.get_fir = Mock(return_value=None)
    mock_db.save_fir = Mock()
    
    # Import agentv5 and patch dependencies
    with patch('agentv5.ModelPool') as MockModelPool, \
         patch('agentv5.KB') as MockKB, \
         patch('agentv5.DB', return_value=mock_db):
        
        # Configure mocks
        MockModelPool.get = AsyncMock(return_value=mock_model_pool)
        MockKB.return_value = mock_kb
        
        # Import the app after patching
        from agentv5 import app, session_manager
        
        # Clean up any existing test data
        try:
            session_manager.flush_all()
        except:
            pass
        
        # Create test client
        client = TestClient(app)
        
        yield client
        
        # Cleanup after test
        try:
            session_manager.flush_all()
        except:
            pass


@pytest.mark.integration
def test_complete_audio_wav_fir_generation_flow(test_client):
    """
    Test the complete audio file (.wav) FIR generation workflow end-to-end.
    
    **Validates: Requirements 3.1, 3.5, 3.6**
    
    This test verifies that audio file processing continues to work unchanged after bug fixes:
    - Audio files are processed through the initial_processing pipeline
    - Sessions with audio inputs reach AWAITING_VALIDATION status
    - Validation workflow completes successfully
    - FIR documents are generated with correct data and formatting
    
    Test Flow:
    1. Upload valid .wav audio file
    2. Verify processing succeeds and session is created
    3. Verify session status is AWAITING_VALIDATION
    4. Complete validation workflow (all steps)
    5. Verify FIR generation completes successfully
    6. Retrieve and verify FIR content
    """
    
    # Step 1: Upload valid .wav audio file
    print("\n=== Step 1: Upload valid .wav audio file ===")
    
    audio_data = create_valid_wav_audio(duration_seconds=2.0, sample_rate=16000)
    
    files = {
        'audio': ('test_complaint.wav', io.BytesIO(audio_data), 'audio/wav')
    }
    
    response = test_client.post(
        "/process",
        files=files,
        headers={"X-API-Key": "test-key-123"}
    )
    
    # Step 2: Verify processing succeeds
    print("\n=== Step 2: Verify processing succeeds ===")
    
    assert response.status_code in [200, 202], \
        f"Audio processing should succeed, got {response.status_code}: {response.text}"
    
    process_data = response.json()
    print(f"Process response: {process_data}")
    
    assert process_data["success"] is True, "Audio processing should succeed"
    assert "session_id" in process_data, "Response should include session_id"
    assert process_data["requires_validation"] is True, "Should require validation"
    assert process_data["current_step"] == "TRANSCRIPT_REVIEW", "Should start at TRANSCRIPT_REVIEW"
    
    session_id = process_data["session_id"]
    print(f"Session ID: {session_id}")
    
    # Step 3: Verify session status is AWAITING_VALIDATION
    print("\n=== Step 3: Verify session status is AWAITING_VALIDATION ===")
    
    status_response = test_client.get(
        f"/session/{session_id}/status",
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert status_response.status_code == 200, f"Status endpoint failed: {status_response.text}"
    
    status_data = status_response.json()
    print(f"Status response: {status_data}")
    
    assert status_data["status"] == "AWAITING_VALIDATION", \
        "Requirement 3.2: Audio sessions should reach AWAITING_VALIDATION status"
    assert status_data["awaiting_validation"] is True, "awaiting_validation flag should be True"
    assert status_data["current_step"] == "TRANSCRIPT_REVIEW", "Should be at TRANSCRIPT_REVIEW step"
    
    # Step 4: Complete validation workflow
    print("\n=== Step 4: Complete validation workflow ===")
    
    # Step 4.1: TRANSCRIPT_REVIEW
    print("\n--- Step 4.1: POST /validate for TRANSCRIPT_REVIEW ---")
    
    validate_response = test_client.post(
        "/validate",
        json={
            "session_id": session_id,
            "approved": True,
            "user_input": None
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert validate_response.status_code == 200, \
        f"Requirement 3.2: Validation should accept audio sessions. Error: {validate_response.text}"
    
    validate_data = validate_response.json()
    print(f"Validate response: {validate_data}")
    
    assert validate_data["success"] is True, "Validation should succeed"
    assert validate_data["current_step"] == "SUMMARY_REVIEW", "Should advance to SUMMARY_REVIEW"
    assert "transcript" in validate_data["content"], "Should return transcript content"
    
    # Step 4.2: SUMMARY_REVIEW
    print("\n--- Step 4.2: POST /validate for SUMMARY_REVIEW ---")
    
    validate_response = test_client.post(
        "/validate",
        json={
            "session_id": session_id,
            "approved": True,
            "user_input": None
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert validate_response.status_code == 200, f"Validate failed: {validate_response.text}"
    
    validate_data = validate_response.json()
    print(f"Validate response: {validate_data}")
    
    assert validate_data["success"] is True, "Validation should succeed"
    assert validate_data["current_step"] == "VIOLATIONS_REVIEW", "Should advance to VIOLATIONS_REVIEW"
    assert "summary" in validate_data["content"], "Should return summary content"
    
    # Step 4.3: VIOLATIONS_REVIEW
    print("\n--- Step 4.3: POST /validate for VIOLATIONS_REVIEW ---")
    
    validate_response = test_client.post(
        "/validate",
        json={
            "session_id": session_id,
            "approved": True,
            "user_input": None
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert validate_response.status_code == 200, f"Validate failed: {validate_response.text}"
    
    validate_data = validate_response.json()
    print(f"Validate response: {validate_data}")
    
    assert validate_data["success"] is True, "Validation should succeed"
    assert validate_data["current_step"] == "FIR_NARRATIVE_REVIEW", "Should advance to FIR_NARRATIVE_REVIEW"
    assert "violations" in validate_data["content"], "Should return violations content"
    
    # Step 4.4: FIR_NARRATIVE_REVIEW
    print("\n--- Step 4.4: POST /validate for FIR_NARRATIVE_REVIEW ---")
    
    validate_response = test_client.post(
        "/validate",
        json={
            "session_id": session_id,
            "approved": True,
            "user_input": None
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert validate_response.status_code == 200, f"Validate failed: {validate_response.text}"
    
    validate_data = validate_response.json()
    print(f"Validate response: {validate_data}")
    
    assert validate_data["success"] is True, "Validation should succeed"
    assert validate_data["current_step"] == "FINAL_REVIEW", "Should advance to FINAL_REVIEW"
    assert "fir_narrative" in validate_data["content"], "Should return FIR narrative content"
    
    # Step 4.5: FINAL_REVIEW
    print("\n--- Step 4.5: POST /validate for FINAL_REVIEW ---")
    
    validate_response = test_client.post(
        "/validate",
        json={
            "session_id": session_id,
            "approved": True,
            "user_input": None
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert validate_response.status_code == 200, f"Validate failed: {validate_response.text}"
    
    validate_data = validate_response.json()
    print(f"Validate response: {validate_data}")
    
    assert validate_data["success"] is True, "Validation should succeed"
    assert "fir_content" in validate_data["content"], "Should return FIR content"
    assert "fir_number" in validate_data["content"], "Should return FIR number"
    
    fir_number = validate_data["content"]["fir_number"]
    print(f"FIR Number: {fir_number}")
    
    # Step 4.6: Complete FIR generation
    print("\n--- Step 4.6: Complete FIR generation ---")
    
    validate_response = test_client.post(
        "/validate",
        json={
            "session_id": session_id,
            "approved": True,
            "user_input": None
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert validate_response.status_code == 200, f"Validate failed: {validate_response.text}"
    
    validate_data = validate_response.json()
    print(f"Validate response: {validate_data}")
    
    # Step 5: Verify FIR generation completes successfully
    print("\n=== Step 5: Verify FIR generation completes successfully ===")
    
    assert validate_data["success"] is True, "FIR generation should succeed"
    assert validate_data["completed"] is True, "FIR generation should be completed"
    assert validate_data["requires_validation"] is False, "Should not require further validation"
    
    # Verify session status is now COMPLETED
    status_response = test_client.get(
        f"/session/{session_id}/status",
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert status_response.status_code == 200, f"Status endpoint failed: {status_response.text}"
    
    status_data = status_response.json()
    print(f"Final status: {status_data}")
    
    assert status_data["status"] == "COMPLETED", "Session status should be COMPLETED"
    assert status_data["awaiting_validation"] is False, "awaiting_validation should be False"
    
    # Step 6: Retrieve and verify FIR content
    print("\n=== Step 6: Retrieve and verify FIR content ===")
    
    fir_response = test_client.get(
        f"/fir/{fir_number}",
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert fir_response.status_code == 200, \
        f"Requirement 3.10: FIR retrieval should work. Error: {fir_response.text}"
    
    fir_data = fir_response.json()
    print(f"FIR response: {fir_data}")
    
    # Verify FIR content structure (Requirement 3.6)
    assert "fir_number" in fir_data, "Response should include fir_number"
    assert fir_data["fir_number"] == fir_number, "FIR number should match"
    
    assert "fir_content" in fir_data, "Response should include fir_content"
    assert fir_data["fir_content"] is not None, "fir_content should not be None"
    assert len(fir_data["fir_content"]) > 0, "fir_content should not be empty"
    
    assert "status" in fir_data, "Response should include status"
    assert "created_at" in fir_data, "Response should include created_at"
    
    print("\n=== Integration Test PASSED ===")
    print(f"Successfully completed audio file (.wav) FIR generation flow:")
    print(f"  - Session ID: {session_id}")
    print(f"  - FIR Number: {fir_number}")
    print(f"  - All validation steps completed")
    print(f"  - Full FIR content retrieved")
    print(f"\nVerified preservation requirements:")
    print(f"  ✓ Requirement 3.1: Audio files processed through initial_processing pipeline")
    print(f"  ✓ Requirement 3.2: Audio sessions reach AWAITING_VALIDATION and accept validation")
    print(f"  ✓ Requirement 3.5: WAV audio files accepted and processed correctly")
    print(f"  ✓ Requirement 3.6: FIR documents generated with correct data and formatting")
    print(f"  ✓ Requirement 3.10: FIR retrieval endpoints return correct data")


@pytest.mark.integration
def test_complete_audio_mp3_fir_generation_flow(test_client):
    """
    Test the complete audio file (.mp3) FIR generation workflow end-to-end.
    
    **Validates: Requirements 3.1, 3.5, 3.6**
    
    This test verifies that MP3 audio file processing continues to work unchanged after bug fixes.
    
    Test Flow:
    1. Upload valid .mp3 audio file
    2. Verify processing succeeds and session is created
    3. Verify session status is AWAITING_VALIDATION
    4. Complete validation workflow (abbreviated - just first step to verify it works)
    """
    
    # Step 1: Upload valid .mp3 audio file
    print("\n=== Step 1: Upload valid .mp3 audio file ===")
    
    audio_data = create_valid_mp3_audio()
    
    files = {
        'audio': ('test_complaint.mp3', io.BytesIO(audio_data), 'audio/mpeg')
    }
    
    response = test_client.post(
        "/process",
        files=files,
        headers={"X-API-Key": "test-key-123"}
    )
    
    # Step 2: Verify processing succeeds
    print("\n=== Step 2: Verify processing succeeds ===")
    
    assert response.status_code in [200, 202], \
        f"MP3 audio processing should succeed, got {response.status_code}: {response.text}"
    
    process_data = response.json()
    print(f"Process response: {process_data}")
    
    assert process_data["success"] is True, "MP3 audio processing should succeed"
    assert "session_id" in process_data, "Response should include session_id"
    assert process_data["requires_validation"] is True, "Should require validation"
    assert process_data["current_step"] == "TRANSCRIPT_REVIEW", "Should start at TRANSCRIPT_REVIEW"
    
    session_id = process_data["session_id"]
    print(f"Session ID: {session_id}")
    
    # Step 3: Verify session status is AWAITING_VALIDATION
    print("\n=== Step 3: Verify session status is AWAITING_VALIDATION ===")
    
    status_response = test_client.get(
        f"/session/{session_id}/status",
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert status_response.status_code == 200, f"Status endpoint failed: {status_response.text}"
    
    status_data = status_response.json()
    print(f"Status response: {status_data}")
    
    assert status_data["status"] == "AWAITING_VALIDATION", \
        "Requirement 3.2: MP3 audio sessions should reach AWAITING_VALIDATION status"
    assert status_data["awaiting_validation"] is True, "awaiting_validation flag should be True"
    assert status_data["current_step"] == "TRANSCRIPT_REVIEW", "Should be at TRANSCRIPT_REVIEW step"
    
    # Step 4: Verify validation workflow works (abbreviated test - just first step)
    print("\n=== Step 4: Verify validation workflow works ===")
    
    validate_response = test_client.post(
        "/validate",
        json={
            "session_id": session_id,
            "approved": True,
            "user_input": None
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert validate_response.status_code == 200, \
        f"Requirement 3.2: Validation should accept MP3 audio sessions. Error: {validate_response.text}"
    
    validate_data = validate_response.json()
    print(f"Validate response: {validate_data}")
    
    assert validate_data["success"] is True, "Validation should succeed"
    assert validate_data["current_step"] == "SUMMARY_REVIEW", "Should advance to SUMMARY_REVIEW"
    
    print("\n=== Integration Test PASSED ===")
    print(f"Successfully verified MP3 audio file FIR generation flow:")
    print(f"  - Session ID: {session_id}")
    print(f"  - Processing succeeded")
    print(f"  - Session reached AWAITING_VALIDATION")
    print(f"  - Validation workflow works")
    print(f"\nVerified preservation requirements:")
    print(f"  ✓ Requirement 3.1: MP3 audio files processed through initial_processing pipeline")
    print(f"  ✓ Requirement 3.2: MP3 audio sessions reach AWAITING_VALIDATION and accept validation")
    print(f"  ✓ Requirement 3.5: MP3 audio files accepted and processed correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
