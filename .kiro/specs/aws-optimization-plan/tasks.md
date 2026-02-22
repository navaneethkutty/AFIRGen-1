# Implementation Plan: AWS Free Tier Optimization

## Overview

This implementation plan deploys the AFIRGen system on AWS infrastructure using only Free Tier services. The deployment follows a 12-day roadmap organized into four phases: Infrastructure Setup, Application Deployment, Monitoring and Optimization, and Documentation and Handoff. All services run on a single t2.micro EC2 instance with optimized memory usage, RDS MySQL database, S3 storage, and CloudFront CDN for frontend delivery.

## Tasks

- [ ] 1. Phase 1: Infrastructure Setup (Days 1-3)
  - [x] 1.1 Create AWS account setup and VPC networking
    - Create VPC with CIDR 10.0.0.0/16
    - Create public subnet (10.0.1.0/24) in us-east-1a
    - Create private subnets (10.0.11.0/24, 10.0.12.0/24) for RDS
    - Configure Internet Gateway and route tables
    - Set up S3 Gateway VPC Endpoint for free S3 access
    - _Requirements: 13.1, 13.3_
  
  - [x] 1.2 Create security groups for EC2 and RDS
    - Create EC2 security group (ports 80, 443, 22)
    - Create RDS security group (port 3306 from EC2 only)
    - Restrict SSH access to specific admin IP
    - _Requirements: 9.2, 9.1_
  
  - [x] 1.3 Create S3 buckets with lifecycle policies
    - Create afirgen-frontend-{account-id} bucket with website configuration
    - Create afirgen-models-{account-id} bucket for ML models
    - Create afirgen-temp-{account-id} bucket with 1-day expiration policy
    - Create afirgen-backups-{account-id} bucket with Glacier transition
    - Enable S3 encryption (SSE-S3)
    - _Requirements: 10.1, 10.2, 10.3, 9.4_
  
  - [x] 1.4 Write property test for Free Tier Limit Compliance
    - **Property 1: Free Tier Limit Compliance**
    - **Validates: Requirements 1.2, 1.3**
    - Test that AWS Cost Explorer shows $0.00 charges for free tier services
    - Generate test data for various resource usage levels
  
  - [ ] 1.5 Launch EC2 t2.micro instance with user data script
    - Launch t2.micro instance in public subnet
    - Attach 30GB gp3 EBS volume
    - Configure user data script to install Docker, Docker Compose, CloudWatch agent
    - Create and attach IAM role for S3 access
    - Allocate and attach Elastic IP
    - _Requirements: 2.1, 2.5_
  
  - [ ] 1.6 Create RDS db.t3.micro MySQL instance
    - Launch db.t3.micro instance with 20GB storage
    - Configure in private subnets with RDS subnet group
    - Enable encryption at rest
    - Set backup window (03:00-04:00 UTC) and 7-day retention
    - Configure max_connections=50, innodb_buffer_pool_size=512MB
    - _Requirements: 5.1, 9.3, 15.1, 15.2_
  
  - [ ] 1.7 Write property test for Storage Limit Compliance
    - **Property 3: Storage Limit Compliance**
    - **Validates: Requirements 5.2, 5.3, 5.4**
    - Test that database size stays under 18GB with automatic cleanup
    - Generate test FIR records to approach storage limit

- [ ] 2. Create CloudFront distribution for frontend
  - [ ] 2.1 Configure CloudFront distribution with S3 origin
    - Create Origin Access Identity for S3 bucket access
    - Configure default cache behavior (redirect-to-https, compress=true)
    - Set cache TTL (default: 24 hours, max: 1 year)
    - Use PriceClass_100 (US, Canada, Europe only)
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ] 2.2 Upload frontend static files to S3
    - Build frontend application
    - Upload HTML, CSS, JS files to S3 frontend bucket
    - Set appropriate content types and cache headers
    - Update S3 bucket policy for CloudFront OAI access
    - _Requirements: 4.1_
  
  - [ ] 2.3 Write property test for Frontend Asset Delivery
    - **Property 6: Frontend Asset Delivery**
    - **Validates: Requirements 4.2, 4.3, 4.4**
    - Test that assets are served via HTTPS with correct cache headers
    - Verify cache hit ratio >99%

