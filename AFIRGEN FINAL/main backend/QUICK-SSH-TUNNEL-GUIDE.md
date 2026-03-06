# Quick SSH Tunnel Setup (Recommended Solution)

Since direct connection to RDS is being blocked (likely by ISP or Windows Firewall), use an SSH tunnel through your EC2 instance.

## What You Need

- SSH access to EC2: `98.86.30.145`
- Your SSH key file (`.pem` or `.ppk`)

## Option 1: Using PowerShell/CMD (Windows)

### Step 1: Open a NEW terminal and create the tunnel

```powershell
# Replace "path\to\your-key.pem" with your actual key file path
ssh -i "path\to\your-key.pem" -L 3306:afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com:3306 ubuntu@98.86.30.145 -N
```

**Keep this terminal open!** The tunnel stays active as long as this command is running.

### Step 2: Update .env file

In your `.env` file, change:
```env
DB_HOST=localhost
```

(Change it back to the RDS endpoint when deploying to EC2)

### Step 3: Start backend in ANOTHER terminal

```powershell
cd "AFIRGEN FINAL\main backend"
.\venv\Scripts\activate
python start_backend.py
```

The backend will now connect to `localhost:3306`, which tunnels through EC2 to RDS!

## Option 2: Using PuTTY (if you have .ppk key)

1. Open PuTTY
2. Session:
   - Host: `ubuntu@98.86.30.145`
   - Port: 22
3. Connection → SSH → Auth:
   - Browse and select your `.ppk` key file
4. Connection → SSH → Tunnels:
   - Source port: `3306`
   - Destination: `afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com:3306`
   - Click "Add"
5. Click "Open" to connect
6. Keep PuTTY window open
7. Update `.env` to use `DB_HOST=localhost`
8. Start backend

## Option 3: Skip Local Testing (Fastest)

Since you're having connectivity issues, you can:

1. Commit your code changes
2. Deploy directly to EC2
3. Test everything there (where RDS access already works)

This is actually the fastest path forward since EC2 already has VPC access to RDS.

## Troubleshooting

### "Permission denied (publickey)"
Your SSH key doesn't have the right permissions. Fix:
```powershell
icacls "path\to\your-key.pem" /inheritance:r
icacls "path\to\your-key.pem" /grant:r "%username%:R"
```

### "Connection refused"
EC2 security group might not allow SSH from your IP. Add your IP to port 22 in EC2 security group.

### Don't have SSH key?
You'll need to either:
1. Get the SSH key from whoever set up the EC2 instance
2. Create a new key pair and associate it with the EC2 instance
3. Use Option 3 (skip local testing)

## Recommendation

If you have the SSH key: Use **Option 1** (SSH tunnel)

If you don't have the SSH key: Use **Option 3** (deploy to EC2 and test there)

The EC2 deployment will work perfectly since it's already in the same VPC as RDS!
