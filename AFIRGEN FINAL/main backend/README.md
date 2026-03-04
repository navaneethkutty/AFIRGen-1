# AFIRGen Backend - AWS Bedrock Architecture

Minimal, production-ready backend for automated FIR (First Information Report) generation using AWS managed services.

## Architecture Overview

- **FastAPI** application in single file (agentv5.py)
- **AWS Bedrock** (Claude 3 Sonnet) for text generation
- **AWS Transcribe** for audio-to-text
- **AWS Textract** for image OCR
- **Amazon RDS MySQL** for persistent storage
- **Amazon S3** for temporary file storage
- **SQLite** for session management

## Quick Start Guides

- **[Local Testing Guide](LOCAL-TESTING-GUIDE.md)** - Complete guide for testing on Windows
- **[EC2 Deployment Guide](EC2-DEPLOYMENT-GUIDE.md)** - Step-by-step EC2 deployment
- **[Final Checkpoint Guide](FINAL-CHECKPOINT-GUIDE.md)** - Production readiness verification
- **[Frontend Configuration](../frontend/FRONTEND-CONFIGURATION-GUIDE.md)** - Frontend setup

## Prerequisites

### For Local Development (Windows)

- Python 3.11 or higher
- AWS credentials configured (via AWS CLI or environment variables)
- Access to AWS services (Bedrock, Transcribe, Textract, S3, RDS)
- MySQL RDS instance running and accessible
- S3 bucket created

### For EC2 Deployment (Linux)

- EC2 instance (t2.micro or larger)
- IAM role attached to EC2 with permissions for:
  - Bedrock (invoke model)
  - Transcribe (start/get transcription jobs)
  - Textract (detect document text)
  - S3 (read/write/delete objects)
- MySQL RDS instance accessible from EC2 security group
- S3 bucket created

## Local Development Setup (Windows)

**For detailed instructions, see [LOCAL-TESTING-GUIDE.md](LOCAL-TESTING-GUIDE.md)**

### 1. Clone Repository

```bash
git clone <repository-url>
cd "AFIRGEN FINAL/main backend"
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file from the template:

```bash
copy .env.example .env
```

Edit `.env` file with your configuration:
- Set `AWS_REGION` (default: us-east-1)
- Set `S3_BUCKET_NAME` to your S3 bucket
- Set `DB_HOST`, `DB_PASSWORD` for MySQL RDS
- Set `API_KEY` for authentication
- Set AWS credentials if not using AWS CLI profile

**Windows-Specific Notes:**
- Use backslashes (`\`) or forward slashes (`/`) in paths - Python handles both
- Ensure your AWS credentials are configured via AWS CLI or environment variables
- If using AWS CLI, run `aws configure` to set up credentials
- The application will create `logs\` directory and `sessions.db` automatically

### 5. Load IPC Sections

The application requires IPC sections data. On first startup, it will automatically load from `ipc_sections.json`:

```bash
# Verify the file exists
dir ipc_sections.json

# The file contains 24 sample IPC sections
# You can edit this file to add more sections if needed
```

### 6. Initialize Database

The application will automatically create required tables on first startup.

### 7. Start Application

```bash
python -m uvicorn agentv5:app --host 0.0.0.0 --port 8000 --reload
```

**On first startup, the application will:**
1. Create MySQL tables (`fir_records`, `ipc_sections`)
2. Create SQLite database (`sessions.db`)
3. Load IPC sections from `ipc_sections.json` into MySQL
4. Start the API server on port 8000

**Windows Troubleshooting:**
- If you see "Address already in use", another application is using port 8000
- Change the port: `--port 8001`
- If you see database connection errors, verify RDS security group allows your IP
- If you see AWS errors, verify credentials with: `aws sts get-caller-identity`

### 8. Verify Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "checks": {
    "mysql": true,
    "bedrock": true
  },
  "timestamp": "2024-01-15T10:30:45.123Z"
}
```

## EC2 Deployment (Linux)

### 1. Connect to EC2 Instance

```bash
ssh -i your-key.pem ubuntu@98.86.30.145
```

### 2. Install Python 3.11

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git
```

### 3. Clone Repository

```bash
cd /home/ubuntu
git clone <repository-url> afirgen-backend
cd afirgen-backend/"AFIRGEN FINAL/main backend"
```

### 4. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure Environment

```bash
cp .env.example .env
nano .env
```

Set required variables:
- `S3_BUCKET_NAME`
- `DB_HOST`, `DB_PASSWORD`
- `API_KEY`

**Note:** AWS credentials are not needed if EC2 has IAM role attached.

### 7. Create Logs Directory

```bash
mkdir -p logs
```

### 8. Test Application

```bash
python -m uvicorn agentv5:app --host 0.0.0.0 --port 8000
```

Press Ctrl+C to stop after verifying it starts without errors.

### 9. Load IPC Sections into Database

The application requires IPC (Indian Penal Code) sections to be loaded into the MySQL database. This is done automatically on first startup if the `ipc_sections` table is empty.

**Option 1: Automatic loading (recommended)**

The application will automatically load IPC sections from `ipc_sections.json` on first startup. Just ensure the file exists:

```bash
ls -l ipc_sections.json
```

**Option 2: Manual loading**

If you need to manually load or reload IPC sections:

```bash
# Connect to MySQL
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME

