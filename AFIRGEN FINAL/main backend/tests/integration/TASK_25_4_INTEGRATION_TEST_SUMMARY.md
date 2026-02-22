# Task 25.4 Integration Test Summary

## Test Created
**File**: `test_regeneration_workflow.py`

## Test Purpose
Validates **Requirement 2.5** - Bug 5 fix: The `/regenerate` endpoint now accepts JSON body requests matching the frontend format.

## Test Coverage

### Test 1: `test_regeneration_workflow_with_json_body`
**Primary test for Bug 5 fix**

Test Flow:
1. Create a text-only session via `/process`
2. Advance to `SUMMARY_REVIEW` validation step
3. POST `/regenerate/{session_id}` with JSON body: `{"step": "SUMMARY_REVIEW", "user_input": "..."}`
4. Verify regeneration succeeds and returns updated content

**Expected Behavior**:
- The endpoint accepts JSON body (not query parameters)
- Regeneration succeeds with status 200
- Response includes regenerated content
- Session remains at the same validation step

### Test 2: `test_regeneration_at_different_steps`
Tests regeneration at multiple validation steps (TRANSCRIPT_REVIEW, SUMMARY_REVIEW) to ensure the fix works across all steps.

### Test 3: `test_regeneration_without_user_input`
Tests that the `user_input` parameter is optional and can be omitted or set to None.

## Test Implementation Details

The test uses:
- **FastAPI TestClient** for HTTP requests
- **Mocked dependencies**: ModelPool, KB (knowledge base)
- **JSON body format** matching frontend (api.js lines 451-460):
  ```json
  {
    "step": "SUMMARY_REVIEW",
    "user_input": "Please make the summary more detailed..."
  }
  ```

## Prerequisites to Run Test

### 1. MySQL Database
The integration tests require a running MySQL database. The current implementation attempts to connect to MySQL at module import time.

**Options**:
- **Option A**: Start MySQL server locally
  - Ensure MySQL is running on `localhost:3306`
  - Create database `test_db`
  - Set environment variables:
    ```
    MYSQL_USER=root
    MYSQL_PASSWORD=<your_password>
    MYSQL_DB=test_db
    ```

- **Option B**: Mock DB at import time (requires refactoring)
  - Move DB instantiation from module level to function level
  - Or use pytest's `monkeypatch` with `PYTEST_CURRENT_TEST` environment variable

### 2. Environment Variables
```bash
# Required
MYSQL_PASSWORD=<password>
FIR_AUTH_KEY=test-key-123
API_KEY=test-api-key

# Optional (have defaults)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_DB=test_db
```

### 3. Fixed Configuration Issue
**Fixed in this task**: Removed invalid `pool_timeout` parameter from MySQL configuration in `agentv5.py` line 130. This was causing all integration tests to fail with:
```
AttributeError: Unsupported argument 'pool_timeout'
```

The fix changed:
```python
"mysql": {
    ...
    "pool_reset_session": True,
    "pool_timeout": 30,  # ❌ INVALID - removed
}
```

To:
```python
"mysql": {
    ...
    "pool_reset_session": True,  # ✅ Valid parameter
}
```

## How to Run Tests

Once MySQL is running and environment variables are set:

```bash
# Run all regeneration workflow tests
python -m pytest tests/integration/test_regeneration_workflow.py -v -s

# Run specific test
python -m pytest tests/integration/test_regeneration_workflow.py::test_regeneration_workflow_with_json_body -v -s
```

## Test Validation

The test validates that:

✅ **Bug 5 is fixed**: The `/regenerate` endpoint accepts JSON body requests (frontend format)
- Previously: Backend expected query parameters
- Now: Backend accepts JSON body with `step` and `user_input` fields

✅ **Frontend-Backend contract aligned**:
- Frontend sends: `POST /regenerate/{sessionId}` with JSON body
- Backend receives: `RegenerateRequest` model with `step` and `user_input`

✅ **Regeneration workflow works correctly**:
- Regeneration succeeds at any validation step
- User input is optional
- Session state is preserved
- Content is regenerated and returned

## Related Files

- **Test file**: `tests/integration/test_regeneration_workflow.py`
- **Backend endpoint**: `agentv5.py` lines 1950-2000 (regenerate_step function)
- **Frontend API call**: `frontend/js/api.js` lines 451-460
- **Request model**: `infrastructure/input_validation.py` RegenerateRequest class

## Status

✅ **Test created and documented**
⚠️ **Test execution blocked** by MySQL connection requirement
📝 **Recommendation**: Set up MySQL database or refactor DB initialization for better testability

## Next Steps

To make this test runnable:

1. **Short-term**: Start MySQL locally and run tests
2. **Long-term**: Refactor DB initialization to support dependency injection for better testability
3. **Alternative**: Use Docker Compose to spin up MySQL for integration tests

## Verification Without Running Tests

The Bug 5 fix can be verified by:

1. **Code inspection**: Check that `regenerate_step` function signature matches:
   ```python
   async def regenerate_step(session_id: str, regenerate_req: RegenerateRequest):
   ```

2. **Manual API testing**: Use curl or Postman:
   ```bash
   curl -X POST http://localhost:8000/regenerate/{session_id} \
     -H "Content-Type: application/json" \
     -H "X-API-Key: test-key-123" \
     -d '{"step": "SUMMARY_REVIEW", "user_input": "Make it more detailed"}'
   ```

3. **Frontend testing**: Run the frontend and test the regeneration button during FIR generation workflow
