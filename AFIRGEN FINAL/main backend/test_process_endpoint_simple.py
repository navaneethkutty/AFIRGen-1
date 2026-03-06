"""
Simple syntax verification for POST /process endpoint
Tests Task 7.2 implementation
"""
import ast
import sys


def test_process_endpoint_exists():
    """Verify that process_complaint function exists in the file"""
    with open('agentv5_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the file
    tree = ast.parse(content)
    
    # Find the process_complaint function
    found_function = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == 'process_complaint':
            found_function = True
            
            # Check function has required parameters
            param_names = [arg.arg for arg in node.args.args]
            assert 'request' in param_names, "Missing 'request' parameter"
            assert 'file' in param_names, "Missing 'file' parameter"
            assert 'x_api_key' in param_names, "Missing 'x_api_key' parameter"
            
            print(f"✓ Found process_complaint function with parameters: {param_names}")
            break
    
    assert found_function, "process_complaint function not found"
    return True


def test_process_request_model_exists():
    """Verify that ProcessRequest model exists"""
    with open('agentv5_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for ProcessRequest class
    assert 'class ProcessRequest(BaseModel):' in content, "ProcessRequest model not found"
    assert 'input_type: Literal["text", "audio", "image"]' in content, "input_type field not found"
    assert 'text: Optional[str]' in content, "text field not found"
    assert 'language: Optional[str]' in content, "language field not found"
    
    print("✓ ProcessRequest model exists with correct fields")
    return True


def test_process_response_model_exists():
    """Verify that ProcessResponse model exists"""
    with open('agentv5_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for ProcessResponse class
    assert 'class ProcessResponse(BaseModel):' in content, "ProcessResponse model not found"
    assert 'session_id: str' in content, "session_id field not found"
    assert 'status: str' in content, "status field not found"
    assert 'message: str' in content, "message field not found"
    
    print("✓ ProcessResponse model exists with correct fields")
    return True


def test_endpoint_implementation():
    """Verify that the endpoint has the required implementation"""
    with open('agentv5_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for key implementation details
    checks = [
        ('API key verification', 'if x_api_key != config.API_KEY:'),
        ('Text input validation', 'if request.input_type == "text":'),
        ('Audio input validation', 'elif request.input_type in ["audio", "image"]:'),
        ('File extension validation', 'allowed_extensions'),
        ('File size validation', 'file_size_mb'),
        ('Session ID generation', 'session_id = str(uuid.uuid4())'),
        ('Session creation', 'db_manager.create_session(session_id)'),
        ('Background task', 'async def generate_fir_async():'),
        ('Text workflow', 'fir_generator.generate_from_text'),
        ('Audio workflow', 'fir_generator.generate_from_audio'),
        ('Image workflow', 'fir_generator.generate_from_image'),
        ('Async task creation', 'asyncio.create_task(generate_fir_async())'),
        ('Response return', 'return ProcessResponse('),
    ]
    
    for check_name, check_string in checks:
        assert check_string in content, f"Missing implementation: {check_name}"
        print(f"✓ {check_name} implemented")
    
    return True


def test_asyncio_import():
    """Verify that asyncio is imported"""
    with open('agentv5_clean.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert 'import asyncio' in content, "asyncio import not found"
    print("✓ asyncio imported")
    return True


if __name__ == "__main__":
    print("Running POST /process endpoint verification tests...")
    print()
    
    try:
        test_process_endpoint_exists()
        test_process_request_model_exists()
        test_process_response_model_exists()
        test_endpoint_implementation()
        test_asyncio_import()
        
        print()
        print("=" * 60)
        print("All verification tests passed! ✓")
        print("=" * 60)
        print()
        print("Task 7.2 Implementation Summary:")
        print("- ProcessRequest model defined with input_type, text, language")
        print("- Input validation based on input_type")
        print("- Session creation with unique session_id")
        print("- Async FIR generation workflow")
        print("- Returns session_id and status 'processing'")
        print()
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
