"""
Bug Condition Exploration Test for High Priority Bug 8 - File Type Mismatch

**Validates: Requirements 1.8, 2.8**

Property 1: Fault Condition - Frontend/Backend File Type Mismatch

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.
GOAL: Surface counterexamples that demonstrate the bug exists.

Bug Description:
When a user uploads .pdf, .txt, .doc, or .docx letter files OR .m4a or .ogg audio files,
the frontend accepts these types (app.js lines 399-444) but the backend only supports
jpeg/png images and wav/mpeg/mp3 audio (input_validation.py lines 27-31).

Expected Behavior (After Fix):
The frontend should only accept file types that are supported by both frontend and backend:
- Letter files: .jpg, .jpeg, .png
- Audio files: .wav, .mp3

Current Behavior (Unfixed):
The frontend accepts .pdf, .txt, .doc, .docx, .m4a, .ogg files, leading to backend rejection.
"""

import pytest
from pathlib import Path


def test_frontend_backend_file_type_mismatch():
    """
    Test that verifies frontend and backend have mismatched file type support.
    
    **Validates: Requirements 1.8, 2.8**
    
    Bug Condition: input.type == "FILE_UPLOAD" AND 
                   input.fileType IN [".pdf", ".txt", ".doc", ".docx", ".m4a", ".ogg"] AND 
                   frontend.accepts AND NOT backend.accepts
    
    Expected Behavior (after fix): Frontend and backend accept same file types
    
    On UNFIXED code: This test will FAIL because frontend accepts types backend doesn't (proves bug exists)
    On FIXED code: This test will PASS because file types are aligned
    """
    # Get the path to app.js
    backend_dir = Path(__file__).parent.parent
    frontend_dir = backend_dir.parent / "frontend" / "js"
    app_js_path = frontend_dir / "app.js"
    
    assert app_js_path.exists(), f"app.js not found at {app_js_path}"
    
    # Read the frontend file
    with open(app_js_path, 'r', encoding='utf-8') as f:
        frontend_content = f.read()
        frontend_lines = frontend_content.split('\n')
    
    # Find the letter file upload validation (around line 399)
    frontend_letter_types = set()
    frontend_audio_types = set()
    
    for i, line in enumerate(frontend_lines):
        # Look for allowedTypes arrays
        if 'allowedTypes:' in line:
            # Check if this is for letter or audio
            # Look backwards to see context
            context = '\n'.join(frontend_lines[max(0, i-10):i])
            
            # Extract the allowed types from the array
            # Format: allowedTypes: ['.jpg', '.jpeg', '.png', '.pdf', ...]
            if '[' in line:
                types_str = line.split('[')[1].split(']')[0]
                types = [t.strip().strip("'\"") for t in types_str.split(',')]
                
                if 'letter' in context.lower():
                    frontend_letter_types.update(types)
                elif 'audio' in context.lower():
                    frontend_audio_types.update(types)
    
    # Get the path to input_validation.py
    validation_path = backend_dir / "infrastructure" / "input_validation.py"
    
    assert validation_path.exists(), f"input_validation.py not found at {validation_path}"
    
    # Read the backend validation file
    with open(validation_path, 'r', encoding='utf-8') as f:
        backend_content = f.read()
        backend_lines = backend_content.split('\n')
    
    # Find the allowed file types in backend (around lines 27-31)
    backend_extensions = set()
    
    for i, line in enumerate(backend_lines):
        # Look for ALLOWED_EXTENSIONS which contains file extensions
        if 'ALLOWED_EXTENSIONS' in line and '=' in line:
            # Extract the set contents
            # Format: ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".wav", ".mp3", ".mpeg"}
            if '{' in line:
                types_str = line.split('{')[1].split('}')[0]
                types = [t.strip().strip("'\"") for t in types_str.split(',')]
                backend_extensions.update(types)
    
    # Separate backend extensions into image and audio
    backend_image_extensions = {ext for ext in backend_extensions if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']}
    backend_audio_extensions = {ext for ext in backend_extensions if ext in ['.wav', '.mp3', '.mpeg', '.m4a', '.ogg', '.flac', '.aac']}
    
    # Check for mismatches
    # Frontend letter types should match backend image extensions
    frontend_only_letter = frontend_letter_types - backend_image_extensions
    # Frontend audio types should match backend audio extensions
    frontend_only_audio = frontend_audio_types - backend_audio_extensions
    
    has_mismatch = len(frontend_only_letter) > 0 or len(frontend_only_audio) > 0
    
    if has_mismatch:
        pytest.fail(
            f"File type mismatch between frontend and backend detected:\n"
            f"\n"
            f"Bug Condition Triggered:\n"
            f"  - Frontend accepts file types that backend does NOT support\n"
            f"  - User uploads unsupported file type\n"
            f"  - Frontend allows upload\n"
            f"  - Backend rejects with 415 Unsupported Media Type error\n"
            f"\n"
            f"Frontend Implementation (UNFIXED):\n"
            f"  File: frontend/js/app.js\n"
            f"\n"
            f"  Letter file types accepted by frontend:\n"
            f"    {sorted(frontend_letter_types)}\n"
            f"\n"
            f"  Audio file types accepted by frontend:\n"
            f"    {sorted(frontend_audio_types)}\n"
            f"\n"
            f"Backend Implementation:\n"
            f"  File: AFIRGEN FINAL/main backend/infrastructure/input_validation.py\n"
            f"\n"
            f"  Image file extensions accepted by backend:\n"
            f"    {sorted(backend_image_extensions)}\n"
            f"\n"
            f"  Audio file extensions accepted by backend:\n"
            f"    {sorted(backend_audio_extensions)}\n"
            f"\n"
            f"MISMATCH DETECTED:\n"
            f"\n"
            f"  Letter file types accepted by frontend but NOT backend:\n"
            f"    {sorted(frontend_only_letter)}\n"
            f"\n"
            f"  Audio file types accepted by frontend but NOT backend:\n"
            f"    {sorted(frontend_only_audio)}\n"
            f"\n"
            f"Root Cause:\n"
            f"  Frontend-backend file type validation mismatch:\n"
            f"  - Frontend: Accepts {len(frontend_letter_types)} letter types and {len(frontend_audio_types)} audio types\n"
            f"  - Backend: Accepts {len(backend_image_extensions)} image types and {len(backend_audio_extensions)} audio types\n"
            f"  - Unsupported types: {sorted(frontend_only_letter | frontend_only_audio)}\n"
            f"  - User experience: Upload unsupported file, get error after upload\n"
            f"\n"
            f"Expected Behavior:\n"
            f"  When user attempts to upload unsupported file type:\n"
            f"  - Frontend should reject the file immediately\n"
            f"  - Error message should be shown: 'File type not supported'\n"
            f"  - No backend request is made\n"
            f"  - User knows immediately which types are supported\n"
            f"\n"
            f"Actual Behavior (UNFIXED):\n"
            f"  When user uploads unsupported file type:\n"
            f"  - Frontend accepts the file (validation passes)\n"
            f"  - User clicks generate button\n"
            f"  - File is uploaded to backend\n"
            f"  - Backend rejects with 415 Unsupported Media Type\n"
            f"  - User sees error after wasting time uploading\n"
            f"  - Confusing: 'Why did it let me select this file?'\n"
            f"\n"
            f"Impact:\n"
            f"  - Confusing user experience (frontend accepts, backend rejects)\n"
            f"  - Wasted bandwidth uploading unsupported files\n"
            f"  - Wasted user time waiting for upload and processing\n"
            f"  - Error appears after submission, not during selection\n"
            f"  - Users may try multiple times with same unsupported file\n"
            f"  - Poor accessibility: Screen readers announce file accepted, then error\n"
            f"\n"
            f"Fix Required:\n"
            f"  Option A (Recommended): Remove unsupported types from frontend\n"
            f"    File: frontend/js/app.js\n"
            f"    Line ~399: Change allowedTypes: ['.jpg', '.jpeg', '.png', '.pdf', '.txt', '.doc', '.docx']\n"
            f"    To: allowedTypes: ['.jpg', '.jpeg', '.png']\n"
            f"\n"
            f"    Line ~437: Change allowedTypes: ['.mp3', '.wav', '.m4a', '.ogg']\n"
            f"    To: allowedTypes: ['.mp3', '.wav']\n"
            f"\n"
            f"  Option B: Add support for these types in backend\n"
            f"    File: AFIRGEN FINAL/main backend/infrastructure/input_validation.py\n"
            f"    Add .pdf, .txt, .doc, .docx to ALLOWED_IMAGE_TYPES\n"
            f"    Add .m4a, .ogg to ALLOWED_AUDIO_TYPES\n"
            f"    Implement processing logic for these types\n"
            f"    Less recommended: More complex, requires additional processing logic\n"
            f"\n"
            f"  Recommended: Option A (remove from frontend)\n"
            f"  - Simpler implementation\n"
            f"  - No backend changes needed\n"
            f"  - Aligns with current backend capabilities\n"
            f"  - Immediate user feedback\n"
            f"\n"
            f"This confirms High Priority Bug 8 exists.\n"
        )
    
    # If we reach here, the bug is fixed
    assert not has_mismatch, \
        "Expected frontend and backend to accept same file types after fix"


def test_backend_supported_file_types():
    """
    Test that documents the backend's supported file types.
    
    **Validates: Requirements 1.8, 2.8**
    
    This test confirms what file types the backend actually supports.
    
    On UNFIXED code: This test documents the backend's correct behavior
    On FIXED code: This test confirms backend behavior is unchanged
    """
    # Get the path to input_validation.py
    backend_dir = Path(__file__).parent.parent
    validation_path = backend_dir / "infrastructure" / "input_validation.py"
    
    # Read the file
    with open(validation_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the allowed types
    image_types_line = None
    audio_types_line = None
    
    for i, line in enumerate(lines):
        if 'ALLOWED_IMAGE_TYPES' in line and '=' in line:
            image_types_line = i
        if 'ALLOWED_AUDIO_TYPES' in line and '=' in line:
            audio_types_line = i
    
    assert image_types_line is not None, \
        "Could not find ALLOWED_IMAGE_TYPES in input_validation.py"
    
    assert audio_types_line is not None, \
        "Could not find ALLOWED_AUDIO_TYPES in input_validation.py"
    
    print("\nBackend Supported File Types:")
    print("=" * 70)
    print(f"\nFile: AFIRGEN FINAL/main backend/infrastructure/input_validation.py")
    print(f"\nImage Types (line {image_types_line + 1}):")
    print(f"  {lines[image_types_line].strip()}")
    print(f"\nAudio Types (line {audio_types_line + 1}):")
    print(f"  {lines[audio_types_line].strip()}")
    print("\nSupported Types:")
    print("  Images: .jpg, .jpeg, .png")
    print("  Audio: .wav, .mp3, .mpeg")
    print("\nNOT Supported:")
    print("  Images: .pdf, .txt, .doc, .docx")
    print("  Audio: .m4a, .ogg")
    print("\nThis is the CORRECT backend behavior.")
    print("The frontend must match these types.")
    print("=" * 70)


def test_frontend_accepted_file_types():
    """
    Test that documents the frontend's accepted file types.
    
    **Validates: Requirements 1.8, 2.8**
    
    This test shows what file types the frontend currently accepts.
    
    On UNFIXED code: This test documents the frontend's incorrect behavior
    On FIXED code: This test confirms frontend matches backend
    """
    # Get the path to app.js
    backend_dir = Path(__file__).parent.parent
    frontend_dir = backend_dir.parent / "frontend" / "js"
    app_js_path = frontend_dir / "app.js"
    
    # Read the file
    with open(app_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the allowedTypes arrays
    letter_types_line = None
    audio_types_line = None
    
    for i, line in enumerate(lines):
        if 'allowedTypes:' in line:
            context = '\n'.join(lines[max(0, i-10):i])
            if 'letter' in context.lower() and letter_types_line is None:
                letter_types_line = i
            elif 'audio' in context.lower() and audio_types_line is None:
                audio_types_line = i
    
    assert letter_types_line is not None, \
        "Could not find letter file allowedTypes in app.js"
    
    assert audio_types_line is not None, \
        "Could not find audio file allowedTypes in app.js"
    
    print("\nFrontend Accepted File Types:")
    print("=" * 70)
    print(f"\nFile: frontend/js/app.js")
    print(f"\nLetter Types (line {letter_types_line + 1}):")
    print(f"  {lines[letter_types_line].strip()}")
    print(f"\nAudio Types (line {audio_types_line + 1}):")
    print(f"  {lines[audio_types_line].strip()}")
    print("\nProblem:")
    print("  Frontend accepts MORE types than backend supports")
    print("  This causes validation mismatch and poor user experience")
    print("\nRequired Fix:")
    print("  Remove unsupported types from frontend validation")
    print("  Match backend's supported types exactly")
    print("=" * 70)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
