# Fix SSH Access to EC2 Instance

**Problem:** Your EC2 instance was created without an SSH key pair, so you can't SSH into it.

**EC2 Instance:** i-0bc18e312758fda7c  
**EC2 IP:** 98.86.30.145

---

## 🔧 Solution Options

### Option 1: Use AWS Systems Manager (SSM) - Recommended ✅

This doesn't require SSH keys and works immediately:

```bash
# Install AWS Session Manager plugin first
# Download from: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html

# Connect to EC2 via SSM
aws ssm start-session --target i-0bc18e312758fda7c --region us-east-1
```

**Advantages:**
- No SSH key needed
- Works immediately
- More secure (no open SSH port needed)
- Logs all sessions

---

### Option 2: Add SSH Key to Existing Instance

You need to add a key pair to the running instance:

#### Step 1: Create a new key pair

```bash
# Create new key pair
aws ec2 create-key-pair \
  --key-name afirgen-key \
  --query 'KeyMaterial' \
  --output text \
  --region us-east-1 > afirgen-key.pem

# Set permissions (Git Bash or WSL)
chmod 400 afirgen-key.pem
```

#### Step 2: Use SSM to add the key to the instance

```bash
# First, connect via SSM (Option 1)
aws ssm start-session --target i-0bc18e312758fda7c --region us-east-1

# Once connected, add your public key
# Get your public key first (on local machine):
ssh-keygen -y -f afirgen-key.pem

# Copy the output, then in the SSM session:
echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

#### Step 3: Update Terraform to include key

Edit `AFIRGEN FINAL/terraform/free-tier/ec2.tf`:

```hcl
resource "aws_instance" "main" {
  ami           = var.ami_id
  instance_type = var.ec2_instance_type
  key_name      = "afirgen-key"  # Add this line
  
  # ... rest of configuration
}
```

Then apply:

```bash
cd "AFIRGEN FINAL/terraform/free-tier"
terraform apply
```

---

### Option 3: Recreate Instance with SSH Key

If you don't mind recreating the instance:

#### Step 1: Create key pair first

```bash
aws ec2 create-key-pair \
  --key-name afirgen-key \
  --query 'KeyMaterial' \
  --output text \
  --region us-east-1 > afirgen-key.pem

chmod 400 afirgen-key.pem
```

#### Step 2: Update Terraform

Edit `AFIRGEN FINAL/terraform/free-tier/ec2.tf`:

```hcl
resource "aws_instance" "main" {
  ami           = var.ami_id
  instance_type = var.ec2_instance_type
  key_name      = "afirgen-key"  # Add this line
  
  # ... rest of configuration
}
```

#### Step 3: Recreate instance

```bash
cd "AFIRGEN FINAL/terraform/free-tier"

# Destroy old instance
terraform destroy -target=aws_instance.main -target=aws_eip.main

# Create new instance with key
terraform apply
```

---

### Option 4: Use EC2 Instance Connect (Temporary)

For quick access without keys:

```bash
# From AWS Console
# 1. Go to EC2 > Instances
# 2. Select instance i-0bc18e312758fda7c
# 3. Click "Connect" button
# 4. Choose "EC2 Instance Connect" tab
# 5. Click "Connect"
```

**Note:** This only works if the instance has EC2 Instance Connect installed (most Ubuntu AMIs do).

---

## 🎯 Recommended Approach

**For immediate access:** Use Option 1 (SSM) or Option 4 (EC2 Instance Connect)

**For permanent solution:** Use Option 2 (Add key to existing instance)

---

## 📋 Step-by-Step: SSM Setup (Recommended)

### 1. Install Session Manager Plugin

**Windows:**
```powershell
# Download installer
Invoke-WebRequest -Uri "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/SessionManagerPluginSetup.exe" -OutFile "SessionManagerPluginSetup.exe"

# Run installer
.\SessionManagerPluginSetup.exe

# Verify installation
session-manager-plugin
```

**Or download manually:**
https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html

### 2. Verify IAM Permissions

Your EC2 instance needs SSM permissions. Check if the IAM role has `AmazonSSMManagedInstanceCore` policy:

```bash
# Check instance profile
aws ec2 describe-instances \
  --instance-ids i-0bc18e312758fda7c \
  --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn'

# Check role policies
aws iam list-attached-role-policies \
  --role-name <ROLE_NAME_FROM_ABOVE>
```

### 3. Connect via SSM

```bash
# Start session
aws ssm start-session \
  --target i-0bc18e312758fda7c \
  --region us-east-1

# You should now be connected to the instance!
```

### 4. Once Connected, Set Up Application

```bash
# Switch to ubuntu user
sudo su - ubuntu

# Create app directory
sudo mkdir -p /opt/afirgen
sudo chown ubuntu:ubuntu /opt/afirgen

# Now you can upload code or clone from git
cd /opt/afirgen
git clone <YOUR_REPO_URL> .

# Or use S3 to transfer files
aws s3 cp s3://your-bucket/code.tar.gz .
```

---

## 🔐 Adding SSH Key via SSM

Once connected via SSM:

```bash
# Switch to ubuntu user
sudo su - ubuntu

# Create .ssh directory if it doesn't exist
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add your public key
# (Get public key from local machine: ssh-keygen -y -f afirgen-key.pem)
echo "ssh-rsa AAAAB3NzaC1yc2E... your-public-key-here" >> ~/.ssh/authorized_keys

# Set permissions
chmod 600 ~/.ssh/authorized_keys

# Now you can SSH normally
exit
```

Then from your local machine:

```bash
ssh -i afirgen-key.pem ubuntu@98.86.30.145
```

---

## 🛠️ Terraform Fix for Future Deployments

Create/update `AFIRGEN FINAL/terraform/free-tier/variables.tf`:

```hcl
variable "key_name" {
  description = "SSH key pair name for EC2 access"
  type        = string
  default     = "afirgen-key"
}
```

Update `AFIRGEN FINAL/terraform/free-tier/ec2.tf`:

```hcl
resource "aws_instance" "main" {
  ami           = var.ami_id
  instance_type = var.ec2_instance_type
  key_name      = var.key_name  # Add this line
  
  # ... rest of configuration
}
```

---

## ✅ Verification

After getting access, verify:

```bash
# Check you're connected
whoami  # Should show: ubuntu

# Check instance details
curl http://169.254.169.254/latest/meta-data/instance-id

# Check AWS CLI works
aws sts get-caller-identity

# Check internet connectivity
ping -c 3 google.com
```

---

## 📞 Still Having Issues?

If SSM doesn't work:

1. **Check SSM Agent is running:**
   ```bash
   # Via EC2 Instance Connect or user data
   sudo systemctl status amazon-ssm-agent
   ```

2. **Check IAM role has SSM permissions:**
   - Role needs: `AmazonSSMManagedInstanceCore` policy

3. **Check VPC endpoints:**
   - SSM requires VPC endpoints or internet gateway

4. **Use EC2 Instance Connect as fallback:**
   - AWS Console > EC2 > Connect > EC2 Instance Connect

---

**Created:** March 2, 2026  
**Issue:** EC2 instance created without SSH key pair  
**Solution:** Use SSM Session Manager or add key via user data
