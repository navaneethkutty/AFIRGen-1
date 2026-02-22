"""
Bug Condition Exploration Test for Bug 1.8 - Multiple File Upload Rejection

**Validates: Requirement 1.8**

Property 1: Fault Condition - Multiple Input Rejection

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.
GOAL: Surface counterexamples that demonstrate the bug exists.

Bug Description:
When the frontend uploads both audio and image files simultaneously (or any combination
of multiple input types), the backend validation at agentv5.py lines 1717-1720 rejects
the request with a 400 error: "Please provide only one input type (audio, image, or text)".

Expected Behavior (After Fix):
The backend should accept and process multiple files when input_count > 1, OR
the frontend should prevent multiple file selection before submission.

Current Behavior (Unfixed):
The backend rejects requests when input_count > 1, causing unexpected failure after upload.
"""

import pytest
import ast
from pathlib import Path


def test_backend_validation_rejects_multiple_inputs():
    """
    Test that verifies the backend validation logic rejects multiple input types.
    
    **Validates: Requirement 1.8**
    
    Bug Condition: POST /process with input_count > 1 (multiple of: audio, image, text)
    Expected Behavior (after fix): Backend accepts and processes multiple inputs
    
    On UNFIXED code: This test will FAIL because validation rejects input_count > 1
    On FIXED code: This test will PASS because validation allows multiple inputs
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    assert agentv5_path.exists(), f"agentv5.py not found at {agentv5_path}"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the validation logic around lines 1717-1720
    validation_found = False
    validation_line_num = None
    rejection_line_num = None
    
    for i in range(1710, min(1730, len(lines))):
        line = lines[i]
        # Look for the input_count calculation
        if 'input_count' in line and 'sum' in line and 'bool(audio)' in line:
            validation_line_num = i + 1
            
            # Check the next few lines for the rejection condition
            for j in range(i, min(i + 5, len(lines))):
                if 'input_count > 1' in lines[j]:
                    # Check if this raises an HTTPException
                    for k in range(j, min(j + 3, len(lines))):
                        if 'raise HTTPException' in lines[k] and '400' in lines[k]:
                            validation_found = True
                            rejection_line_num = k + 1
                            break
                    break
            break
    
    if validation_found:
        pytest.fail(
            f"BUG CONFIRMED: Backend rejects multiple input types\n"
            f"\n"
            f"Bug Condition Triggered:\n"
            f"  - POST /process with multiple input types (audio + image, audio + text, etc.)\n"
            f"  - Backend validation at agentv5.py lines {validation_line_num}-{rejection_line_num}\n"
            f"\n"
            f"Validation Logic:\n"
            f"  Line {validation_line_num}: {lines[validation_line_num - 1].strip()}\n"
            f"  Line {validation_line_num + 1}: {lines[validation_line_num].strip()}\n"
            f"  Line {rejection_line_num}: {lines[rejection_line_num - 1].strip()}\n"
            f"\n"
            f"Current Behavior (UNFIXED):\n"
            f"  1. Calculate input_count = sum([bool(audio), bool(image), bool(text)])\n"
            f"  2. If input_count > 1, raise HTTPException with 400 status\n"
            f"  3. Error message: 'Please provide only one input type (audio, image, or text)'\n"
            f"\n"
            f"Expected Behavior (FIXED):\n"
            f"  - Backend should accept and process multiple input types\n"
            f"  - Remove or modify the validation to allow input_count > 1\n"
            f"  - Enable richer FIR generation from multiple sources\n"
            f"\n"
            f"Root Cause:\n"
            f"  The backend intentionally restricts to one input type at a time.\n"
            f"  This prevents users from providing richer context (e.g., letter + audio statement).\n"
            f"\n"
            f"Impact:\n"
            f"  - Users cannot provide multiple forms of evidence\n"
            f"  - Limits FIR generation capabilities\n"
            f"  - Poor user experience if frontend allows selection\n"
            f"  - Wasted bandwidth uploading files that will be rejected\n"
            f"\n"
            f"Fix Options:\n"
            f"  Option A: Remove the validation (lines {validation_line_num}-{rejection_line_num}) to allow multiple inputs\n"
            f"  Option B: Keep restriction, ensure frontend prevents multiple selection before submission\n"
            f"\n"
            f"This confirms Bug 1.8 exists.\n"
        )
    
    # If we reach here, the validation is removed (bug is fixed)
    # The test passes, confirming the expected behavior


def test_document_multiple_input_rejection_logic():
    """
    Document the exact validation logic that causes Bug 1.8.
    
    **Validates: Requirement 1.8**
    
    This test reads the backend code to document the exact validation logic
    that rejects multiple file uploads at agentv5.py lines 1717-1720.
    
    This test always passes but provides detailed documentation of the bug.
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    assert agentv5_path.exists(), f"agentv5.py not found at {agentv5_path}"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the validation logic around lines 1717-1720
    validation_lines = []
    
    for i in range(1710, min(1730, len(lines))):
        line = lines[i]
        if 'input_count' in line or 'Please provide only one input type' in line:
            validation_lines.append((i + 1, line.rstrip()))
    
    assert len(validation_lines) > 0, "Could not find multiple input validation logic"
    
    print("\n" + "=" * 70)
    print("Bug 1.8: Backend Multiple Input Validation Logic")
    print("=" * 70)
    print(f"\nFile: {agentv5_path}")
    print("\nValidation Code:")
    for line_num, line_content in validation_lines:
        print(f"  Line {line_num}: {line_content}")
    
    print("\nLogic Explanation:")
    print("  1. Calculate input_count = sum([bool(audio), bool(image), bool(text)])")
    print("  2. If input_count > 1, raise HTTPException with 400 status")
    print("  3. Error message: 'Please provide only one input type (audio, image, or text)'")
    
    print("\nBug Condition:")
    print("  - User uploads both audio and image files")
    print("  - OR user uploads audio/image file with text input")
    print("  - OR user uploads all three input types")
    print("  - Backend calculates input_count = 2 or 3")
    print("  - Backend rejects with 400 error")
    
    print("\nExpected Behavior (After Fix):")
    print("  - Backend should accept multiple input types")
    print("  - Process all provided inputs to generate richer FIR")
    print("  - OR frontend should prevent multiple selection before submission")
    
    print("\nCurrent Behavior (Unfixed):")
    print("  - Backend rejects any request with input_count > 1")
    print("  - Users cannot provide multiple forms of evidence")
    print("  - Limits FIR generation capabilities")
    
    print("\nImpact:")
    print("  - Users cannot provide multiple forms of evidence")
    print("  - Limits FIR generation capabilities")
    print("  - Prevents richer context from multiple sources")
    print("  - Poor UX if frontend allows selection but backend rejects")
    print("  - Wasted bandwidth uploading files that will be rejected")
    
    print("\nFix Options:")
    print("  Option A: Remove validation to allow multiple inputs")
    print("    - Remove lines containing 'input_count > 1' check")
    print("    - Update processing logic to handle multiple inputs")
    print("    - Enable richer FIR generation")
    print("\n  Option B: Keep restriction, improve frontend UX")
    print("    - Keep backend validation as-is")
    print("    - Update frontend to prevent multiple file selection")
    print("    - Disable file inputs when one is already selected")
    print("    - Show clear message about single-input restriction")
    print("=" * 70)


