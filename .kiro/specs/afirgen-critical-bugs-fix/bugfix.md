# Bugfix Requirements Document

## Introduction

The AFIRGEN application has 11 critical and high-priority bugs identified through comprehensive code audit that are blocking production deployment. These bugs span three categories: backend startup/runtime blockers preventing the application from starting, API contract mismatches causing frontend-backend communication failures, and validation/error handling issues causing incorrect behavior. The bugs affect core functionality including FIR generation, session management, file uploads, and validation workflows.

## Bug Analysis

### Current Behavior (Defect)

**Critical Issues - Backend Startup/Runtime Blockers:**

1.1 WHEN the backend starts THEN the system crashes with IndentationError at agentv5.py line 1695 because RequestTrackingMiddleware has no body

1.2 WHEN get_fir_data() is called at lines 1869-1873 THEN the system crashes with TypeError because the function is defined with 1 parameter but called with 2 arguments

1.3 WHEN the backend initializes middleware THEN the system has duplicated/nested APIAuthMiddleware declarations causing structural corruption and unpredictable behavior

**High Priority - API Contract Mismatches:**

1.4 WHEN the frontend calls the regenerate endpoint with JSON body THEN the system fails because the backend expects query parameters instead

1.5 WHEN the frontend polls session completion status THEN the system returns incomplete data missing validation_history and fir_number fields that the frontend expects

1.6 WHEN the frontend calls /fir/{firNumber} expecting full FIR content THEN the system returns only metadata instead of the complete FIR document

1.7 WHEN a text-only session completes processing THEN the system never marks it as AWAITING_VALIDATION causing validation requests to be rejected

1.8 WHEN the frontend uploads multiple files THEN the system rejects the request with 400 error because backend validation fails when input_count > 1

**Medium Priority - Validation & Error Handling:**

1.9 WHEN the frontend uploads files with extensions .pdf, .doc, .docx, .m4a, or .ogg THEN the system rejects them even though the frontend UI allows these file types

1.10 WHEN non-image letter files are uploaded THEN the system reads them incorrectly via File.text() causing corrupted payloads to be sent to the backend

1.11 WHEN middleware encounters an error during shutdown THEN the system crashes because HTTPException.to_response() is called incorrectly

### Expected Behavior (Correct)

**Critical Issues - Backend Startup/Runtime Blockers:**

2.1 WHEN the backend starts THEN the system SHALL start successfully with RequestTrackingMiddleware having a proper body implementation

2.2 WHEN get_fir_data() is called THEN the system SHALL execute successfully with matching function signature (either 1 or 2 parameters consistently)

2.3 WHEN the backend initializes middleware THEN the system SHALL have a single, properly structured APIAuthMiddleware declaration without duplication or nesting

**High Priority - API Contract Mismatches:**

2.4 WHEN the frontend calls the regenerate endpoint with JSON body THEN the system SHALL accept and process the JSON body correctly

2.5 WHEN the frontend polls session completion status THEN the system SHALL return complete data including validation_history and fir_number fields

2.6 WHEN the frontend calls /fir/{firNumber} THEN the system SHALL return the full FIR document content as expected by the frontend

2.7 WHEN a text-only session completes processing THEN the system SHALL mark it as AWAITING_VALIDATION to allow validation requests

2.8 WHEN the frontend uploads multiple files THEN the system SHALL accept and process all files when input_count > 1

**Medium Priority - Validation & Error Handling:**

2.9 WHEN the frontend uploads files with extensions .pdf, .doc, .docx, .m4a, or .ogg THEN the system SHALL accept them if they are allowed by the frontend UI, or the frontend SHALL disable these file types if backend doesn't support them

2.10 WHEN non-image letter files are uploaded THEN the system SHALL read them correctly using appropriate methods (not File.text()) to prevent payload corruption

2.11 WHEN middleware encounters an error during shutdown THEN the system SHALL handle the error gracefully without crashing

### Unchanged Behavior (Regression Prevention)

3.1 WHEN valid image files are uploaded THEN the system SHALL CONTINUE TO process them correctly as before

3.2 WHEN single file uploads are submitted THEN the system SHALL CONTINUE TO process them successfully

3.3 WHEN audio files with supported formats are uploaded THEN the system SHALL CONTINUE TO process them correctly

3.4 WHEN FIR generation completes successfully THEN the system SHALL CONTINUE TO store and retrieve FIR data correctly

3.5 WHEN session status is polled for sessions with all expected fields THEN the system SHALL CONTINUE TO return complete status information

3.6 WHEN authentication middleware processes valid requests THEN the system SHALL CONTINUE TO authenticate and authorize correctly

3.7 WHEN validation workflows are triggered for properly marked sessions THEN the system SHALL CONTINUE TO process validation requests correctly

3.8 WHEN error handling works correctly in existing paths THEN the system SHALL CONTINUE TO handle errors gracefully

3.9 WHEN file type validation accepts currently supported types THEN the system SHALL CONTINUE TO validate and accept them

3.10 WHEN the backend processes requests with correct parameter formats THEN the system SHALL CONTINUE TO handle them successfully
