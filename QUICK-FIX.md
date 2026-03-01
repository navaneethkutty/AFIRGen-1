# Quick Fix - Install Terraform Now

## Your Error
```
'terraform' is not recognized as an internal or external command
```

## Quick Fix (Choose One)

### Option 1: Run This Script (Easiest)
```powershell
.\install-terraform.ps1
```

Then **close and reopen PowerShell**.

### Option 2: Download Manually (5 minutes)
1. Click: https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_windows_amd64.zip
2. Extract the ZIP file
3. Copy `terraform.exe` to `C:\terraform\`
4. Add `C:\terraform` to your PATH:
   - Press `Windows + R`
   - Type: `sysdm.cpl`
   - Press Enter
   - Click "Advanced" tab
   - Click "Environment Variables"
   - Under "User variables", select "Path"
   - Click "Edit"
   - Click "New"
   - Type: `C:\terraform`
   - Click OK on everything
5. **Close and reopen PowerShell**

### Option 3: Use Chocolatey
If you have Chocolatey installed:
```powershell
choco install terraform -y
```

---

## After Installation

Close PowerShell completely, open a new one, then:

```powershell
# Verify it works
terraform --version

# If you see the version, you're good!
# Now deploy:
cd "C:\Users\knith\OneDrive\Desktop\AFIRGen-1"
make deploy-all
```

---

## Still Not Working?

Try this in PowerShell:
```powershell
# Check if terraform.exe exists
Test-Path "C:\terraform\terraform.exe"

# If True, add to current session:
$env:Path = "$env:Path;C:\terraform"

# Try again:
terraform --version
```

---

## What You Need Installed

- ✅ AWS CLI (you have this)
- ❌ Terraform (installing now)
- ❓ Python (might need this too)

Check Python:
```powershell
python --version
```

If that fails, install Python:
- Download: https://www.python.org/downloads/
- Check "Add Python to PATH" during install

---

## Summary

**Fastest way:**
1. Run: `.\install-terraform.ps1`
2. Close PowerShell
3. Open new PowerShell  
4. Run: `make deploy-all`

**Manual way:**
1. Download: https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_windows_amd64.zip
2. Extract to C:\terraform
3. Add to PATH (see Option 2 above)
4. Close and reopen PowerShell
5. Run: `make deploy-all`