def test_counterexample_audio_and_image():
    """
    Counterexample: Uploading both audio and image files triggers the bug.
    
    **Validates: Requirement 1.8**
    
    This test documents a specific counterexample that demonstrates Bug 1.8.
    
    Scenario:
    - User has a complaint letter (image) and an audio recording
    - User wants to upload both for comprehensive FIR generation
    - Backend rejects the request with 400 error
    
    This test always passes but documents the counterexample.
    """
    print("\n" + "=" * 70)
    print("Counterexample 1: Audio + Image Upload")
    print("=" * 70)
    print("\nScenario:")
    print("  User has:")
    print("    - Complaint letter as image (complaint.jpg)")
    print("    - Audio recording of incident (statement.wav)")
    print("\nUser Action:")
    print("  1. User selects complaint.jpg in letter upload")
    print("  2. User selects statement.wav in audio upload")
    print("  3. User clicks 'Generate FIR' button")
    print("  4. Frontend uploads both files to POST /process")
    print("\nBackend Processing:")
    print("  1. Receives audio file and image file")
    print("  2. Calculates input_count = sum([bool(audio=True), bool(image=True), bool(text=False)])")
    print("  3. input_count = 2")
    print("  4. Checks: if input_count > 1")
    print("  5. Condition is TRUE (2 > 1)")
    print("  6. Raises HTTPException(status_code=400, detail='Please provide only one input type')")
    print("\nResult:")
    print("  - Backend returns 400 error")
    print("  - Frontend shows error message")
    print("  - User's files are rejected")
    print("  - User must choose only one input type")
    print("\nExpected Behavior:")
    print("  - Backend should accept both files")
    print("  - Process image to extract letter text")
    print("  - Process audio to extract statement text")
    print("  - Combine both sources for richer FIR generation")
    print("=" * 70)