# Verify table exists
SHOW TABLES LIKE 'ipc_sections';

# Check if sections are loaded
SELECT COUNT(*) FROM ipc_sections;

# Exit MySQL
exit
```

Then start the application once to trigger automatic loading, or use a custom script.

### 10. Create Systemd Service

Copy the provided systemd service file:

```bash
sudo cp afirgen.service /etc/systemd/system/afirgen.service
```

Or create it manually:

```bash
sudo nano /etc/systemd/system/afirgen.service
```

Add the following content (adjust paths if your installation directory differs):

```ini
[Unit]
Description=AFIRGen Backend Service - Automated FIR Generation
Documentation=https://github.com/your-repo/afirgen
After=network.target mysql.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/afirgen-backend/AFIRGEN FINAL/main backend
Environment="PATH=/home/ubuntu/afirgen-backend/AFIRGEN FINAL/main backend/venv/bin"
EnvironmentFile=/home/ubuntu/afirgen-backend/AFIRGEN FINAL/main backend/.env
ExecStart=/home/ubuntu/afirgen-backend/AFIRGEN FINAL/main backend/venv/bin/uvicorn agentv5:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/afirgen-backend/AFIRGEN FINAL/main backend/logs/systemd.log
StandardError=append:/home/ubuntu/afirgen-backend/AFIRGEN FINAL/main backend/logs/systemd-error.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/ubuntu/afirgen-backend/AFIRGEN FINAL/main backend/logs
ReadWritePaths=/home/ubuntu/afirgen-backend/AFIRGEN FINAL/main backend/sessions.db

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

**Important Notes:**
- `EnvironmentFile` loads environment variables from `.env` file
- `StandardOutput` and `StandardError` redirect systemd logs to files
- Security hardening options restrict file system access
- Adjust `WorkingDirectory` and paths if you installed in a different location

### 11. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable afirgen
sudo systemctl start afirgen
```

### 12. Check Service Status

```bash
sudo systemctl status afirgen
```

### 13. View Logs

```bash
# Application logs
tail -f logs/main_backend.log

# Systemd logs (stdout/stderr)
tail -f logs/systemd.log
tail -f logs/systemd-error.log

