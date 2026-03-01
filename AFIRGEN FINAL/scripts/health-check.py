"""
Health check script for AFIRGen application.
Verifies all endpoints and AWS service connectivity.
"""

import sys
import requests
import boto3
import logging
from typing import Dict, Any, List


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthChecker:
    """Performs health checks on application and AWS services."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize health checker.
        
        Args:
            base_url: Base URL of application
        """
        self.base_url = base_url
        self.checks_passed = 0
        self.checks_failed = 0
    
    def check_application_health(self) -> bool:
        """Check application health endpoint."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            
            if response.status_code == 200:
                logger.info("✓ Application health check passed")
                self.checks_passed += 1
                return True
            else:
                logger.error(f"✗ Application health check failed: {response.status_code}")
                self.checks_failed += 1
                return False
                
        except Exception as e:
            logger.error(f"✗ Application health check failed: {e}")
            self.checks_failed += 1
            return False
    
    def check_bedrock_access(self, region: str) -> bool:
        """Check Bedrock service access."""
        try:
            client = boto3.client('bedrock', region_name=region)
            client.list_foundation_models()
            
            logger.info("✓ Bedrock access check passed")
            self.checks_passed += 1
            return True
            
        except Exception as e:
            logger.error(f"✗ Bedrock access check failed: {e}")
            self.checks_failed += 1
            return False
    
    def check_s3_access(self, bucket_name: str) -> bool:
        """Check S3 bucket access."""
        try:
            client = boto3.client('s3')
            client.head_bucket(Bucket=bucket_name)
            
            logger.info(f"✓ S3 bucket access check passed: {bucket_name}")
            self.checks_passed += 1
            return True
            
        except Exception as e:
            logger.error(f"✗ S3 bucket access check failed: {e}")
            self.checks_failed += 1
            return False
    
    def check_rds_connectivity(self, host: str, port: int) -> bool:
        """Check RDS connectivity."""
        import socket
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                logger.info(f"✓ RDS connectivity check passed: {host}:{port}")
                self.checks_passed += 1
                return True
            else:
                logger.error(f"✗ RDS connectivity check failed: {host}:{port}")
                self.checks_failed += 1
                return False
                
        except Exception as e:
            logger.error(f"✗ RDS connectivity check failed: {e}")
            self.checks_failed += 1
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get health check summary."""
        total = self.checks_passed + self.checks_failed
        success_rate = (self.checks_passed / total * 100) if total > 0 else 0
        
        return {
            'total_checks': total,
            'passed': self.checks_passed,
            'failed': self.checks_failed,
            'success_rate': success_rate,
            'status': 'healthy' if self.checks_failed == 0 else 'unhealthy'
        }


def main():
    """Main health check function."""
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description='AFIRGen health check')
    parser.add_argument(
        '--base-url',
        default=os.getenv('APP_URL', 'http://localhost:8000'),
        help='Application base URL'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("AFIRGen Health Check")
    logger.info("=" * 60)
    
    checker = HealthChecker(args.base_url)
    
    # Run checks
    checker.check_application_health()
    
    # AWS service checks
    region = os.getenv('AWS_REGION', 'us-east-1')
    checker.check_bedrock_access(region)
    
    s3_bucket = os.getenv('S3_BUCKET_NAME')
    if s3_bucket:
        checker.check_s3_access(s3_bucket)
    
    rds_host = os.getenv('RDS_HOST')
    rds_port = int(os.getenv('RDS_PORT', '3306'))
    if rds_host:
        checker.check_rds_connectivity(rds_host, rds_port)
    
    # Print summary
    summary = checker.get_summary()
    
    logger.info("=" * 60)
    logger.info("Health Check Summary")
    logger.info(f"Total Checks: {summary['total_checks']}")
    logger.info(f"Passed: {summary['passed']}")
    logger.info(f"Failed: {summary['failed']}")
    logger.info(f"Success Rate: {summary['success_rate']:.1f}%")
    logger.info(f"Status: {summary['status'].upper()}")
    logger.info("=" * 60)
    
    # Exit with appropriate code
    return 0 if summary['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
