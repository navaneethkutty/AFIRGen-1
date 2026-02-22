# Implementation Plan

## CRITICAL UPDATE: Code Review Findings

After comprehensive code review of the entire AFIRGEN codebase (backend + frontend), the following status was determined:

### ALREADY FIXED (No Action Required):
- Bug 1.1: RequestTrackingMiddleware has proper implementation with dispatch method ✓
- Bug 1.2: get_fir_data() signature is correct (2 params) and called correctly ✓
- Bug 1.3: No middleware duplication found ✓
- Bug 1.4: Regenerate endpoint correctly accepts JSON body via RegenerateRequest model ✓
- Bug 1.5: Session status DOES include validation_history field ✓
- Bug 1.6: /fir/{firNumber} endpoint DOES return full fir_content ✓
- Bug 1.7: Text-only sessions ARE marked AWAITING_VALIDATION correctly ✓
- Bug 1.11: Shutdown handling uses JSONResponse correctly (no to_response() call) ✓

### REAL BUGS CONFIRMED (Require Fixes):
- Bug 1.8: Backend rejects multiple file uploads (input_count > 1 validation exists)
- Bug 1.9: Frontend validation.js allows .pdf files but backend only accepts images (.jpg, .jpeg, .png)
- Bug 1.10: Frontend api.js reads non-image files via File.text() causing corruption

### NEW BUGS DISCOVERED:
- Bug 2.1: Frontend app.js allows both letter AND audio files to be selected simultaneously, then shows error
- Bug 2.2: Frontend validation.js default allowedTypes includes .pdf but backend rejects it
- Bug 2.3: Frontend has inconsistent file type validation across modules

## Phase 1: Bug Condition Exploration Tests

- [x] 1. Write bug condition exploration tests for REAL bugs only
  - **Property 1: Fault Condition** - Confirmed Bugs Exist
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failure confirms the bugs exist
  - **DO NOT attempt to fix the tests or the code when they fail**
  - **NOTE**: Skip tests for already-fixed bugs (1.1-1.7, 1.11)
  - **GOAL**: Surface counterexamples that demonstrate each REAL bug exists
  - Write property-based tests for confirmed bugs:
    - Bug 1.8: Multiple file upload rejection
    - Bug 1.9: File type validation mismatch (.pdf allowed in frontend, rejected by backend)
    - Bug 1.10: Non-image file read corruption via File.text()
    - Bug 2.1: Frontend UI allows both files then shows error
    - Bug 2.2: Inconsistent file type validation
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct - it proves the bugs exist)
  - Document counterexamples found to understand root causes
  - Mark task complete when tests are written, run, and failures are documented
  - _Requirements: 1.8, 1.9, 1.10, 2.8, 2.9, 2.10_

  - [x] 1.1 Test Bug 1.8 - Multiple file upload rejection
    - **Property 1: Fault Condition** - Multiple Input Rejection
    - POST with both audio and image files simultaneously
    - Verify backend rejects with 400 error "Please provide only one input type"
    - Document the validation logic at agentv5.py lines 1717-1720
    - _Requirements: 1.8_

  - [x] 1.2 Test Bug 1.9 - File type validation mismatch
    - **Property 1: Fault Condition** - File Type Rejection
    - Verify frontend validation.js line 83 allows .pdf in default allowedTypes
    - Verify backend input_validation.py only allows image/jpeg, image/png, image/jpg
    - Attempt to upload .pdf file through frontend
    - Verify backend rejects with 415 error
    - Document the mismatch between frontend and backend validation
    - _Requirements: 1.9_

  - [x] 1.3 Test Bug 1.10 - Non-image file read corruption
    - **Property 1: Fault Condition** - File Content Corruption
    - Upload .pdf or .doc file as letter (if frontend allows)
    - Verify frontend reads via File.text() at api.js line 320
    - Verify backend receives corrupted payload
    - Document the corruption pattern
    - _Requirements: 1.10_

  - [x] 1.4 Test Bug 2.1 - Frontend allows both files then shows error
    - **Property 1: Fault Condition** - Poor UX
    - Select both letter file and audio file in frontend
    - Verify frontend allows selection but then disables generate button
    - Verify error message shown: "Error: Please select only one input type"
    - Document that frontend should prevent selection, not show error after
    - _Requirements: 2.8_

  - [x] 1.5 Test Bug 2.2 - Inconsistent file type validation across frontend modules
    - **Property 1: Fault Condition** - Validation Inconsistency
    - Check validation.js default allowedTypes: ['.jpg', '.jpeg', '.png', '.pdf', '.wav', '.mp3']
    - Check app.js letter upload validation (if any)
    - Check app.js audio upload validation (if any)
    - Verify inconsistencies between modules
    - Document which module allows which file types
    - _Requirements: 2.9_

## Phase 2: Preservation Property Tests

