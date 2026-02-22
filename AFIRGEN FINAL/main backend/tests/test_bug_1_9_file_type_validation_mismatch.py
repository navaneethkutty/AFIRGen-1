"""
Bug Condition Exploration Test for Bug 1.9 - File Type Validation Mismatch

**Validates: Requirement 1.9**

Property 1: Fault Condition - File Type Rejection

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.
GOAL: Surface counterexamples that demonstrate the bug exists.

Bug Description:
The frontend validation.js line 83 allows .pdf in the default allowedTypes array,
but the backend input_validation.py only allows image/jpeg, image/png, image/jpg
for images. When a user attempts to upload a .pdf file through the frontend,
the backend rejects it with a 415 error (Unsupported Media Type).

Expected Behavior (After Fix):
The frontend and backend should have consistent file type validation. Either:
- Backend should accept .pdf files if frontend allows them, OR
- Frontend should remove .pdf from allowedTypes if backend doesn't support them

Current Behavior (Unfixed):
Frontend allows .pdf selection, but backend rejects with 415 error,
causing poor user experience and wasted bandwidth.
"""

import pytest
from pathlib import Path


def test_frontend_backend_file_type_mismatch():
    """
    Test that verifies the mismatch between frontend and backend file type validation.
    
    **Validates: Requirement 1.9**
    
    Bug Condition: Frontend allows .pdf but backend rejects it
    Expected Behavior (after fix): Consistent validation between frontend and backend
    
    On UNFIXED code: This test will FAIL because validation is inconsistent
    On FIXED code: This test will PASS because validation is consistent
    """
    # Get paths to validation files
    backend_dir = Path(__file__).parent.parent
    frontend_dir = backend_dir.parent / "frontend"
    
    validation_py_path = backend_dir / "infrastructure" / "input_validation.py"
    validation_js_path = frontend_dir / "js" / "validation.js"
    
    assert validation_py_path.exists(), f"input_validation.py not found at {validation_py_path}"
    assert validation_js_path.exists(), f"validation.js not found at {validation_js_path}"
    
    # Read backend validation file
    with open(validation_py_path, 'r', encoding='utf-8') as f:
        backend_content = f.read()
        backend_lines = backend_content.split('\n')
    
    # Read frontend validation file
    with open(validation_js_path, 'r', encoding='utf-8') as f:
        frontend_content = f.read()
        frontend_lines = frontend_content.split('\n')
    
    # Find backend allowed types (around line 32-34)
    backend_image_types = None
    backend_extensions = None
    
    for i, line in enumerate(backend_lines):
        if 'ALLOWED_IMAGE_TYPES' in line and '=' in line:
            backend_image_types = line.strip()
        if 'ALLOWED_EXTENSIONS' in line and '=' in line:
            backend_extensions = line.strip()
    
    # Find frontend allowed types - check for centralized constants (Bug 2.2 fix)
    frontend_default_types = None
    frontend_line_num = None
    
    # First check for centralized constants (post-fix)
    for i, line in enumerate(frontend_lines):
        if 'const ALLOWED_IMAGE_TYPES' in line or 'const ALLOWED_FILE_TYPES' in line:
            frontend_default_types = line.strip()
            frontend_line_num = i + 1
            break
    
    # If not found, check for old function parameter default (pre-fix)
    if frontend_default_types is None:
        for i, line in enumerate(frontend_lines):
            if 'function validateFileType' in line and 'allowedTypes' in line:
                # Look for the default parameter value
                if '[' in line:
                    frontend_default_types = line.strip()
                    frontend_line_num = i + 1
                else:
                    # Check next line for default value
                    for j in range(i, min(i + 5, len(frontend_lines))):
                        if 'allowedTypes' in frontend_lines[j] and '[' in frontend_lines[j]:
                            frontend_default_types = frontend_lines[j].strip()
                            frontend_line_num = j + 1
                            break
    
    assert backend_image_types is not None, "Could not find ALLOWED_IMAGE_TYPES in backend"
    assert backend_extensions is not None, "Could not find ALLOWED_EXTENSIONS in backend"
    assert frontend_default_types is not None, "Could not find file type configuration in frontend (ALLOWED_IMAGE_TYPES, ALLOWED_AUDIO_TYPES, ALLOWED_FILE_TYPES, or allowedTypes parameter)"
    
    # Check for .pdf in frontend
    frontend_allows_pdf = '.pdf' in frontend_default_types
    
    # Check for .pdf in backend
    backend_allows_pdf = (
        'application/pdf' in backend_image_types or
        '.pdf' in backend_extensions
    )
    
    # Check for other mismatches
    frontend_allows_doc = '.doc' in frontend_default_types
    frontend_allows_docx = '.docx' in frontend_default_types
    frontend_allows_m4a = '.m4a' in frontend_default_types
    frontend_allows_ogg = '.ogg' in frontend_default_types
    
    backend_allows_doc = '.doc' in backend_extensions
    backend_allows_docx = '.docx' in backend_extensions
    backend_allows_m4a = '.m4a' in backend_extensions
    backend_allows_ogg = '.ogg' in backend_extensions
    
    # Collect all mismatches
    mismatches = []
    
    if frontend_allows_pdf and not backend_allows_pdf:
        mismatches.append('.pdf')
    if frontend_allows_doc and not backend_allows_doc:
        mismatches.append('.doc')
    if frontend_allows_docx and not backend_allows_docx:
        mismatches.append('.docx')
    if frontend_allows_m4a and not backend_allows_m4a:
        mismatches.append('.m4a')
    if frontend_allows_ogg and not backend_allows_ogg:
        mismatches.append('.ogg')
    
    if mismatches:
        pytest.fail(
            f"BUG CONFIRMED: File type validation mismatch between frontend and backend\n"
            f"\n"
            f"Bug Condition Triggered:\n"
            f"  - Frontend allows file types that backend rejects\n"
            f"  - User can select files in UI but backend returns 415 error\n"
            f"\n"
            f"Frontend Validation (validation.js line {frontend_line_num}):\n"
            f"  {frontend_default_types}\n"
            f"\n"
            f"Backend Validation (input_validation.py):\n"
            f"  {backend_image_types}\n"
            f"  {backend_extensions}\n"
            f"\n"
            f"Mismatched File Types:\n"
            f"  Frontend allows but backend rejects: {', '.join(mismatches)}\n"
            f"\n"
            f"Current Behavior (UNFIXED):\n"
            f"  1. User selects {mismatches[0]} file in frontend file picker\n"
            f"  2. Frontend validation passes (file type is in allowedTypes)\n"
            f"  3. File is uploaded to backend\n"
            f"  4. Backend validation checks ALLOWED_EXTENSIONS\n"
            f"  5. Backend rejects with 415 error: 'Unsupported file extension'\n"
            f"  6. User sees error after wasting time and bandwidth\n"
            f"\n"
            f"Expected Behavior (FIXED):\n"
            f"  Option A: Backend accepts {', '.join(mismatches)} files\n"
            f"    - Add to ALLOWED_IMAGE_TYPES or ALLOWED_AUDIO_TYPES\n"
            f"    - Add to ALLOWED_EXTENSIONS\n"
            f"    - Implement processing logic for these file types\n"
            f"\n"
            f"  Option B: Frontend removes {', '.join(mismatches)} from allowedTypes\n"
            f"    - Update validation.js line {frontend_line_num}\n"
            f"    - Update app.js file picker accept attributes\n"
            f"    - Prevent user from selecting unsupported types\n"
            f"\n"
            f"Root Cause:\n"
            f"  Frontend and backend validation rules are not synchronized.\n"
            f"  Frontend validation.js has default allowedTypes that include\n"
            f"  file types not supported by backend input_validation.py.\n"
            f"\n"
            f"Impact:\n"
            f"  - Poor user experience (file selected but rejected)\n"
            f"  - Wasted bandwidth uploading files that will be rejected\n"
            f"  - Confusing error messages after upload\n"
            f"  - Users don't know which file types are actually supported\n"
            f"\n"
            f"This confirms Bug 1.9 exists.\n"
        )
    
    # If we reach here, validation is consistent (bug is fixed)
    # The test passes, confirming the expected behavior


