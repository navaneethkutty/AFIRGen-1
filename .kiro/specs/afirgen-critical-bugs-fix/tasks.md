# Implementation Plan

## Phase 1: Bug Condition Exploration Tests (BEFORE Fix)

### Critical Bugs

- [x] 1. Write bug condition exploration test for Critical Bug 1 - IndentationError
  - **Property 1: Fault Condition** - Backend Import Failure
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that importing agentv5.py module succeeds without IndentationError
  - Verify RequestTrackingMiddleware class has a properly defined body
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with IndentationError at line 1646 (this is correct - it proves the bug exists)
  - Document the exact IndentationError message and line number
  - _Requirements: 1.1, 2.1_

- [x] 2. Write bug condition exploration test for Critical Bug 2 - get_fir_data Signature Mismatch
  - **Property 1: Fault Condition** - Function Signature Mismatch
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that get_fir_data() can be called with two arguments (state_dict, fir_number)
  - Simulate FIR generation reaching FINAL_REVIEW step at line 1866
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with TypeError about argument count (this is correct - it proves the bug exists)
  - Document the exact TypeError message
  - _Requirements: 1.2, 2.2_


### High Priority Bugs

- [x] 3. Write bug condition exploration test for High Priority Bug 3 - Text-only Validation Flow
  - **Property 1: Fault Condition** - Text-only Session Status Not Set
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that POST /process with text-only input sets session status to AWAITING_VALIDATION
  - Verify session.status == SessionStatus.AWAITING_VALIDATION after text-only processing
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS because status is not set to AWAITING_VALIDATION (this is correct - it proves the bug exists)
  - Document the actual status value returned
  - _Requirements: 1.3, 2.3_

- [x] 4. Write bug condition exploration test for High Priority Bug 4 - Validation Endpoint Rejection
  - **Property 1: Fault Condition** - Validation Endpoint Rejects Text-only Sessions
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that POST /validate succeeds after text-only session creation
  - Create text-only session via /process, then call /validate
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with 400 error "Session not awaiting validation" (this is correct - it proves the bug exists)
  - Document the exact error response
  - _Requirements: 1.4, 2.4_

- [x] 5. Write bug condition exploration test for High Priority Bug 5 - Regenerate Endpoint Mismatch
  - **Property 1: Fault Condition** - Regenerate Parameter Passing Mismatch
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that POST /regenerate with JSON body {step, user_input} succeeds
  - Send request matching frontend format (JSON body, not query params)
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with 422 Unprocessable Entity or parameter binding error (this is correct - it proves the bug exists)
  - Document the exact error response
  - _Requirements: 1.5, 2.5_

- [x] 6. Write bug condition exploration test for High Priority Bug 6 - Session Polling Missing Fields
  - **Property 1: Fault Condition** - Status Response Missing validation_history
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that GET /session/{id}/status returns validation_history with content.fir_number
  - Create session, complete validation step, poll status
  - Verify response includes validation_history[-1].content.fir_number
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS because validation_history field is missing (this is correct - it proves the bug exists)
  - Document the actual response structure
  - _Requirements: 1.6, 2.6_

- [x] 7. Write bug condition exploration test for High Priority Bug 7 - Multiple File Upload Allowed
  - **Property 1: Fault Condition** - Frontend Allows Multiple File Selection
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that frontend prevents submission when both letter and audio files are selected
  - Simulate selecting both file types in UI
  - Verify generate button is disabled or validation error is shown
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS because frontend allows submission (this is correct - it proves the bug exists)
  - Document the actual frontend behavior
  - _Requirements: 1.7, 2.7_

- [x] 8. Write bug condition exploration test for High Priority Bug 8 - File Type Mismatch
  - **Property 1: Fault Condition** - Frontend/Backend File Type Mismatch
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that only mutually supported file types (.jpg, .jpeg, .png, .wav, .mp3) are accepted
  - Attempt to upload .pdf, .txt, .doc, .docx, .m4a, .ogg files
  - Verify frontend rejects these types before submission
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS because frontend accepts unsupported types (this is correct - it proves the bug exists)
  - Document which unsupported types are accepted by frontend
  - _Requirements: 1.8, 2.8_


