# SSH Tunnel Setup for RDS Access

Since your RDS instance is not publicly accessible (which is good for security), you can use an SSH tunnel through your EC2 instance to access it from your local machine.

## Prerequisites

- SSH key file for EC2 instance (e.g., `afirgen-key.pem`)
- EC2 instance IP: `98.86.30.145`
- RDS endpoint: `afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com`

## Option A: SSH Tunnel (Recommended)

### Step 1: Create SSH Tunnel

Open a new terminal and run:

```bash
ssh -i path/to/your-key.pem -L 3306:afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com:3306 ubuntu@98.86.30.145 -N
```

Replace `path/to/your-key.pem` with your actual key file path.

This command:
- Creates a tunnel from your local port 3306 to RDS through EC2
- `-L 3306:...` forwards local port 3306 to RDS
- `-N` means don't execute any commands, just create the tunnel
- Keep this terminal open while testing

### Step 2: Update .env File

Change DB_HOST to localhost:

```env
DB_HOST=localhost
```

### Step 3: Start Backend

In a new terminal:

```bash
cd "AFIRGEN FINAL/main backend"
.\venv\Scripts\activate
python start_backend.py
```

### Step 4: When Done

- Press Ctrl+C in the SSH tunnel terminal to close the tunnel
- Change DB_HOST back to the RDS endpoint for EC2 deployment

## Option B: Make RDS Publicly Accessible (Quick but Less Secure)

If you want direct access without SSH tunnel:

### Step 1: Modify RDS Instance

1. Go to: https://console.aws.amazon.com/rds/
2. Select "afirgen-free-tier-mysql"
3. Click "Modify"
4. Under "Connectivity" → "Additional configuration"
5. Set "Public access" to "Yes"
6. Click "Continue"
7. Select "Apply immediately"
8. Click "Modify DB instance"

Wait 5-10 minutes for the change to apply.

### Step 2: Test Connection

```bash
python start_backend.py
```

### Security Note

Making RDS publicly accessible is convenient for development but less secure. Consider:
- Using strong passwords (you already have this)
- Restricting security group to only your IP (you already did this)
- Switching back to private access before production deployment

## Option C: Test on EC2 Directly (Fastest)

Skip local testing and deploy directly to EC2 where RDS access is already configured:

1. Commit your changes
2. Push to git
3. SSH into EC2
4. Pull latest code
5. Test there

This is the fastest option since EC2 already has VPC access to RDS.

## Recommendation

For development: Use **Option A (SSH Tunnel)** - it's secure and works well.

For quick testing: Use **Option C (Test on EC2)** - fastest path to testing.

For convenience: Use **Option B (Public Access)** - but remember to switch back to private before production.
