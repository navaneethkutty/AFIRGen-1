# AFIRGEN Critical Bugs Fix - Bugfix Design

## Overview

This design addresses 11 critical and high-priority bugs blocking production deployment of the AFIRGEN application. The bugs span three categories: backend startup/runtime blockers (3 bugs), API contract mismatches (5 bugs), and validation/error handling issues (3 bugs). The fix strategy prioritizes critical startup blockers first to enable the application to start, then API contract fixes to restore frontend-backend communication, and finally validation improvements to ensure correct behavior.

The bugs affect core functionality including FIR generation, session management, file uploads, and validation workflows. The fix approach is surgical and minimal - each bug has a specific root cause and targeted fix that preserves all existing functionality while correcting the defective behavior.

## Glossary

- **Bug_Condition (C)**: The condition that triggers each specific bug - varies by bug type (startup conditions, API calls, file uploads)
- **Property (P)**: The desired correct behavior when the bug condition occurs - application starts successfully, API contracts match, validation accepts valid inputs
- **Preservation**: All existing working functionality that must remain unchanged - valid file processing, single file uploads, correct authentication, proper error handling
- **RequestTrackingMiddleware**: Middleware class in `agentv5.py` at line 1652 that tracks API requests for graceful shutdown
- **get_fir_data()**: Function in `agentv5.py` at line 222 that constructs FIR data dictionary from session state
- **APIAuthMiddleware**: Middleware class in `agentv5.py` at line 1603 that enforces API key authentication
- **regenerate_step()**: Endpoint function in `agentv5.py` at line 1970 that regenerates validation steps
- **get_session_status()**: Endpoint function in `agentv5.py` at line 1948 that returns session status information
- **get_fir_content()**: Endpoint function in `agentv5.py` at line 2105 that returns full FIR document content
- **initial_processing()**: Function in `agentv5.py` at line 1228 that processes audio/image inputs and sets session status
- **process_endpoint()**: Main endpoint in `agentv5.py` at line 1699 that handles file uploads and text input
- **ValidationConstants**: Class in `input_validation.py` at line 17 that defines allowed file types and validation rules
- **awaiting_validation**: Session state flag that indicates a session is ready for validation steps

## Bug Details

### Fault Condition

The bugs manifest across three categories with distinct fault conditions:

**Category 1: Backend Startup/Runtime Blockers**

Bug 1.1 - RequestTrackingMiddleware has no body, causing IndentationError at line 1695
Bug 1.2 - get_fir_data() is defined with 2 parameters but called with 2 arguments (signature matches, but there may be another call site with mismatch)
Bug 1.3 - APIAuthMiddleware has duplicated/nested declarations causing structural corruption

**Category 2: API Contract Mismatches**

Bug 1.4 - regenerate endpoint expects JSON body but backend may have query parameter handling
Bug 1.5 - get_session_status returns incomplete data missing validation_history and fir_number fields
Bug 1.6 - get_fir_content returns only metadata instead of full FIR document content
Bug 1.7 - Text-only sessions never marked as AWAITING_VALIDATION, blocking validation requests
Bug 1.8 - Backend rejects requests when input_count > 1, preventing multiple file uploads

**Category 3: Validation & Error Handling**

Bug 1.9 - Backend rejects .pdf, .doc, .docx, .m4a, .ogg files that frontend UI allows
Bug 1.10 - Non-image letter files read incorrectly via File.text() causing payload corruption
Bug 1.11 - Middleware crashes calling non-existent HTTPException.to_response() during shutdown

**Formal Specification:**