- [ ] 3. Checkpoint - Verify infrastructure provisioned correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Phase 2: Application Deployment (Days 4-6)
  - [ ] 4.1 Quantize GGUF models and upload to S3
    - Quantize gguf_summariser model to Q4_K_M (7GB → 2.5GB)
    - Quantize gguf_bns_check model to Q4_K_M (7GB → 2.5GB)
    - Verify Whisper base model (290MB) and dots_ocr model (150MB)
    - Calculate checksums for model integrity verification
    - Upload all models to S3 models bucket (~5GB total)
    - _Requirements: 3.1, 3.3, 19.5_
  
  - [ ] 4.2 Write property test for Model Loading Performance
    - **Property 4: Model Loading Performance**
    - **Validates: Requirements 19.2, 19.3**
    - Test that models load from local disk within 60 seconds
    - Test model loading after container restart
  
  - [ ] 4.3 Write property test for S3 Request Optimization
    - **Property 9: S3 Request Optimization**
    - **Validates: Requirements 3.5, 10.4, 19.2**
    - Test that models are cached locally after first download
    - Verify S3 GET requests stay under 100/month

- [ ] 5. Create Docker Compose configuration for free tier
  - [ ] 5.1 Write docker-compose.free-tier.yml with memory limits
    - Configure main-backend service (300MB memory limit)
    - Configure gguf-server service (400MB memory limit, Q4_K_M quantization)
    - Configure asr-ocr-server service (300MB memory limit, Whisper base)
    - Configure nginx service (50MB memory limit)
    - Set MAX_WORKERS=1 for all services
    - Configure volume mounts for models, KB, sessions
    - _Requirements: 2.3, 2.4, 3.1, 3.2_
  
  - [ ] 5.2 Configure environment variables and secrets
    - Create .env file with RDS endpoint, credentials
    - Set ENVIRONMENT=free-tier
    - Configure model paths and quantization settings
    - Set up database connection pooling (max 5 connections per service)
    - _Requirements: 12.1, 12.2_
  
  - [ ] 5.3 Write property test for Memory Constraint Satisfaction
    - **Property 2: Memory Constraint Satisfaction**
    - **Validates: Requirements 2.3, 2.4**
    - Test that total memory allocation stays under 1GB
    - Test memory usage under concurrent load
  
  - [ ] 5.4 Write property test for Database Connection Pooling
    - **Property 8: Database Connection Pooling**
    - **Validates: Requirements 12.1, 12.2**
    - Test that max 5 connections per service are enforced
    - Test connection reuse under load

- [ ] 6. Deploy application services on EC2
  - [ ] 6.1 Download models from S3 to EC2 local disk
    - SSH to EC2 instance
    - Run aws s3 sync to download models to /opt/afirgen/models/
    - Verify model checksums
    - Set appropriate file permissions
    - _Requirements: 19.1, 19.2_
  
  - [ ] 6.2 Start Docker containers and verify health
    - Run docker-compose -f docker-compose.free-tier.yml up -d
    - Verify all containers start successfully
    - Check container memory usage with docker stats
    - Test health endpoints for all services
    - Verify total memory usage <1GB
    - _Requirements: 2.1, 2.2_
  
  - [ ] 6.3 Configure Nginx for SSL termination
    - Install certbot for Let's Encrypt certificates
    - Generate SSL certificate for domain
    - Configure nginx.conf with SSL settings (TLS 1.2+)
    - Set up reverse proxy to backend services
    - Enable gzip compression
    - _Requirements: 13.4, 13.5, 9.5, 14.1_

- [ ] 7. Test FIR generation end-to-end flow
  - [ ] 7.1 Test text-only FIR generation
    - Submit FIR generation request via API
    - Monitor memory usage during processing
    - Verify completion within 45 seconds
    - Verify FIR stored in RDS
    - _Requirements: 6.1_
  
  - [ ] 7.2 Test FIR generation with audio input
    - Upload audio file to S3 temp bucket
    - Submit FIR generation request with audio
    - Verify Whisper transcription works
    - Verify completion within 90 seconds
    - Verify temp file deleted after 24 hours
    - _Requirements: 6.2, 10.2_
  
  - [ ] 7.3 Test FIR generation with image input
    - Upload image file to S3 temp bucket
    - Submit FIR generation request with image
    - Verify OCR processing works
    - Verify completion within 60 seconds
    - _Requirements: 6.3_
  
  - [ ] 7.4 Write property test for Concurrent Request Handling
    - **Property 5: Concurrent Request Handling**
    - **Validates: Requirements 6.4, 11.3**
    - Test that 3 concurrent requests complete without crashing
    - Verify processing times and memory stability

