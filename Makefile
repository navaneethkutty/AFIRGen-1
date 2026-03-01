# AFIRGen AWS Deployment Makefile
# Automates the entire deployment process

.PHONY: help install-tools setup-aws deploy-infra download-models download-kb setup-env deploy-app verify clean

# Default target
help:
	@echo "AFIRGen AWS Deployment Automation"
	@echo "=================================="
	@echo ""
	@echo "Available targets:"
	@echo "  make install-tools    - Install required tools (Terraform, AWS CLI)"
	@echo "  make setup-aws        - Configure AWS credentials"
	@echo "  make deploy-infra     - Deploy AWS infrastructure with Terraform"
	@echo "  make download-models  - Download ML models from HuggingFace"
	@echo "  make download-kb      - Download knowledge base from HuggingFace"
	@echo "  make setup-env        - Generate .env configuration file"
	@echo "  make deploy-app       - Deploy application to EC2"
	@echo "  make verify           - Verify deployment"
	@echo "  make deploy-all       - Run complete deployment (infra + app)"
	@echo "  make clean            - Destroy all AWS resources"
	@echo ""
	@echo "Quick start:"
	@echo "  1. make install-tools"
	@echo "  2. make setup-aws"
	@echo "  3. make deploy-all"
	@echo ""

# Install required tools
install-tools:
	@echo "Installing required tools..."
	@command -v terraform >/dev/null 2>&1 || { \
		echo "Installing Terraform..."; \
		if [ "$$(uname)" = "Darwin" ]; then \
			brew install terraform; \
		elif [ "$$(uname)" = "Linux" ]; then \
			wget -q https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip; \
			unzip -q terraform_1.6.0_linux_amd64.zip; \
			sudo mv terraform /usr/local/bin/; \
			rm terraform_1.6.0_linux_amd64.zip; \
		fi; \
	}
	@command -v aws >/dev/null 2>&1 || { \
		echo "Installing AWS CLI..."; \
		if [ "$$(uname)" = "Darwin" ]; then \
			brew install awscli; \
		elif [ "$$(uname)" = "Linux" ]; then \
			curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"; \
			unzip -q awscliv2.zip; \
			sudo ./aws/install; \
			rm -rf aws awscliv2.zip; \
		fi; \
	}
	@echo "✓ Tools installed successfully"

# Configure AWS credentials
setup-aws:
	@echo "Configuring AWS credentials..."
	@aws configure
	@echo "✓ AWS configured"
	@echo ""
	@echo "Verifying credentials..."
	@aws sts get-caller-identity

# Deploy infrastructure with Terraform
deploy-infra:
	@echo "Deploying AWS infrastructure..."
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		terraform init && \
		terraform validate && \
		terraform plan && \
		terraform apply -auto-approve
	@echo "✓ Infrastructure deployed"
	@echo ""
	@echo "Saving outputs..."
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		terraform output -json > ../../deployment-outputs.json
	@echo "✓ Outputs saved to AFIRGEN FINAL/deployment-outputs.json"

# Download models from HuggingFace
download-models:
	@echo "Downloading models from HuggingFace..."
	@cd "AFIRGEN FINAL" && \
		chmod +x scripts/download-models.sh && \
		./scripts/download-models.sh
	@echo "✓ Models downloaded"

# Download knowledge base from HuggingFace
download-kb:
	@echo "Downloading knowledge base from HuggingFace..."
	@cd "AFIRGEN FINAL" && \
		chmod +x scripts/download-knowledge-base.sh && \
		./scripts/download-knowledge-base.sh
	@echo "✓ Knowledge base downloaded"

# Generate .env configuration
setup-env:
	@echo "Generating .env configuration..."
	@cd "AFIRGEN FINAL" && \
		chmod +x scripts/setup-env.sh && \
		./scripts/setup-env.sh
	@echo "✓ Environment configured"

# Upload models to S3
upload-models-s3:
	@echo "Uploading models to S3..."
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		MODELS_BUCKET=$$(terraform output -raw s3_models_bucket) && \
		cd ../.. && \
		aws s3 sync models/ s3://$$MODELS_BUCKET/ --exclude "MODELS.MD"
	@echo "✓ Models uploaded to S3"

# Upload knowledge base to S3 (optional backup)
upload-kb-s3:
	@echo "Uploading knowledge base to S3..."
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		TEMP_BUCKET=$$(terraform output -raw s3_temp_bucket) && \
		cd ../.. && \
		aws s3 sync "rag db/" s3://$$TEMP_BUCKET/rag-db/ && \
		aws s3 sync "general retrieval db/" s3://$$TEMP_BUCKET/general-db/
	@echo "✓ Knowledge base uploaded to S3"

# Deploy application to EC2
deploy-app:
	@echo "Deploying application to EC2..."
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		EC2_IP=$$(terraform output -raw ec2_public_ip) && \
		echo "EC2 IP: $$EC2_IP" && \
		echo "Waiting for EC2 to be ready..." && \
		sleep 30 && \
		cd ../.. && \
		echo "Copying application files..." && \
		scp -o StrictHostKeyChecking=no -i ~/.ssh/afirgen-key.pem -r \
			"main backend" "gguf model server" "asr ocr model server" \
			frontend nginx docker-compose.yaml .env \
			ubuntu@$$EC2_IP:/opt/afirgen/ && \
		echo "Copying knowledge base..." && \
		scp -o StrictHostKeyChecking=no -i ~/.ssh/afirgen-key.pem -r \
			"rag db" "general retrieval db" \
			ubuntu@$$EC2_IP:/opt/afirgen/ && \
		echo "Starting services..." && \
		ssh -o StrictHostKeyChecking=no -i ~/.ssh/afirgen-key.pem ubuntu@$$EC2_IP \
			"cd /opt/afirgen && docker-compose up -d"
	@echo "✓ Application deployed"

# Verify deployment
verify:
	@echo "Verifying deployment..."
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		EC2_IP=$$(terraform output -raw ec2_public_ip) && \
		echo "Testing health endpoint..." && \
		curl -f http://$$EC2_IP:8000/health || echo "Health check failed" && \
		echo "" && \
		echo "Deployment verification complete!" && \
		echo "" && \
		echo "Access your application at:" && \
		echo "  Frontend: http://$$EC2_IP" && \
		echo "  API: http://$$EC2_IP:8000" && \
		echo "  API Docs: http://$$EC2_IP:8000/docs"

# Complete deployment (infrastructure + application)
deploy-all: deploy-infra download-models download-kb setup-env upload-models-s3 deploy-app verify
	@echo ""
	@echo "=========================================="
	@echo "Deployment Complete!"
	@echo "=========================================="
	@echo ""
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		EC2_IP=$$(terraform output -raw ec2_public_ip) && \
		echo "Your AFIRGen instance is ready at:" && \
		echo "  http://$$EC2_IP"

# Quick deploy (assumes tools are installed and AWS is configured)
quick-deploy: deploy-infra download-models download-kb setup-env deploy-app verify

# Clean up - destroy all resources
clean:
	@echo "WARNING: This will destroy all AWS resources!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		terraform destroy -auto-approve
	@echo "✓ All resources destroyed"

# Show deployment status
status:
	@echo "Deployment Status"
	@echo "================="
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		terraform output

# SSH to EC2 instance
ssh:
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		EC2_IP=$$(terraform output -raw ec2_public_ip) && \
		ssh -i ~/.ssh/afirgen-key.pem ubuntu@$$EC2_IP

# View application logs
logs:
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		EC2_IP=$$(terraform output -raw ec2_public_ip) && \
		ssh -i ~/.ssh/afirgen-key.pem ubuntu@$$EC2_IP \
			"cd /opt/afirgen && docker-compose logs -f"

# Restart application services
restart:
	@cd "AFIRGEN FINAL/terraform/free-tier" && \
		EC2_IP=$$(terraform output -raw ec2_public_ip) && \
		ssh -i ~/.ssh/afirgen-key.pem ubuntu@$$EC2_IP \
			"cd /opt/afirgen && docker-compose restart"

# Update application (redeploy without infrastructure changes)
update: deploy-app verify
	@echo "✓ Application updated"