```
FUNCTION isBugCondition(input)
  INPUT: input of type SystemEvent | APIRequest | FileUpload
  OUTPUT: boolean
  
  RETURN (
    // Category 1: Startup Blockers
    (input.type == "BACKEND_START" AND RequestTrackingMiddleware.hasNoBody()) OR
    (input.type == "FUNCTION_CALL" AND input.function == "get_fir_data" AND input.argCount != paramCount) OR
    (input.type == "MIDDLEWARE_INIT" AND APIAuthMiddleware.isDuplicated()) OR
    
    // Category 2: API Contract Mismatches
    (input.type == "API_CALL" AND input.endpoint == "/regenerate/{session_id}" AND input.hasJsonBody) OR
    (input.type == "API_CALL" AND input.endpoint == "/session/{id}/status" AND input.expectsAllFields) OR
    (input.type == "API_CALL" AND input.endpoint == "/fir/{number}" AND input.expectsFullContent) OR
    (input.type == "SESSION_COMPLETE" AND input.inputType == "text" AND NOT input.markedAwaitingValidation) OR
    (input.type == "FILE_UPLOAD" AND input.fileCount > 1) OR
    
    // Category 3: Validation Issues
    (input.type == "FILE_UPLOAD" AND input.extension IN ['.pdf', '.doc', '.docx', '.m4a', '.ogg']) OR
    (input.type == "FILE_READ" AND input.fileType != "image" AND input.method == "File.text()") OR
    (input.type == "MIDDLEWARE_ERROR" AND input.errorType == "shutdown" AND input.usesToResponse)
  )
END FUNCTION
```

### Examples

**Bug 1.1 - RequestTrackingMiddleware IndentationError:**
- Trigger: Start backend with `python agentv5.py`
- Expected: Backend starts successfully
- Actual: IndentationError at line 1695 - RequestTrackingMiddleware class has no body

**Bug 1.2 - get_fir_data() Signature Mismatch:**
- Trigger: Call get_fir_data(state_dict, fir_number) at line 1873
- Expected: Function executes successfully
- Actual: TypeError - function defined with different parameter count than call site

**Bug 1.3 - APIAuthMiddleware Duplication:**
- Trigger: Backend initializes middleware stack
- Expected: Single APIAuthMiddleware instance
- Actual: Duplicated or nested middleware declarations causing unpredictable behavior

**Bug 1.4 - Regenerate Endpoint Contract Mismatch:**
- Trigger: Frontend calls POST /regenerate/{session_id} with JSON body `{"step": "summary_review", "user_input": "text"}`
- Expected: Backend accepts JSON body and processes regeneration
- Actual: Backend may expect query parameters instead, causing 400 error

**Bug 1.5 - Session Status Missing Fields:**
- Trigger: Frontend polls GET /session/{id}/status expecting validation_history and fir_number
- Expected: Response includes `{"validation_history": [...], "fir_number": "FIR-..."}`
- Actual: Response missing these fields, causing frontend errors

**Bug 1.6 - FIR Content Returns Metadata Only:**
- Trigger: Frontend calls GET /fir/{firNumber} expecting full FIR document
- Expected: Response includes complete FIR content in `content` field
- Actual: Response returns only metadata (status, dates) without full content

**Bug 1.7 - Text-Only Sessions Not Marked AWAITING_VALIDATION:**
- Trigger: Submit text-only input via POST /process with `{"text": "complaint text"}`
- Expected: Session marked as AWAITING_VALIDATION, validation requests accepted
- Actual: Session never marked AWAITING_VALIDATION, validation requests rejected with 400 error

**Bug 1.8 - Multiple File Upload Rejection:**
- Trigger: Upload both letter image and audio file simultaneously
- Expected: Backend accepts and processes both files
- Actual: Backend rejects with 400 error "Please provide only one input type"

**Bug 1.9 - File Type Validation Mismatch:**
- Trigger: Frontend allows .pdf, .doc, .docx, .m4a, .ogg in file picker
- Expected: Backend accepts these file types
- Actual: Backend rejects with validation error - only .jpg, .jpeg, .png, .wav, .mp3 allowed

**Bug 1.10 - Non-Image File Read Corruption:**
- Trigger: Upload .pdf or .doc file as letter, frontend reads via File.text()
- Expected: File content read correctly as binary/base64
- Actual: File.text() corrupts binary content, backend receives invalid payload