- [ ] 8. Checkpoint - Verify application deployed and functional
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Phase 3: Monitoring and Optimization (Days 7-9)
  - [ ] 9.1 Configure CloudWatch custom metrics
    - Create 10 custom metrics: FIR/GenerationTime, FIR/GenerationCount, API/ErrorRate, API/ResponseTime, System/CPUUtilization, System/MemoryUtilization, Database/ConnectionCount, Database/QueryTime, Model/InferenceTime, Storage/DiskUsage
    - Configure CloudWatch agent on EC2 with config.json
    - Set metrics collection interval to 60 seconds
    - Verify metrics appearing in CloudWatch console
    - _Requirements: 8.1_
  
  - [ ] 9.2 Create CloudWatch alarms with SNS notifications
    - Create HighErrorRate alarm (threshold: 10%, 2 evaluation periods)
    - Create HighCPU alarm (threshold: 90%, 3 evaluation periods)
    - Create HighMemory alarm (threshold: 95%, 2 evaluation periods)
    - Create DatabaseStorageFull alarm (threshold: 90%, 1 evaluation period)
    - Create SNS topic for email notifications
    - Subscribe admin email to SNS topic
    - _Requirements: 8.2, 8.5, 1.4_
  
  - [ ] 9.3 Configure CloudWatch Logs with sampling
    - Create log groups: /aws/ec2/afirgen, /aws/rds/afirgen-mysql
    - Set 7-day retention period
    - Configure structured JSON logging in application
    - Implement log sampling (1 in 10 successful requests, all errors)
    - Set log level to INFO and above (no DEBUG)
    - _Requirements: 8.3, 8.4, 18.1, 18.2, 18.3, 18.4_
  
  - [ ] 9.4 Write property test for Log Volume Compliance
    - **Property 7: Log Volume Compliance**
    - **Validates: Requirements 8.3, 18.2**
    - Test that daily log ingestion stays under 170MB
    - Verify log sampling configuration works
  
  - [ ] 9.5 Implement request queuing for memory management
    - Add memory monitoring middleware to backend
    - Implement request queue when memory >85%
    - Process queued requests when memory <80%
    - Return HTTP 503 when queue exceeds 10 requests
    - Provide queue position feedback to users
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 2.4_

- [ ] 10. Implement auto-recovery and error handling
  - [ ] 10.1 Configure Docker restart policies
    - Set restart: unless-stopped for all containers
    - Configure health checks for each service
    - Test container restart after manual stop
    - _Requirements: 7.2_
  
  - [ ] 10.2 Implement OOM detection and logging
    - Add memory usage logging before potential OOM
    - Configure Docker to log exit codes
    - Set up CloudWatch alarm for OOM events (exit code 137)
    - Test OOM scenario and verify auto-restart
    - _Requirements: 7.1, 7.3, 7.4_
  
  - [ ] 10.3 Write property test for Auto-Recovery from OOM
    - **Property 10: Auto-Recovery from OOM**
    - **Validates: Requirements 7.1, 7.2**
    - Trigger OOM condition and verify container restarts within 30 seconds
    - Verify service restoration after OOM
  
  - [ ] 10.4 Implement database storage cleanup automation
    - Create cleanup script to delete validation_history >90 days
    - Create cleanup script to delete archived FIR records >180 days
    - Schedule cleanup via cron when storage >18GB
    - Add storage monitoring query to check database size
    - _Requirements: 5.2, 5.3, 5.4_

- [ ] 11. Run performance and load testing
  - [ ] 11.1 Execute light load test (1 concurrent user, 60 minutes)
    - Run load test with 1 concurrent user
    - Monitor memory, CPU, response times
    - Verify p95 response time <90 seconds
    - Verify 100% success rate
    - _Requirements: 6.1, 6.5_
  
  - [ ] 11.2 Execute moderate load test (3 concurrent users, 30 minutes)
    - Run load test with 3 concurrent users
    - Monitor for OOM events and auto-recovery
    - Verify p95 response time <120 seconds
    - Verify >95% success rate
    - _Requirements: 6.4, 11.3_
  
  - [ ] 11.3 Execute stress test (5 concurrent users, 10 minutes)
    - Run stress test to trigger OOM conditions
    - Verify auto-recovery mechanisms work
    - Verify request queuing activates
    - Document expected failures and recovery times
    - _Requirements: 7.1, 7.2, 11.1, 11.2_