### Medium Priority Bugs

- [x] 9. Write bug condition exploration test for Medium Priority Bug 9 - FIR Retrieval Endpoint Mismatch
  - **Property 1: Fault Condition** - FIR Endpoint Returns Metadata Only
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that GET /fir/{firNumber} returns full FIR content including fir_content field
  - Create completed FIR, retrieve via /fir/{firNumber}
  - Verify response includes full content, not just metadata
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS because response only contains metadata (this is correct - it proves the bug exists)
  - Document the actual response structure
  - _Requirements: 1.9, 2.9_

- [x] 10. Write bug condition exploration test for Medium Priority Bug 10 - Shutdown Handling Crash
  - **Property 1: Fault Condition** - Shutdown Error Response Crashes
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that RuntimeError with "shutting down" message returns proper 503 response
  - Trigger shutdown scenario in RequestTrackingMiddleware
  - Verify 503 JSONResponse is returned without crash
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with AttributeError on to_response() method (this is correct - it proves the bug exists)
  - Document the exact error message
  - _Requirements: 1.10, 2.10_

- [x] 11. Write bug condition exploration test for Medium Priority Bug 11 - Binary File Corruption
  - **Property 1: Fault Condition** - Binary Files Read as Text
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - Test that PDF/DOC files are read correctly without corruption
  - Upload binary file, verify data integrity
  - Check that File.arrayBuffer() or similar is used, not File.text()
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS because binary data is corrupted (this is correct - it proves the bug exists)
  - Document the corruption observed
  - _Requirements: 1.11, 2.11_


## Phase 2: Preservation Property Tests (BEFORE Fix)

- [x] 12. Write preservation property tests (BEFORE implementing fixes)
  - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (cases where isBugCondition returns false)
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  
  - [x] 12.1 Audio file processing preservation test
    - Test that valid .wav/.mp3 audio files continue to process correctly
    - Generate random valid audio files and verify processing succeeds
    - Verify processing pipeline, session creation, and status updates work as before
    - _Requirements: 3.1, 3.5_
  
  - [x] 12.2 Image file processing preservation test
    - Test that valid .jpg/.png image files continue to process correctly
    - Generate random valid image files and verify processing succeeds
    - Verify processing pipeline, session creation, and status updates work as before
    - _Requirements: 3.1, 3.4_
  
  - [x] 12.3 Audio/image validation flow preservation test
    - Test that validation workflow for audio/image inputs continues to work
    - Complete full validation workflow from AWAITING_VALIDATION to COMPLETED
    - Verify all validation steps (TRANSCRIPT_REVIEW, SUMMARY_REVIEW, etc.) work as before
    - _Requirements: 3.2, 3.12_
  
  - [x] 12.4 Authentication preservation test
    - Test that APIAuthMiddleware continues to enforce authentication
    - Generate random API requests with valid/invalid keys
    - Verify authentication behavior is unchanged
    - _Requirements: 3.7_
  
  - [x] 12.5 Health check preservation test
    - Test that /health endpoint continues to work without authentication
    - Verify health status response format is unchanged
    - _Requirements: 3.8_
  
  - [x] 12.6 Session status endpoint preservation test
    - Test that /status endpoint continues to return existing fields
    - Verify session_id, status, current_step, awaiting_validation, created_at, last_activity fields
    - Ensure new validation_history field doesn't break existing consumers
    - _Requirements: 3.3_
  
  - [x] 12.7 FIR generation quality preservation test
    - Test that FIR content generation quality and format remain unchanged
    - Generate random FIR data and verify output structure
    - Verify all FIR fields are populated correctly
    - _Requirements: 3.6_
  
  - [x] 12.8 Graceful shutdown preservation test
    - Test that graceful shutdown continues to track active requests
    - Verify shutdown waits for request completion
    - _Requirements: 3.9_
  
  - [x] 12.9 FIR retrieval preservation test
    - Test that FIR retrieval endpoints continue to return correct data
    - Verify /fir/{fir_number}/content endpoint still works
    - _Requirements: 3.10_
  
  - [x] 12.10 Frontend progress display preservation test
    - Test that frontend continues to show step-by-step progress updates
    - Verify progress indicators and status messages work as before
    - _Requirements: 3.11_


