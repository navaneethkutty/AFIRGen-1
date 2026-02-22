"""
Bug Condition Exploration Test for High Priority Bug 6 - Session Polling Missing Fields

**Validates: Requirements 1.6, 2.6**

**Property 1: Fault Condition** - Status Response Missing validation_history

This test verifies that GET /session/{id}/status returns validation_history with content.fir_number.
The bug is that the /status endpoint returns minimal response (lines 1948-1956) but frontend 
expects validation_history array with nested content.fir_number field (api.js lines 551-553).

**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
**DO NOT attempt to fix the test or the code when it fails**
**GOAL**: Surface counterexamples that demonstrate the bug exists

**EXPECTED OUTCOME**: Test FAILS because validation_history field is missing (this is correct - it proves the bug exists)

When the bug is fixed, this test will pass, confirming the expected behavior is satisfied.
"""

import pytest
from pathlib import Path


def test_status_endpoint_missing_validation_history():
    """
    Test that verifies the /session/{id}/status endpoint returns validation_history.
    
    **Validates: Requirements 1.6, 2.6**
    
    Bug Condition: input.type == "API_REQUEST" AND input.endpoint == "/session/{id}/status" 
                   AND frontend.expects("validation_history[-1].content.fir_number") 
                   AND NOT response.includes("validation_history")
    
    Expected Behavior (after fix): Response includes validation_history with content.fir_number
    
    On UNFIXED code: This test will FAIL because validation_history is not in the response
    On FIXED code: This test will PASS because validation_history is included
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    assert agentv5_path.exists(), f"agentv5.py not found at {agentv5_path}"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the /session/{session_id}/status endpoint (around line 1940)
    status_endpoint_line = None
    status_return_start = None
    status_return_end = None
    
    for i, line in enumerate(lines):
        if '@app.get("/session/{session_id}/status")' in line or \
           "@app.get('/session/{session_id}/status')" in line:
            status_endpoint_line = i
            
            # Look for the return statement in the next 30 lines
            for j in range(i, min(i + 30, len(lines))):
                if 'return {' in lines[j]:
                    status_return_start = j
                    
                    # Find the closing brace
                    brace_count = 1
                    for k in range(j + 1, min(j + 20, len(lines))):
                        if '{' in lines[k]:
                            brace_count += 1
                        if '}' in lines[k]:
                            brace_count -= 1
                            if brace_count == 0:
                                status_return_end = k
                                break
                    break
            break
    
    assert status_endpoint_line is not None, \
        "Could not find /session/{session_id}/status endpoint around line 1940"
    
    assert status_return_start is not None, \
        f"Could not find return statement in status endpoint after line {status_endpoint_line + 1}"
    
    assert status_return_end is not None, \
        f"Could not find end of return statement starting at line {status_return_start + 1}"
    
    # Extract the return statement
    return_statement = '\n'.join(lines[status_return_start:status_return_end + 1])
    
    # Check if validation_history is in the response
    has_validation_history = 'validation_history' in return_statement
    
    # Now check the frontend code
    frontend_dir = backend_dir.parent / "frontend" / "js"
    api_js_path = frontend_dir / "api.js"
    
    assert api_js_path.exists(), f"api.js not found at {api_js_path}"
    
    with open(api_js_path, 'r', encoding='utf-8') as f:
        frontend_content = f.read()
        frontend_lines = frontend_content.split('\n')
    
    # Find the pollSessionStatus function (around line 541)
    poll_function_line = None
    fir_number_access_line = None
    
    for i, line in enumerate(frontend_lines):
        if 'function pollSessionStatus' in line or 'pollSessionStatus:' in line:
            poll_function_line = i
            
            # Look for validation_history access in the next 30 lines
            for j in range(i, min(i + 30, len(frontend_lines))):
                if 'validation_history' in frontend_lines[j] and 'fir_number' in frontend_lines[j]:
                    fir_number_access_line = j
                    break
                # Check next line too in case it's split
                if 'validation_history' in frontend_lines[j]:
                    if j + 1 < len(frontend_lines) and 'fir_number' in frontend_lines[j + 1]:
                        fir_number_access_line = j
                        break
            break
    
    assert poll_function_line is not None, \
        "Could not find pollSessionStatus function in api.js"
    
    assert fir_number_access_line is not None, \
        "Could not find validation_history.fir_number access in pollSessionStatus"
    
    # Check for mismatch
    if not has_validation_history:
        pytest.fail(
            f"Session status endpoint missing validation_history field:\n"
            f"\n"
            f"Bug Condition Triggered:\n"
            f"  - Endpoint: GET /session/{{session_id}}/status\n"
            f"  - Frontend expects: status.validation_history[-1].content.fir_number\n"
            f"  - Backend returns: Minimal response without validation_history\n"
            f"\n"
            f"Backend Implementation (UNFIXED):\n"
            f"  File: AFIRGEN FINAL/main backend/agentv5.py\n"
            f"  Endpoint at line: {status_endpoint_line + 1}\n"
            f"  Return statement (lines {status_return_start + 1}-{status_return_end + 1}):\n"
            f"{return_statement}\n"
            f"\n"
            f"  Current response fields:\n"
            f"    - session_id\n"
            f"    - status\n"
            f"    - current_step\n"
            f"    - awaiting_validation\n"
            f"    - created_at\n"
            f"    - last_activity\n"
            f"\n"
            f"  Missing field:\n"
            f"    - validation_history (REQUIRED by frontend)\n"
            f"\n"
            f"Frontend Implementation:\n"
            f"  File: frontend/js/api.js\n"
            f"  Function: pollSessionStatus (line {poll_function_line + 1})\n"
            f"  Line {fir_number_access_line + 1}: {frontend_lines[fir_number_access_line].strip()}\n"
            f"\n"
            f"  The frontend accesses:\n"
            f"    status.validation_history?.at(-1)?.content?.fir_number\n"
            f"\n"
            f"  This expects:\n"
            f"    - validation_history: array of validation steps\n"
            f"    - validation_history[-1]: last validation step\n"
            f"    - validation_history[-1].content: step content object\n"
            f"    - validation_history[-1].content.fir_number: the FIR number string\n"
            f"\n"
            f"Root Cause:\n"
            f"  Backend returns minimal response for performance (comment: 'PERFORMANCE: Return minimal data')\n"
            f"  but frontend needs validation_history to extract the FIR number when session completes.\n"
            f"\n"
            f"Expected Behavior:\n"
            f"  When frontend polls GET /session/{{session_id}}/status:\n"
            f"  - Backend should return validation_history array\n"
            f"  - validation_history should include all validation steps\n"
            f"  - Each step should have a content object with fir_number when available\n"
            f"  - Frontend can then extract: status.validation_history.at(-1).content.fir_number\n"
            f"\n"
            f"Actual Behavior (UNFIXED):\n"
            f"  When frontend polls GET /session/{{session_id}}/status:\n"
            f"  - Backend returns minimal response without validation_history\n"
            f"  - Frontend tries to access status.validation_history?.at(-1)?.content?.fir_number\n"
            f"  - status.validation_history is undefined\n"
            f"  - firNumber becomes empty string: ''\n"
            f"  - Frontend cannot retrieve the FIR data\n"
            f"  - Session completion flow is broken\n"
            f"\n"
            f"Impact:\n"
            f"  - Frontend cannot extract FIR number when session completes\n"
            f"  - pollSessionStatus cannot call getFIR(firNumber) with valid FIR number\n"
            f"  - User never sees the completed FIR document\n"
            f"  - Session appears to complete but no result is displayed\n"
            f"  - Critical user experience failure\n"
            f"\n"
            f"Fix Required:\n"
            f"  Add validation_history to the response in agentv5.py:\n"
            f"\n"
            f"  return {{\n"
            f"    \"session_id\": session_id,\n"
            f"    \"status\": session[\"status\"],\n"
            f"    \"current_step\": session[\"state\"].get(\"current_validation_step\"),\n"
            f"    \"awaiting_validation\": session[\"state\"].get(\"awaiting_validation\", False),\n"
            f"    \"validation_history\": session[\"state\"].get(\"validation_history\", []),  # ADD THIS\n"
            f"    \"created_at\": session[\"created_at\"].isoformat(),\n"
            f"    \"last_activity\": session[\"last_activity\"].isoformat()\n"
            f"  }}\n"
            f"\n"
            f"  Ensure validation_history includes content.fir_number:\n"
            f"  - validation_history is an array of validation step objects\n"
            f"  - Each step should have: {{\"step\": \"...\", \"content\": {{\"fir_number\": \"...\", ...}}}}\n"
            f"  - The last step (at(-1)) should have the final FIR number\n"
            f"\n"
            f"This confirms High Priority Bug 6 exists.\n"
        )
    
    # If we reach here, the bug is fixed
    assert has_validation_history, \
        "Expected validation_history field in status response after fix"


def test_frontend_validation_history_access_pattern():
    """
    Test that documents the frontend's validation_history access pattern.
    
    **Validates: Requirements 1.6, 2.6**
    
    This test verifies and documents how the frontend accesses validation_history.
    
    On UNFIXED code: This test documents the frontend's expected data structure
    On FIXED code: This test confirms the frontend pattern is correct
    """
    # Get the path to api.js
    backend_dir = Path(__file__).parent.parent
    frontend_dir = backend_dir.parent / "frontend" / "js"
    api_js_path = frontend_dir / "api.js"
    
    assert api_js_path.exists(), f"api.js not found at {api_js_path}"
    
    with open(api_js_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the pollSessionStatus function
    poll_line = None
    fir_number_line = None
    
    for i, line in enumerate(lines):
        if 'function pollSessionStatus' in line:
            poll_line = i
            
            # Look for validation_history access
            for j in range(i, min(i + 30, len(lines))):
                if 'validation_history' in lines[j] and ('fir_number' in lines[j] or 'fir_number' in lines[j + 1] if j + 1 < len(lines) else False):
                    fir_number_line = j
                    break
            break
    
    assert poll_line is not None, \
        "Could not find pollSessionStatus function in api.js"
    
    assert fir_number_line is not None, \
        "Could not find validation_history access in pollSessionStatus"
    
    print("\nFrontend validation_history Access Pattern:")
    print("=" * 70)
    print(f"\nFile: frontend/js/api.js")
    print(f"Function: pollSessionStatus (line {poll_line + 1})")
    print(f"\nAccess Pattern (line {fir_number_line + 1}):")
    print(f"  {lines[fir_number_line].strip()}")
    if fir_number_line + 1 < len(lines) and 'fir_number' in lines[fir_number_line + 1]:
        print(f"  {lines[fir_number_line + 1].strip()}")
    print("\nExpected Data Structure:")
    print("  status = {")
    print("    session_id: 'abc123',")
    print("    status: 'completed',")
    print("    validation_history: [")
    print("      {")
    print("        step: 'transcript_review',")
    print("        content: {")
    print("          transcript: '...',")
    print("          fir_number: 'FIR-2024-001'  // <-- Frontend needs this")
    print("        }")
    print("      },")
    print("      {")
    print("        step: 'summary_review',")
    print("        content: {")
    print("          summary: '...',")
    print("          fir_number: 'FIR-2024-001'  // <-- Frontend accesses this")
    print("        }")
    print("      }")
    print("    ]")
    print("  }")
    print("\nAccess Chain:")
    print("  1. status.validation_history -> array")
    print("  2. .at(-1) -> last element")
    print("  3. .content -> content object")
    print("  4. .fir_number -> FIR number string")
    print("\nOptional Chaining (?.):")
    print("  - Prevents errors if any intermediate value is null/undefined")
    print("  - Returns undefined if any step fails")
    print("  - Falls back to empty string: || ''")
    print("\nThis access pattern is CORRECT for a REST API.")
    print("The backend needs to include validation_history in the response.")
    print("=" * 70)


def test_status_endpoint_performance_comment():
    """
    Test that documents the performance optimization comment in the status endpoint.
    
    **Validates: Requirements 1.6, 2.6**
    
    This test shows that the minimal response was intentional for performance,
    but it breaks the frontend contract.
    
    On UNFIXED code: This test documents the performance vs functionality tradeoff
    On FIXED code: This test confirms validation_history is included despite performance concern
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the status endpoint
    status_endpoint_line = None
    performance_comment_line = None
    
    for i, line in enumerate(lines):
        if '@app.get("/session/{session_id}/status")' in line:
            status_endpoint_line = i
            
            # Look for PERFORMANCE comment in the next 20 lines
            for j in range(i, min(i + 20, len(lines))):
                if 'PERFORMANCE' in lines[j] and 'minimal' in lines[j].lower():
                    performance_comment_line = j
                    break
            break
    
    assert status_endpoint_line is not None, \
        "Could not find /session/{session_id}/status endpoint"
    
    if performance_comment_line:
        print("\nPerformance Optimization vs Functionality:")
        print("=" * 70)
        print(f"\nFile: AFIRGEN FINAL/main backend/agentv5.py")
        print(f"Endpoint at line: {status_endpoint_line + 1}")
        print(f"\nPerformance Comment (line {performance_comment_line + 1}):")
        print(f"  {lines[performance_comment_line].strip()}")
        print("\nIntent:")
        print("  - Return minimal data for faster serialization")
        print("  - Reduce response size for polling endpoint")
        print("  - Improve performance for frequent status checks")
        print("\nProblem:")
        print("  - Frontend needs validation_history to extract FIR number")
        print("  - Minimal response breaks frontend functionality")
        print("  - Performance optimization causes critical bug")
        print("\nSolution:")
        print("  - Include validation_history in response")
        print("  - validation_history is typically small (few validation steps)")
        print("  - Performance impact is minimal compared to broken functionality")
        print("  - Frontend contract must be honored")
        print("\nLesson:")
        print("  - Performance optimizations should not break API contracts")
        print("  - Frontend-backend contracts must be validated")
        print("  - Measure performance impact before optimizing")
        print("=" * 70)


