# Bugfix Requirements Document

## Introduction

The AFIRGEN application (FIR generation system with frontend + FastAPI backend) has multiple critical bugs preventing production deployment. These bugs span backend startup failures, FIR generation crashes, validation flow issues, and frontend/backend contract mismatches. This document defines the requirements for fixing all identified issues using the bug condition methodology to ensure systematic validation through fix checking (verify bugs are fixed) and preservation checking (verify existing behavior is unchanged).

## Bug Analysis

### Current Behavior (Defect)

#### Critical Issues (Blocking)

1.1 WHEN the backend server attempts to import agentv5.py THEN the system fails with IndentationError at line 1693-1695 because RequestTrackingMiddleware class has no body after its declaration

1.2 WHEN FIR generation is triggered and get_fir_data() is called at line 1866 with two arguments (state_dict, fir_number) THEN the system crashes with TypeError because the function is defined at line 223 to accept only one parameter (session_state)

#### High Priority Issues

1.3 WHEN a text-only FIR processing session is created via /process endpoint THEN the system never transitions the session status to AWAITING_VALIDATION (lines 1755-1764 only set awaiting_validation flag but not status)

1.4 WHEN the text-only session from 1.3 attempts validation via /validate endpoint THEN the system rejects the request with 400 error "Session not awaiting validation" (lines 1798-1802 check status != AWAITING_VALIDATION)

1.5 WHEN the frontend calls /regenerate endpoint and sends request data as JSON body (frontend/js/api.js lines 451-460) THEN the system fails because the backend expects query parameters (lines 1950-1952)

1.6 WHEN the frontend polls session completion status and expects validation_history[-1].content.fir_number (frontend/js/api.js lines 551-553) THEN the system fails because the backend status endpoint doesn't include these fields in the response (lines 1940-1948)

1.7 WHEN a user selects both letter file and audio file in the frontend UI THEN the system allows generation to proceed but the backend rejects multiple inputs (lines 1716-1719), causing unexpected failure after upload

1.8 WHEN a user uploads .pdf, .txt, .doc, or .docx letter files OR .m4a or .ogg audio files (frontend accepts these at frontend/js/app.js lines 399-444) THEN the system rejects them because the backend only supports jpeg/png images and wav/mpeg/mp3 audio (input_validation.py lines 27-31)

#### Medium Priority Issues

1.9 WHEN the frontend calls /fir/{firNumber} endpoint expecting full FIR content (frontend/js/api.js lines 515-531) THEN the system returns only metadata because full content is at /fir/{fir_number}/content endpoint (lines 2054-2086)

1.10 WHEN RequestTrackingMiddleware catches a RuntimeError with "shutting down" message (lines 1616-1619) THEN the system crashes because HTTPException.to_response() method does not exist

1.11 WHEN the frontend uploads PDF or DOC files and uses File.text() to read them (frontend/js/api.js lines 311-316) THEN the system corrupts binary data because text() method is for text files only

### Expected Behavior (Correct)

#### Critical Issues (Blocking)

2.1 WHEN the backend server attempts to import agentv5.py THEN the system SHALL successfully import without IndentationError and RequestTrackingMiddleware SHALL have a properly defined class body

2.2 WHEN FIR generation is triggered and get_fir_data() is called THEN the system SHALL successfully execute with matching function signature (either define with 2 params or call with 1 param)

#### High Priority Issues

2.3 WHEN a text-only FIR processing session is created via /process endpoint THEN the system SHALL transition the session status to AWAITING_VALIDATION to enable validation flow

2.4 WHEN the text-only session attempts validation via /validate endpoint THEN the system SHALL accept the request and proceed with validation because the session status is AWAITING_VALIDATION

2.5 WHEN the frontend calls /regenerate endpoint THEN the system SHALL successfully process the request with aligned parameter passing (both use JSON body OR both use query params)

2.6 WHEN the frontend polls session completion status THEN the system SHALL return validation_history with content.fir_number field so the frontend can extract the FIR number

2.7 WHEN a user selects both letter file and audio file in the frontend UI THEN the system SHALL disable the generation button or show a validation error preventing submission

2.8 WHEN a user attempts to upload files THEN the system SHALL only accept file types supported by both frontend and backend (jpeg/png images and wav/mpeg/mp3 audio)

#### Medium Priority Issues

2.9 WHEN the frontend calls /fir/{firNumber} endpoint THEN the system SHALL return full FIR content matching frontend expectations OR the frontend SHALL call the correct /fir/{fir_number}/content endpoint

2.10 WHEN RequestTrackingMiddleware catches a RuntimeError with "shutting down" message THEN the system SHALL return a proper 503 response using JSONResponse or Response object

2.11 WHEN the frontend uploads PDF or DOC files THEN the system SHALL read them as binary data using appropriate methods (File.arrayBuffer() or similar) to prevent corruption

### Unchanged Behavior (Regression Prevention)

3.1 WHEN audio or image files are processed via /process endpoint THEN the system SHALL CONTINUE TO process them through the initial_processing pipeline as before

3.2 WHEN valid sessions with audio/image inputs reach AWAITING_VALIDATION status THEN the system SHALL CONTINUE TO accept validation requests via /validate endpoint

3.3 WHEN the /status endpoint is called for active sessions THEN the system SHALL CONTINUE TO return session status, steps, and other existing fields

3.4 WHEN users upload jpeg or png image files THEN the system SHALL CONTINUE TO accept and process them correctly

3.5 WHEN users upload wav, mpeg, or mp3 audio files THEN the system SHALL CONTINUE TO accept and process them correctly

3.6 WHEN the backend processes valid FIR generation requests THEN the system SHALL CONTINUE TO generate FIR documents with correct data and formatting

3.7 WHEN APIAuthMiddleware validates API keys THEN the system SHALL CONTINUE TO enforce authentication as before

3.8 WHEN health check endpoint /health is called THEN the system SHALL CONTINUE TO return health status without authentication

3.9 WHEN graceful shutdown is initiated THEN the system SHALL CONTINUE TO track active requests and wait for completion

3.10 WHEN FIR retrieval endpoints are called with valid FIR numbers THEN the system SHALL CONTINUE TO return FIR data correctly

3.11 WHEN the frontend displays FIR generation progress THEN the system SHALL CONTINUE TO show step-by-step progress updates

3.12 WHEN validation steps are completed and approved THEN the system SHALL CONTINUE TO advance to the next validation step or complete the FIR generation
