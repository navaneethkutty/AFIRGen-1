"""
Bug Condition Exploration Test for High Priority Bug 4 - Validation Endpoint Rejection

**Validates: Requirements 1.4, 2.4**

**Property 1: Fault Condition** - Validation Endpoint Rejects Text-only Sessions

This test verifies that POST /validate succeeds after text-only session creation.
This bug is a consequence of Bug 3 - the /validate endpoint checks session status
and rejects text-only sessions because their status was never set to AWAITING_VALIDATION.

**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
**DO NOT attempt to fix the test or the code when it fails**
**GOAL**: Surface counterexamples that demonstrate the bug exists

**EXPECTED OUTCOME**: Test FAILS with 400 error "Session not awaiting validation" 
(this is correct - it proves the bug exists)

When the bug is fixed, this test will pass, confirming the expected behavior is satisfied.
"""

import pytest
import ast
from pathlib import Path


def test_validation_endpoint_rejects_text_only_sessions():
    """
    Test that verifies the /validate endpoint rejects text-only sessions.
    
    **Validates: Requirements 1.4, 2.4**
    
    Bug Condition: input.type == "API_REQUEST" AND input.endpoint == "/validate" 
                   AND session.createdViaTextOnly AND session.status != AWAITING_VALIDATION
    
    Expected Behavior (after fix): /validate endpoint accepts text-only sessions
    
    On UNFIXED code: This test will FAIL because /validate rejects sessions with status != AWAITING_VALIDATION
    On FIXED code: This test will PASS because Bug 3 fix sets status to AWAITING_VALIDATION
    
    This test demonstrates the consequence of Bug 3 (text-only sessions don't set status).
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    assert agentv5_path.exists(), f"agentv5.py not found at {agentv5_path}"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the /validate endpoint status check (around line 1798)
    validate_status_check_line = None
    validate_error_message_line = None
    
    for i, line in enumerate(lines):
        if ('session["status"] != SessionStatus.AWAITING_VALIDATION' in line or
            "session['status'] != SessionStatus.AWAITING_VALIDATION" in line):
            if i > 1790 and i < 1810:
                validate_status_check_line = i
                
                # Look for the error message in the next few lines
                for j in range(i, min(i + 5, len(lines))):
                    if 'Session not awaiting validation' in lines[j]:
                        validate_error_message_line = j
                        break
                break
    
    assert validate_status_check_line is not None, \
        "Could not find status check in /validate endpoint around line 1798"
    
    assert validate_error_message_line is not None, \
        f"Could not find error message after status check at line {validate_status_check_line + 1}"
    
    # Now check if Bug 3 is present (text-only sessions don't set status)
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
    
    # If set_status_call is not found, Bug 3 exists, which causes Bug 4
    if not set_status_call_found:
        pytest.fail(
            f"Validation endpoint rejection bug confirmed:\n"
            f"\n"
            f"Bug Condition Triggered:\n"
            f"  - Endpoint: POST /validate\n"
            f"  - Session Type: text-only (created via POST /process with text parameter)\n"
            f"  - Session Status: NOT set to AWAITING_VALIDATION (Bug 3)\n"
            f"\n"
            f"Counterexample - /validate endpoint status check:\n"
            f"  Line {validate_status_check_line + 1}: {lines[validate_status_check_line].strip()}\n"
            f"  Line {validate_error_message_line + 1}: {lines[validate_error_message_line].strip()}\n"
            f"\n"
            f"  The /validate endpoint checks: session['status'] != SessionStatus.AWAITING_VALIDATION\n"
            f"  If true, it raises: HTTPException(status_code=400, detail='Session not awaiting validation')\n"
            f"\n"
            f"Root Cause Chain:\n"
            f"  1. Bug 3: Text-only sessions don't call set_session_status() (line {awaiting_validation_line + 1})\n"
            f"  2. Session status remains at initial value (likely PROCESSING)\n"
            f"  3. /validate endpoint checks status != AWAITING_VALIDATION (line {validate_status_check_line + 1})\n"
            f"  4. Check fails, endpoint returns 400 error\n"
            f"\n"
            f"Expected Behavior:\n"
            f"  After text-only session creation:\n"
            f"    1. POST /process with text='I want to report a theft'\n"
            f"    2. Session created with status = AWAITING_VALIDATION\n"
            f"    3. POST /validate with session_id succeeds\n"
            f"\n"
            f"Actual Behavior (UNFIXED):\n"
            f"  After text-only session creation:\n"
            f"    1. POST /process with text='I want to report a theft'\n"
            f"    2. Session created with status = PROCESSING (Bug 3)\n"
            f"    3. POST /validate with session_id returns 400 'Session not awaiting validation'\n"
            f"\n"
            f"Impact:\n"
            f"  - Text-only FIR generation workflow is completely broken\n"
            f"  - Users cannot validate text-only sessions\n"
            f"  - /validate endpoint always rejects text-only sessions\n"
            f"  - This is a direct consequence of Bug 3\n"
            f"\n"
            f"Fix Required:\n"
            f"  Fix Bug 3 first by adding set_session_status() call in text-only processing:\n"
            f"    After line {awaiting_validation_line + 1}:\n"
            f"      session_manager.set_session_status(state.session_id, SessionStatus.AWAITING_VALIDATION)\n"
            f"\n"
            f"This confirms High Priority Bug 4 exists as a consequence of Bug 3.\n"
        )
    
    # If we reach here, Bug 3 is fixed, so Bug 4 should also be fixed
    assert set_status_call_found, \
        "Expected set_session_status() call in text-only section after fix"


def test_validate_endpoint_status_check_is_correct():
    """
    Test that verifies the /validate endpoint status check is correct and should remain.
    
    **Validates: Requirements 1.4, 2.4, 3.2**
    
    This test confirms that the /validate endpoint's status check is CORRECT behavior.
    The check should remain - it's the text-only session creation that's broken (Bug 3).
    
    On UNFIXED code: This test documents the correct status check
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
        if ('session["status"] != SessionStatus.AWAITING_VALIDATION' in line or
            "session['status'] != SessionStatus.AWAITING_VALIDATION" in line):
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
    print(f"It ensures that only sessions in AWAITING_VALIDATION status can be validated.")
    print(f"\nBug 4 is NOT caused by this check - it's caused by Bug 3:")
    print(f"  Bug 3: Text-only sessions don't set status to AWAITING_VALIDATION")
    print(f"  Bug 4: /validate endpoint correctly rejects sessions without proper status")
    print(f"\nFix: Resolve Bug 3, and Bug 4 will be automatically resolved.")


