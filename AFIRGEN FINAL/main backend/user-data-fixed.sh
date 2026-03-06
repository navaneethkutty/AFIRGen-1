#!/bin/bash
set -e
apt-get update && apt-get upgrade -y
apt-get install -y python3 python3-venv python3-pip git mysql-client
mkdir -p /opt/afirgen-backend && cd /opt/afirgen-backend
git clone https://github.com/navaneethkutty/AFIRGen-1.git .
cd "AFIRGEN FINAL/main backend"
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
cat > .env << 'EOF'
AWS_REGION=us-east-1
S3_BUCKET_NAME=afirgen-storage-bucket
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
DB_HOST=afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_USER=admin
DB_PASSWORD=Prathiush12.
DB_NAME=afirgen
API_KEY=dev-test-key-12345678901234567890123456789012
EOF
mkdir -p logs
cp afirgen.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable afirgen && systemctl start afirgen