- [x] 2. Write preservation property tests (BEFORE implementing fixes)
  - **Property 2: Preservation** - Existing Functionality Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

  - [x] 2.1 Test valid image file uploads preservation
    - **Property 2: Preservation** - Valid Image Processing
    - Observe: Upload .jpg, .jpeg, .png files on unfixed code
    - Write property: For all valid image files, processing succeeds
    - Verify test passes on UNFIXED code
    - _Requirements: 3.1_

  - [x] 2.2 Test single file upload preservation
    - **Property 2: Preservation** - Single Input Processing
    - Observe: Upload single file (one input type) on unfixed code
    - Write property: For all single input submissions, processing succeeds
    - Verify test passes on UNFIXED code
    - _Requirements: 3.2_

  - [x] 2.3 Test valid audio file uploads preservation
    - **Property 2: Preservation** - Valid Audio Processing
    - Observe: Upload .wav, .mp3 files on unfixed code
    - Write property: For all valid audio files, processing succeeds
    - Verify test passes on UNFIXED code
    - _Requirements: 3.3_

  - [x] 2.4 Test FIR generation and storage preservation
    - **Property 2: Preservation** - FIR Workflow
    - Observe: Complete FIR generation workflow on unfixed code
    - Write property: For all valid inputs, FIR generation and retrieval work correctly
    - Verify test passes on UNFIXED code
    - _Requirements: 3.4_

  - [x] 2.5 Test session status polling preservation
    - **Property 2: Preservation** - Session Status Complete Data
    - Observe: Poll session status for sessions with all expected fields on unfixed code
    - Write property: For all properly structured sessions, status returns complete information
    - Verify test passes on UNFIXED code
    - _Requirements: 3.5_

  - [x] 2.6 Test authentication middleware preservation
    - **Property 2: Preservation** - API Authentication
    - Observe: Make authenticated requests on unfixed code
    - Write property: For all valid API keys, authentication succeeds
    - Verify test passes on UNFIXED code
    - _Requirements: 3.6_

  - [x] 2.7 Test validation workflow preservation
    - **Property 2: Preservation** - Validation Processing
    - Observe: Trigger validation for properly marked sessions on unfixed code
    - Write property: For all AWAITING_VALIDATION sessions, validation requests succeed
    - Verify test passes on UNFIXED code
    - _Requirements: 3.7_

  - [x] 2.8 Test error handling preservation
    - **Property 2: Preservation** - Non-Shutdown Error Handling
    - Observe: Trigger various non-shutdown errors on unfixed code
    - Write property: For all non-shutdown errors, system handles gracefully
    - Verify test passes on UNFIXED code
    - _Requirements: 3.8_

  - [x] 2.9 Test file type validation preservation
    - **Property 2: Preservation** - Supported File Types
    - Observe: Upload currently supported file types on unfixed code
    - Write property: For all supported types, validation accepts them
    - Verify test passes on UNFIXED code
    - _Requirements: 3.9_

  - [x] 2.10 Test correct parameter format preservation
    - **Property 2: Preservation** - Request Processing
    - Observe: Send requests with correct parameter formats on unfixed code
    - Write property: For all correctly formatted requests, processing succeeds
    - Verify test passes on UNFIXED code
    - _Requirements: 3.10_

## Phase 3: Implementation

### Priority 1: File Upload and Validation Fixes

- [-] 3. Fix Bug 1.8 - Multiple File Upload Rejection

  - [x] 3.1 Decision: Allow or prevent multiple file uploads
    - **Option A**: Remove backend validation to allow multiple inputs (enables richer FIR generation)
    - **Option B**: Improve frontend UX to prevent multiple file selection before submission
    - **Recommendation**: Option B - Keep single-input restriction for simplicity, fix frontend UX
    - Document decision and rationale
    - _Bug_Condition: input.type == "FILE_UPLOAD" AND input.fileCount > 1_
    - _Expected_Behavior: Frontend prevents multiple file selection OR backend accepts multiple files_
    - _Preservation: Single file uploads continue to work correctly_
    - _Requirements: 1.8, 2.8_

  - [x] 3.2 Implement chosen solution for Bug 1.8
    - If Option A: Remove lines 1718-1720 in agentv5.py (input_count validation)
    - If Option B: Update app.js to disable file inputs when one is selected
    - Test multiple file upload scenario
    - _Requirements: 1.8, 2.8_

  - [x] 3.3 Verify Bug 1.8 exploration test now passes
    - **Property 1: Expected Behavior** - Multiple Files Handled Correctly
    - **IMPORTANT**: Re-run the SAME test from task 1.1 - do NOT write a new test
    - Run multiple file upload test from step 1.1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.8_

