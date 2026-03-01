# Simple Windows Installation Guide

You got an error because AWS CLI isn't installed yet. Here's the simplest way to fix it:

## Option 1: Direct AWS CLI Installation (Easiest)

### Step 1: Download and Install AWS CLI
1. Download: https://awscli.amazonaws.com/AWSCLIV2.msi
2. Double-click the downloaded file
3. Follow the installation wizard (click Next, Next, Install)
4. Close and reopen PowerShell

### Step 2: Verify Installation
```powershell
aws --version
```

You should see something like: `aws-cli/2.x.x Python/3.x.x Windows/10`

### Step 3: Configure AWS
```powershell
aws configure
```

Enter:
- **AWS Access Key ID**: (from your AWS Console)
- **AWS Secret Access Key**: (from your AWS Console)
- **Default region name**: `us-east-1`
- **Default output format**: `json`

### Step 4: Deploy
```powershell
cd "C:\Users\knith\OneDrive\Desktop\AFIRGen-1"
make deploy-all
```

---

## Option 2: Use PowerShell Script

Run this in PowerShell (normal, not admin):
```powershell
.\install-aws-cli.ps1
```

Then close and reopen PowerShell.

---

## Option 3: Skip Make, Use Commands Directly

If `make` isn't working, you can run commands directly:

### Configure AWS
```powershell
aws configure
```

### Deploy Infrastructure
```powershell
cd "AFIRGEN FINAL\terraform\free-tier"
terraform init
terraform apply
```

### Download Models
```powershell
cd ..\..
pip install huggingface-hub datasets
python -c "
from huggingface_hub import hf_hub_download
import os
os.makedirs('models', exist_ok=True)
hf_hub_download(repo_id='navaneeth005/complaint_2summarizing', filename='complaint_2summarizing.gguf', local_dir='models')
hf_hub_download(repo_id='navaneeth005/complaint_summarizing_model_gguf', filename='complaint_summarizing_model.gguf', local_dir='models')
hf_hub_download(repo_id='navaneeth005/BNS-RAG-gguf', filename='BNS-RAG-q4k.gguf', local_dir='models')
"
```

---

## Getting Your AWS Credentials

If you don't have AWS credentials yet:

1. Go to AWS Console: https://console.aws.amazon.com/
2. Click your name (top right) → Security credentials
3. Scroll to "Access keys"
4. Click "Create access key"
5. Choose "Command Line Interface (CLI)"
6. Check the confirmation box
7. Click "Create access key"
8. **Save both keys** (you won't see the secret key again!)

---

## Quick Fix for Your Error

Your error: `The system cannot find the file specified`

This means AWS CLI isn't installed. Fix it:

```powershell
# Download and run installer
Invoke-WebRequest -Uri "https://awscli.amazonaws.com/AWSCLIV2.msi" -OutFile "$env:TEMP\AWSCLIV2.msi"
Start-Process msiexec.exe -ArgumentList "/i `"$env:TEMP\AWSCLIV2.msi`" /qn" -Wait

# Close and reopen PowerShell, then:
aws --version
aws configure
```

---

## After AWS CLI is Installed

Once `aws --version` works:

```powershell
# Configure AWS
aws configure

# Then deploy
cd "C:\Users\knith\OneDrive\Desktop\AFIRGen-1"
make deploy-all
```

---

## Still Having Issues?

### Make Not Working?
Install make:
```powershell
choco install make -y
```

Or use Git Bash instead of PowerShell (if you have Git for Windows).

### Python Not Installed?
Download from: https://www.python.org/downloads/
- Check "Add Python to PATH" during installation

### Terraform Not Installed?
Download from: https://www.terraform.io/downloads
- Extract to `C:\terraform`
- Add to PATH

---

## Summary

**Simplest path:**
1. Download AWS CLI: https://awscli.amazonaws.com/AWSCLIV2.msi
2. Install it
3. Close and reopen PowerShell
4. Run: `aws configure`
5. Run: `make deploy-all`

**If make doesn't work:**
- Use the commands in "Option 3" above
- Or install make: `choco install make -y`
