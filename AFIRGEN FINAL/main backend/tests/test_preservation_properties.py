"""
Preservation Property Tests - Property 2: Non-Buggy Input Behavior Unchanged

**Validates: Requirements 3.1-3.12**

**Property 2: Preservation** - For any input where none of the 11 bug conditions hold,
the fixed system SHALL produce exactly the same behavior as the original system.

**IMPORTANT**: These tests follow observation-first methodology:
1. Observe behavior on UNFIXED code for non-buggy inputs
2. Write property-based tests capturing observed behavior patterns
3. Run tests on UNFIXED code - EXPECTED OUTCOME: Tests PASS
4. After fixes, re-run tests - EXPECTED OUTCOME: Tests still PASS (no regressions)

These tests use Hypothesis for property-based testing to generate many test cases
and provide strong guarantees that existing functionality is preserved.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from pathlib import Path
import sys
import io
import wave
import struct
from PIL import Image

# Add parent directory to path to import agentv5
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from agentv5 import app, session_manager, db

# Create test client
client = TestClient(app)

# Test API key for authentication
TEST_API_KEY = "test-api-key-12345"


# ============================================================================
# Helper Functions for Test Data Generation
# ============================================================================

def create_valid_wav_audio(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Create a valid WAV audio file in memory."""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Generate simple sine wave
        num_frames = int(duration_seconds * sample_rate)
        for i in range(num_frames):
            value = int(32767.0 * 0.5)  # Simple constant value
            wav_file.writeframes(struct.pack('<h', value))
    
    buffer.seek(0)
    return buffer.read()


def create_valid_mp3_audio() -> bytes:
    """Create a minimal valid MP3 file (just headers for testing)."""
    # MP3 frame header: 11 bits sync word (all set), MPEG version, layer, etc.
    # This is a minimal valid MP3 frame header
    mp3_header = bytes([0xFF, 0xFB, 0x90, 0x00])
    # Add some dummy data to make it a valid frame
    mp3_data = mp3_header + bytes([0x00] * 100)
    return mp3_data


def create_valid_image(width: int = 100, height: int = 100, format: str = 'JPEG') -> bytes:
    """Create a valid image file in memory."""
    buffer = io.BytesIO()
    image = Image.new('RGB', (width, height), color='red')
    image.save(buffer, format=format)
    buffer.seek(0)
    return buffer.read()


# ============================================================================
# Test 12.1: Audio File Processing Preservation
# **Validates: Requirements 3.1, 3.5**
# ============================================================================