## Phase 3: Implementation

### Critical Bug Fixes

- [x] 13. Fix Critical Bug 1 - IndentationError in RequestTrackingMiddleware

  - [x] 13.1 Implement the fix
    - Add proper class body to RequestTrackingMiddleware at line 1646
    - Ensure dispatch method is properly indented within the class
    - Verify no empty class body exists
    - File: `AFIRGEN FINAL/main backend/agentv5.py`
    - _Bug_Condition: input.type == "IMPORT" AND input.module == "agentv5.py" AND RequestTrackingMiddleware.hasEmptyBody()_
    - _Expected_Behavior: Backend imports successfully without IndentationError_
    - _Preservation: All existing middleware functionality, authentication, metrics, and request tracking continue to work_
    - _Requirements: 1.1, 2.1, 3.7, 3.8, 3.9_

  - [x] 13.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Backend Import Success
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1_

  - [x] 13.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

- [x] 14. Fix Critical Bug 2 - get_fir_data Signature Mismatch

  - [x] 14.1 Implement the fix
    - Update get_fir_data function signature at line 223
    - Change from: `def get_fir_data(session_state: dict) -> dict:`
    - To: `def get_fir_data(session_state: dict, fir_number: str) -> dict:`
    - Update function body to use fir_number parameter instead of extracting from session_state
    - File: `AFIRGEN FINAL/main backend/agentv5.py`
    - _Bug_Condition: input.type == "FUNCTION_CALL" AND input.function == "get_fir_data" AND input.argCount == 2 AND functionDefinition.paramCount == 1_
    - _Expected_Behavior: get_fir_data executes successfully with two arguments_
    - _Preservation: All existing FIR generation functionality continues to work_
    - _Requirements: 1.2, 2.2, 3.6_

  - [x] 14.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Function Signature Match
    - **IMPORTANT**: Re-run the SAME test from task 2 - do NOT write a new test
    - Run bug condition exploration test from step 2
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.2_

  - [x] 14.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)


### High Priority Bug Fixes

