#!/bin/bash
# Fix EC2 Access - Add SSM permissions and SSH key
# Run this from your local machine

set -e

echo "=========================================="
echo "AFIRGen EC2 Access Fix"
echo "=========================================="
echo ""

INSTANCE_ID="i-0bc18e312758fda7c"
REGION="us-east-1"
KEY_NAME="afirgen-key"

# Get IAM role name
echo "Step 1: Getting IAM role name..."
ROLE_NAME=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $REGION \
  --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' \
  --output text | awk -F'/' '{print $NF}')

if [ -z "$ROLE_NAME" ]; then
    echo "ERROR: Could not find IAM role for instance"
    exit 1
fi

echo "IAM Role: $ROLE_NAME"

# Extract actual role name (remove -profile suffix if present)
ACTUAL_ROLE_NAME=$(aws iam get-instance-profile \
  --instance-profile-name $ROLE_NAME \
  --query 'InstanceProfile.Roles[0].RoleName' \
  --output text)

echo "Actual IAM Role: $ACTUAL_ROLE_NAME"

# Step 2: Attach SSM managed policy
echo ""
echo "Step 2: Attaching SSM managed policy..."
aws iam attach-role-policy \
  --role-name $ACTUAL_ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore \
  --region $REGION

echo "✓ SSM policy attached"

# Step 3: Wait for SSM agent to register (can take 5-10 minutes)
echo ""
echo "Step 3: Waiting for SSM agent to register..."
echo "This can take 5-10 minutes. Checking every 30 seconds..."

MAX_ATTEMPTS=20
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "Attempt $ATTEMPT/$MAX_ATTEMPTS..."
    
    if aws ssm describe-instance-information \
        --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
        --region $REGION \
        --query 'InstanceInformationList[0].PingStatus' \
        --output text 2>/dev/null | grep -q "Online"; then
        echo "✓ SSM agent is online!"
        break
    fi
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo "⚠ SSM agent not online yet. You may need to wait longer or reboot the instance."
        echo ""
        echo "To reboot the instance:"
        echo "  aws ec2 reboot-instances --instance-ids $INSTANCE_ID --region $REGION"
        echo ""
        echo "Then wait 2-3 minutes and try connecting again."
        exit 1
    fi
    
    sleep 30
done

# Step 4: Test SSM connection
echo ""
echo "Step 4: Testing SSM connection..."
echo "If this works, you'll be connected to the instance!"
echo ""
echo "Once connected, you can add an SSH key by running:"
echo "  sudo su - ubuntu"
echo "  mkdir -p ~/.ssh && chmod 700 ~/.ssh"
echo "  echo 'YOUR_PUBLIC_KEY' >> ~/.ssh/authorized_keys"
echo "  chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to connect..."
sleep 5

aws ssm start-session --target $INSTANCE_ID --region $REGION