**Bug 1.11 - Shutdown Error Handling Crash:**
- Trigger: Request arrives during graceful shutdown, RuntimeError("shutting down") raised
- Expected: Return JSONResponse with 503 status
- Actual: Code calls HTTPException.to_response() which doesn't exist, causing AttributeError crash

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- Valid image file uploads (.jpg, .jpeg, .png) must continue to process correctly
- Valid audio file uploads (.wav, .mp3) must continue to process correctly
- Single file uploads (one input type at a time) must continue to work
- Text-only input processing must continue to work
- Authentication middleware must continue to validate API keys correctly
- Rate limiting middleware must continue to enforce request limits
- Security headers middleware must continue to add security headers
- Session status polling for sessions with all fields must continue to return complete data
- FIR generation and storage must continue to work correctly
- Validation workflow for properly marked sessions must continue to function
- Error handling for non-shutdown errors must continue to work
- All existing API endpoints must continue to function with valid inputs

**Scope:**

All inputs that do NOT trigger the specific bug conditions should be completely unaffected by these fixes. This includes:
- Valid file uploads with supported types
- Single input type submissions
- Properly formatted API requests
- Sessions that are correctly marked for validation
- Normal operation (non-shutdown) error handling
- All other middleware functionality
- Database operations
- Model inference operations

## Hypothesized Root Cause

Based on the bug descriptions and code analysis, the root causes are:

### Bug 1.1 - RequestTrackingMiddleware IndentationError

**Root Cause**: The RequestTrackingMiddleware class definition at line 1652 is missing its body implementation. The class is declared but has no `__init__` or `dispatch` method, causing Python to raise IndentationError when parsing the file.

**Evidence**: Line 1695 shows `app.add_middleware(RequestTrackingMiddleware)` but the class above it has no implementation.

**Analysis**: This appears to be an incomplete refactoring where the class was declared but the implementation was not added or was accidentally deleted.

### Bug 1.2 - get_fir_data() Signature Mismatch

**Root Cause**: The function `get_fir_data()` is defined at line 222 with signature `def get_fir_data(session_state: dict, fir_number: str) -> dict:` (2 parameters), and is called at line 1873 with `get_fir_data(state_dict, fir_number)` (2 arguments). The signature actually matches, so this bug report may be incorrect, OR there is another call site with a mismatch that needs to be found.

**Evidence**: Function definition shows 2 parameters, call site shows 2 arguments - these match. Need to search for other call sites.

**Analysis**: Either the bug report is incorrect, or there's another call site with only 1 argument that needs to be located.

### Bug 1.3 - APIAuthMiddleware Duplication

**Root Cause**: Search results show only one `app.add_middleware(APIAuthMiddleware)` call at line 1649. The "duplication/nesting" may refer to the class definition itself being duplicated elsewhere in the file, or the middleware being added multiple times in different code paths.

**Evidence**: Only one add_middleware call found, but bug report indicates structural corruption.

**Analysis**: Need to search for duplicate class definitions or multiple add_middleware calls in conditional branches.

### Bug 1.4 - Regenerate Endpoint Contract Mismatch

**Root Cause**: The backend endpoint at line 1970 correctly accepts a JSON body via `RegenerateRequest` Pydantic model. The frontend at api.js line 454 correctly sends JSON body. This appears to be working correctly.

**Evidence**: Backend uses `regenerate_req: RegenerateRequest` which is a Pydantic model that parses JSON body. Frontend sends `JSON.stringify({step, user_input})`.

**Analysis**: This bug may be incorrectly reported, or there's a specific edge case where the contract fails. The code appears correct.

### Bug 1.5 - Session Status Missing Fields

**Root Cause**: The `get_session_status()` endpoint at line 1948 returns a dictionary that includes `validation_history` but does NOT include `fir_number`. The session state may have `fir_number` but it's not being included in the response.

