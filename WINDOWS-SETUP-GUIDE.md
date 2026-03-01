# Windows Setup Guide for AFIRGen AWS Deployment

## Option 1: Automated Installation (Recommended)

### Step 1: Run PowerShell as Administrator
1. Press `Windows + X`
2. Select "Windows PowerShell (Admin)" or "Terminal (Admin)"

### Step 2: Run Installation Script
```powershell
cd "C:\Users\knith\OneDrive\Desktop\AFIRGen-1"
.\install-tools-windows.ps1
```

This installs:
- Chocolatey (package manager)
- Terraform
- AWS CLI
- Make
- Python

### Step 3: Close and Reopen PowerShell
**Important**: Close PowerShell and open a new one (normal, not admin) for changes to take effect.

### Step 4: Continue with Deployment
```powershell
cd "C:\Users\knith\OneDrive\Desktop\AFIRGen-1"
make setup-aws
make deploy-all
```

---

## Option 2: Manual Installation

If the automated script doesn't work, install manually:

### 1. Install Chocolatey
Open PowerShell as Administrator and run:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### 2. Install Tools
```powershell
choco install terraform -y
choco install awscli -y
choco install make -y
choco install python -y
```

### 3. Verify Installation
Close and reopen PowerShell, then:
```powershell
terraform --version
aws --version
make --version
python --version
```

---

## Option 3: Direct Downloads (No Chocolatey)

### Terraform
1. Download from: https://www.terraform.io/downloads
2. Extract to `C:\terraform`
3. Add to PATH:
   - Press `Windows + R`, type `sysdm.cpl`, press Enter
   - Go to "Advanced" tab → "Environment Variables"
   - Under "System variables", find "Path", click "Edit"
   - Click "New", add `C:\terraform`
   - Click OK

### AWS CLI
1. Download from: https://awscli.amazonaws.com/AWSCLIV2.msi
2. Run the installer
3. Follow the installation wizard

### Make
1. Download from: http://gnuwin32.sourceforge.net/packages/make.htm
2. Install to `C:\Program Files (x86)\GnuWin32`
3. Add to PATH: `C:\Program Files (x86)\GnuWin32\bin`

### Python
1. Download from: https://www.python.org/downloads/
2. Run installer
3. **Important**: Check "Add Python to PATH" during installation

---

## After Installation

### Verify Everything Works
```powershell
terraform --version
aws --version
make --version
python --version
```

You should see version numbers for all tools.

### Configure AWS
```powershell
aws configure
```

Enter:
- AWS Access Key ID: (from your AWS account)
- AWS Secret Access Key: (from your AWS account)
- Default region: `us-east-1`
- Default output format: `json`

### Deploy AFIRGen
```powershell
cd "C:\Users\knith\OneDrive\Desktop\AFIRGen-1"
make deploy-all
```

---

## Troubleshooting

### "Execution Policy" Error
Run PowerShell as Administrator:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "Command not found" After Installation
Close and reopen PowerShell. Windows needs to refresh the PATH.

### Chocolatey Installation Fails
Use Option 3 (Direct Downloads) instead.

### Make Command Not Working
Alternative: Use the scripts directly without make:
```powershell
# Instead of: make download-models
cd "AFIRGEN FINAL"
bash scripts/download-models.sh

# Instead of: make setup-aws
aws configure

# Instead of: make deploy-all
cd terraform/free-tier
terraform init
terraform apply
```

### Git Bash Alternative
If you have Git for Windows installed, you can use Git Bash which has better Linux compatibility:
1. Open Git Bash
2. Navigate to project: `cd /c/Users/knith/OneDrive/Desktop/AFIRGen-1`
3. Run commands normally: `make deploy-all`

---

## Quick Reference

### Installation (PowerShell as Admin)
```powershell
.\install-tools-windows.ps1
```

### Configuration (Normal PowerShell)
```powershell
aws configure
```

### Deployment (Normal PowerShell)
```powershell
make deploy-all
```

---

## Need Help?

- **Chocolatey**: https://chocolatey.org/install
- **Terraform**: https://www.terraform.io/downloads
- **AWS CLI**: https://aws.amazon.com/cli/
- **Make for Windows**: http://gnuwin32.sourceforge.net/packages/make.htm
- **Python**: https://www.python.org/downloads/

---

## Summary

**Easiest**: Run `install-tools-windows.ps1` as Administrator

**Manual**: Install Chocolatey, then `choco install terraform awscli make python -y`

**Direct**: Download each tool individually and add to PATH

After installation, run:
```powershell
make setup-aws
make deploy-all
```