def test_counterexample_audio_and_text():
    """
    Counterexample: Uploading audio file with text input triggers the bug.
    
    **Validates: Requirement 1.8**
    
    This test documents another counterexample that demonstrates Bug 1.8.
    
    Scenario:
    - User has an audio recording and wants to add additional text context
    - Backend rejects the request with 400 error
    
    This test always passes but documents the counterexample.
    """
    print("\n" + "=" * 70)
    print("Counterexample 2: Audio + Text Input")
    print("=" * 70)
    print("\nScenario:")
    print("  User has:")
    print("    - Audio recording of incident (statement.wav)")
    print("    - Additional text context to provide")
    print("\nUser Action:")
    print("  1. User selects statement.wav in audio upload")
    print("  2. User types additional context in text field:")
    print("     'The incident occurred at 10 PM near the market.'")
    print("  3. User clicks 'Generate FIR' button")
    print("  4. Frontend sends both audio file and text to POST /process")
    print("\nBackend Processing:")
    print("  1. Receives audio file and text input")
    print("  2. Calculates input_count = sum([bool(audio=True), bool(image=False), bool(text=True)])")
    print("  3. input_count = 2")
    print("  4. Checks: if input_count > 1")
    print("  5. Condition is TRUE (2 > 1)")
    print("  6. Raises HTTPException(status_code=400, detail='Please provide only one input type')")
    print("\nResult:")
    print("  - Backend returns 400 error")
    print("  - User's audio and text are rejected")
    print("  - User must choose only audio OR only text")
    print("\nExpected Behavior:")
    print("  - Backend should accept both audio and text")
    print("  - Process audio to extract statement")
    print("  - Use text as additional context")
    print("  - Generate FIR with both sources of information")
    print("=" * 70)


def test_counterexample_all_three_inputs():
    """
    Counterexample: Uploading all three input types triggers the bug.
    
    **Validates: Requirement 1.8**
    
    This test documents the most comprehensive counterexample.
    
    Scenario:
    - User has letter image, audio recording, and additional text
    - Backend rejects the request with 400 error
    
    This test always passes but documents the counterexample.
    """
    print("\n" + "=" * 70)
    print("Counterexample 3: Audio + Image + Text Input")
    print("=" * 70)
    print("\nScenario:")
    print("  User has:")
    print("    - Complaint letter as image (complaint.jpg)")
    print("    - Audio recording of incident (statement.wav)")
    print("    - Additional text context")
    print("\nUser Action:")
    print("  1. User selects complaint.jpg in letter upload")
    print("  2. User selects statement.wav in audio upload")
    print("  3. User types additional context:")
    print("     'Witness contact: John Doe, 555-1234'")
    print("  4. User clicks 'Generate FIR' button")
    print("  5. Frontend sends all three inputs to POST /process")
    print("\nBackend Processing:")
    print("  1. Receives audio file, image file, and text input")
    print("  2. Calculates input_count = sum([bool(audio=True), bool(image=True), bool(text=True)])")
    print("  3. input_count = 3")
    print("  4. Checks: if input_count > 1")
    print("  5. Condition is TRUE (3 > 1)")
    print("  6. Raises HTTPException(status_code=400, detail='Please provide only one input type')")
    print("\nResult:")
    print("  - Backend returns 400 error")
    print("  - All three inputs are rejected")
    print("  - User must choose only ONE input type")
    print("\nExpected Behavior:")
    print("  - Backend should accept all three inputs")
    print("  - Process image to extract letter text")
    print("  - Process audio to extract statement")
    print("  - Use text as additional context")
    print("  - Generate comprehensive FIR from all sources")
    print("\nThis is the most comprehensive use case that demonstrates")
    print("the limitation of the current single-input restriction.")
    print("=" * 70)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