- [ ] 12. Set up cost monitoring and alerts
  - [ ] 12.1 Configure AWS Cost Explorer and budgets
    - Enable AWS Cost Explorer
    - Create zero-dollar budget with 80% alert threshold
    - Set up daily cost monitoring checks
    - Create cost monitoring dashboard
    - _Requirements: 1.3, 1.4, 1.5_
  
  - [ ] 12.2 Implement resource usage tracking
    - Track EC2 hours used (750/month limit)
    - Track RDS hours used (750/month limit)
    - Track S3 storage (5GB limit)
    - Track S3 GET/PUT requests (20K/2K limits)
    - Track data transfer out (15GB limit)
    - Track CloudWatch metrics/alarms (10/10 limits)
    - _Requirements: 1.1, 1.2_

- [ ] 13. Checkpoint - Verify monitoring and optimization complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Phase 4: Documentation and Handoff (Days 10-12)
  - [ ] 14.1 Write deployment guide
    - Document AWS account setup steps
    - Document Terraform deployment instructions
    - Document manual configuration steps
    - Include troubleshooting for common deployment issues
    - _Requirements: 20.1_
  
  - [ ] 14.2 Write operational runbooks
    - Create runbook for OOM recovery
    - Create runbook for database storage cleanup
    - Create runbook for scaling to next tier
    - Create runbook for backup and restore procedures
    - Document disaster recovery procedures
    - _Requirements: 20.2, 20.5_
  
  - [ ] 14.3 Document monitoring and alerting
    - Document all 10 CloudWatch metrics and their meanings
    - Document all 10 CloudWatch alarms and thresholds
    - Create monitoring dashboard guide
    - Document alert response procedures
    - _Requirements: 20.3_
  
  - [ ] 14.4 Create upgrade path documentation
    - Document indicators for when to upgrade from Free Tier
    - Provide step-by-step upgrade instructions for each tier
    - Estimate costs for Basic, Standard, and Production tiers
    - Document expected performance improvements at each tier
    - Create migration scripts for tier transitions
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_
  
  - [ ] 14.5 Document security best practices
    - Document security group configurations
    - Document encryption settings (RDS, S3, TLS)
    - Document IAM roles and policies
    - Document access control procedures
    - List security trade-offs in Free Tier deployment
    - _Requirements: 20.5, 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 15. Create Terraform infrastructure as code
  - [ ] 15.1 Write Terraform configuration for all AWS resources
    - Create main.tf with VPC, subnets, security groups
    - Add EC2 instance with user data script
    - Add RDS instance configuration
    - Add S3 buckets with lifecycle policies
    - Add CloudFront distribution
    - Add IAM roles and policies
    - _Requirements: 16.1, 16.3_
  
  - [ ] 15.2 Create Terraform variables and outputs
    - Create variables.tf for region, AMI, admin IP, DB credentials
    - Create outputs.tf for EC2 IP, RDS endpoint, CloudFront domain
    - Mark sensitive variables appropriately
    - _Requirements: 16.2, 16.5_
  
  - [ ] 15.3 Write user data script for EC2 initialization
    - Install Docker, Docker Compose, CloudWatch agent
    - Configure CloudWatch agent with metrics and logs
    - Download models from S3
    - Create environment file with RDS connection details
    - Start Docker containers
    - Set up log rotation
    - _Requirements: 16.4_
  
  - [ ] 15.4 Test Terraform deployment end-to-end
    - Run terraform plan and verify resources
    - Run terraform apply in test AWS account
    - Verify all resources provisioned correctly
    - Test application functionality after Terraform deployment
    - Run terraform destroy to clean up

- [ ] 16. Final validation and testing
  - [ ] 16.1 Run complete test suite
    - Execute all property-based tests
    - Execute all integration tests
    - Verify all 10 correctness properties pass
    - Document any test failures and resolutions
    - _Requirements: All requirements_
  
  - [ ] 16.2 Verify Free Tier compliance
    - Check AWS Cost Explorer for $0.00 charges
    - Verify all resources within Free Tier limits
    - Test cost monitoring alerts
    - Document resource usage levels
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [ ] 16.3 Test disaster recovery procedures
    - Test RDS backup restoration
    - Test EC2 instance recovery from snapshot
    - Test model re-download from S3
    - Verify data integrity after recovery
    - _Requirements: 15.3, 15.5_
  
  - [ ] 16.4 Conduct security review
    - Verify security groups properly configured
    - Verify encryption enabled (RDS, S3, TLS)
    - Verify no exposed credentials
    - Run security scan with free tools (OWASP ZAP)
    - Document security findings and mitigations
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 17. Final checkpoint - Complete deployment validation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at end of each phase
- Property tests validate universal correctness properties from design document
- All infrastructure provisioned via Terraform for repeatability
- Total implementation time: 12 days following the design roadmap
- Memory constraints require careful monitoring throughout deployment
- Free Tier limits must be monitored continuously to avoid charges
