"""
Bug Condition Exploration Test for Medium Priority Bug 9 - FIR Retrieval Endpoint Mismatch

**Validates: Requirements 1.9, 2.9**

**Property 1: Fault Condition** - FIR Endpoint Returns Metadata Only

This test verifies that GET /fir/{firNumber} returns full FIR content including fir_content field.
The bug is that the frontend calls /fir/{firNumber} expecting full content but the backend only 
returns metadata; full content is at /fir/{fir_number}/content endpoint.

**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
**DO NOT attempt to fix the test or the code when it fails**
**GOAL**: Surface counterexamples that demonstrate the bug exists

**EXPECTED OUTCOME**: Test FAILS because response only contains metadata (this is correct - it proves the bug exists)

When the bug is fixed, this test will pass, confirming the expected behavior is satisfied.
"""

import pytest
from pathlib import Path


def test_fir_retrieval_endpoint_returns_full_content():
    """
    Test that verifies the /fir/{firNumber} endpoint returns full FIR content.
    
    **Validates: Requirements 1.9, 2.9**
    
    Bug Condition: input.type == "API_REQUEST" AND input.endpoint == "/fir/{firNumber}" 
                   AND frontend.expectsFullContent AND backend.returnsMetadataOnly
    
    Expected Behavior (after fix): Response includes full FIR content with fir_content field
    
    On UNFIXED code: This test will FAIL because only metadata is returned
    On FIXED code: This test will PASS because full content including fir_content is returned
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    assert agentv5_path.exists(), f"agentv5.py not found at {agentv5_path}"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the /fir/{fir_number} endpoint (should be around line 2040-2060)
    fir_endpoint_line = None
    fir_return_start = None
    fir_return_end = None
    
    for i, line in enumerate(lines):
        if '@app.get("/fir/{fir_number}")' in line or \
           "@app.get('/fir/{fir_number}')" in line:
            fir_endpoint_line = i
            
            # Look for the return statement in the next 30 lines
            for j in range(i, min(i + 30, len(lines))):
                if 'return {' in lines[j]:
                    fir_return_start = j
                    
                    # Find the closing brace
                    brace_count = 1
                    for k in range(j + 1, min(j + 30, len(lines))):
                        if '{' in lines[k]:
                            brace_count += 1
                        if '}' in lines[k]:
                            brace_count -= 1
                            if brace_count == 0:
                                fir_return_end = k
                                break
                    break
            break
    
    assert fir_endpoint_line is not None, \
        "Could not find /fir/{fir_number} endpoint"
    
    assert fir_return_start is not None, \
        f"Could not find return statement in FIR endpoint after line {fir_endpoint_line + 1}"
    
    # Extract the return statement
    return_statement = '\n'.join(lines[fir_return_start:fir_return_end + 1]) if fir_return_end else lines[fir_return_start]
    
    # Check if fir_content is in the response
    has_fir_content = 'fir_content' in return_statement
    
    # Now check the frontend code
    frontend_dir = backend_dir.parent / "frontend" / "js"
    api_js_path = frontend_dir / "api.js"
    
    assert api_js_path.exists(), f"api.js not found at {api_js_path}"
    
    with open(api_js_path, 'r', encoding='utf-8') as f:
        frontend_content = f.read()
        frontend_lines = frontend_content.split('\n')
    
    # Find the getFIR function (around line 515)
    get_fir_line = None
    fir_fetch_line = None
    
    for i, line in enumerate(frontend_lines):
        if 'function getFIR' in line or 'getFIR:' in line or 'getFIR =' in line:
            get_fir_line = i
            
            # Look for fetch call to /fir/{firNumber} in the next 20 lines
            for j in range(i, min(i + 20, len(frontend_lines))):
                if 'fetch' in frontend_lines[j] and '/fir/' in frontend_lines[j]:
                    fir_fetch_line = j
                    break
            break
    
    assert get_fir_line is not None, \
        "Could not find getFIR function in api.js"
    
    # Check for mismatch
    if not has_fir_content:
        pytest.fail(
            f"FIR retrieval endpoint missing fir_content field:\n"
            f"\n"
            f"Bug Condition Triggered:\n"
            f"  - Endpoint: GET /fir/{{firNumber}}\n"
            f"  - Frontend expects: Full FIR content including fir_content field\n"
            f"  - Backend returns: Only metadata (fir_number, created_at, etc.)\n"
            f"\n"
            f"Backend Implementation (UNFIXED):\n"
            f"  File: AFIRGEN FINAL/main backend/agentv5.py\n"
            f"  Endpoint at line: {fir_endpoint_line + 1}\n"
            f"  Return statement (lines {fir_return_start + 1}-{fir_return_end + 1 if fir_return_end else fir_return_start + 1}):\n"
            f"{return_statement}\n"
            f"\n"
            f"  Current response fields (metadata only):\n"
            f"    - fir_number\n"
            f"    - created_at\n"
            f"    - status\n"
            f"    - session_id\n"
            f"\n"
            f"  Missing field:\n"
            f"    - fir_content (REQUIRED by frontend)\n"
            f"\n"
            f"Frontend Implementation:\n"
            f"  File: frontend/js/api.js\n"
            f"  Function: getFIR (line {get_fir_line + 1})\n"
            f"  Fetch call at line: {fir_fetch_line + 1 if fir_fetch_line else 'N/A'}\n"
            f"\n"
            f"  The frontend calls:\n"
            f"    GET /fir/{{firNumber}}\n"
            f"\n"
            f"  And expects the response to include:\n"
            f"    - fir_content: The full FIR document text\n"
            f"    - All metadata fields (fir_number, created_at, etc.)\n"
            f"\n"
            f"Root Cause:\n"
            f"  Backend has TWO separate endpoints:\n"
            f"    1. GET /fir/{{fir_number}} - Returns metadata only\n"
            f"    2. GET /fir/{{fir_number}}/content - Returns full content\n"
            f"\n"
            f"  Frontend only knows about endpoint #1 and expects it to return full content.\n"
            f"  This is an API contract mismatch between frontend and backend.\n"
            f"\n"
            f"Expected Behavior:\n"
            f"  When frontend calls GET /fir/{{firNumber}}:\n"
            f"  - Backend should return full FIR content including fir_content field\n"
            f"  - Response should include both metadata AND content\n"
            f"  - Frontend can display the FIR document to the user\n"
            f"\n"
            f"Actual Behavior (UNFIXED):\n"
            f"  When frontend calls GET /fir/{{firNumber}}:\n"
            f"  - Backend returns only metadata (fir_number, created_at, status, session_id)\n"
            f"  - fir_content field is missing\n"
            f"  - Frontend cannot display the FIR document\n"
            f"  - User sees metadata but not the actual FIR content\n"
            f"\n"
            f"Impact:\n"
            f"  - Frontend cannot retrieve full FIR content\n"
            f"  - User cannot view the completed FIR document\n"
            f"  - FIR generation appears to complete but content is not accessible\n"
            f"  - Critical functionality failure\n"
            f"\n"
            f"Fix Options:\n"
            f"  Option A (Recommended): Modify backend /fir/{{fir_number}} endpoint to include fir_content\n"
            f"    - Add fir_content field to the response\n"
            f"    - Maintain backward compatibility\n"
            f"    - Keep /fir/{{fir_number}}/content endpoint for alternative access\n"
            f"\n"
            f"  Option B: Modify frontend to call /fir/{{fir_number}}/content endpoint\n"
            f"    - Change frontend to use correct endpoint\n"
            f"    - Requires frontend code changes\n"
            f"    - Less backward compatible\n"
            f"\n"
            f"  Recommended: Option A for backward compatibility and simpler frontend code.\n"
            f"\n"
            f"This confirms Medium Priority Bug 9 exists.\n"
        )
    
    # If we reach here, the bug is fixed
    assert has_fir_content, \
        "Expected fir_content field in /fir/{fir_number} response after fix"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