- [x] 15. Fix High Priority Bug 3 - Text-only Validation Flow

  - [x] 15.1 Implement the fix
    - Add session status update in /process endpoint after line 1764
    - After: `state.awaiting_validation = True`
    - Add: `session_manager.set_session_status(state.session_id, SessionStatus.AWAITING_VALIDATION)`
    - File: `AFIRGEN FINAL/main backend/agentv5.py`
    - _Bug_Condition: input.type == "API_REQUEST" AND input.endpoint == "/process" AND input.hasTextOnly AND NOT session.status == AWAITING_VALIDATION_
    - _Expected_Behavior: Session status set to AWAITING_VALIDATION for text-only input_
    - _Preservation: Audio/image processing workflows continue to work unchanged_
    - _Requirements: 1.3, 2.3, 3.1, 3.2_

  - [x] 15.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Text-only Session Status Set
    - **IMPORTANT**: Re-run the SAME test from task 3 - do NOT write a new test
    - Run bug condition exploration test from step 3
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.3_

  - [x] 15.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 16. Fix High Priority Bug 4 - Validation Endpoint Rejection

  - [x] 16.1 Verify fix is complete
    - This bug is automatically fixed by Bug 3 fix (task 15)
    - No additional code changes needed
    - Validation endpoint will now accept text-only sessions because status is correctly set
    - _Bug_Condition: input.type == "API_REQUEST" AND input.endpoint == "/validate" AND session.createdViaTextOnly AND session.status != AWAITING_VALIDATION_
    - _Expected_Behavior: Validation endpoint accepts text-only sessions_
    - _Preservation: Audio/image validation workflows continue to work unchanged_
    - _Requirements: 1.4, 2.4, 3.2_

  - [x] 16.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Validation Endpoint Accepts Text-only Sessions
    - **IMPORTANT**: Re-run the SAME test from task 4 - do NOT write a new test
    - Run bug condition exploration test from step 4
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.4_

  - [x] 16.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 17. Fix High Priority Bug 5 - Regenerate Endpoint Mismatch

  - [x] 17.1 Implement the fix
    - Change regenerate endpoint to accept JSON body instead of query parameters
    - Update function signature at line 1962
    - Change from: `async def regenerate_step(session_id: str, step: ValidationStep, user_input: Optional[str] = None):`
    - To: `async def regenerate_step(session_id: str, regenerate_req: RegenerateRequest):`
    - Extract step and user_input from regenerate_req body
    - Update route decorator to: `@app.post("/regenerate/{session_id}")`
    - Define RegenerateRequest Pydantic model if not exists
    - File: `AFIRGEN FINAL/main backend/agentv5.py`
    - _Bug_Condition: input.type == "API_REQUEST" AND input.endpoint == "/regenerate" AND frontend.sendsJSONBody AND backend.expectsQueryParams_
    - _Expected_Behavior: Regenerate endpoint processes JSON body requests_
    - _Preservation: All existing regeneration functionality continues to work_
    - _Requirements: 1.5, 2.5_

  - [x] 17.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Regenerate Accepts JSON Body
    - **IMPORTANT**: Re-run the SAME test from task 5 - do NOT write a new test
    - Run bug condition exploration test from step 5
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.5_

  - [x] 17.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 18. Fix High Priority Bug 6 - Session Polling Missing Fields

  - [x] 18.1 Implement the fix
    - Enhance /status endpoint response at lines 1948-1956
    - Add validation_history field from session state
    - Ensure validation_history includes content with fir_number when available
    - Update response to include: `"validation_history": session["state"].get("validation_history", [])`
    - File: `AFIRGEN FINAL/main backend/agentv5.py`
    - _Bug_Condition: input.type == "API_REQUEST" AND input.endpoint == "/session/{id}/status" AND frontend.expects("validation_history[-1].content.fir_number") AND NOT response.includes("validation_history")_
    - _Expected_Behavior: Status endpoint returns validation_history with fir_number_
    - _Preservation: All existing status endpoint fields continue to be returned_
    - _Requirements: 1.6, 2.6, 3.3_

  - [x] 18.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Status Response Includes validation_history
    - **IMPORTANT**: Re-run the SAME test from task 6 - do NOT write a new test
    - Run bug condition exploration test from step 6
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.6_

  - [x] 18.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 19. Fix High Priority Bug 7 - Multiple File Upload Allowed

  - [x] 19.1 Implement the fix
    - Add client-side validation in updateFilesState function
    - After file selection, check if both letterFile and audioFile are non-null
    - If both are selected, disable generate button and show error message
    - Add: `if (letterFile && audioFile) { generateBtn.disabled = true; showToast("Please select only one input type", "error"); }`
    - File: `AFIRGEN FINAL/frontend/js/app.js`
    - _Bug_Condition: input.type == "FILE_UPLOAD" AND input.letterFile != NULL AND input.audioFile != NULL AND frontend.allowsSubmit_
    - _Expected_Behavior: Frontend prevents submission when both files selected_
    - _Preservation: Single file uploads continue to work unchanged_
    - _Requirements: 1.7, 2.7_

  - [x] 19.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Frontend Prevents Multiple File Selection
    - **IMPORTANT**: Re-run the SAME test from task 7 - do NOT write a new test
    - Run bug condition exploration test from step 7
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.7_

  - [x] 19.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 20. Fix High Priority Bug 8 - File Type Mismatch

  - [x] 20.1 Implement backend fix
    - Remove unsupported file types from ValidationConstants
    - Keep only: {".jpg", ".jpeg", ".png", ".wav", ".mp3", ".mpeg"}
    - Update ALLOWED_IMAGE_TYPES to: {".jpg", ".jpeg", ".png"}
    - Update ALLOWED_AUDIO_TYPES to: {".wav", ".mp3", ".mpeg"}
    - File: `AFIRGEN FINAL/main backend/infrastructure/input_validation.py`
    - _Bug_Condition: input.type == "FILE_UPLOAD" AND input.fileType IN [".pdf", ".txt", ".doc", ".docx", ".m4a", ".ogg"] AND frontend.accepts AND NOT backend.accepts_
    - _Expected_Behavior: Only mutually supported file types accepted_
    - _Preservation: Existing supported file types (.jpg, .png, .wav, .mp3) continue to work_
    - _Requirements: 1.8, 2.8, 3.4, 3.5_

  - [x] 20.2 Implement frontend fix
    - Remove unsupported file types from frontend validation
    - Line 399: Change allowedTypes to: `['.jpg', '.jpeg', '.png']`
    - Line 437: Change allowedTypes to: `['.mp3', '.wav']`
    - File: `AFIRGEN FINAL/frontend/js/app.js`
    - _Requirements: 1.8, 2.8_

  - [x] 20.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Only Supported File Types Accepted
    - **IMPORTANT**: Re-run the SAME test from task 8 - do NOT write a new test
    - Run bug condition exploration test from step 8
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.8_

  - [x] 20.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)


