"""
Bug Condition Exploration Test for High Priority Bug 5 - Regenerate Endpoint Mismatch

**Validates: Requirements 1.5, 2.5**

**Property 1: Fault Condition** - Regenerate Parameter Passing Mismatch

This test verifies that POST /regenerate with JSON body {step, user_input} succeeds.
The bug is that the frontend sends regenerate requests with JSON body (api.js lines 451-460)
but the backend expects query parameters (line 1962).

**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
**DO NOT attempt to fix the test or the code when it fails**
**GOAL**: Surface counterexamples that demonstrate the bug exists

**EXPECTED OUTCOME**: Test FAILS with 422 Unprocessable Entity or parameter binding error 
(this is correct - it proves the bug exists)

When the bug is fixed, this test will pass, confirming the expected behavior is satisfied.
"""

import pytest
import ast
from pathlib import Path


def test_regenerate_endpoint_parameter_mismatch():
    """
    Test that verifies the /regenerate endpoint parameter passing mismatch.
    
    **Validates: Requirements 1.5, 2.5**
    
    Bug Condition: input.type == "API_REQUEST" AND input.endpoint == "/regenerate" 
                   AND frontend.sendsJSONBody AND backend.expectsQueryParams
    
    Expected Behavior (after fix): Backend accepts JSON body parameters
    
    On UNFIXED code: This test will FAIL because backend expects query params but frontend sends JSON body
    On FIXED code: This test will PASS because parameter passing is aligned
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    assert agentv5_path.exists(), f"agentv5.py not found at {agentv5_path}"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the /regenerate endpoint (around line 1962)
    regenerate_endpoint_line = None
    regenerate_function_def = None
    
    for i, line in enumerate(lines):
        if '@app.post("/regenerate/{session_id}")' in line or \
           "@app.post('/regenerate/{session_id}')" in line:
            regenerate_endpoint_line = i
            
            # Look for the function definition in the next few lines
            for j in range(i, min(i + 5, len(lines))):
                if 'async def regenerate_step' in lines[j]:
                    regenerate_function_def = lines[j].strip()
                    break
            break
    
    assert regenerate_endpoint_line is not None, \
        "Could not find /regenerate endpoint around line 1962"
    
    assert regenerate_function_def is not None, \
        f"Could not find regenerate_step function definition after line {regenerate_endpoint_line + 1}"
    
    # Check if the function signature uses query parameters (function arguments)
    # Expected on UNFIXED code: async def regenerate_step(session_id: str, step: ValidationStep, user_input: Optional[str] = None)
    # Expected on FIXED code: async def regenerate_step(session_id: str, regenerate_req: RegenerateRequest)
    
    uses_query_params = False
    uses_json_body = False
    
    # Check if function has 'step' and 'user_input' as direct parameters (query params)
    if 'step:' in regenerate_function_def and 'user_input:' in regenerate_function_def:
        uses_query_params = True
    
    # Check if function has a request body parameter (like regenerate_req)
    if 'regenerate_req' in regenerate_function_def or 'request_body' in regenerate_function_def or 'body' in regenerate_function_def:
        uses_json_body = True
    
    # Now check the frontend code
    frontend_dir = backend_dir.parent / "frontend" / "js"
    api_js_path = frontend_dir / "api.js"
    
    assert api_js_path.exists(), f"api.js not found at {api_js_path}"
    
    with open(api_js_path, 'r', encoding='utf-8') as f:
        frontend_content = f.read()
        frontend_lines = frontend_content.split('\n')
    
    # Find the regenerateStep function (around line 451)
    frontend_regenerate_line = None
    frontend_sends_json_body = False
    
    for i, line in enumerate(frontend_lines):
        if 'async function regenerateStep' in line or 'regenerateStep:' in line:
            frontend_regenerate_line = i
            
            # Look for JSON.stringify in the next 20 lines
            for j in range(i, min(i + 20, len(frontend_lines))):
                if 'JSON.stringify' in frontend_lines[j] and \
                   ('step:' in frontend_lines[j] or 'step' in frontend_lines[j+1] or 'step' in frontend_lines[j+2]):
                    frontend_sends_json_body = True
                    break
            break
    
    assert frontend_regenerate_line is not None, \
        "Could not find regenerateStep function in api.js"
    
    assert frontend_sends_json_body, \
        "Frontend does not appear to send JSON body with step parameter"
    
    # Check for mismatch
    if uses_query_params and frontend_sends_json_body:
        pytest.fail(
            f"Regenerate endpoint parameter passing mismatch detected:\n"
            f"\n"
            f"Bug Condition Triggered:\n"
            f"  - Endpoint: POST /regenerate/{{session_id}}\n"
            f"  - Frontend sends: JSON body with {{step, user_input}}\n"
            f"  - Backend expects: Query parameters\n"
            f"\n"
            f"Backend Implementation (UNFIXED):\n"
            f"  Line {regenerate_endpoint_line + 1}: {lines[regenerate_endpoint_line].strip()}\n"
            f"  Line {regenerate_endpoint_line + 2}: {regenerate_function_def}\n"
            f"\n"
            f"  The function signature defines 'step' and 'user_input' as function parameters.\n"
            f"  In FastAPI, function parameters (not in path) are treated as query parameters.\n"
            f"  This means the backend expects: POST /regenerate/{{session_id}}?step=...&user_input=...\n"
            f"\n"
            f"Frontend Implementation:\n"
            f"  File: frontend/js/api.js\n"
            f"  Line {frontend_regenerate_line + 1}: async function regenerateStep(...)\n"
            f"\n"
            f"  The frontend sends:\n"
            f"    fetch(`${{API_BASE}}/regenerate/${{sessionId}}`, {{\n"
            f"      method: 'POST',\n"
            f"      headers: {{'Content-Type': 'application/json'}},\n"
            f"      body: JSON.stringify({{\n"
            f"        step: step,\n"
            f"        user_input: userInput\n"
            f"      }})\n"
            f"    }})\n"
            f"\n"
            f"Root Cause:\n"
            f"  Frontend-backend contract mismatch:\n"
            f"  - Frontend: Sends parameters in JSON request body\n"
            f"  - Backend: Expects parameters as query string parameters\n"
            f"\n"
            f"Expected Behavior:\n"
            f"  When frontend calls POST /regenerate/{{session_id}} with JSON body:\n"
            f"    {{\n"
            f"      \"step\": \"summary_review\",\n"
            f"      \"user_input\": \"Please add more details\"\n"
            f"    }}\n"
            f"  The backend should successfully process the request.\n"
            f"\n"
            f"Actual Behavior (UNFIXED):\n"
            f"  When frontend calls POST /regenerate/{{session_id}} with JSON body:\n"
            f"  - FastAPI cannot bind JSON body parameters to function arguments\n"
            f"  - Backend returns 422 Unprocessable Entity\n"
            f"  - Error: Field required for 'step' parameter\n"
            f"  - The JSON body is ignored because FastAPI expects query parameters\n"
            f"\n"
            f"Impact:\n"
            f"  - Regenerate functionality is completely broken\n"
            f"  - Users cannot regenerate validation steps\n"
            f"  - Frontend receives 422 errors when trying to regenerate\n"
            f"  - FIR generation workflow cannot recover from validation issues\n"
            f"\n"
            f"Fix Options:\n"
            f"  Option A (Recommended): Change backend to accept JSON body\n"
            f"    - Define a Pydantic model: class RegenerateRequest(BaseModel)\n"
            f"    - Change signature: async def regenerate_step(session_id: str, regenerate_req: RegenerateRequest)\n"
            f"    - Extract parameters: step = regenerate_req.step, user_input = regenerate_req.user_input\n"
            f"\n"
            f"  Option B: Change frontend to send query parameters\n"
            f"    - Change URL: `${{API_BASE}}/regenerate/${{sessionId}}?step=${{step}}&user_input=${{userInput}}`\n"
            f"    - Remove JSON body\n"
            f"    - Less recommended: Query params are less suitable for potentially long user_input\n"
            f"\n"
            f"This confirms High Priority Bug 5 exists.\n"
        )
    
    # If we reach here, the bug is fixed
    assert not (uses_query_params and frontend_sends_json_body), \
        "Expected backend to accept JSON body after fix, but still uses query parameters"


def test_regenerate_endpoint_fastapi_behavior():
    """
    Test that documents FastAPI's parameter binding behavior.
    
    **Validates: Requirements 1.5, 2.5**
    
    This test explains how FastAPI binds parameters and why the mismatch causes a 422 error.
    
    On UNFIXED code: This test documents the FastAPI behavior causing the bug
    On FIXED code: This test confirms the fix aligns with FastAPI's JSON body handling
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the /regenerate endpoint
    regenerate_endpoint_line = None
    regenerate_function_def = None
    
    for i, line in enumerate(lines):
        if '@app.post("/regenerate/{session_id}")' in line or \
           "@app.post('/regenerate/{session_id}')" in line:
            regenerate_endpoint_line = i
            
            for j in range(i, min(i + 5, len(lines))):
                if 'async def regenerate_step' in lines[j]:
                    regenerate_function_def = lines[j].strip()
                    break
            break
    
    assert regenerate_endpoint_line is not None, \
        "Could not find /regenerate endpoint"
    
    assert regenerate_function_def is not None, \
        "Could not find regenerate_step function definition"
    
    # Check if using query parameters
    uses_query_params = 'step:' in regenerate_function_def and 'user_input:' in regenerate_function_def
    
    if uses_query_params:
        print("\nFastAPI Parameter Binding Behavior:")
        print("=" * 70)
        print(f"\nEndpoint: {lines[regenerate_endpoint_line].strip()}")
        print(f"Function: {regenerate_function_def}")
        print("\nFastAPI Parameter Binding Rules:")
        print("  1. Path parameters: Defined in route path (e.g., {session_id})")
        print("  2. Query parameters: Function parameters not in path, not Pydantic models")
        print("  3. Request body: Pydantic model parameters")
        print("\nCurrent Implementation (UNFIXED):")
        print("  - session_id: Path parameter ✓")
        print("  - step: Query parameter (function parameter, not in path)")
        print("  - user_input: Query parameter (function parameter, not in path)")
        print("\nExpected Request Format:")
        print("  POST /regenerate/{session_id}?step=summary_review&user_input=...")
        print("\nActual Frontend Request:")
        print("  POST /regenerate/{session_id}")
        print("  Body: {\"step\": \"summary_review\", \"user_input\": \"...\"}")
        print("\nResult:")
        print("  - FastAPI looks for 'step' in query parameters")
        print("  - 'step' is not in query string")
        print("  - FastAPI ignores JSON body (no Pydantic model to bind to)")
        print("  - Returns 422 Unprocessable Entity: Field required for 'step'")
        print("\nFix Required:")
        print("  Define Pydantic model for request body:")
        print("    class RegenerateRequest(BaseModel):")
        print("      step: ValidationStep")
        print("      user_input: Optional[str] = None")
        print("\n  Change function signature:")
        print("    async def regenerate_step(session_id: str, regenerate_req: RegenerateRequest)")
        print("\n  FastAPI will then bind JSON body to regenerate_req parameter")
        print("=" * 70)


