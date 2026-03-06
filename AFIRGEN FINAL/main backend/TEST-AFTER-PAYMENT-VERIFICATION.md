# Test AFIRGen Backend After Payment Verification

## Current Status

✅ Backend deployed and running on EC2 (http://18.206.148.182:8000)
✅ All infrastructure configured (RDS, S3, Security Groups)
✅ Systemd service active
✅ Health endpoint working
⏳ **Waiting for AWS payment verification (24-48 hours)**

## What's Configured

- **Model**: Claude Sonnet 4.6 (`anthropic.claude-sonnet-4-6`)
- **EC2 Instance**: i-02ecca1d375ab2cec (18.206.148.182)
- **Database**: MySQL RDS + SQLite sessions
- **Legal KB**: 988 sections loaded

## How to Check if Payment is Verified

Run this command:

```powershell
aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic --query "modelSummaries[?contains(modelId, 'claude-sonnet-4-6')].{ModelId:modelId, Status:modelLifecycle.status}" --output table
```

Look for `Status: ACTIVE` (not just model access granted in console).

## Test Commands (After Verification)

### Option 1: Run the Test Script

```powershell
cd "C:\Users\knith\OneDrive\Desktop\AFIRGen-1\AFIRGEN FINAL\main backend"
.\test-ec2-nova-lite.ps1
```

### Option 2: Manual Test

```powershell
# 1. Health check
Invoke-RestMethod -Uri "http://18.206.148.182:8000/health" -Method Get -Headers @{"X-API-Key"="dev-test-key-12345678901234567890123456789012"}

# 2. Submit FIR request
$form = @{
    input_type = "text"
    text = "A person stole my mobile phone at the market yesterday"
}
$response = Invoke-RestMethod -Uri "http://18.206.148.182:8000/process" -Method Post -Headers @{"X-API-Key"="dev-test-key-12345678901234567890123456789012"} -Form $form

# 3. Check session status (replace SESSION_ID with actual value from step 2)
Invoke-RestMethod -Uri "http://18.206.148.182:8000/session/SESSION_ID" -Method Get -Headers @{"X-API-Key"="dev-test-key-12345678901234567890123456789012"}
```

## If It Still Doesn't Work

The backend is already configured correctly. If you still get payment errors after 24-48 hours:

1. Check AWS Bedrock console → Model access
2. Verify your payment method is valid
3. Contact AWS support if needed

## No Code Changes Needed

Once AWS verifies your payment method, the backend will work immediately. No restart or configuration changes required.

## Next Steps After Successful Test

1. Mark Task 17 subtasks complete in `.kiro/specs/backend-cleanup-aws/tasks.md`
2. Configure frontend to use `http://18.206.148.182:8000`
3. Complete Task 18 (Final checkpoint)