### Medium Priority Bug Fixes

- [x] 21. Fix Medium Priority Bug 9 - FIR Retrieval Endpoint Mismatch

  - [x] 21.1 Implement the fix
    - Modify /fir/{firNumber} endpoint to return full FIR content
    - Add fir_content field to response (currently only returns metadata)
    - Option A (recommended): Change backend endpoint to include full content
    - Option B: Change frontend to call /fir/{fir_number}/content endpoint instead
    - Implement Option A for backward compatibility
    - File: `AFIRGEN FINAL/main backend/agentv5.py`
    - _Bug_Condition: input.type == "API_REQUEST" AND input.endpoint == "/fir/{firNumber}" AND frontend.expectsFullContent AND backend.returnsMetadataOnly_
    - _Expected_Behavior: FIR endpoint returns full content including fir_content field_
    - _Preservation: /fir/{fir_number}/content endpoint continues to work, existing metadata fields continue to be returned_
    - _Requirements: 1.9, 2.9, 3.10_

  - [x] 21.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - FIR Endpoint Returns Full Content
    - **IMPORTANT**: Re-run the SAME test from task 9 - do NOT write a new test
    - Run bug condition exploration test from step 9
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.9_

  - [x] 21.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 22. Fix Medium Priority Bug 10 - Shutdown Handling Crash

  - [x] 22.1 Implement the fix
    - Replace HTTPException.to_response() with proper response object at line 1676
    - Change from: `return HTTPException(status_code=503, detail="Server is shutting down").to_response()`
    - To: `from fastapi.responses import JSONResponse; return JSONResponse(status_code=503, content={"detail": "Server is shutting down"})`
    - File: `AFIRGEN FINAL/main backend/agentv5.py`
    - _Bug_Condition: input.type == "EXCEPTION" AND input.exception == "RuntimeError" AND input.message.contains("shutting down") AND HTTPException.hasNoMethod("to_response")_
    - _Expected_Behavior: Shutdown error returns proper 503 JSONResponse_
    - _Preservation: All existing error handling and graceful shutdown functionality continues to work_
    - _Requirements: 1.10, 2.10, 3.9_

  - [x] 22.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Shutdown Returns 503 Response
    - **IMPORTANT**: Re-run the SAME test from task 10 - do NOT write a new test
    - Run bug condition exploration test from step 10
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.10_

  - [x] 22.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)