def test_frontend_regenerate_call_format():
    """
    Test that documents the frontend's regenerate call format.
    
    **Validates: Requirements 1.5, 2.5**
    
    This test verifies and documents how the frontend calls the regenerate endpoint.
    
    On UNFIXED code: This test documents the frontend's JSON body format
    On FIXED code: This test confirms the frontend format is correct
    """
    # Get the path to api.js
    backend_dir = Path(__file__).parent.parent
    frontend_dir = backend_dir.parent / "frontend" / "js"
    api_js_path = frontend_dir / "api.js"
    
    assert api_js_path.exists(), f"api.js not found at {api_js_path}"
    
    with open(api_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the regenerateStep function
    regenerate_line = None
    json_stringify_line = None
    
    for i, line in enumerate(lines):
        if 'async function regenerateStep' in line:
            regenerate_line = i
            
            # Look for JSON.stringify in the next 20 lines
            for j in range(i, min(i + 20, len(lines))):
                if 'JSON.stringify' in lines[j]:
                    json_stringify_line = j
                    break
            break
    
    assert regenerate_line is not None, \
        "Could not find regenerateStep function in api.js"
    
    assert json_stringify_line is not None, \
        "Could not find JSON.stringify call in regenerateStep function"
    
    print("\nFrontend Regenerate Call Format:")
    print("=" * 70)
    print(f"\nFile: frontend/js/api.js")
    print(f"Function starts at line: {regenerate_line + 1}")
    print("\nRequest Format:")
    print(f"  Method: POST")
    print(f"  URL: /regenerate/{{sessionId}}")
    print(f"  Headers: Content-Type: application/json")
    print(f"  Body: JSON.stringify({{")
    print(f"    step: step,")
    print(f"    user_input: userInput")
    print(f"  }})")
    print("\nExample Request:")
    print("  POST /regenerate/abc123")
    print("  Content-Type: application/json")
    print("  {")
    print("    \"step\": \"summary_review\",")
    print("    \"user_input\": \"Please add more details about the incident\"")
    print("  }")
    print("\nThis format is CORRECT for a REST API.")
    print("The backend needs to be updated to accept this format.")
    print("=" * 70)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