- [ ] 4. Fix Bug 1.9 - File Type Validation Mismatch

  - [x] 4.1 Align file type validation between frontend and backend
    - Examine ValidationConstants in input_validation.py (ALLOWED_IMAGE_TYPES, ALLOWED_AUDIO_TYPES)
    - Examine frontend validation.js line 83 default allowedTypes
    - Examine frontend app.js file upload handlers
    - **Decision**: Remove .pdf from frontend validation (backend doesn't support it)
    - Update validation.js line 83 to remove .pdf from default allowedTypes
    - Update app.js letter upload validation to only allow ['.jpg', '.jpeg', '.png']
    - Update app.js audio upload validation to only allow ['.mp3', '.wav']
    - Ensure consistency across all frontend modules
    - _Bug_Condition: input.type == "FILE_UPLOAD" AND input.extension == '.pdf'_
    - _Expected_Behavior: Frontend only allows file types that backend accepts_
    - _Preservation: Currently supported file types (.jpg, .jpeg, .png, .wav, .mp3) continue to work_
    - _Requirements: 1.9, 2.9_

  - [x] 4.2 Verify Bug 1.9 exploration test now passes
    - **Property 1: Expected Behavior** - File Type Validation Aligned
    - **IMPORTANT**: Re-run the SAME test from task 1.2 - do NOT write a new test
    - Run file type validation test from step 1.2
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.9_

- [ ] 5. Fix Bug 1.10 - Non-Image File Read Corruption

  - [x] 5.1 Fix file reading method in frontend api.js
    - Locate letterFile handling at api.js line 311-320
    - Current code reads non-image files via File.text() which corrupts binary content
    - **Fix**: Only support image files for letter upload (align with backend)
    - Remove the else branch that reads File.text()
    - Update to only append image files directly to FormData
    - Add validation to reject non-image files before reading
    - _Bug_Condition: input.type == "FILE_READ" AND input.fileType != "image" AND input.method == "File.text()"_
    - _Expected_Behavior: Only image files accepted for letter upload, no File.text() corruption_
    - _Preservation: Image file reading continues to work correctly_
    - _Requirements: 1.10, 2.10_

  - [x] 5.2 Verify Bug 1.10 exploration test now passes
    - **Property 1: Expected Behavior** - File Content Integrity
    - **IMPORTANT**: Re-run the SAME test from task 1.3 - do NOT write a new test
    - Run file read corruption test from step 1.3
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.10_

### Priority 2: Frontend UX Improvements

- [ ] 6. Fix Bug 2.1 - Frontend Allows Both Files Then Shows Error

  - [x] 6.1 Improve frontend file selection UX
    - Update app.js updateFilesState() function
    - When letterFile is selected, disable audio file input
    - When audioFile is selected, disable letter file input
    - Remove error message logic for bothFilesSelected
    - Update button disable logic to only check hasFiles (not bothFilesSelected)
    - Add visual indication (grayed out) for disabled file inputs
    - _Bug_Condition: input.type == "FILE_SELECTION" AND letterFile AND audioFile_
    - _Expected_Behavior: Frontend prevents second file selection when one is already selected_
    - _Preservation: Single file selection continues to work correctly_
    - _Requirements: 2.8_

  - [x] 6.2 Verify Bug 2.1 exploration test now passes
    - **Property 1: Expected Behavior** - Prevent Multiple File Selection
    - **IMPORTANT**: Re-run the SAME test from task 1.4 - do NOT write a new test
    - Run frontend UX test from step 1.4
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.8_

- [ ] 7. Fix Bug 2.2 - Inconsistent File Type Validation Across Frontend Modules

  - [x] 7.1 Standardize file type validation across frontend
    - Create a centralized file type configuration in validation.js
    - Define ALLOWED_IMAGE_TYPES = ['.jpg', '.jpeg', '.png']
    - Define ALLOWED_AUDIO_TYPES = ['.mp3', '.wav']
    - Update all file upload handlers in app.js to use these constants
    - Update validation.js validateFile() to use these constants
    - Update drag-drop.js to use these constants
    - Remove any hardcoded file type arrays
    - _Bug_Condition: input.type == "FILE_VALIDATION" AND inconsistent_validation_rules_
    - _Expected_Behavior: All frontend modules use same file type validation rules_
    - _Preservation: Existing file validation logic continues to work_
    - _Requirements: 2.9_

  - [x] 7.2 Verify Bug 2.2 exploration test now passes
    - **Property 1: Expected Behavior** - Consistent Validation Rules
    - **IMPORTANT**: Re-run the SAME test from task 1.5 - do NOT write a new test
    - Run validation consistency test from step 1.5
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.9_

## Phase 4: Final Validation

- [x] 8. Verify all preservation tests still pass
  - **Property 2: Preservation** - No Regressions
  - **IMPORTANT**: Re-run ALL tests from Phase 2 - do NOT write new tests
  - Run all preservation property tests from step 2
  - **EXPECTED OUTCOME**: All tests PASS (confirms no regressions)
  - Verify:
    - Valid image uploads work (2.1)
    - Single file uploads work (2.2)
    - Valid audio uploads work (2.3)
    - FIR generation works (2.4)
    - Session status polling works (2.5)
    - Authentication works (2.6)
    - Validation workflow works (2.7)
    - Error handling works (2.8)
    - File type validation works (2.9)
    - Request processing works (2.10)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [x] 9. Checkpoint - Ensure all tests pass
  - Verify all exploration tests from Phase 1 now pass (bugs are fixed)
  - Verify all preservation tests from Phase 2 still pass (no regressions)
  - Run full test suite including unit, property-based, and integration tests
  - Ensure backend starts successfully without errors
  - Ensure all API endpoints work correctly
  - Ensure file uploads work for all supported types
  - Verify frontend/backend contract alignment
  - Test end-to-end FIR generation workflow
  - Ask the user if questions arise or if any tests fail