def test_document_frontend_allowed_types():
    """
    Document the frontend file type validation configuration.
    
    **Validates: Requirement 1.9**
    
    This test reads the frontend validation.js to document the allowed file types
    at line 83 (validateFileType function default parameter).
    
    This test always passes but provides detailed documentation.
    """
    # Get path to frontend validation file
    backend_dir = Path(__file__).parent.parent
    frontend_dir = backend_dir.parent / "frontend"
    validation_js_path = frontend_dir / "js" / "validation.js"
    
    assert validation_js_path.exists(), f"validation.js not found at {validation_js_path}"
    
    # Read frontend validation file
    with open(validation_js_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the validateFileType function and its default allowedTypes
    validation_lines = []
    
    for i in range(75, min(95, len(lines))):
        line = lines[i]
        if 'validateFileType' in line or 'allowedTypes' in line:
            validation_lines.append((i + 1, line.rstrip()))
    
    assert len(validation_lines) > 0, "Could not find validateFileType function"
    
    print("\n" + "=" * 70)
    print("Bug 1.9: Frontend File Type Validation")
    print("=" * 70)
    print(f"\nFile: {validation_js_path}")
    print("\nValidation Code:")
    for line_num, line_content in validation_lines:
        print(f"  Line {line_num}: {line_content}")
    
    print("\nFrontend Allowed Types (Default):")
    print("  - .jpg")
    print("  - .jpeg")
    print("  - .png")
    print("  - .pdf   <-- MISMATCH: Backend doesn't support")
    print("  - .wav")
    print("  - .mp3")
    
    print("\nFrontend Validation Logic:")
    print("  1. User selects file in file picker")
    print("  2. validateFileType() is called with file and allowedTypes")
    print("  3. Function checks if file extension is in allowedTypes array")
    print("  4. If extension matches, validation passes")
    print("  5. File is uploaded to backend")
    
    print("\nProblem:")
    print("  Frontend allows .pdf files, but backend will reject them")
    print("  with 415 error (Unsupported Media Type)")
    print("=" * 70)


def test_document_backend_allowed_types():
    """
    Document the backend file type validation configuration.
    
    **Validates: Requirement 1.9**
    
    This test reads the backend input_validation.py to document the allowed
    file types in ValidationConstants class (lines 17-34).
    
    This test always passes but provides detailed documentation.
    """
    # Get path to backend validation file
    backend_dir = Path(__file__).parent.parent
    validation_py_path = backend_dir / "infrastructure" / "input_validation.py"
    
    assert validation_py_path.exists(), f"input_validation.py not found at {validation_py_path}"
    
    # Read backend validation file
    with open(validation_py_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the ValidationConstants class
    validation_lines = []
    
    for i in range(15, min(40, len(lines))):
        line = lines[i]
        if 'ALLOWED_IMAGE_TYPES' in line or 'ALLOWED_AUDIO_TYPES' in line or 'ALLOWED_EXTENSIONS' in line:
            validation_lines.append((i + 1, line.rstrip()))
    
    assert len(validation_lines) > 0, "Could not find ValidationConstants"
    
    print("\n" + "=" * 70)
    print("Bug 1.9: Backend File Type Validation")
    print("=" * 70)
    print(f"\nFile: {validation_py_path}")
    print("\nValidation Code:")
    for line_num, line_content in validation_lines:
        print(f"  Line {line_num}: {line_content}")
    
    print("\nBackend Allowed Types:")
    print("  Image MIME types:")
    print("    - image/jpeg")
    print("    - image/png")
    print("    - image/jpg")
    print("    - NO application/pdf   <-- MISMATCH")
    print("\n  Audio MIME types:")
    print("    - audio/wav")
    print("    - audio/mpeg")
    print("    - audio/mp3")
    print("    - audio/x-wav")
    print("    - NO audio/m4a   <-- MISMATCH")
    print("    - NO audio/ogg   <-- MISMATCH")
    print("\n  Allowed Extensions:")
    print("    - .jpg, .jpeg, .png")
    print("    - .wav, .mp3, .mpeg")
    print("    - NO .pdf   <-- MISMATCH")
    print("    - NO .doc, .docx   <-- MISMATCH")
    print("    - NO .m4a, .ogg   <-- MISMATCH")
    
    print("\nBackend Validation Logic:")
    print("  1. Backend receives uploaded file")
    print("  2. validate_file_upload() is called")
    print("  3. Function checks file extension against ALLOWED_EXTENSIONS")
    print("  4. If extension not in set, raise HTTPException with 415 status")
    print("  5. Function checks MIME type against allowed_types parameter")
    print("  6. If MIME type not in set, raise HTTPException with 415 status")
    
    print("\nProblem:")
    print("  Backend rejects .pdf files that frontend allows")
    print("  Error: 'Unsupported file extension: .pdf'")
    print("=" * 70)


def test_counterexample_pdf_upload():
    """
    Counterexample: Uploading a .pdf file triggers the bug.
    
    **Validates: Requirement 1.9**
    
    This test documents a specific counterexample that demonstrates Bug 1.9.
    
    Scenario:
    - User has a complaint letter in PDF format
    - Frontend allows .pdf selection (validation.js line 83)
    - Backend rejects .pdf with 415 error
    
    This test always passes but documents the counterexample.
    """
    print("\n" + "=" * 70)
    print("Counterexample 1: PDF File Upload")
    print("=" * 70)
    print("\nScenario:")
    print("  User has:")
    print("    - Complaint letter in PDF format (complaint.pdf)")
    print("\nUser Action:")
    print("  1. User opens the AFIRGEN application")
    print("  2. User clicks on letter upload file picker")
    print("  3. User selects complaint.pdf")
    print("  4. Frontend validation.js validateFileType() is called")
    print("  5. File extension '.pdf' is in default allowedTypes")
    print("  6. Frontend validation PASSES")
    print("  7. User clicks 'Generate FIR' button")
    print("  8. Frontend uploads complaint.pdf to POST /process")
    print("\nBackend Processing:")
    print("  1. Backend receives UploadFile with filename='complaint.pdf'")
    print("  2. validate_file_upload() is called")
    print("  3. Extract extension: ext = '.pdf'")
    print("  4. Check: if ext not in ValidationConstants.ALLOWED_EXTENSIONS")
    print("  5. ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.wav', '.mp3', '.mpeg'}")
    print("  6. '.pdf' is NOT in the set")
    print("  7. Condition is TRUE")
    print("  8. Raise HTTPException(status_code=415, detail='Unsupported file extension: .pdf')")
    print("\nResult:")
    print("  - Backend returns 415 Unsupported Media Type error")
    print("  - Frontend shows error message to user")
    print("  - User's PDF file is rejected")
    print("  - User wasted time selecting and uploading the file")
    print("\nExpected Behavior:")
    print("  Option A: Backend accepts .pdf files")
    print("    - Add 'application/pdf' to ALLOWED_IMAGE_TYPES")
    print("    - Add '.pdf' to ALLOWED_EXTENSIONS")
    print("    - Implement PDF text extraction logic")
    print("\n  Option B: Frontend removes .pdf from allowedTypes")
    print("    - Update validation.js line 83 to remove '.pdf'")
    print("    - Update file picker accept attribute")
    print("    - User cannot select .pdf files")
    print("=" * 70)


def test_counterexample_doc_upload():
    """
    Counterexample: Uploading a .doc or .docx file triggers the bug.
    
    **Validates: Requirement 1.9**
    
    This test documents another counterexample for document files.
    
    Scenario:
    - User has a complaint letter in Word format
    - Frontend may allow .doc/.docx selection
    - Backend rejects with 415 error
    
    This test always passes but documents the counterexample.
    """
    print("\n" + "=" * 70)
    print("Counterexample 2: Word Document Upload")
    print("=" * 70)
    print("\nScenario:")
    print("  User has:")
    print("    - Complaint letter in Word format (complaint.docx)")
    print("\nUser Action:")
    print("  1. User opens the AFIRGEN application")
    print("  2. User clicks on letter upload file picker")
    print("  3. User selects complaint.docx")
    print("  4. If frontend allows .docx, validation passes")
    print("  5. User clicks 'Generate FIR' button")
    print("  6. Frontend uploads complaint.docx to POST /process")
    print("\nBackend Processing:")
    print("  1. Backend receives UploadFile with filename='complaint.docx'")
    print("  2. validate_file_upload() is called")
    print("  3. Extract extension: ext = '.docx'")
    print("  4. Check: if ext not in ValidationConstants.ALLOWED_EXTENSIONS")
    print("  5. ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.wav', '.mp3', '.mpeg'}")
    print("  6. '.docx' is NOT in the set")
    print("  7. Condition is TRUE")
    print("  8. Raise HTTPException(status_code=415, detail='Unsupported file extension: .docx')")
    print("\nResult:")
    print("  - Backend returns 415 Unsupported Media Type error")
    print("  - User's Word document is rejected")
    print("\nExpected Behavior:")
    print("  Option A: Backend accepts .doc/.docx files")
    print("    - Add MIME types to ALLOWED_IMAGE_TYPES")
    print("    - Add '.doc', '.docx' to ALLOWED_EXTENSIONS")
    print("    - Implement Word document text extraction")
    print("\n  Option B: Frontend prevents .doc/.docx selection")
    print("    - Ensure validation.js doesn't include these types")
    print("    - Update file picker to only allow supported types")
    print("=" * 70)


def test_counterexample_m4a_ogg_upload():
    """
    Counterexample: Uploading .m4a or .ogg audio files triggers the bug.
    
    **Validates: Requirement 1.9**
    
    This test documents counterexamples for audio file formats.
    
    Scenario:
    - User has audio recording in .m4a or .ogg format
    - Frontend may allow these formats
    - Backend rejects with 415 error
    
    This test always passes but documents the counterexample.
    """
    print("\n" + "=" * 70)
    print("Counterexample 3: M4A/OGG Audio Upload")
    print("=" * 70)
    print("\nScenario:")
    print("  User has:")
    print("    - Audio recording in M4A format (statement.m4a)")
    print("    - OR audio recording in OGG format (statement.ogg)")
    print("\nUser Action:")
    print("  1. User opens the AFIRGEN application")
    print("  2. User clicks on audio upload file picker")
    print("  3. User selects statement.m4a")
    print("  4. If frontend allows .m4a, validation passes")
    print("  5. User clicks 'Generate FIR' button")
    print("  6. Frontend uploads statement.m4a to POST /process")
    print("\nBackend Processing:")
    print("  1. Backend receives UploadFile with filename='statement.m4a'")
    print("  2. validate_file_upload() is called")
    print("  3. Extract extension: ext = '.m4a'")
    print("  4. Check: if ext not in ValidationConstants.ALLOWED_EXTENSIONS")
    print("  5. ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.wav', '.mp3', '.mpeg'}")
    print("  6. '.m4a' is NOT in the set")
    print("  7. Condition is TRUE")
    print("  8. Raise HTTPException(status_code=415, detail='Unsupported file extension: .m4a')")
    print("\nResult:")
    print("  - Backend returns 415 Unsupported Media Type error")
    print("  - User's audio file is rejected")
    print("\nExpected Behavior:")
    print("  Option A: Backend accepts .m4a/.ogg files")
    print("    - Add 'audio/m4a', 'audio/ogg' to ALLOWED_AUDIO_TYPES")
    print("    - Add '.m4a', '.ogg' to ALLOWED_EXTENSIONS")
    print("    - Ensure ASR service can process these formats")
    print("\n  Option B: Frontend prevents .m4a/.ogg selection")
    print("    - Ensure validation.js doesn't include these types")
    print("    - Update file picker to only allow .wav, .mp3")
    print("=" * 70)


def test_verify_backend_rejection_logic():
    """
    Verify the exact backend validation logic that rejects unsupported file types.
    
    **Validates: Requirement 1.9**
    
    This test examines the validate_file_upload() function in input_validation.py
    to confirm the rejection logic for unsupported file extensions.
    
    This test always passes but provides detailed documentation.
    """
    # Get path to backend validation file
    backend_dir = Path(__file__).parent.parent
    validation_py_path = backend_dir / "infrastructure" / "input_validation.py"
    
    assert validation_py_path.exists(), f"input_validation.py not found at {validation_py_path}"
    
    # Read backend validation file
    with open(validation_py_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the validate_file_upload function
    validation_function_lines = []
    in_function = False
    
    for i, line in enumerate(lines):
        if 'def validate_file_upload' in line:
            in_function = True
        
        if in_function:
            validation_function_lines.append((i + 1, line.rstrip()))
            
            # Stop at the next function definition or class
            if i > 0 and (line.startswith('def ') or line.startswith('class ')) and 'validate_file_upload' not in line:
                break
    
    assert len(validation_function_lines) > 0, "Could not find validate_file_upload function"
    
    print("\n" + "=" * 70)
    print("Bug 1.9: Backend File Upload Validation Logic")
    print("=" * 70)
    print(f"\nFile: {validation_py_path}")
    print("\nFunction: validate_file_upload()")
    print("\nKey Validation Steps:")
    
    # Extract key lines
    for line_num, line_content in validation_function_lines:
        if 'ALLOWED_EXTENSIONS' in line_content or 'HTTPException' in line_content or 'status_code=415' in line_content:
            print(f"  Line {line_num}: {line_content}")
    
    print("\nValidation Flow:")
    print("  1. Check if file exists")
    print("  2. Check if filename is valid")
    print("  3. Extract file extension using Path(file.filename).suffix.lower()")
    print("  4. Check: if ext not in ValidationConstants.ALLOWED_EXTENSIONS")
    print("  5. If extension not allowed:")
    print("     - Raise HTTPException(status_code=415)")
    print("     - Detail: 'Unsupported file extension: {ext}'")
    print("  6. Check MIME type against allowed_types parameter")
    print("  7. If MIME type not allowed:")
    print("     - Raise HTTPException(status_code=415)")
    print("     - Detail: 'Unsupported content type: {content_type}'")
    print("  8. Check file size")
    
    print("\nCritical Issue:")
    print("  The ALLOWED_EXTENSIONS set is hardcoded and does NOT include:")
    print("    - .pdf (document)")
    print("    - .doc, .docx (Word documents)")
    print("    - .m4a, .ogg (audio formats)")
    print("\n  But frontend validation.js default allowedTypes DOES include .pdf")
    print("\n  This creates a mismatch where frontend allows but backend rejects")
    print("=" * 70)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
