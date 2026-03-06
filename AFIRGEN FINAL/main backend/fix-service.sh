#!/bin/bash
# Fix the systemd service file

cat > /etc/systemd/system/afirgen.service << 'EOF'
[Unit]
Description=AFIRGen Backend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/afirgen-backend/AFIRGEN FINAL/main backend
EnvironmentFile=/opt/afirgen-backend/AFIRGEN FINAL/main backend/.env
ExecStart=/opt/afirgen-backend/AFIRGEN FINAL/main backend/venv/bin/uvicorn agentv5:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl restart afirgen
sleep 3
systemctl status afirgen