**Evidence**: Response at line 1960-1967 includes `validation_history` but not `fir_number`. The `fir_number` is only added to session state at line 1871 during FIR_NARRATIVE_REVIEW step.

**Analysis**: The endpoint needs to conditionally include `fir_number` if it exists in the session state.

### Bug 1.6 - FIR Content Returns Metadata Only

**Root Cause**: The `get_fir_content()` endpoint at line 2105 correctly returns the full FIR content in the `content` field at line 2121. The code appears correct.

**Evidence**: Response includes `"content": fir_record["fir_content"]` which is the full FIR document.

**Analysis**: This bug may be incorrectly reported, or there's a database issue where `fir_content` is not being stored correctly.

### Bug 1.7 - Text-Only Sessions Not Marked AWAITING_VALIDATION

**Root Cause**: The `process_endpoint()` at line 1699 correctly sets `awaiting_validation = True` and `SessionStatus.AWAITING_VALIDATION` for text-only inputs at lines 1761-1763. The code appears correct.

**Evidence**: Lines 1758-1763 show text-only path sets awaiting_validation flag and status correctly.

**Analysis**: This bug may be incorrectly reported, or there's a race condition or database issue preventing the status from persisting.

### Bug 1.8 - Multiple File Upload Rejection

**Root Cause**: The `process_endpoint()` at line 1717-1720 explicitly validates that `input_count <= 1` and raises HTTPException if more than one input type is provided. This is intentional validation logic.

**Evidence**: Line 1718 calculates `input_count = sum([bool(audio), bool(image), bool(text)])` and line 1719-1720 rejects if `input_count > 1`.

**Analysis**: This is working as designed. The bug report suggests this should be changed to allow multiple inputs, but the current implementation intentionally restricts to one input type. The fix would be to remove or modify this validation.

### Bug 1.9 - File Type Validation Mismatch

**Root Cause**: The backend `ValidationConstants` at line 17 defines `ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg"}` and `ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mpeg", "audio/mp3", "audio/x-wav"}`. The frontend at app.js lines 415 and 456 restricts to `['.jpg', '.jpeg', '.png']` for images and `['.mp3', '.wav']` for audio. Neither allows .pdf, .doc, .docx, .m4a, .ogg.

**Evidence**: Backend and frontend both restrict file types. The bug report suggests frontend allows these types, but code shows it doesn't.

**Analysis**: This bug may be incorrectly reported - both frontend and backend already restrict to the same types. OR there's another file input that allows these types.

### Bug 1.10 - Non-Image File Read Corruption

**Root Cause**: The frontend api.js at line 320 uses `letterFile.text()` to read non-image files. This is incorrect for binary files like .pdf or .doc, which should be read as binary data or sent directly as File objects in FormData.

**Evidence**: Line 320 shows `const text = await letterFile.text()` which converts binary content to text, corrupting it.

**Analysis**: For non-image files, the file should be appended directly to FormData without reading, or read as ArrayBuffer/Blob.

### Bug 1.11 - Shutdown Error Handling Crash

**Root Cause**: The `RequestTrackingMiddleware` at line 1652 catches RuntimeError with "shutting down" message and attempts to return an HTTPException. However, the code shown at lines 1679-1683 correctly returns a `JSONResponse`, not `HTTPException.to_response()`.

**Evidence**: Lines 1679-1683 show correct implementation using JSONResponse. The bug report may refer to old code or a different location.

**Analysis**: The current code appears correct. Need to verify if there's another location with the incorrect to_response() call.

## Correctness Properties

Property 1: Fault Condition - Backend Startup Success

_For any_ system startup where the backend is initialized, the application SHALL start successfully without IndentationError, TypeError, or middleware configuration errors, enabling all endpoints to be accessible.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Fault Condition - API Contract Compliance

