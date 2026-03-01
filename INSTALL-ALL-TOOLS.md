# Install All Required Tools - Windows

You need 3 tools installed:
1. ✅ AWS CLI (you have this!)
2. ❌ Terraform (missing)
3. ❓ Python (check below)

## Quick Install All Tools

### Option 1: Run Installation Script

```powershell
.\install-terraform.ps1
```

Then close and reopen PowerShell.

### Option 2: Manual Installation

#### Install Terraform
1. Download: https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_windows_amd64.zip
2. Extract to `C:\terraform`
3. Add to PATH:
   - Press `Windows + R`
   - Type `sysdm.cpl` and press Enter
   - Go to "Advanced" tab → "Environment Variables"
   - Under "User variables", find "Path", click "Edit"
   - Click "New", add `C:\terraform`
   - Click OK on all windows
4. Close and reopen PowerShell

#### Install Python (if needed)
1. Download: https://www.python.org/downloads/
2. Run installer
3. **Important**: Check "Add Python to PATH"
4. Click "Install Now"

---

## Verify All Tools

After installation, close and reopen PowerShell, then run:

```powershell
# Check AWS CLI
aws --version

# Check Terraform
terraform --version

# Check Python
python --version

# Check pip
pip --version
```

All commands should show version numbers.

---

## Then Deploy

Once all tools are installed:

```powershell
cd "C:\Users\knith\OneDrive\Desktop\AFIRGen-1"
make deploy-all
```

---

## Alternative: Use Chocolatey (Package Manager)

If you want to use a package manager like Linux:

### Install Chocolatey
Open PowerShell as Administrator:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### Install All Tools
```powershell
choco install terraform python -y
```

Close and reopen PowerShell.

---

## Quick Status Check

Run this to see what you have:

```powershell
Write-Host "AWS CLI: " -NoNewline; if (Get-Command aws -ErrorAction SilentlyContinue) { Write-Host "✓ Installed" -ForegroundColor Green } else { Write-Host "✗ Missing" -ForegroundColor Red }
Write-Host "Terraform: " -NoNewline; if (Get-Command terraform -ErrorAction SilentlyContinue) { Write-Host "✓ Installed" -ForegroundColor Green } else { Write-Host "✗ Missing" -ForegroundColor Red }
Write-Host "Python: " -NoNewline; if (Get-Command python -ErrorAction SilentlyContinue) { Write-Host "✓ Installed" -ForegroundColor Green } else { Write-Host "✗ Missing" -ForegroundColor Red }
```

---

## Summary

**Right now:**
1. Run: `.\install-terraform.ps1`
2. Close PowerShell
3. Open new PowerShell
4. Run: `terraform --version` (should work)
5. Run: `make deploy-all`

**Or manually:**
1. Download Terraform: https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_windows_amd64.zip
2. Extract to C:\terraform
3. Add C:\terraform to PATH
4. Close and reopen PowerShell
5. Run: `make deploy-all`
