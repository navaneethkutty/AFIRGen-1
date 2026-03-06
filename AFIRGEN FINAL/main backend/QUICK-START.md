# Quick Start Guide

## 🚀 One-Command Setup

```powershell
.\setup-local.ps1
```

This will:
- ✓ Check Python version
- ✓ Create virtual environment
- ✓ Activate virtual environment
- ✓ Upgrade pip
- ✓ Install all dependencies
- ✓ Create .env file from template
- ✓ Create logs directory

## 📝 Manual Setup (If Needed)

### 1. Create Virtual Environment
```powershell
python -m venv venv
```

### 2. Activate Virtual Environment

**PowerShell (Recommended):**
```powershell
.\activate-venv.ps1
```

**Or manually:**
```powershell
.\venv\Scripts\Activate.ps1
```

**If you get an error, run this first:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### 3. Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment
```powershell
# Copy template
Copy-Item .env.example .env

# Edit .env with your credentials
notepad .env
```

## 🧪 Run Tests

```powershell
# Activate venv first
.\activate-venv.ps1

# Run all tests
pytest -v

# Run specific test suite
pytest test_pbt_*.py -v
```

## 🏃 Run Backend

```powershell
# Activate venv first
.\activate-venv.ps1

# Start backend (development mode with auto-reload)
uvicorn agentv5:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at: http://localhost:8000

## 🔍 Verify Installation

```powershell
# Activate venv
.\activate-venv.ps1

# Check Python version
python --version

# Check installed packages
pip list

# Test health endpoint (after starting backend)
curl http://localhost:8000/health
```

## 📚 Common Commands

### Virtual Environment
```powershell
# Activate
.\activate-venv.ps1

# Deactivate
deactivate

# Recreate (if corrupted)
Remove-Item -Recurse -Force venv
python -m venv venv
.\activate-venv.ps1
pip install -r requirements.txt
```

### Testing
```powershell
# All tests
pytest -v

# Property-based tests only
pytest test_pbt_*.py -v

# Unit tests only
pytest test_*_unit*.py -v

# Specific test file
pytest test_config_validation.py -v

# With coverage
pytest --cov=agentv5 --cov-report=html
```

### Backend
```powershell
# Development mode (auto-reload)
uvicorn agentv5:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn agentv5:app --host 0.0.0.0 --port 8000

# Different port
uvicorn agentv5:app --host 0.0.0.0 --port 8001

# View logs
Get-Content logs/main_backend.log -Tail 50 -Wait
```

### Database
```powershell
# Test MySQL connection
python -c "import mysql.connector; from dotenv import load_dotenv; import os; load_dotenv(); conn = mysql.connector.connect(host=os.getenv('DB_HOST'), port=int(os.getenv('DB_PORT', 3306)), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), database=os.getenv('DB_NAME')); print('✓ Connected'); conn.close()"

# Check SQLite database
sqlite3 sessions.db ".tables"
```

## 🐛 Troubleshooting

### Virtual Environment Won't Activate
```powershell
# Fix execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# Then activate
.\activate-venv.ps1
```

### Module Not Found
```powershell
# Ensure venv is activated
.\activate-venv.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

### Port Already in Use
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or use different port
uvicorn agentv5:app --host 0.0.0.0 --port 8001
```

### Database Connection Failed
- Check RDS security group allows your IP
- Verify credentials in .env file
- Test connection with MySQL Workbench

### AWS Service Access Denied
- Verify AWS credentials: `aws configure list`
- Check IAM permissions
- Ensure region is correct in .env

## 📖 Full Documentation

- **[LOCAL-TESTING-GUIDE.md](LOCAL-TESTING-GUIDE.md)** - Complete testing guide
- **[EC2-DEPLOYMENT-GUIDE.md](EC2-DEPLOYMENT-GUIDE.md)** - EC2 deployment
- **[DEPLOYMENT-SUMMARY.md](DEPLOYMENT-SUMMARY.md)** - Overview and status
- **[README.md](README.md)** - Full documentation

## 🎯 Next Steps

1. ✅ Complete setup (run `.\setup-local.ps1`)
2. ✅ Configure .env file
3. ✅ Run tests (`pytest -v`)
4. ✅ Start backend (`uvicorn agentv5:app --host 0.0.0.0 --port 8000 --reload`)
5. ✅ Test health endpoint (`curl http://localhost:8000/health`)
6. ✅ Follow [LOCAL-TESTING-GUIDE.md](LOCAL-TESTING-GUIDE.md) for complete testing
7. ✅ Deploy to EC2 using [EC2-DEPLOYMENT-GUIDE.md](EC2-DEPLOYMENT-GUIDE.md)

## 💡 Tips

- Always activate venv before running commands
- Use `--reload` flag during development for auto-reload
- Check logs in `logs/main_backend.log` for debugging
- Use `pytest -v` to see detailed test output
- Use `curl` or Postman to test API endpoints
- Keep .env file secure (never commit to git)

## 🆘 Need Help?

1. Check the troubleshooting section above
2. Review [LOCAL-TESTING-GUIDE.md](LOCAL-TESTING-GUIDE.md)
3. Check logs: `Get-Content logs/main_backend.log -Tail 50`
4. Verify environment: `python --version`, `pip list`
