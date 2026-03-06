#!/bin/bash
# Switch to Amazon Nova Lite model on EC2

echo "Switching to Amazon Nova Lite model..."

# Navigate to backend directory
cd "/opt/afirgen-backend/AFIRGEN FINAL/main backend" || exit 1

# Update .env file to use Nova Lite
sudo sed -i 's/BEDROCK_MODEL_ID=.*/BEDROCK_MODEL_ID=amazon.nova-lite-v1:0/' .env

echo "Updated .env file:"
grep "BEDROCK_MODEL_ID" .env

# Delete old sessions.db to fix schema issue
echo "Deleting old sessions.db..."
sudo rm -f sessions.db

# Restart the service
echo "Restarting afirgen service..."
sudo systemctl restart afirgen

# Wait a moment for service to start
sleep 3

# Check service status
echo "Service status:"
sudo systemctl status afirgen --no-pager

echo ""
echo "Recent logs:"
sudo journalctl -u afirgen -n 20 --no-pager

echo ""
echo "Done! The backend is now using Amazon Nova Lite."
echo "Test with: bash test-ec2-simple.sh"