# Systemd journal
sudo journalctl -u afirgen -f
```

### 14. Configure Firewall

```bash
sudo ufw allow 8000/tcp
sudo ufw enable
```

## AWS IAM Role Configuration

Create an IAM role with the following policy and attach to EC2:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
    },
    {
      "Effect": "Allow",
      "Action": [
        "transcribe:StartTranscriptionJob",
        "transcribe:GetTranscriptionJob"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "textract:DetectDocumentText"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

## API Endpoints

### POST /process
Process complaint input (text, audio, or image) and generate FIR.

**Headers:**
- `X-API-Key`: Your API key

**Request Body:**
```json
{
  "input_type": "text",
  "text": "Complaint text here",
  "language": "en-IN"
}
```

**Response:**
```json
{
  "session_id": "abc-123-def-456",
  "status": "processing",
  "message": "FIR generation started"
}
```

### GET /session/{session_id}
Poll session status and retrieve results.

**Headers:**
- `X-API-Key`: Your API key

**Response:**
```json
{
  "session_id": "abc-123-def-456",
  "status": "completed",
  "transcript": "Transcribed text",
  "summary": "Formal narrative",
  "violations": [...],
  "fir_content": {...},
  "fir_number": "FIR-20240115-00001"
}
```

### POST /authenticate
Finalize FIR and generate PDF.

**Headers:**
- `X-API-Key`: Your API key

**Request Body:**
```json
{
  "session_id": "abc-123-def-456",
  "complainant_signature": "signature_data",
  "officer_signature": "signature_data"
}
```

### GET /fir/{fir_number}
Retrieve FIR by number.

**Headers:**
- `X-API-Key`: Your API key

### GET /firs
List all FIRs with pagination.

**Headers:**
- `X-API-Key`: Your API key

**Query Parameters:**
- `limit`: Number of records (default: 20, max: 100)
- `offset`: Offset for pagination (default: 0)

### GET /health
Health check endpoint (no authentication required).

## Troubleshooting

### Application Won't Start

**Windows:**

1. **Check Python version:**
   ```bash
   python --version
   # Should be 3.11 or higher
   ```

2. **Check virtual environment is activated:**
   ```bash
   # You should see (venv) in your prompt
   # If not, activate it:
   venv\Scripts\activate
   ```

3. **Check environment variables:**
   ```bash
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('S3_BUCKET_NAME:', os.getenv('S3_BUCKET_NAME'))"
   ```

4. **Check database connectivity:**
   ```bash
   # Install MySQL client if needed
   pip install mysql-connector-python
   python -c "import mysql.connector; conn = mysql.connector.connect(host='your-host', user='admin', password='your-password'); print('Connected!')"
   ```

5. **Check AWS credentials:**
   ```bash
   aws sts get-caller-identity
   # Should return your AWS account info
   ```

6. **Check logs:**
   ```bash
   type logs\main_backend.log
   ```

**Linux (EC2):**

1. **Check environment variables:**
   ```bash
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('S3_BUCKET_NAME:', os.getenv('S3_BUCKET_NAME'))"
   ```

2. **Check database connectivity:**
   ```bash
   mysql -h $DB_HOST -u $DB_USER -p
   ```

3. **Check AWS credentials (should use IAM role):**
   ```bash
   aws sts get-caller-identity
   ```

4. **Check logs:**
   ```bash
   tail -f logs/main_backend.log
   sudo journalctl -u afirgen -n 50
   ```

5. **Check systemd service status:**
   ```bash
   sudo systemctl status afirgen
   ```

### IPC Sections Not Loading

**Symptoms:**
- FIR generation fails with "No IPC sections found"
- Empty `ipc_sections` table in MySQL

**Solutions:**

1. **Verify JSON file exists:**
   ```bash
   # Windows
   dir ipc_sections.json
   
   # Linux
   ls -l ipc_sections.json
   ```

2. **Verify JSON file is valid:**
   ```bash
   python -c "import json; print(len(json.load(open('ipc_sections.json'))))"
   # Should print: 24
   ```

3. **Check MySQL table:**
   ```bash
   mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "SELECT COUNT(*) FROM ipc_sections;"
   ```

4. **Manually load IPC sections:**
   
   If automatic loading fails, you can manually insert sections:
   
   ```bash
   # Connect to MySQL
   mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME
   
   # Check if table exists
   SHOW TABLES LIKE 'ipc_sections';
   
   # If empty, restart the application to trigger auto-load
   # Or manually insert from JSON (requires custom script)
   ```

5. **Check application logs for loading errors:**
   ```bash
   # Windows
   findstr "ipc_sections" logs\main_backend.log
   
   # Linux
   grep "ipc_sections" logs/main_backend.log
   ```

### FIR Generation Fails

1. **Check Bedrock access:**
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   # Should list available models including Claude 3 Sonnet
   ```

2. **Check Bedrock model permissions:**
   ```bash
   # Verify your IAM role/user has bedrock:InvokeModel permission
   aws bedrock get-foundation-model --model-identifier anthropic.claude-3-sonnet-20240229-v1:0 --region us-east-1
   ```

3. **Check S3 bucket access:**
   ```bash
   aws s3 ls s3://$S3_BUCKET_NAME
   ```

4. **Check session status for detailed error:**
   ```bash
   curl -H "X-API-Key: your-key" http://localhost:8000/session/{session_id}
   ```

5. **Check application logs for AWS errors:**
   ```bash
   # Windows
   findstr "ERROR" logs\main_backend.log
   
   # Linux
   grep "ERROR" logs/main_backend.log
   ```

### Database Errors

**Windows:**

1. **Check RDS security group allows your IP:**
   - Go to AWS Console → RDS → Your instance → Security groups
   - Ensure inbound rule allows MySQL (port 3306) from your IP

2. **Test connection manually:**
   ```bash
   mysql -h your-rds-endpoint.rds.amazonaws.com -u admin -p
   ```

3. **Check for "Too many connections" errors:**
   ```bash
   mysql -h $DB_HOST -u $DB_USER -p -e "SHOW PROCESSLIST;"
   ```

**Linux (EC2):**

1. Check RDS status in AWS console
2. Verify security group allows EC2 security group access
3. Test connection manually
4. Check for "Too many connections" errors

### Port Already in Use (Windows)

If port 8000 is already in use:

1. **Find process using port 8000:**
   ```bash
   netstat -ano | findstr :8000
   ```

2. **Kill the process:**
   ```bash
   taskkill /PID <process_id> /F
   ```

3. **Or use a different port:**
   ```bash
   python -m uvicorn agentv5:app --host 0.0.0.0 --port 8001
   ```

### Systemd Service Issues (Linux)

1. **Service fails to start:**
   ```bash
   # Check detailed status
   sudo systemctl status afirgen -l
   
   # Check journal logs
   sudo journalctl -u afirgen -n 100 --no-pager
   ```

