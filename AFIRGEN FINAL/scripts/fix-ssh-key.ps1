# Fix SSH Key Format and Permissions
# Run this script to fix your PEM key file

param(
    [Parameter(Mandatory=$false)]
    [string]$KeyFile = "afirgen-key.pem"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SSH Key Fix Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$KeyPath = Join-Path $ScriptDir $KeyFile

if (!(Test-Path $KeyPath)) {
    Write-Host "ERROR: Key file not found: $KeyPath" -ForegroundColor Red
    exit 1
}

Write-Host "Key file: $KeyPath" -ForegroundColor Yellow
Write-Host ""

# Step 1: Convert line endings to Unix (LF)
Write-Host "Step 1: Converting line endings to Unix format..." -ForegroundColor Cyan
$content = Get-Content -Path $KeyPath -Raw
$content = $content -replace "`r`n", "`n"
[System.IO.File]::WriteAllText($KeyPath, $content, [System.Text.UTF8Encoding]::new($false))
Write-Host "✓ Line endings converted" -ForegroundColor Green

# Step 2: Set file permissions (Windows)
Write-Host ""
Write-Host "Step 2: Setting file permissions..." -ForegroundColor Cyan

# Remove inheritance
$acl = Get-Acl $KeyPath
$acl.SetAccessRuleProtection($true, $false)

# Remove all existing rules
$acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) | Out-Null }

# Add only current user with read permission
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$readRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $currentUser,
    "Read",
    "Allow"
)
$acl.AddAccessRule($readRule)

Set-Acl -Path $KeyPath -AclObject $acl
Write-Host "✓ Permissions set (read-only for current user)" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Key file fixed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Now try connecting:" -ForegroundColor Yellow
Write-Host "ssh -i `"$KeyPath`" ubuntu@98.86.30.145" -ForegroundColor Cyan
Write-Host ""