def test_validation_history_structure():
    """
    Test that documents the expected validation_history structure.
    
    **Validates: Requirements 1.6, 2.6**
    
    This test documents what the validation_history structure should look like
    to satisfy the frontend's access pattern.
    
    On UNFIXED code: This test documents the required structure
    On FIXED code: This test can verify the structure matches expectations
    """
    print("\nExpected validation_history Structure:")
    print("=" * 70)
    print("\nData Type: Array of validation step objects")
    print("\nEach validation step object should have:")
    print("  {")
    print("    step: string,           // e.g., 'transcript_review', 'summary_review'")
    print("    content: {              // Step-specific content")
    print("      fir_number: string,   // The FIR number (REQUIRED by frontend)")
    print("      ...                   // Other step-specific fields")
    print("    },")
    print("    timestamp: string,      // Optional: when step was completed")
    print("    status: string          // Optional: 'approved', 'regenerated', etc.")
    print("  }")
    print("\nExample validation_history:")
    print("  [")
    print("    {")
    print("      step: 'transcript_review',")
    print("      content: {")
    print("        transcript: 'I want to report a theft...',")
    print("        fir_number: 'FIR-2024-001'")
    print("      },")
    print("      status: 'approved'")
    print("    },")
    print("    {")
    print("      step: 'summary_review',")
    print("      content: {")
    print("        summary: 'Theft reported at...',")
    print("        fir_number: 'FIR-2024-001'")
    print("      },")
    print("      status: 'approved'")
    print("    },")
    print("    {")
    print("      step: 'final_review',")
    print("      content: {")
    print("        fir_content: 'Full FIR document...',")
    print("        fir_number: 'FIR-2024-001'")
    print("      },")
    print("      status: 'completed'")
    print("    }")
    print("  ]")
    print("\nFrontend Access:")
    print("  validation_history.at(-1)        -> Last step (final_review)")
    print("  .content                         -> {fir_content: '...', fir_number: 'FIR-2024-001'}")
    print("  .fir_number                      -> 'FIR-2024-001'")
    print("\nKey Requirements:")
    print("  1. validation_history must be an array")
    print("  2. Each element must have a 'content' object")
    print("  3. content must include 'fir_number' field")
    print("  4. fir_number should be consistent across all steps")
    print("  5. Last element (at(-1)) should have the final FIR number")
    print("=" * 70)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
