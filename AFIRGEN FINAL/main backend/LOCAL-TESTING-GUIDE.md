# Local Testing Guide for Windows

This guide walks you through testing the AFIRGen backend locally on Windows before deploying to EC2.

## Prerequisites

Before starting, ensure you have:
- Python 3.11+ installed on Windows
- Git installed
- AWS CLI configured with credentials
- Access to AWS services (Bedrock, Transcribe, Textract, S3, RDS)
- MySQL Workbench or similar tool (optional, for database inspection)

## Task 16.1: Set Up Local Development Environment

### 1. Install Python 3.11+

Check your Python version:
```bash
python --version
```

If you need to install Python, download from: https://www.python.org/downloads/

### 2. Navigate to Backend Directory

```bash
cd "AFIRGEN FINAL/main backend"
```

### 3. Create Virtual Environment

```bash
python -m venv venv
```

### 4. Activate Virtual Environment

**If you get an execution policy error in PowerShell, run this first:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

**Option A: Use the helper script (Recommended)**

PowerShell:
```powershell
.\activate-venv.ps1
```

CMD:
```cmd
activate-venv.bat
```

**Option B: Manual activation**

On Windows (PowerShell):
```powershell
.\venv\Scripts\Activate.ps1
```

On Windows (CMD):
```cmd
venv\Scripts\activate.bat
```

On Git Bash:
```bash
source venv/Scripts/activate
```

**Verify activation:**
You should see `(venv)` at the beginning of your command prompt.

### 5. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` file with your configuration:
```env
# AWS Configuration
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-s3-bucket-name
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Database Configuration
DB_HOST=afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_USER=admin
DB_PASSWORD=Prathiush12.
DB_NAME=afirgen

# API Configuration
API_KEY=your-test-api-key

# Optional Configuration (defaults shown)
RATE_LIMIT_PER_MINUTE=100
REQUEST_TIMEOUT=60
MAX_FILE_SIZE_MB=10
```

**Important:** Use test/development credentials for local testing, not production credentials.

## Task 16.2: Test Database Connectivity

### 1. Test MySQL RDS Connection

Create a test script `test_db_connection.py`:
```python
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    print("✓ MySQL RDS connection successful!")
    print(f"  Connected to: {os.getenv('DB_HOST')}")
    print(f"  Database: {os.getenv('DB_NAME')}")
    conn.close()
except Exception as e:
    print(f"✗ MySQL RDS connection failed: {e}")
```

Run the test:
```bash
python test_db_connection.py
```

### 2. Verify SQLite Sessions Database

The sessions database will be created automatically when you start the backend. It will be located at:
- `sessions.db` in the backend directory

### 3. Test Database Table Initialization

Start the backend once to initialize tables:
```bash
python -c "from agentv5 import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)" &
```

Wait a few seconds, then stop it (Ctrl+C). Check the logs to verify tables were created.

## Task 16.3: Test AWS Service Access

### 1. Configure AWS Credentials

Ensure your AWS credentials are configured:
```bash
aws configure
```

Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

### 2. Test AWS Bedrock Access

Create a test script `test_bedrock.py`:
```python
import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv()

try:
    client = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION'))
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "Say 'Hello, AFIRGen!' in one sentence."
            }
        ]
    })
    
    response = client.invoke_model(
        modelId=os.getenv('BEDROCK_MODEL_ID'),
        body=body
    )
    
    response_body = json.loads(response['body'].read())
    print("✓ AWS Bedrock access successful!")
    print(f"  Model: {os.getenv('BEDROCK_MODEL_ID')}")
    print(f"  Response: {response_body['content'][0]['text']}")
except Exception as e:
    print(f"✗ AWS Bedrock access failed: {e}")
```

Run the test:
```bash
python test_bedrock.py
```

### 3. Test AWS Transcribe Access

```python
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

try:
    client = boto3.client('transcribe', region_name=os.getenv('AWS_REGION'))
    response = client.list_transcription_jobs(MaxResults=1)
    print("✓ AWS Transcribe access successful!")
    print(f"  Region: {os.getenv('AWS_REGION')}")
except Exception as e:
    print(f"✗ AWS Transcribe access failed: {e}")
```

### 4. Test AWS Textract Access

```python
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

try:
    client = boto3.client('textract', region_name=os.getenv('AWS_REGION'))
    # Just test that we can create the client
    print("✓ AWS Textract access successful!")
    print(f"  Region: {os.getenv('AWS_REGION')}")
except Exception as e:
    print(f"✗ AWS Textract access failed: {e}")
```

