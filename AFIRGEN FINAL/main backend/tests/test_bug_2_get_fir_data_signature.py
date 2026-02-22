"""
Bug Condition Exploration Test for Critical Bug 2 - get_fir_data Signature Mismatch

**Validates: Requirements 1.2, 2.2**

**Property 1: Fault Condition** - Function Signature Mismatch

This test verifies that get_fir_data() can be called with two arguments (state_dict, fir_number)
as it is called at line 1866 during FIR generation at the FINAL_REVIEW step.

**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
**EXPECTED OUTCOME**: Test FAILS with TypeError about argument count (this is correct - it proves the bug exists)

When the bug is fixed, this test will pass, confirming the expected behavior is satisfied.
"""

import pytest
import ast
from pathlib import Path
from datetime import datetime


def test_get_fir_data_signature_mismatch():
    """
    Test that verifies the signature mismatch between get_fir_data definition and call site.
    
    **Validates: Requirements 1.2, 2.2**
    
    Bug Condition: input.type == "FUNCTION_CALL" AND input.function == "get_fir_data" 
                   AND input.argCount == 2 AND functionDefinition.paramCount == 1
    
    Expected Behavior (after fix): get_fir_data is defined with 2 parameters to match the call site
    
    On UNFIXED code: This test will FAIL because function has 1 parameter but is called with 2 arguments
    On FIXED code: This test will PASS because function signature matches call site
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    assert agentv5_path.exists(), f"agentv5.py not found at {agentv5_path}"
    
    # Read and parse the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content, filename=str(agentv5_path))
    except SyntaxError as e:
        pytest.fail(f"Failed to parse agentv5.py: {e}")
    
    # Find the get_fir_data function definition
    get_fir_data_def = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "get_fir_data":
            get_fir_data_def = node
            break
    
    assert get_fir_data_def is not None, "get_fir_data function not found in agentv5.py"
    
    # Count the parameters (excluding self if present)
    param_count = len(get_fir_data_def.args.args)
    param_names = [arg.arg for arg in get_fir_data_def.args.args]
    
    # Find the call site (should be around line 1866-1880 depending on fixes)
    call_site_found = False
    call_arg_count = 0
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "get_fir_data":
                # Check if this is around line 1866-1880 (wider range to account for code changes)
                if hasattr(node, 'lineno') and 1860 <= node.lineno <= 1880:
                    call_site_found = True
                    call_arg_count = len(node.args)
                    call_line = node.lineno
                    break
    
    assert call_site_found, "get_fir_data call site not found around line 1866-1880"
    
    # Check for signature mismatch
    if param_count != call_arg_count:
        pytest.fail(
            f"Function signature mismatch detected:\n"
            f"Definition (line ~223): get_fir_data is defined with {param_count} parameter(s): {param_names}\n"
            f"Call site (line {call_line}): get_fir_data is called with {call_arg_count} argument(s)\n"
            f"This confirms Critical Bug 2 exists.\n"
            f"\n"
            f"Counterexample:\n"
            f"  - Function definition expects {param_count} argument(s)\n"
            f"  - Call site provides {call_arg_count} argument(s) (state_dict, fir_number)\n"
            f"\n"
            f"Expected: Function signature should match call site (2 parameters)\n"
            f"Actual: Function has {param_count} parameter(s), called with {call_arg_count} argument(s)\n"
            f"\n"
            f"When this code executes, it will raise:\n"
            f"TypeError: get_fir_data() takes {param_count} positional argument but {call_arg_count} were given"
        )
    
    # If we reach here, the signatures match (bug is fixed)
    assert param_count == 2, f"Expected 2 parameters after fix, got {param_count}"
    assert call_arg_count == 2, f"Expected 2 arguments at call site, got {call_arg_count}"


def test_get_fir_data_call_site_verification():
    """
    Test that verifies the exact call site at line 1866 and documents the bug.
    
    **Validates: Requirements 1.2, 2.2**
    
    This test reads the source code to verify the call site exists and documents
    the exact nature of the bug for the bug report.
    
    On UNFIXED code: This test will FAIL and document the mismatch
    On FIXED code: This test will PASS
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    # Read the file
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Search for the call line in the expected range (1866-1880)
    call_line_num = None
    call_line = None
    for i in range(1865, min(1880, len(lines))):
        if "get_fir_data" in lines[i]:
            call_line_num = i + 1
            call_line = lines[i].strip()
            break
    
    # Verify the call site exists
    assert call_line is not None, \
        f"get_fir_data call not found in lines 1866-1880"
    
    # Check if it's called with two arguments
    if "get_fir_data(state_dict, fir_number)" in call_line or \
       "get_fir_data(state_dict,fir_number)" in call_line:
        # Call site has 2 arguments - now check the definition
        
        # Find the function definition around line 223
        definition_found = False
        for i in range(220, min(230, len(lines))):
            if "def get_fir_data(" in lines[i]:
                def_line = lines[i].strip()
                definition_found = True
                
                # Check if it has only 1 parameter (BUG - should have 2)
                if "def get_fir_data(session_state:" in def_line and "fir_number" not in def_line:
                    pytest.fail(
                        f"Function signature mismatch confirmed:\n"
                        f"\n"
                        f"Definition at line {i+1}:\n"
                        f"  {def_line}\n"
                        f"  Parameters: 1 (session_state)\n"
                        f"\n"
                        f"Call site at line {call_line_num}:\n"
                        f"  {call_line}\n"
                        f"  Arguments: 2 (state_dict, fir_number)\n"
                        f"\n"
                        f"This confirms Critical Bug 2 exists.\n"
                        f"\n"
                        f"When FIR generation reaches FINAL_REVIEW step and executes line {call_line_num},\n"
                        f"it will raise: TypeError: get_fir_data() takes 1 positional argument but 2 were given"
                    )
                # If we reach here, the function has 2 parameters (FIXED)
                # Verify it has both parameters
                assert "session_state" in def_line and "fir_number" in def_line, \
                    f"Function should have both session_state and fir_number parameters. Found: {def_line}"
                break
        
        assert definition_found, "get_fir_data function definition not found around line 223"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