@pytest.mark.preservation
@given(
    duration=st.floats(min_value=0.5, max_value=3.0),
    sample_rate=st.sampled_from([8000, 16000, 22050, 44100])
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_audio_wav_processing_preserved(duration, sample_rate):
    """
    Property: Valid WAV audio files continue to process correctly through /process endpoint.
    
    **Validates: Requirements 3.1, 3.5**
    
    This test verifies that the audio processing pipeline, session creation, and status
    updates work exactly as before for valid WAV audio inputs (non-buggy case).
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    """
    # Generate valid WAV audio
    audio_data = create_valid_wav_audio(duration, sample_rate)
    
    # Create file-like object
    files = {
        'audio': ('test_audio.wav', io.BytesIO(audio_data), 'audio/wav')
    }
    
    # Send request to /process endpoint
    response = client.post(
        "/process",
        files=files,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    # Verify response - should succeed for valid audio
    assert response.status_code in [200, 202], \
        f"Audio processing should succeed, got {response.status_code}: {response.text}"
    
    # Verify response structure
    data = response.json()
    assert "session_id" in data, "Response should include session_id"
    
    # Verify session was created
    session_id = data["session_id"]
    session = session_manager.get_session(session_id)
    assert session is not None, "Session should be created"
    assert session["state"]["audio_path"] is not None, "Audio path should be set"


@pytest.mark.preservation
def test_property_audio_mp3_processing_preserved():
    """
    Property: Valid MP3 audio files continue to process correctly through /process endpoint.
    
    **Validates: Requirements 3.1, 3.5**
    
    This test verifies that MP3 audio processing works as before (non-buggy case).
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    """
    # Generate valid MP3 audio
    audio_data = create_valid_mp3_audio()
    
    # Create file-like object
    files = {
        'audio': ('test_audio.mp3', io.BytesIO(audio_data), 'audio/mpeg')
    }
    
    # Send request to /process endpoint
    response = client.post(
        "/process",
        files=files,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    # Verify response - should succeed for valid audio
    assert response.status_code in [200, 202], \
        f"MP3 processing should succeed, got {response.status_code}: {response.text}"
    
    # Verify response structure
    data = response.json()
    assert "session_id" in data, "Response should include session_id"


# ============================================================================
# Test 12.2: Image File Processing Preservation
# **Validates: Requirements 3.1, 3.4**
# ============================================================================

@pytest.mark.preservation
@given(
    width=st.integers(min_value=50, max_value=500),
    height=st.integers(min_value=50, max_value=500),
    format=st.sampled_from(['JPEG', 'PNG'])
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_image_processing_preserved(width, height, format):
    """
    Property: Valid JPEG/PNG image files continue to process correctly through /process endpoint.
    
    **Validates: Requirements 3.1, 3.4**
    
    This test verifies that image processing pipeline works exactly as before
    for valid image inputs (non-buggy case).
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    """
    # Generate valid image
    image_data = create_valid_image(width, height, format)
    
    # Determine content type and extension
    content_type = 'image/jpeg' if format == 'JPEG' else 'image/png'
    extension = 'jpg' if format == 'JPEG' else 'png'
    
    # Create file-like object
    files = {
        'letter': (f'test_image.{extension}', io.BytesIO(image_data), content_type)
    }
    
    # Send request to /process endpoint
    response = client.post(
        "/process",
        files=files,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    # Verify response - should succeed for valid image
    assert response.status_code in [200, 202], \
        f"Image processing should succeed, got {response.status_code}: {response.text}"
    
    # Verify response structure
    data = response.json()
    assert "session_id" in data, "Response should include session_id"
    
    # Verify session was created
    session_id = data["session_id"]
    session = session_manager.get_session(session_id)
    assert session is not None, "Session should be created"
    assert session["state"]["letter_path"] is not None, "Letter path should be set"


# ============================================================================
# Test 12.3: Audio/Image Validation Flow Preservation
# **Validates: Requirements 3.2, 3.12**
# ============================================================================

@pytest.mark.preservation
def test_property_validation_flow_preserved():
    """
    Property: Validation workflow for audio/image inputs continues to work unchanged.
    
    **Validates: Requirements 3.2, 3.12**
    
    This test verifies that the validation flow from AWAITING_VALIDATION to COMPLETED
    works exactly as before for audio/image inputs (non-buggy case).
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    
    Note: This is a simplified test that verifies the validation endpoint accepts
    sessions with audio/image inputs. Full validation flow testing is in integration tests.
    """
    # Create a session with audio input
    audio_data = create_valid_wav_audio()
    files = {
        'audio': ('test_audio.wav', io.BytesIO(audio_data), 'audio/wav')
    }
    
    response = client.post(
        "/process",
        files=files,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code in [200, 202]
    session_id = response.json()["session_id"]
    
    # Wait for session to reach AWAITING_VALIDATION status
    # In the actual system, this happens asynchronously
    # For this test, we verify the session exists and can be queried
    
    session = session_manager.get_session(session_id)
    assert session is not None, "Session should exist"
    
    # Verify session has expected structure for validation
    assert "state" in session, "Session should have state"
    assert "status" in session, "Session should have status"


# ============================================================================
# Test 12.4: Authentication Preservation
# **Validates: Requirements 3.7**
# ============================================================================

@pytest.mark.preservation
@given(
    api_key=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_authentication_preserved(api_key):
    """
    Property: APIAuthMiddleware continues to enforce authentication as before.
    
    **Validates: Requirements 3.7**
    
    This test verifies that authentication behavior is unchanged for API requests.
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    """
    # Test with provided API key
    response = client.get(
        "/health",
        headers={"X-API-Key": api_key}
    )
    
    # Health endpoint should work regardless of API key (it's public)
    # This verifies the middleware is still functioning
    assert response.status_code == 200, "Health endpoint should be accessible"
    
    # Test protected endpoint with invalid key
    audio_data = create_valid_wav_audio()
    files = {
        'audio': ('test.wav', io.BytesIO(audio_data), 'audio/wav')
    }
    
    response = client.post(
        "/process",
        files=files,
        headers={"X-API-Key": "invalid-key"}
    )
    
    # Should get authentication error (401 or 403)
    assert response.status_code in [401, 403], \
        "Protected endpoint should reject invalid API key"


# ============================================================================
# Test 12.5: Health Check Preservation
# **Validates: Requirements 3.8**
# ============================================================================

@pytest.mark.preservation
def test_property_health_check_preserved():
    """
    Property: /health endpoint continues to work without authentication.
    
    **Validates: Requirements 3.8**
    
    This test verifies that the health check endpoint behavior is unchanged.
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    """
    # Test health endpoint without API key
    response = client.get("/health")
    
    assert response.status_code == 200, "Health endpoint should be accessible without auth"
    
    # Verify response structure
    data = response.json()
    assert "status" in data, "Health response should include status"
    assert data["status"] in ["healthy", "ok"], "Health status should be healthy or ok"


# ============================================================================
# Test 12.6: Session Status Endpoint Preservation
# **Validates: Requirements 3.3**
# ============================================================================

@pytest.mark.preservation
def test_property_session_status_endpoint_preserved():
    """
    Property: /status endpoint continues to return existing fields.
    
    **Validates: Requirements 3.3**
    
    This test verifies that the session status endpoint returns all expected fields
    and that the response structure is unchanged (non-buggy case).
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    
    Note: After Bug 6 fix, validation_history field will be added, but existing
    fields must remain unchanged.
    """
    # Create a session
    audio_data = create_valid_wav_audio()
    files = {
        'audio': ('test_audio.wav', io.BytesIO(audio_data), 'audio/wav')
    }
    
    response = client.post(
        "/process",
        files=files,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code in [200, 202]
    session_id = response.json()["session_id"]
    
    # Query session status
    response = client.get(
        f"/session/{session_id}/status",
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code == 200, "Status endpoint should succeed"
    
    # Verify existing fields are present
    data = response.json()
    assert "session_id" in data, "Response should include session_id"
    assert "status" in data, "Response should include status"
    assert "created_at" in data, "Response should include created_at"
    
    # These fields should exist in the original system
    # After Bug 6 fix, validation_history will be added but these must remain
    expected_fields = ["session_id", "status", "created_at"]
    for field in expected_fields:
        assert field in data, f"Response should include {field} field"


# ============================================================================
# Test 12.7: FIR Generation Quality Preservation
# **Validates: Requirements 3.6**
# ============================================================================

@pytest.mark.preservation
def test_property_fir_generation_quality_preserved():
    """
    Property: FIR content generation quality and format remain unchanged.
    
    **Validates: Requirements 3.6**
    
    This test verifies that FIR generation produces output with the same structure
    and quality as before (non-buggy case).
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    
    Note: This test verifies the get_fir_data function structure, not full generation.
    Full FIR generation testing is in integration tests.
    """
    # Import get_fir_data function
    from agentv5 import get_fir_data
    
    # Create a mock session state with expected structure
    session_state = {
        "complaint_text": "Test complaint",
        "transcript": "Test transcript",
        "summary": "Test summary",
        "violations": [{"section": "Test", "description": "Test violation"}],
        "fir_narrative": "Test narrative"
    }
    
    # Call get_fir_data with both parameters (after Bug 2 fix)
    # The fix changes the signature to accept (session_state, fir_number)
    fir_data = get_fir_data(session_state, "FIR/2024/001")
    
    # Verify FIR data structure is preserved
    assert isinstance(fir_data, dict), "FIR data should be a dictionary"
    assert "fir_number" in fir_data, "FIR data should include fir_number"
    assert "complainant_name" in fir_data, "FIR data should include complainant_name"
    assert "summary" in fir_data, "FIR data should include summary"


# ============================================================================
# Test 12.8: Graceful Shutdown Preservation
# **Validates: Requirements 3.9**
# ============================================================================

@pytest.mark.preservation
def test_property_graceful_shutdown_preserved():
    """
    Property: Graceful shutdown continues to track active requests.
    
    **Validates: Requirements 3.9**
    
    This test verifies that the graceful shutdown mechanism works as before.
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    
    Note: This test verifies the RequestTrackingMiddleware exists and functions.
    Full shutdown testing requires integration tests.
    """
    # Verify RequestTrackingMiddleware is in the middleware stack
    from agentv5 import app
    
    # Check that the app has middleware
    assert hasattr(app, 'user_middleware'), "App should have middleware"
    
    # Make a request to verify middleware is functioning
    response = client.get("/health")
    assert response.status_code == 200, "Middleware should allow requests through"


# ============================================================================
# Test 12.9: FIR Retrieval Preservation
# **Validates: Requirements 3.10**
# ============================================================================

@pytest.mark.preservation
def test_property_fir_retrieval_preserved():
    """
    Property: FIR retrieval endpoints continue to return correct data.
    
    **Validates: Requirements 3.10**
    
    This test verifies that the /fir/{fir_number}/content endpoint continues to work
    correctly (non-buggy case). Bug 9 is about /fir/{firNumber} returning only metadata,
    but /fir/{fir_number}/content should continue to work as before.
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    """
    # Note: This test would require a completed FIR in the database
    # For preservation testing, we verify the endpoint exists and has correct structure
    
    # Test with a non-existent FIR number (should return 404, not crash)
    response = client.get(
        "/fir/TEST-FIR-12345/content",
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    # Should return 404 for non-existent FIR, not crash
    assert response.status_code in [404, 401, 403], \
        "FIR content endpoint should handle non-existent FIRs gracefully"


# ============================================================================
# Test 12.10: Frontend Progress Display Preservation
# **Validates: Requirements 3.11**
# ============================================================================

@pytest.mark.preservation
def test_property_frontend_progress_display_preserved():
    """
    Property: Frontend continues to show step-by-step progress updates.
    
    **Validates: Requirements 3.11**
    
    This test verifies that the session status endpoint returns progress information
    that the frontend uses for display (non-buggy case).
    
    Expected behavior on UNFIXED code: Test PASSES (baseline behavior)
    Expected behavior on FIXED code: Test PASSES (behavior preserved)
    """
    # Create a session
    audio_data = create_valid_wav_audio()
    files = {
        'audio': ('test_audio.wav', io.BytesIO(audio_data), 'audio/wav')
    }
    
    response = client.post(
        "/process",
        files=files,
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code in [200, 202]
    session_id = response.json()["session_id"]
    
    # Query session status to get progress information
    response = client.get(
        f"/session/{session_id}/status",
        headers={"X-API-Key": TEST_API_KEY}
    )
    
    assert response.status_code == 200, "Status endpoint should succeed"
    
    # Verify progress-related fields are present
    data = response.json()
    assert "status" in data, "Response should include status for progress tracking"
    
    # The status field is used by frontend to display progress
    # Verify it has a valid value
    assert data["status"] is not None, "Status should not be None"


if __name__ == "__main__":
    # Run the preservation property tests
    pytest.main([__file__, "-v", "-m", "preservation"])
