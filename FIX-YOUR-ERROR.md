# Fix Your Error - AWS CLI Not Found

## Your Error
```
process_begin: CreateProcess(NULL, aws configure, ...) failed.
make (e=2): The system cannot find the file specified.
```

## What This Means
AWS CLI is not installed on your computer yet.

## Quick Fix (3 Steps)

### Step 1: Install AWS CLI

**Option A: Download and Install (Easiest)**
1. Click this link: https://awscli.amazonaws.com/AWSCLIV2.msi
2. Save the file
3. Double-click the downloaded file
4. Click "Next" → "Next" → "Install"
5. Wait for installation to complete
6. Click "Finish"

**Option B: Use PowerShell Script**
```powershell
.\install-aws-cli.ps1
```

### Step 2: Close and Reopen PowerShell
**Important!** You must close PowerShell completely and open a new window.

### Step 3: Verify It Works
```powershell
aws --version
```

You should see: `aws-cli/2.x.x ...`

If you see this, AWS CLI is installed! ✅

---

## Now Configure AWS

```powershell
aws configure
```

You'll be asked for 4 things:

1. **AWS Access Key ID**: 
   - Go to https://console.aws.amazon.com/
   - Click your name (top right) → Security credentials
   - Scroll to "Access keys" → Create access key
   - Copy the Access Key ID

2. **AWS Secret Access Key**: 
   - Copy from the same screen (you won't see it again!)

3. **Default region name**: 
   - Type: `us-east-1`

4. **Default output format**: 
   - Type: `json`

---

## Then Deploy

```powershell
cd "C:\Users\knith\OneDrive\Desktop\AFIRGen-1"
make deploy-all
```

---

## If Make Still Doesn't Work

You might also need to install other tools. Run this:

```powershell
# Check what's installed
terraform --version
python --version
make --version
```

If any command fails, install that tool:

**Terraform:**
- Download: https://www.terraform.io/downloads
- Extract to `C:\terraform`
- Add to PATH

**Python:**
- Download: https://www.python.org/downloads/
- Install (check "Add Python to PATH")

**Make:**
- Install Chocolatey first: https://chocolatey.org/install
- Then: `choco install make -y`

---

## Alternative: Skip Make

If make is too much trouble, use commands directly:

### 1. Configure AWS
```powershell
aws configure
```

### 2. Install Python packages
```powershell
pip install huggingface-hub datasets transformers torch
```

### 3. Deploy with Terraform
```powershell
cd "AFIRGEN FINAL\terraform\free-tier"
terraform init
terraform apply
```

---

## Summary

**Right now, do this:**

1. Download AWS CLI: https://awscli.amazonaws.com/AWSCLIV2.msi
2. Install it (double-click, click Next/Install)
3. Close PowerShell
4. Open new PowerShell
5. Run: `aws --version` (should work now)
6. Run: `aws configure` (enter your credentials)
7. Run: `make deploy-all`

**That's it!** 🚀
