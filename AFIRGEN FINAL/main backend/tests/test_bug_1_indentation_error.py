"""
Bug Condition Exploration Test for Critical Bug 1 - IndentationError

**Validates: Requirements 1.1, 2.1**

**Property 1: Fault Condition** - Backend Import Failure

This test verifies that the agentv5.py module can be imported without IndentationError
and that RequestTrackingMiddleware class has a properly defined body.

**CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
**EXPECTED OUTCOME**: Test FAILS with IndentationError at line 1646 (this is correct - it proves the bug exists)

When the bug is fixed, this test will pass, confirming the expected behavior is satisfied.
"""

import pytest
import sys
import importlib.util
from pathlib import Path


def test_agentv5_import_without_indentation_error():
    """
    Test that importing agentv5.py module succeeds without IndentationError.
    
    **Validates: Requirements 1.1, 2.1**
    
    Bug Condition: input.type == "IMPORT" AND input.module == "agentv5.py" 
                   AND RequestTrackingMiddleware.hasEmptyBody()
    
    Expected Behavior (after fix): Backend imports successfully without IndentationError
    
    On UNFIXED code: This test will FAIL with IndentationError at line 1646
    On FIXED code: This test will PASS
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    assert agentv5_path.exists(), f"agentv5.py not found at {agentv5_path}"
    
    # Attempt to compile the module - this will catch IndentationError
    try:
        with open(agentv5_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Compile the code - this will raise IndentationError if the bug exists
        compile(code, str(agentv5_path), 'exec')
        
    except IndentationError as e:
        # If we get an IndentationError, the bug exists
        # Document the error for the bug report
        pytest.fail(
            f"IndentationError detected in agentv5.py at line {e.lineno}: {e.msg}\n"
            f"This confirms Critical Bug 1 exists.\n"
            f"Error details: {str(e)}"
        )
    except SyntaxError as e:
        # Other syntax errors might also indicate the bug
        pytest.fail(
            f"SyntaxError detected in agentv5.py at line {e.lineno}: {e.msg}\n"
            f"Error details: {str(e)}"
        )


def test_request_tracking_middleware_has_body():
    """
    Test that RequestTrackingMiddleware class has a properly defined body.
    
    **Validates: Requirements 1.1, 2.1**
    
    This test verifies that the RequestTrackingMiddleware class is not empty
    and has the required dispatch method.
    
    On UNFIXED code: This test will FAIL because the class has no body
    On FIXED code: This test will PASS
    """
    # Get the path to agentv5.py
    backend_dir = Path(__file__).parent.parent
    agentv5_path = backend_dir / "agentv5.py"
    
    # Read the file and check for the class definition
    with open(agentv5_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that RequestTrackingMiddleware class exists
    assert "class RequestTrackingMiddleware" in content, \
        "RequestTrackingMiddleware class not found in agentv5.py"
    
    # Check that the class has a dispatch method (not an empty body)
    # An empty class body would cause IndentationError
    assert "async def dispatch(self, request: Request, call_next):" in content, \
        "RequestTrackingMiddleware.dispatch method not found - class may have empty body"
    
    # Verify the dispatch method has implementation (not just pass)
    # Look for key functionality in the dispatch method
    lines = content.split('\n')
    in_dispatch = False
    dispatch_has_implementation = False
    
    for i, line in enumerate(lines):
        if "class RequestTrackingMiddleware" in line:
            # Found the class, now look for dispatch method
            for j in range(i, min(i + 100, len(lines))):
                if "async def dispatch" in lines[j]:
                    in_dispatch = True
                elif in_dispatch and ("graceful_shutdown.request_started()" in lines[j] or 
                                     "await call_next(request)" in lines[j]):
                    dispatch_has_implementation = True
                    break
            break
    
    assert dispatch_has_implementation, \
        "RequestTrackingMiddleware.dispatch method appears to be empty or incomplete"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