- [x] 23. Fix Medium Priority Bug 11 - Binary File Corruption

  - [x] 23.1 Implement the fix
    - Change file reading method for binary files in frontend
    - Line 313: Check file type first before reading
    - For binary files (PDF, DOC), use: `const buffer = await letterFile.arrayBuffer();`
    - For text files, keep: `const text = await letterFile.text();`
    - Note: After Bug 8 fix, PDF/DOC files are no longer accepted, but implement proper handling for good practice
    - File: `AFIRGEN FINAL/frontend/js/api.js`
    - _Bug_Condition: input.type == "FILE_READ" AND input.fileType IN [".pdf", ".doc"] AND frontend.usesTextMethod_
    - _Expected_Behavior: Binary files read correctly using arrayBuffer() method_
    - _Preservation: Text file reading continues to work unchanged_
    - _Requirements: 1.11, 2.11_

  - [x] 23.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Binary Files Read Correctly
    - **IMPORTANT**: Re-run the SAME test from task 11 - do NOT write a new test
    - Run bug condition exploration test from step 11
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.11_

  - [x] 23.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Input Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 12 - do NOT write new tests
    - Run preservation property tests from step 12
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)


## Phase 4: Final Validation

- [x] 24. Checkpoint - Ensure all tests pass
  - Run all bug condition exploration tests (tasks 1-11) - all should PASS
  - Run all preservation property tests (task 12) - all should PASS
  - Verify no regressions in existing functionality
  - Confirm all 11 bugs are fixed
  - Ask the user if questions arise

## Phase 5: Integration Testing

- [x] 25. Run integration tests

  - [x] 25.1 Test complete text-only FIR generation flow
    - POST /process with text input
    - Verify session status is AWAITING_VALIDATION
    - POST /validate to proceed through validation steps
    - Poll /session/{id}/status and verify validation_history is returned
    - Complete all validation steps
    - Retrieve FIR via /fir/{firNumber} and verify full content is returned
    - _Requirements: 2.3, 2.4, 2.6, 2.9_

  - [x] 25.2 Test complete audio file FIR generation flow
    - Upload valid .wav or .mp3 audio file
    - Verify processing succeeds
    - Complete validation workflow
    - Verify FIR generation completes successfully
    - _Requirements: 3.1, 3.5, 3.6_

  - [x] 25.3 Test complete image file FIR generation flow
    - Upload valid .jpg or .png image file
    - Verify processing succeeds
    - Complete validation workflow
    - Verify FIR generation completes successfully
    - _Requirements: 3.1, 3.4, 3.6_

  - [x] 25.4 Test regeneration workflow
    - Create session and reach validation step
    - POST /regenerate with JSON body
    - Verify regeneration succeeds
    - _Requirements: 2.5_

  - [x] 25.5 Test file upload validation
    - Attempt to select both letter and audio files
    - Verify frontend prevents submission
    - Attempt to upload unsupported file types (.pdf, .m4a)
    - Verify frontend rejects them
    - _Requirements: 2.7, 2.8_

  - [x] 25.6 Test graceful shutdown
    - Initiate shutdown during active request
    - Verify 503 response is returned properly
    - Verify no crashes occur
    - _Requirements: 2.10, 3.9_

  - [x] 25.7 Test authentication and health check
    - Verify API authentication continues to work
    - Verify /health endpoint works without authentication
    - _Requirements: 3.7, 3.8_

- [x] 26. Final checkpoint - Production readiness verification
  - Verify all 11 bugs are fixed and validated
  - Verify all preservation tests pass (no regressions)
  - Verify all integration tests pass
  - Confirm system is ready for production deployment
  - Document any remaining issues or follow-up tasks

