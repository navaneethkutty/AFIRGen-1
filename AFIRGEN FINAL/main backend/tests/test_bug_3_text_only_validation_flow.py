"""
Bug Condition Exploration Test for High Priority Bug 3 - Text-only Validation Flow

**Validates: Requirements 1.3, 2.3**

**Property 1: Fault Condition** - Text-only Session Status Not Set

This test verifies that POST /process with text-only input sets session status to AWAITING_VALIDATION.

**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
**DO NOT attempt to fix the test or the code when it fails**
**GOAL**: Surface counterexamples that demonstrate the bug exists

**EXPECTED OUTCOME**: Test FAILS because status is not set to AWAITING_VALIDATION (this is correct - it proves the bug exists)

When the bug is fixed, this test will pass, confirming the expected behavior is satisfied.
"""

import pytest
import ast
from pathlib import Path


def test_text_only_session_status_not_set():
    """
    Test that verifies the /process endpoint sets session status for text-only input.
    
    **Validates: Requirements 1.3, 2.3**
    
    Bug Condition: input.type == "API_REQUEST" AND input.endpoint == "/process" 
                   AND input.hasTextOnly AND NOT session.status == AWAITING_VALIDATION
    
    Expected Behavior (after fix): Session status is set to AWAITING_VALIDATION
    
    On UNFIXED code: This test will FAIL because set_session_status() is not called
    On FIXED code: This test will PASS because set_session_status() is called
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    assert agentv5_path.exists(), f"agentv5.py not found at {agentv5_path}"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the text-only processing section (around line 1755)
    # Look for: elif text:
    #              state.transcript = text
    #              ...
    #              state.awaiting_validation = True
    
    text_only_section_start = None
    awaiting_validation_line = None
    set_status_call_found = False
    
    for i, line in enumerate(lines):
        # Look for the text-only processing section
        if 'elif text:' in line and i > 1700 and i < 1800:
            text_only_section_start = i
            
            # Check the next 20 lines for awaiting_validation and set_session_status
            for j in range(i, min(i + 20, len(lines))):
                if 'state.awaiting_validation = True' in lines[j]:
                    awaiting_validation_line = j
                
                # Check if set_session_status is called in this section
                if 'session_manager.set_session_status' in lines[j] and \
                   'SessionStatus.AWAITING_VALIDATION' in lines[j]:
                    set_status_call_found = True
                    break
            
            break
    
    assert text_only_section_start is not None, \
        "Could not find text-only processing section (elif text:) around line 1755"
    
    assert awaiting_validation_line is not None, \
        f"Could not find 'state.awaiting_validation = True' in text-only section starting at line {text_only_section_start + 1}"
    
    # Check if set_session_status is called
    if not set_status_call_found:
        # Find the audio processing section for comparison (around line 1248)
        audio_set_status_line = None
        for i, line in enumerate(lines):
            if 'session_manager.set_session_status' in line and \
               'SessionStatus.AWAITING_VALIDATION' in line and \
               i > 1200 and i < 1300:
                audio_set_status_line = i
                break
        
        comparison_text = ""
        if audio_set_status_line:
            comparison_text = (
                f"\n"
                f"Comparison with Audio Processing (CORRECT):\n"
                f"  Line {audio_set_status_line + 1}: {lines[audio_set_status_line].strip()}\n"
                f"  This correctly sets the session status to AWAITING_VALIDATION\n"
            )
        
        pytest.fail(
            f"Text-only session status not set correctly:\n"
            f"\n"
            f"Bug Condition Triggered:\n"
            f"  - Endpoint: POST /process\n"
            f"  - Input Type: text-only (elif text: branch)\n"
            f"  - Section starts at line: {text_only_section_start + 1}\n"
            f"\n"
            f"Counterexample:\n"
            f"  Line {awaiting_validation_line + 1}: {lines[awaiting_validation_line].strip()}\n"
            f"  The code sets state.awaiting_validation = True\n"
            f"  BUT does NOT call session_manager.set_session_status(session_id, SessionStatus.AWAITING_VALIDATION)\n"
            f"{comparison_text}\n"
            f"Root Cause:\n"
            f"  The /process endpoint sets the awaiting_validation flag but does not update\n"
            f"  the session status in the database. This causes the /validate endpoint to\n"
            f"  reject the session because it checks session['status'] != AWAITING_VALIDATION\n"
            f"\n"
            f"Expected Fix:\n"
            f"  Add after line {awaiting_validation_line + 1}:\n"
            f"    session_manager.set_session_status(state.session_id, SessionStatus.AWAITING_VALIDATION)\n"
            f"\n"
            f"Impact:\n"
            f"  - Text-only sessions cannot proceed to validation (Bug 4)\n"
            f"  - /validate endpoint returns 400 'Session not awaiting validation'\n"
            f"  - Text-only FIR generation workflow is completely broken\n"
            f"\n"
            f"This confirms High Priority Bug 3 exists.\n"
        )
    
    # If we reach here, the bug is fixed
    assert set_status_call_found, \
        "Expected set_session_status() call in text-only section after fix"


def test_validate_endpoint_status_check():
    """
    Test that verifies the /validate endpoint checks session status.
    
    **Validates: Requirements 1.3, 1.4, 2.3, 2.4**
    
    This test confirms that the /validate endpoint will reject sessions
    where status != AWAITING_VALIDATION, which is the consequence of Bug 3.
    
    On UNFIXED code: This test documents the status check that causes Bug 4
    On FIXED code: This test confirms the check still exists (it's correct)
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the /validate endpoint (around line 1798)
    validate_status_check_found = False
    validate_check_line = None
    
    for i, line in enumerate(lines):
        if 'session["status"] != SessionStatus.AWAITING_VALIDATION' in line or \
           "session['status'] != SessionStatus.AWAITING_VALIDATION" in line:
            if i > 1790 and i < 1810:
                validate_status_check_found = True
                validate_check_line = i
                break
    
    assert validate_status_check_found, \
        "Could not find status check in /validate endpoint around line 1798"
    
    # Document the check
    print(f"\n/validate endpoint status check found at line {validate_check_line + 1}:")
    print(f"  {lines[validate_check_line].strip()}")
    print(f"\nThis check is CORRECT and should remain.")
    print(f"Bug 3 causes this check to fail for text-only sessions because")
    print(f"the session status is never set to AWAITING_VALIDATION.")


def test_audio_processing_comparison():
    """
    Test that compares text-only and audio processing to document the inconsistency.
    
    **Validates: Requirements 1.3, 2.3, 3.1, 3.2**
    
    This test shows that audio processing correctly calls set_session_status()
    while text-only processing does not, documenting the root cause.
    
    On UNFIXED code: This test will FAIL showing the inconsistency
    On FIXED code: This test will PASS showing both behave the same
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find audio processing set_session_status call (around line 1248)
    audio_set_status_line = None
    for i, line in enumerate(lines):
        if 'session_manager.set_session_status' in line and \
           'SessionStatus.AWAITING_VALIDATION' in line and \
           i > 1200 and i < 1300:
            audio_set_status_line = i
            break
    
    # Find text-only processing section (around line 1755)
    text_only_section_start = None
    text_awaiting_validation_line = None
    text_set_status_found = False
    
    for i, line in enumerate(lines):
        if 'elif text:' in line and i > 1700 and i < 1800:
            text_only_section_start = i
            
            for j in range(i, min(i + 20, len(lines))):
                if 'state.awaiting_validation = True' in lines[j]:
                    text_awaiting_validation_line = j
                
                if 'session_manager.set_session_status' in lines[j] and \
                   'SessionStatus.AWAITING_VALIDATION' in lines[j]:
                    text_set_status_found = True
                    break
            
            break
    
    assert audio_set_status_line is not None, \
        "Could not find set_session_status call in audio processing section"
    
    assert text_only_section_start is not None, \
        "Could not find text-only processing section"
    
    assert text_awaiting_validation_line is not None, \
        "Could not find awaiting_validation flag in text-only section"
    
    # Compare the two sections
    if not text_set_status_found:
        pytest.fail(
            f"Inconsistency between audio and text-only session handling:\n"
            f"\n"
            f"Audio Processing (CORRECT):\n"
            f"  Line {audio_set_status_line + 1}: {lines[audio_set_status_line].strip()}\n"
            f"  ✓ Calls session_manager.set_session_status()\n"
            f"  ✓ Sets status to AWAITING_VALIDATION\n"
            f"\n"
            f"Text-only Processing (INCORRECT):\n"
            f"  Line {text_awaiting_validation_line + 1}: {lines[text_awaiting_validation_line].strip()}\n"
            f"  ✓ Sets state.awaiting_validation = True flag\n"
            f"  ✗ Does NOT call session_manager.set_session_status()\n"
            f"  ✗ Session status remains at initial value (PROCESSING)\n"
            f"\n"
            f"Root Cause:\n"
            f"  The text-only processing path is missing the set_session_status() call\n"
            f"  that exists in the audio processing path.\n"
            f"\n"
            f"This confirms High Priority Bug 3: Inconsistent session status handling.\n"
        )
    
    # If we reach here, both sections have the call (bug is fixed)
    assert text_set_status_found, \
        "Expected set_session_status() call in text-only section after fix"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