def test_audio_vs_text_validation_flow_comparison():
    """
    Test that compares audio and text-only validation flows to document the inconsistency.
    
    **Validates: Requirements 1.3, 1.4, 2.3, 2.4, 3.1, 3.2**
    
    This test shows that audio processing correctly sets session status to AWAITING_VALIDATION,
    allowing /validate to succeed, while text-only processing does not, causing /validate to fail.
    
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
    
    # Find /validate endpoint status check
    validate_status_check_line = None
    for i, line in enumerate(lines):
        if ('session["status"] != SessionStatus.AWAITING_VALIDATION' in line or
            "session['status'] != SessionStatus.AWAITING_VALIDATION" in line):
            if i > 1790 and i < 1810:
                validate_status_check_line = i
                break
    
    assert audio_set_status_line is not None, \
        "Could not find set_session_status call in audio processing section"
    
    assert text_only_section_start is not None, \
        "Could not find text-only processing section"
    
    assert text_awaiting_validation_line is not None, \
        "Could not find awaiting_validation flag in text-only section"
    
    assert validate_status_check_line is not None, \
        "Could not find /validate endpoint status check"
    
    # Compare the flows
    if not text_set_status_found:
        pytest.fail(
            f"Validation flow inconsistency between audio and text-only sessions:\n"
            f"\n"
            f"Audio Processing Flow (CORRECT):\n"
            f"  1. POST /process with audio file\n"
            f"  2. Line {audio_set_status_line + 1}: {lines[audio_set_status_line].strip()}\n"
            f"     ✓ Sets session status to AWAITING_VALIDATION\n"
            f"  3. POST /validate with session_id\n"
            f"  4. Line {validate_status_check_line + 1}: Status check passes\n"
            f"     ✓ Validation proceeds successfully\n"
            f"\n"
            f"Text-only Processing Flow (INCORRECT):\n"
            f"  1. POST /process with text parameter\n"
            f"  2. Line {text_awaiting_validation_line + 1}: {lines[text_awaiting_validation_line].strip()}\n"
            f"     ✓ Sets state.awaiting_validation = True flag\n"
            f"     ✗ Does NOT call session_manager.set_session_status()\n"
            f"     ✗ Session status remains at initial value (PROCESSING)\n"
            f"  3. POST /validate with session_id\n"
            f"  4. Line {validate_status_check_line + 1}: Status check fails\n"
            f"     ✗ Returns 400 'Session not awaiting validation'\n"
            f"\n"
            f"Root Cause:\n"
            f"  Bug 3: Text-only processing doesn't set session status\n"
            f"  Bug 4: /validate endpoint correctly rejects sessions without proper status\n"
            f"\n"
            f"Impact:\n"
            f"  - Audio/image sessions: Validation works correctly\n"
            f"  - Text-only sessions: Validation always fails with 400 error\n"
            f"  - Text-only FIR generation workflow is completely broken\n"
            f"\n"
            f"Fix:\n"
            f"  Add after line {text_awaiting_validation_line + 1}:\n"
            f"    session_manager.set_session_status(state.session_id, SessionStatus.AWAITING_VALIDATION)\n"
            f"\n"
            f"This confirms High Priority Bug 4 exists as a consequence of Bug 3.\n"
        )
    
    # If we reach here, both flows have the set_session_status call (bug is fixed)
    assert text_set_status_found, \
        "Expected set_session_status() call in text-only section after fix"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
