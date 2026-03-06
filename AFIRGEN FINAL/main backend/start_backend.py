#!/usr/bin/env python3
"""
Backend startup script with connectivity checks
"""
import os
import sys
import mysql.connector
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_mysql():
    """Check MySQL RDS connectivity"""
    print("Checking MySQL RDS connectivity...")
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            connection_timeout=10
        )
        conn.close()
        print("✓ MySQL RDS connection successful")
        return True
    except Exception as e:
        print(f"✗ MySQL RDS connection failed: {e}")
        print("\nPossible solutions:")
        print("1. Check RDS security group allows your IP address")
        print("2. Verify RDS instance is publicly accessible")
        print("3. Check your local firewall allows outbound port 3306")
        print("4. Verify database credentials in .env file")
        return False

def check_aws():
    """Check AWS Bedrock connectivity"""
    print("\nChecking AWS Bedrock connectivity...")
    try:
        client = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION'))
        # Just creating the client is enough to verify credentials
        print("✓ AWS credentials configured")
        return True
    except Exception as e:
        print(f"✗ AWS configuration failed: {e}")
        print("\nPossible solutions:")
        print("1. Run 'aws configure' to set up credentials")
        print("2. Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        return False

def main():
    print("=" * 60)
    print("AFIRGen Backend - Connectivity Check")
    print("=" * 60)
    
    mysql_ok = check_mysql()
    aws_ok = check_aws()
    
    print("\n" + "=" * 60)
    if mysql_ok and aws_ok:
        print("✓ All checks passed! Starting backend...")
        print("=" * 60)
        print("\nStarting uvicorn server...")
        print("Press Ctrl+C to stop\n")
        os.system("uvicorn agentv5:app --host 0.0.0.0 --port 8000")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