2. **Service starts but crashes:**
   ```bash
   # Check if .env file exists and is readable
   ls -l .env
   
   # Check if paths in service file are correct
   cat /etc/systemd/system/afirgen.service
   
   # Check if virtual environment is activated
   /home/ubuntu/afirgen-backend/AFIRGEN\ FINAL/main\ backend/venv/bin/python --version
   ```

3. **Permission errors:**
   ```bash
   # Ensure ubuntu user owns all files
   sudo chown -R ubuntu:ubuntu /home/ubuntu/afirgen-backend
   
   # Ensure logs directory is writable
   chmod 755 logs
   ```

4. **Reload service after changes:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart afirgen
   ```

### Import Errors

If you see import errors for removed modules:
- Ensure you're using the updated requirements.txt
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
- Check that agentv5.py doesn't import removed modules

## File Structure

```
AFIRGEN FINAL/main backend/
├── agentv5.py              # Main application file
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── .env                    # Your configuration (not in git)
├── README.md               # This file
├── afirgen.service         # Systemd service file for production
├── ipc_sections.json       # IPC sections data (24 sections)
├── sessions.db             # SQLite session storage
└── logs/
    ├── main_backend.log    # Application logs
    ├── systemd.log         # Systemd stdout logs
    └── systemd-error.log   # Systemd stderr logs
```

**Key Files:**

- **agentv5.py**: Single-file FastAPI application with all business logic
- **requirements.txt**: Minimal dependencies (9 packages)
- **.env**: Environment configuration (never commit this file)
- **afirgen.service**: Production systemd service configuration
- **ipc_sections.json**: Indian Penal Code sections database (auto-loaded on first startup)
- **sessions.db**: SQLite database for session management
- **logs/**: All application and system logs

## Maintenance

### Update Application

```bash
cd /home/ubuntu/afirgen-backend
git pull
cd "AFIRGEN FINAL/main backend"
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart afirgen
```

### Update IPC Sections

To add or modify IPC sections:

1. **Edit the JSON file:**
   ```bash
   nano ipc_sections.json
   ```

2. **Validate JSON syntax:**
   ```bash
   python -c "import json; json.load(open('ipc_sections.json'))"
   ```

3. **Update database:**
   ```bash
   # Connect to MySQL
   mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME
   
   # Clear existing sections (optional)
   DELETE FROM ipc_sections;
   
   # Exit and restart application to reload
   exit
   ```

4. **Restart application:**
   ```bash
   sudo systemctl restart afirgen
   ```

5. **Verify sections loaded:**
   ```bash
   mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "SELECT COUNT(*) FROM ipc_sections;"
   ```

### View Logs

```bash
# Last 100 lines
tail -n 100 logs/main_backend.log

# Follow logs in real-time
tail -f logs/main_backend.log

# Search for errors
grep ERROR logs/main_backend.log
```

### Clean Up Old Sessions

Sessions older than 24 hours are automatically cleaned up. To manually clean:

```bash
sqlite3 sessions.db "DELETE FROM sessions WHERE created_at < strftime('%s', 'now', '-1 day');"
```

### Backup Database

```bash
# Backup MySQL RDS
mysqldump -h $DB_HOST -u $DB_USER -p $DB_NAME > backup_$(date +%Y%m%d).sql

# Backup SQLite sessions
cp sessions.db sessions_backup_$(date +%Y%m%d).db
```

## Security Considerations

1. **Never commit .env file** - Contains sensitive credentials
2. **Use strong API keys** - Minimum 32 characters
3. **Rotate credentials regularly** - Update API keys and database passwords
4. **Use IAM roles on EC2** - Avoid hardcoding AWS credentials
5. **Enable RDS encryption** - Encrypt data at rest
6. **Use HTTPS in production** - Configure ALB/CloudFront with SSL
7. **Restrict security groups** - Only allow necessary ports and IPs
8. **Monitor CloudWatch logs** - Set up alerts for errors

## Performance Tuning

### Database Connection Pool

Default pool size is 5. Adjust in code if needed:
```python
pool_size=10  # Increase for high traffic
```

### Rate Limiting

Default is 100 requests/minute per IP. Adjust in .env:
```bash
RATE_LIMIT_PER_MINUTE=200
```

### Timeouts

Adjust timeouts in .env for slow networks:
```bash
TRANSCRIBE_TIMEOUT_SECONDS=300
BEDROCK_TIMEOUT_SECONDS=90
```

## Support

For issues or questions:
1. Check logs: `logs/main_backend.log`
2. Verify health endpoint: `curl http://localhost:8000/health`
3. Check AWS service status
4. Review CloudWatch logs for AWS service errors

## License

[Your License Here]