### 5. Test S3 Bucket Access

```python
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

try:
    client = boto3.client('s3', region_name=os.getenv('AWS_REGION'))
    bucket = os.getenv('S3_BUCKET_NAME')
    
    # Test bucket access
    client.head_bucket(Bucket=bucket)
    print("✓ S3 bucket access successful!")
    print(f"  Bucket: {bucket}")
    print(f"  Region: {os.getenv('AWS_REGION')}")
except Exception as e:
    print(f"✗ S3 bucket access failed: {e}")
```

## Task 16.4: Run Local Backend Server

### 1. Start the Backend

```bash
uvicorn agentv5:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag enables auto-reload on code changes (useful for development).

### 2. Verify Health Check

Open a new terminal and test the health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "aws_bedrock": "ok"
  },
  "timestamp": "2024-03-04T12:00:00Z"
}
```

### 3. Check Logs

Monitor the logs in the terminal where you started the backend. Look for:
- ✓ Configuration validated
- ✓ Database tables initialized
- ✓ IPC sections loaded
- ✓ Application startup complete

Also check `logs/main_backend.log` for detailed logs.

## Task 16.5: Test FIR Generation Workflow Locally

### 1. Test Text Input FIR Generation

Create a test script `test_fir_generation.py`:
```python
import requests
import json
import time

API_BASE = "http://localhost:8000"
API_KEY = "your-test-api-key"  # Match your .env file

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Test text input
print("Testing text input FIR generation...")
response = requests.post(
    f"{API_BASE}/process",
    headers=headers,
    json={
        "input_type": "text",
        "text": "I want to report a theft. Someone stole my laptop from my office yesterday.",
        "language": "en-IN"
    }
)

if response.status_code == 200:
    data = response.json()
    session_id = data['session_id']
    print(f"✓ FIR generation started. Session ID: {session_id}")
    
    # Poll for completion
    print("Polling for completion...")
    for i in range(30):  # Poll for up to 5 minutes
        time.sleep(10)
        status_response = requests.get(
            f"{API_BASE}/session/{session_id}",
            headers=headers
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"  Status: {status_data['status']}")
            
            if status_data['status'] == 'completed':
                print(f"✓ FIR generation completed!")
                print(f"  FIR Number: {status_data.get('fir_number')}")
                print(f"  Transcript: {status_data.get('transcript', '')[:100]}...")
                
                # Verify all 30 fields
                fir_content = status_data.get('fir_content', {})
                if len(fir_content) >= 30:
                    print(f"✓ All 30 FIR fields generated")
                else:
                    print(f"✗ Only {len(fir_content)} fields generated (expected 30)")
                break
            elif status_data['status'] == 'failed':
                print(f"✗ FIR generation failed: {status_data.get('error')}")
                break
else:
    print(f"✗ FIR generation failed: {response.status_code} - {response.text}")
```

Run the test:
```bash
python test_fir_generation.py
```

### 2. Test Audio Input (Optional)

If you have a test audio file:
```python
import requests

API_BASE = "http://localhost:8000"
API_KEY = "your-test-api-key"

headers = {"X-API-Key": API_KEY}

with open("test_audio.wav", "rb") as f:
    files = {"file": f}
    data = {
        "input_type": "audio",
        "language": "en-IN"
    }
    response = requests.post(
        f"{API_BASE}/process",
        headers=headers,
        data=data,
        files=files
    )
    
    if response.status_code == 200:
        print(f"✓ Audio FIR generation started: {response.json()}")
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")
```

### 3. Test Image Input (Optional)

If you have a test image file:
```python
import requests

API_BASE = "http://localhost:8000"
API_KEY = "your-test-api-key"

headers = {"X-API-Key": API_KEY}

with open("test_image.jpg", "rb") as f:
    files = {"file": f}
    data = {
        "input_type": "image",
        "language": "en-IN"
    }
    response = requests.post(
        f"{API_BASE}/process",
        headers=headers,
        data=data,
        files=files
    )
    
    if response.status_code == 200:
        print(f"✓ Image FIR generation started: {response.json()}")
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")
```

### 4. Test PDF Generation

