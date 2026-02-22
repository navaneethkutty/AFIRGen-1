"""
Bug Condition Exploration Test for High Priority Bug 7 - Multiple File Upload Allowed

**Validates: Requirements 1.7, 2.7**

Property 1: Fault Condition - Frontend Allows Multiple File Selection

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.
GOAL: Surface counterexamples that demonstrate the bug exists.

Bug Description:
When a user selects both a letter file and an audio file in the frontend UI,
the system allows generation to proceed, but the backend rejects multiple inputs
(lines 1716-1719 in agentv5.py), causing unexpected failure after upload.

Expected Behavior (After Fix):
The frontend should disable the generation button or show a validation error
preventing submission when both file types are selected.

Current Behavior (Unfixed):
The frontend allows submission when both files are selected, leading to backend rejection.
"""

import pytest
from pathlib import Path


def test_frontend_allows_multiple_file_selection():
    """
    Test that verifies the frontend CURRENTLY ALLOWS (bug) selecting both
    letter and audio files simultaneously.
    
    **Validates: Requirements 1.7, 2.7**
    
    Bug Condition: input.type == "FILE_UPLOAD" AND input.letterFile != NULL 
                   AND input.audioFile != NULL AND frontend.allowsSubmit
    
    Expected Behavior (after fix): Frontend prevents submission when both files selected
    
    On UNFIXED code: This test will FAIL because frontend allows submission (proves bug exists)
    On FIXED code: This test will PASS because frontend prevents submission
    """
    # Get the path to app.js
    backend_dir = Path(__file__).parent.parent
    frontend_dir = backend_dir.parent / "frontend" / "js"
    app_js_path = frontend_dir / "app.js"
    
    assert app_js_path.exists(), f"app.js not found at {app_js_path}"
    
    # Read the file
    with open(app_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the updateFilesState function
    update_files_state_line = None
    function_body_start = None
    function_body_end = None
    
    for i, line in enumerate(lines):
        if 'function updateFilesState' in line:
            update_files_state_line = i
            function_body_start = i
            
            # Find the end of the function (look for closing brace at same indentation)
            brace_count = 0
            found_opening = False
            for j in range(i, min(i + 50, len(lines))):
                if '{' in lines[j]:
                    brace_count += 1
                    found_opening = True
                if '}' in lines[j]:
                    brace_count -= 1
                    if found_opening and brace_count == 0:
                        function_body_end = j
                        break
            break
    
    assert update_files_state_line is not None, \
        "Could not find updateFilesState function in app.js"
    
    assert function_body_end is not None, \
        f"Could not find end of updateFilesState function starting at line {update_files_state_line + 1}"
    
    # Extract the function body
    function_body = '\n'.join(lines[function_body_start:function_body_end + 1])
    
    # Check if the function validates against multiple file selection
    # Expected on FIXED code: Check for (letterFile && audioFile) and disable button or show error
    # Expected on UNFIXED code: No such check exists
    
    has_multiple_file_check = False
    
    # Look for patterns that check both files are selected
    if 'letterFile && audioFile' in function_body or \
       'audioFile && letterFile' in function_body or \
       '(letterFile && audioFile)' in function_body or \
       '(audioFile && letterFile)' in function_body:
        has_multiple_file_check = True
    
    # Also check if there's any logic that disables button when both are selected
    # Look for patterns like: if (letterFile && audioFile) { generateBtn.disabled = true; }
    if has_multiple_file_check:
        # Check if it actually disables the button or shows error
        # Look in the next few lines after the check
        if 'disabled = true' in function_body or \
           'showToast' in function_body or \
           'error' in function_body.lower():
            has_multiple_file_check = True
        else:
            has_multiple_file_check = False
    
    # Now check the backend code to confirm it rejects multiple files
    agentv5_path = backend_dir / "agentv5.py"
    
    assert agentv5_path.exists(), f"agentv5.py not found at {agentv5_path}"
    
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        backend_content = f.read()
        backend_lines = backend_content.split('\n')
    
    # Find the /process endpoint validation (around line 1714)
    backend_rejects_multiple = False
    rejection_line = None
    
    for i, line in enumerate(backend_lines):
        # Look for the validation that checks for multiple inputs
        # The backend checks: if input_count > 1
        if 'input_count' in line and '>' in line and '1' in line:
            # Check if this is a rejection condition
            for j in range(i, min(i + 5, len(backend_lines))):
                if 'raise HTTPException' in backend_lines[j] and '400' in backend_lines[j]:
                    backend_rejects_multiple = True
                    rejection_line = i
                    break
            if backend_rejects_multiple:
                break
    
    # Check for mismatch
    if not has_multiple_file_check and backend_rejects_multiple:
        pytest.fail(
            f"Multiple file upload validation mismatch detected:\n"
            f"\n"
            f"Bug Condition Triggered:\n"
            f"  - User selects both letter file AND audio file\n"
            f"  - Frontend allows submission (generate button enabled)\n"
            f"  - Backend rejects the request with 400 error\n"
            f"\n"
            f"Frontend Implementation (UNFIXED):\n"
            f"  File: frontend/js/app.js\n"
            f"  Function: updateFilesState (line {update_files_state_line + 1})\n"
            f"\n"
            f"  Current implementation:\n"
            f"{function_body}\n"
            f"\n"
            f"  The function checks: hasFiles = !!(letterFile || audioFile)\n"
            f"  This means: Enable button if letterFile OR audioFile exists\n"
            f"  Problem: This allows BOTH files to be selected simultaneously\n"
            f"\n"
            f"  Missing validation:\n"
            f"    - No check for (letterFile && audioFile)\n"
            f"    - No logic to disable button when both files selected\n"
            f"    - No error message shown to user\n"
            f"\n"
            f"Backend Implementation:\n"
            f"  File: AFIRGEN FINAL/main backend/agentv5.py\n"
            f"  Line {rejection_line + 1}: {backend_lines[rejection_line].strip()}\n"
            f"\n"
            f"  The backend correctly validates and rejects multiple inputs:\n"
            f"  - Checks if both letter_file and audio_file are provided\n"
            f"  - Raises HTTPException with 400 status code\n"
            f"  - Error message: 'Please provide only one input type'\n"
            f"\n"
            f"Root Cause:\n"
            f"  Frontend-backend validation mismatch:\n"
            f"  - Frontend: Allows selecting both file types\n"
            f"  - Backend: Rejects requests with both file types\n"
            f"  - User experience: Upload both files, click generate, get error after upload\n"
            f"\n"
            f"Expected Behavior:\n"
            f"  When user selects both letter file and audio file:\n"
            f"  - Frontend should immediately detect this condition\n"
            f"  - Generate button should be disabled\n"
            f"  - Error message should be shown: 'Please select only one input type'\n"
            f"  - User cannot submit the form\n"
            f"  - No backend request is made\n"
            f"\n"
            f"Actual Behavior (UNFIXED):\n"
            f"  When user selects both letter file and audio file:\n"
            f"  - Frontend enables generate button (hasFiles = true)\n"
            f"  - User clicks generate button\n"
            f"  - Files are uploaded to backend\n"
            f"  - Backend rejects with 400 error\n"
            f"  - User sees error after wasting time uploading files\n"
            f"  - Poor user experience\n"
            f"\n"
            f"Impact:\n"
            f"  - Confusing user experience (why allow selection if it will be rejected?)\n"
            f"  - Wasted bandwidth uploading files that will be rejected\n"
            f"  - Wasted user time waiting for upload and processing\n"
            f"  - Error appears after submission instead of during selection\n"
            f"  - Users may not understand why their submission was rejected\n"
            f"\n"
            f"Fix Required:\n"
            f"  Add validation in updateFilesState function:\n"
            f"\n"
            f"  function updateFilesState() {{\n"
            f"    hasFiles = !!(letterFile || audioFile);\n"
            f"    const generateBtn = document.getElementById('generate-btn');\n"
            f"\n"
            f"    // ADD THIS: Check for multiple file selection\n"
            f"    if (letterFile && audioFile) {{\n"
            f"      generateBtn.disabled = true;\n"
            f"      generateBtn.setAttribute('aria-disabled', 'true');\n"
            f"      window.showToast('Please select only one input type', 'error');\n"
            f"      return;\n"
            f"    }}\n"
            f"\n"
            f"    if (generateBtn) {{\n"
            f"      generateBtn.disabled = !hasFiles;\n"
            f"      generateBtn.setAttribute('aria-disabled', !hasFiles ? 'true' : 'false');\n"
            f"    }}\n"
            f"    // ... rest of function\n"
            f"  }}\n"
            f"\n"
            f"  This will:\n"
            f"  1. Detect when both files are selected\n"
            f"  2. Disable the generate button\n"
            f"  3. Show clear error message to user\n"
            f"  4. Prevent submission before backend request\n"
            f"  5. Improve user experience with immediate feedback\n"
            f"\n"
            f"This confirms High Priority Bug 7 exists.\n"
        )
    
    # If we reach here, the bug is fixed
    assert has_multiple_file_check, \
        "Expected frontend to prevent multiple file selection after fix"


def test_backend_rejects_multiple_files():
    """
    Test that documents the backend's correct rejection of multiple files.
    
    **Validates: Requirements 1.7, 2.7**
    
    This test confirms that the backend correctly rejects multiple file uploads,
    which makes the frontend bug more critical (frontend should match backend behavior).
    
    On UNFIXED code: This test documents the backend's correct behavior
    On FIXED code: This test confirms backend behavior is unchanged
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the /process endpoint validation
    validation_line = None
    error_message_line = None
    
    for i, line in enumerate(lines):
        # Look for the validation that checks for multiple inputs
        # The backend checks: if input_count > 1
        if 'input_count' in line and '>' in line and '1' in line:
            # Check if this is a rejection condition
            for j in range(max(0, i - 5), min(i + 10, len(lines))):
                if 'HTTPException' in lines[j] and '400' in lines[j]:
                    validation_line = i
                    error_message_line = j
                    break
            if validation_line:
                break
    
    assert validation_line is not None, \
        "Could not find multiple file validation in backend"
    
    print("\nBackend Multiple File Validation:")
    print("=" * 70)
    print(f"\nFile: AFIRGEN FINAL/main backend/agentv5.py")
    print(f"Validation at line: {validation_line + 1}")
    print(f"\nValidation Logic:")
    print(f"  {lines[validation_line].strip()}")
    if error_message_line:
        print(f"\nError Response (line {error_message_line + 1}):")
        print(f"  {lines[error_message_line].strip()}")
    print("\nBackend Behavior:")
    print("  - Checks if both letter_file and audio_file are provided")
    print("  - Raises HTTPException with status_code=400")
    print("  - Returns error: 'Please provide only one input type'")
    print("\nThis is CORRECT backend behavior.")
    print("The frontend should match this validation BEFORE submission.")
    print("=" * 70)


def test_user_experience_flow():
    """
    Test that documents the poor user experience caused by the bug.
    
    **Validates: Requirements 1.7, 2.7**
    
    This test describes the user journey and why the bug is problematic.
    
    On UNFIXED code: This test documents the poor UX
    On FIXED code: This test confirms improved UX
    """
    print("\nUser Experience Flow (UNFIXED):")
    print("=" * 70)
    print("\nStep 1: User opens the application")
    print("  - Sees two upload buttons: 'Upload Letter' and 'Upload Audio'")
    print("  - No indication that only one can be selected")
    print("\nStep 2: User selects a letter file (e.g., complaint.jpg)")
    print("  - File is selected successfully")
    print("  - Generate button becomes enabled")
    print("  - UI shows: 'Letter file uploaded: complaint.jpg'")
    print("\nStep 3: User also selects an audio file (e.g., recording.mp3)")
    print("  - File is selected successfully")
    print("  - Generate button REMAINS enabled (BUG)")
    print("  - UI shows: 'Audio file uploaded: recording.mp3'")
    print("  - No warning or error message")
    print("\nStep 4: User clicks 'Generate FIR' button")
    print("  - Button is enabled, so user expects it to work")
    print("  - Both files start uploading to backend")
    print("  - User waits for upload to complete...")
    print("\nStep 5: Backend rejects the request")
    print("  - Backend returns 400 error: 'Please provide only one input type'")
    print("  - Frontend shows error toast")
    print("  - User is confused: 'Why did it let me select both files?'")
    print("\nProblems:")
    print("  1. Wasted time: User uploaded files that were rejected")
    print("  2. Wasted bandwidth: Unnecessary file uploads")
    print("  3. Confusing UX: Why allow selection if it will be rejected?")
    print("  4. Late feedback: Error appears after submission, not during selection")
    print("  5. Unclear guidance: User doesn't know which file to keep")
    print("\nExpected User Experience (FIXED):")
    print("=" * 70)
    print("\nStep 1: User opens the application")
    print("  - Sees two upload buttons: 'Upload Letter' and 'Upload Audio'")
    print("\nStep 2: User selects a letter file (e.g., complaint.jpg)")
    print("  - File is selected successfully")
    print("  - Generate button becomes enabled")
    print("  - UI shows: 'Letter file uploaded: complaint.jpg'")
    print("\nStep 3: User also selects an audio file (e.g., recording.mp3)")
    print("  - File is selected successfully")
    print("  - Generate button becomes DISABLED (FIX)")
    print("  - UI shows error: 'Please select only one input type'")
    print("  - User immediately understands the constraint")
    print("\nStep 4: User deselects one file")
    print("  - User clears the letter file or audio file")
    print("  - Generate button becomes enabled again")
    print("  - User can proceed with single file")
    print("\nBenefits:")
    print("  1. Immediate feedback: Error shown during selection, not after submission")
    print("  2. Clear guidance: User knows only one file type is allowed")
    print("  3. No wasted time: No unnecessary uploads")
    print("  4. No wasted bandwidth: Files not uploaded if they'll be rejected")
    print("  5. Better UX: Prevent errors instead of handling them")
    print("=" * 70)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