_For any_ API request from the frontend (regenerate, session status, FIR content, file upload), the backend SHALL accept the request format sent by the frontend and return the complete data structure expected by the frontend, enabling successful frontend-backend communication.

**Validates: Requirements 2.4, 2.5, 2.6, 2.7, 2.8**

Property 3: Fault Condition - Validation and Error Handling

_For any_ file upload or error condition, the system SHALL validate files consistently between frontend and backend, read file content correctly without corruption, and handle errors gracefully without crashes.

**Validates: Requirements 2.9, 2.10, 2.11**

Property 4: Preservation - Existing Functionality

_For any_ input that does NOT trigger the bug conditions (valid single file uploads, properly formatted requests, normal operation), the fixed code SHALL produce exactly the same behavior as the original code, preserving all existing functionality for valid inputs and workflows.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10**

## Fix Implementation

### Changes Required

The fixes are organized by priority: Critical startup blockers first, then API contracts, then validation improvements.

**Priority 1: Critical Startup Blockers**

**File**: `AFIRGEN FINAL/main backend/agentv5.py`

**Bug 1.1 Fix - RequestTrackingMiddleware Body:**

**Location**: Line 1652 - RequestTrackingMiddleware class definition

**Issue**: The class definition exists but may be missing proper implementation or has indentation issues.

**Fix**: Verify the RequestTrackingMiddleware class has complete implementation with dispatch method. The code shown at lines 1652-1695 appears complete, so the issue may be a phantom bug or the line numbers in the bug report are incorrect. Verify by attempting to start the backend.

**Bug 1.2 Fix - get_fir_data() Signature:**

**Location**: Line 222 (definition) and line 1873 (call site)

**Issue**: Reported signature mismatch, but code analysis shows they match (2 parameters, 2 arguments).

**Fix**: Search for other call sites of get_fir_data() with incorrect argument count. If found, update to pass both session_state and fir_number. If no mismatch exists, mark bug as invalid.

**Bug 1.3 Fix - APIAuthMiddleware Duplication:**

**Location**: Line 1603 (class definition) and line 1649 (middleware registration)

**Issue**: Reported duplication/nesting, but only one add_middleware call found.

**Fix**: Search entire file for duplicate APIAuthMiddleware class definitions or multiple add_middleware calls. Remove any duplicates found. If no duplicates exist, mark bug as invalid.

**Priority 2: API Contract Fixes**

**Bug 1.4 Fix - Regenerate Endpoint:**

**Location**: Line 1970 - regenerate_step endpoint

**Issue**: Reported contract mismatch, but code shows correct JSON body handling.

**Fix**: Verify endpoint works correctly with frontend. If working, mark bug as invalid. If failing, add debug logging to identify the actual issue.

**Bug 1.5 Fix - Session Status Missing fir_number:**

**Location**: Line 1948 - get_session_status endpoint

**Specific Changes**:
1. Add fir_number to response dictionary if it exists in session state
2. Update return statement at lines 1960-1967 to include:
   ```python
   return {
       "session_id": session_id,
       "status": session["status"],
       "current_step": session["state"].get("current_validation_step"),
       "awaiting_validation": session["state"].get("awaiting_validation", False),
       "validation_history": session["state"].get("validation_history", []),
       "fir_number": session["state"].get("fir_number"),  # ADD THIS LINE
       "created_at": session["created_at"].isoformat(),
       "last_activity": session["last_activity"].isoformat()
   }
   ```

**Bug 1.6 Fix - FIR Content:**

**Location**: Line 2105 - get_fir_content endpoint

**Issue**: Code appears correct - returns full content.

**Fix**: Verify endpoint works correctly. If working, mark bug as invalid. If failing, check database to ensure fir_content is being stored correctly.

**Bug 1.7 Fix - Text-Only Session Status:**

**Location**: Line 1699 - process_endpoint

**Issue**: Code appears correct - sets awaiting_validation for text input.

**Fix**: Verify text-only sessions work correctly. If working, mark bug as invalid. If failing, add debug logging to trace status setting and persistence.