After generating a FIR, test PDF generation:
```python
import requests

API_BASE = "http://localhost:8000"
API_KEY = "your-test-api-key"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

response = requests.post(
    f"{API_BASE}/authenticate",
    headers=headers,
    json={
        "session_id": "your-session-id",
        "complainant_signature": "John Doe",
        "officer_signature": "Officer Smith"
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"✓ PDF generated successfully!")
    print(f"  FIR Number: {data['fir_number']}")
    print(f"  PDF URL: {data['pdf_url']}")
else:
    print(f"✗ PDF generation failed: {response.status_code} - {response.text}")
```

## Task 16.6: Test Frontend Integration Locally

### 1. Open Frontend

Navigate to the frontend directory and open `index.html` in your browser:
```bash
cd "../frontend"
start index.html  # Windows
```

Or use a local web server:
```bash
python -m http.server 8080
```

Then open: http://localhost:8080

### 2. Configure Frontend for Local Backend

Ensure `js/config.js` points to localhost:
```javascript
API_BASE_URL: 'http://localhost:8000'
```

### 3. Test Frontend Features

- Test text input FIR generation
- Test file upload (audio/image)
- Test session status polling
- Test FIR retrieval
- Test PDF generation
- Test error handling

### 4. Use Connectivity Test Page

Open `test-backend-connectivity.html` in your browser and:
- Select "Use Localhost"
- Click "Test /health Endpoint"
- Click "Test All Endpoints"

## Task 16.7: Document Local Testing Results

Create a file `LOCAL-TESTING-RESULTS.md` with your findings:

```markdown
# Local Testing Results

## Environment
- OS: Windows 11
- Python Version: 3.11.x
- Date: 2024-03-04

## Database Connectivity
- [ ] MySQL RDS connection: ✓ Success / ✗ Failed
- [ ] SQLite sessions.db creation: ✓ Success / ✗ Failed
- [ ] Table initialization: ✓ Success / ✗ Failed

## AWS Service Access
- [ ] AWS Bedrock: ✓ Success / ✗ Failed
- [ ] AWS Transcribe: ✓ Success / ✗ Failed
- [ ] AWS Textract: ✓ Success / ✗ Failed
- [ ] S3 Bucket: ✓ Success / ✗ Failed

## Backend Server
- [ ] Server starts without errors: ✓ Success / ✗ Failed
- [ ] Health check responds: ✓ Success / ✗ Failed
- [ ] Logs are created: ✓ Success / ✗ Failed

## FIR Generation
- [ ] Text input: ✓ Success / ✗ Failed
- [ ] Audio input: ✓ Success / ✗ Failed / ⊘ Skipped
- [ ] Image input: ✓ Success / ✗ Failed / ⊘ Skipped
- [ ] All 30 fields generated: ✓ Success / ✗ Failed
- [ ] PDF generation: ✓ Success / ✗ Failed

## Frontend Integration
- [ ] Frontend loads: ✓ Success / ✗ Failed
- [ ] API connectivity: ✓ Success / ✗ Failed
- [ ] End-to-end workflow: ✓ Success / ✗ Failed

## Issues Encountered
(List any issues and their solutions)

## Windows-Specific Notes
(Document any Windows-specific issues or workarounds)
```

## Troubleshooting

### Issue: Virtual Environment Won't Activate (PowerShell)

**Error:** "cannot be loaded because running scripts is disabled on this system"

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

Then try activating again:
```powershell
.\venv\Scripts\Activate.ps1
```

Or use the helper script:
```powershell
.\activate-venv.ps1
```

### Issue: ModuleNotFoundError

**Solution:** Ensure virtual environment is activated and dependencies are installed:
```bash
pip install -r requirements.txt
```

### Issue: Database Connection Failed

**Solution:** 
- Check RDS security group allows your IP
- Verify credentials in `.env` file
- Test connection with MySQL Workbench

### Issue: AWS Service Access Denied

**Solution:**
- Verify AWS credentials are configured
- Check IAM permissions for Bedrock, Transcribe, Textract, S3
- Ensure region is correct

### Issue: Port 8000 Already in Use

**Solution:**
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or use a different port
uvicorn agentv5:app --host 0.0.0.0 --port 8001
```

### Issue: CORS Errors in Frontend

**Solution:** Ensure CORS middleware is enabled in `agentv5.py` and allows your frontend origin.

## Next Steps

After successful local testing:
1. Commit all changes to git
2. Push to remote repository
3. Proceed with EC2 deployment (Task 17)

## Additional Resources

- Backend README: `README.md`
- Frontend Configuration: `../frontend/FRONTEND-CONFIGURATION-GUIDE.md`
- AWS Documentation: https://docs.aws.amazon.com/