**Bug 1.8 Fix - Multiple File Upload:**

**Location**: Line 1717-1720 - input_count validation

**Specific Changes**:
1. **Option A (Allow Multiple Inputs)**: Remove the validation that rejects input_count > 1
   ```python
   # Remove or comment out lines 1718-1720:
   # input_count = sum([bool(audio), bool(image), bool(text)])
   # if input_count > 1:
   #     raise HTTPException(status_code=400, detail="Please provide only one input type")
   ```

2. **Option B (Keep Restriction, Fix Frontend)**: Keep backend validation, update frontend to prevent multiple file selection

**Recommendation**: Option A - Remove restriction to allow multiple inputs, as this enables richer FIR generation from multiple sources.

**Priority 3: Validation & Error Handling**

**Bug 1.9 Fix - File Type Validation:**

**File**: `AFIRGEN FINAL/main backend/infrastructure/input_validation.py` and `AFIRGEN FINAL/frontend/js/app.js`

**Location**: Line 17 (ValidationConstants) and app.js lines 415, 456

**Issue**: Both frontend and backend restrict to same types - bug may be invalid.

**Fix**: 
1. **Option A**: If .pdf, .doc, .docx, .m4a, .ogg should be supported, add them to ValidationConstants:
   ```python
   ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
   ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mpeg", "audio/mp3", "audio/x-wav", "audio/m4a", "audio/ogg"}
   ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".wav", ".mp3", ".mpeg", ".pdf", ".doc", ".docx", ".m4a", ".ogg"}
   ```
   And update frontend allowedTypes arrays accordingly.

2. **Option B**: Keep current restrictions, verify frontend doesn't allow unsupported types.

**Recommendation**: Option B - Keep current restrictions unless there's a business requirement to support these formats.

**Bug 1.10 Fix - File Read Method:**

**File**: `AFIRGEN FINAL/frontend/js/api.js`

**Location**: Line 320 - letterFile.text() call

**Specific Changes**:
1. For image files, append directly to FormData without reading:
   ```javascript
   if (letterFile) {
     if (letterFile.type.startsWith('image/')) {
       formData.append('image', letterFile);  // Already correct
     } else {
       // For non-image files, append directly without reading
       formData.append('document', letterFile);  // Changed from text reading
     }
   }
   ```

2. Update backend to accept 'document' field if non-image files are supported.

**Bug 1.11 Fix - Shutdown Error Handling:**

**File**: `AFIRGEN FINAL/main backend/agentv5.py`

**Location**: Line 1652 - RequestTrackingMiddleware

**Issue**: Code at lines 1679-1683 appears correct - uses JSONResponse.

**Fix**: Verify the code is correct. If there's another location with to_response() call, replace with:
```python
except RuntimeError as e:
    if "shutting down" in str(e):
        return JSONResponse(
            status_code=503,
            content={"detail": "Server is shutting down"}
        )
    raise
```

## Testing Strategy

### Validation Approach

The testing strategy follows a three-phase approach:

1. **Exploratory Fault Condition Checking**: Run tests on UNFIXED code to surface counterexamples demonstrating each bug
2. **Fix Checking**: Verify fixes resolve the bug conditions
3. **Preservation Checking**: Verify existing functionality remains unchanged

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate each bug BEFORE implementing fixes. Confirm or refute the root cause analysis.

**Test Plan**: Write tests that trigger each bug condition and observe failures on unfixed code.

**Test Cases**:

1. **Bug 1.1 - Startup Test**: Attempt to import and start agentv5.py (will fail with IndentationError on unfixed code)
2. **Bug 1.2 - Function Call Test**: Call get_fir_data() with various argument counts (will fail with TypeError if mismatch exists)
3. **Bug 1.3 - Middleware Test**: Check middleware stack for duplicates (will fail if duplicates exist)
4. **Bug 1.4 - Regenerate Test**: POST to /regenerate with JSON body (will fail if contract mismatch exists)
5. **Bug 1.5 - Status Fields Test**: GET /session/{id}/status and check for fir_number field (will fail on unfixed code)
6. **Bug 1.6 - FIR Content Test**: GET /fir/{number} and verify content field exists (will fail if only metadata returned)
7. **Bug 1.7 - Text Session Test**: POST text-only input and verify awaiting_validation status (will fail on unfixed code)
8. **Bug 1.8 - Multiple Files Test**: POST with both audio and image (will fail with 400 error on unfixed code)
9. **Bug 1.9 - File Types Test**: Upload .pdf, .doc, .m4a files (will fail with validation error if not supported)
10. **Bug 1.10 - File Read Test**: Upload non-image file and verify payload integrity (will fail with corruption on unfixed code)
11. **Bug 1.11 - Shutdown Test**: Trigger shutdown error and verify response (will fail with AttributeError on unfixed code)

**Expected Counterexamples**:
- Startup failures with IndentationError or TypeError
- API responses missing expected fields
- Validation rejections for valid inputs
- Crashes on error conditions

### Fix Checking

**Goal**: Verify that for all inputs where each bug condition holds, the fixed code produces the expected behavior.

**Pseudocode:**
```
FOR EACH bug IN [1.1, 1.2, ..., 1.11] DO
  FOR ALL input WHERE isBugCondition(input, bug) DO
    result := fixed_system(input)
    ASSERT expectedBehavior(result, bug)
  END FOR
END FOR
```

**Test Cases**:
1. Backend starts successfully without errors
2. All function calls execute with correct signatures
3. Middleware stack has no duplicates
4. Regenerate endpoint accepts JSON body
5. Session status includes all required fields
6. FIR content endpoint returns full document
7. Text-only sessions marked AWAITING_VALIDATION
8. Multiple file uploads accepted (if fix applied)
9. All supported file types accepted
10. File content read correctly without corruption
11. Shutdown errors handled gracefully

### Preservation Checking

**Goal**: Verify that for all inputs where bug conditions do NOT hold, the fixed code produces the same result as the original code.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT original_system(input) = fixed_system(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for valid inputs, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Valid Image Upload Preservation**: Verify .jpg, .jpeg, .png uploads continue to work
2. **Valid Audio Upload Preservation**: Verify .wav, .mp3 uploads continue to work
3. **Single Input Preservation**: Verify single file uploads continue to work
4. **Text Input Preservation**: Verify text-only input continues to work
5. **Authentication Preservation**: Verify API key validation continues to work
6. **Session Management Preservation**: Verify session creation, updates, retrieval continue to work
7. **FIR Generation Preservation**: Verify FIR generation workflow continues to work
8. **Validation Workflow Preservation**: Verify validation steps continue to work
9. **Error Handling Preservation**: Verify non-shutdown errors continue to be handled correctly
10. **Middleware Preservation**: Verify rate limiting, security headers, CORS continue to work

### Unit Tests

- Test backend startup and module imports
- Test get_fir_data() with various inputs
- Test middleware initialization and ordering
- Test each API endpoint with valid and invalid inputs
- Test file upload validation with various file types
- Test file reading methods for different file types
- Test error handling for various error conditions
- Test session status transitions
- Test FIR generation and storage

### Property-Based Tests

- Generate random valid file uploads and verify processing succeeds
- Generate random session states and verify status endpoint returns correct data
- Generate random FIR numbers and verify content retrieval works
- Generate random text inputs and verify validation workflow works
- Generate random error conditions and verify graceful handling
- Generate random API requests and verify authentication works

### Integration Tests

- Test full FIR generation flow from file upload to completion
- Test validation workflow across all steps
- Test session lifecycle from creation to completion
- Test error recovery and graceful shutdown
- Test concurrent requests with multiple sessions
- Test file upload with various combinations of inputs
- Test API contract compliance across all endpoints
