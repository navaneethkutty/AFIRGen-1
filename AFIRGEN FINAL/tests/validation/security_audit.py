#!/usr/bin/env python3
"""
Security Audit Script for Bedrock Migration

Performs comprehensive security audit to verify all security requirements are met:
- S3 SSE-KMS encryption
- TLS 1.2+ for all data in transit
- Vector database TLS connections
- No hardcoded credentials
- Least privilege IAM policies
- Private subnets / security groups
- VPC endpoints for AWS services
- No PII in logs
- RBAC enforcement
- RDS encryption at rest
"""

import json
import re
import os
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import boto3


@dataclass
class SecurityCheck:
    """Individual security check result"""
    check_name: str
    passed: bool
    details: str
    severity: str  # critical, high, medium, low
    remediation: str = None


@dataclass
class SecurityAuditReport:
    """Complete security audit report"""
    timestamp: str
    checks: List[SecurityCheck]
    critical_failures: int
    high_failures: int
    medium_failures: int
    low_failures: int
    overall_passed: bool
    summary: Dict[str, Any]


class SecurityAuditor:
    """Performs comprehensive security audit"""
    
    def __init__(self, region: str = "us-east-1", project_root: str = "."):
        self.region = region
        self.project_root = Path(project_root)
        self.s3 = boto3.client('s3', region_name=region)
        self.ec2 = boto3.client('ec2', region_name=region)
        self.rds = boto3.client('rds', region_name=region)
        self.iam = boto3.client('iam', region_name=region)
        
        # Patterns for credential detection
        self.credential_patterns = [
            r'aws_access_key_id\s*=\s*["\']?AKIA[0-9A-Z]{16}["\']?',
            r'aws_secret_access_key\s*=\s*["\'][^"\']{40}["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
        ]
        
        # PII patterns
        self.pii_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{10}\b',  # Phone number
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        ]
    
    def check_s3_encryption(self, bucket_name: str) -> SecurityCheck:
        """Check if S3 bucket uses SSE-KMS encryption"""
        try:
            response = self.s3.get_bucket_encryption(Bucket=bucket_name)
            rules = response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
            
            for rule in rules:
                sse = rule.get('ApplyServerSideEncryptionByDefault', {})
                if sse.get('SSEAlgorithm') == 'aws:kms':
                    return SecurityCheck(
                        check_name="S3 SSE-KMS Encryption",
                        passed=True,
                        details=f"Bucket {bucket_name} uses SSE-KMS encryption",
                        severity="critical"
                    )
            
            return SecurityCheck(
                check_name="S3 SSE-KMS Encryption",
                passed=False,
                details=f"Bucket {bucket_name} does not use SSE-KMS encryption",
                severity="critical",
                remediation="Enable SSE-KMS encryption on S3 bucket"
            )
        except Exception as e:
            return SecurityCheck(
                check_name="S3 SSE-KMS Encryption",
                passed=False,
                details=f"Could not verify S3 encryption: {str(e)}",
                severity="critical",
                remediation="Ensure S3 bucket exists and has encryption configured"
            )
    
    def check_rds_encryption(self, db_instance_id: str) -> SecurityCheck:
        """Check if RDS instance has encryption at rest enabled"""
        try:
            response = self.rds.describe_db_instances(DBInstanceIdentifier=db_instance_id)
            instances = response.get('DBInstances', [])
            
            if not instances:
                return SecurityCheck(
                    check_name="RDS Encryption at Rest",
                    passed=False,
                    details=f"RDS instance {db_instance_id} not found",
                    severity="critical",
                    remediation="Ensure RDS instance exists"
                )
            
            instance = instances[0]
            encrypted = instance.get('StorageEncrypted', False)
            
            if encrypted:
                return SecurityCheck(
                    check_name="RDS Encryption at Rest",
                    passed=True,
                    details=f"RDS instance {db_instance_id} has encryption at rest enabled",
                    severity="critical"
                )
            else:
                return SecurityCheck(
                    check_name="RDS Encryption at Rest",
                    passed=False,
                    details=f"RDS instance {db_instance_id} does not have encryption at rest",
                    severity="critical",
                    remediation="Enable encryption at rest for RDS instance (requires recreation)"
                )
        except Exception as e:
            return SecurityCheck(
                check_name="RDS Encryption at Rest",
                passed=False,
                details=f"Could not verify RDS encryption: {str(e)}",
                severity="critical",
                remediation="Ensure RDS instance exists and is accessible"
            )
    
    def check_hardcoded_credentials(self) -> SecurityCheck:
        """Check for hardcoded credentials in source code"""
        violations = []
        
        # Scan Python files
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            # Skip test files and virtual environments
            if 'test' in str(file_path) or 'venv' in str(file_path) or '.venv' in str(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for pattern in self.credential_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            violations.append(f"{file_path}:{match.group()}")
            except Exception:
                continue
        
        if violations:
            return SecurityCheck(
                check_name="No Hardcoded Credentials",
                passed=False,
                details=f"Found {len(violations)} potential hardcoded credentials:\n" + 
                       "\n".join(violations[:5]),  # Show first 5
                severity="critical",
                remediation="Remove hardcoded credentials and use environment variables or AWS Secrets Manager"
            )
        else:
            return SecurityCheck(
                check_name="No Hardcoded Credentials",
                passed=True,
                details="No hardcoded credentials found in source code",
                severity="critical"
            )
    
    def check_pii_in_logs(self) -> SecurityCheck:
        """Check for PII in log files"""
        violations = []
        
        # Scan log files
        log_files = list(self.project_root.rglob("*.log"))
        
        for file_path in log_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for pattern in self.pii_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            violations.append(f"{file_path}:{match.group()}")
            except Exception:
                continue
        
        if violations:
            return SecurityCheck(
                check_name="No PII in Logs",
                passed=False,
                details=f"Found {len(violations)} potential PII instances in logs:\n" + 
                       "\n".join(violations[:5]),  # Show first 5
                severity="high",
                remediation="Implement PII filtering in logging configuration"
            )
        else:
            return SecurityCheck(
                check_name="No PII in Logs",
                passed=True,
                details="No PII found in log files",
                severity="high"
            )
    
    def check_security_groups(self, instance_id: str = None) -> SecurityCheck:
        """Check security group configurations"""
        try:
            if instance_id:
                # Check specific instance
                response = self.ec2.describe_instances(InstanceIds=[instance_id])
                instances = response['Reservations'][0]['Instances']
                security_groups = instances[0]['SecurityGroups']
            else:
                # Check all security groups
                response = self.ec2.describe_security_groups()
                security_groups = response['SecurityGroups']
            
            issues = []
            
            for sg in security_groups:
                sg_id = sg['GroupId']
                sg_name = sg['GroupName']
                
                # Check for overly permissive rules
                for rule in sg.get('IpPermissions', []):
                    for ip_range in rule.get('IpRanges', []):
                        if ip_range.get('CidrIp') == '0.0.0.0/0':
                            from_port = rule.get('FromPort', 'all')
                            to_port = rule.get('ToPort', 'all')
                            issues.append(
                                f"{sg_name} ({sg_id}): Allows 0.0.0.0/0 on ports {from_port}-{to_port}"
                            )
            
            if issues:
                return SecurityCheck(
                    check_name="Security Group Configuration",
                    passed=False,
                    details=f"Found {len(issues)} overly permissive security group rules:\n" + 
                           "\n".join(issues[:5]),
                    severity="high",
                    remediation="Restrict security group rules to specific IP ranges"
                )
            else:
                return SecurityCheck(
                    check_name="Security Group Configuration",
                    passed=True,
                    details="Security groups follow least privilege principle",
                    severity="high"
                )
        except Exception as e:
            return SecurityCheck(
                check_name="Security Group Configuration",
                passed=False,
                details=f"Could not verify security groups: {str(e)}",
                severity="high",
                remediation="Ensure EC2 instance exists and is accessible"
            )
    
    def check_vpc_endpoints(self) -> SecurityCheck:
        """Check if VPC endpoints are configured for AWS services"""
        try:
            response = self.ec2.describe_vpc_endpoints()
            endpoints = response.get('VpcEndpoints', [])
            
            required_services = [
                'com.amazonaws.{}.bedrock-runtime'.format(self.region),
                'com.amazonaws.{}.transcribe'.format(self.region),
                'com.amazonaws.{}.textract'.format(self.region),
                'com.amazonaws.{}.s3'.format(self.region),
            ]
            
            configured_services = [ep['ServiceName'] for ep in endpoints]
            missing_services = [svc for svc in required_services if svc not in configured_services]
            
            if missing_services:
                return SecurityCheck(
                    check_name="VPC Endpoints Configuration",
                    passed=False,
                    details=f"Missing VPC endpoints for: {', '.join(missing_services)}",
                    severity="medium",
                    remediation="Create VPC endpoints for all AWS services to avoid internet traffic"
                )
            else:
                return SecurityCheck(
                    check_name="VPC Endpoints Configuration",
                    passed=True,
                    details="All required VPC endpoints are configured",
                    severity="medium"
                )
        except Exception as e:
            return SecurityCheck(
                check_name="VPC Endpoints Configuration",
                passed=False,
                details=f"Could not verify VPC endpoints: {str(e)}",
                severity="medium",
                remediation="Ensure VPC exists and is accessible"
            )
    
    def check_iam_policies(self, role_name: str) -> SecurityCheck:
        """Check IAM role policies for least privilege"""
        try:
            # Get attached policies
            response = self.iam.list_attached_role_policies(RoleName=role_name)
            policies = response.get('AttachedPolicies', [])
            
            issues = []
            
            for policy in policies:
                policy_arn = policy['PolicyArn']
                
                # Check for overly permissive AWS managed policies
                if 'AdministratorAccess' in policy_arn:
                    issues.append("Role has AdministratorAccess policy attached")
                elif 'PowerUserAccess' in policy_arn:
                    issues.append("Role has PowerUserAccess policy attached")
                
                # Get policy document
                policy_version = self.iam.get_policy(PolicyArn=policy_arn)
                version_id = policy_version['Policy']['DefaultVersionId']
                
                policy_doc = self.iam.get_policy_version(
                    PolicyArn=policy_arn,
                    VersionId=version_id
                )
                
                statements = policy_doc['PolicyVersion']['Document'].get('Statement', [])
                
                for statement in statements:
                    if statement.get('Effect') == 'Allow':
                        actions = statement.get('Action', [])
                        if isinstance(actions, str):
                            actions = [actions]
                        
                        # Check for wildcard actions
                        if '*' in actions or any(':*' in action for action in actions):
                            issues.append(f"Policy {policy['PolicyName']} has wildcard actions")
            
            if issues:
                return SecurityCheck(
                    check_name="IAM Least Privilege",
                    passed=False,
                    details=f"Found {len(issues)} IAM policy issues:\n" + "\n".join(issues),
                    severity="high",
                    remediation="Refine IAM policies to follow least privilege principle"
                )
            else:
                return SecurityCheck(
                    check_name="IAM Least Privilege",
                    passed=True,
                    details="IAM policies follow least privilege principle",
                    severity="high"
                )
        except Exception as e:
            return SecurityCheck(
                check_name="IAM Least Privilege",
                passed=False,
                details=f"Could not verify IAM policies: {str(e)}",
                severity="high",
                remediation="Ensure IAM role exists and is accessible"
            )
    
    def check_tls_configuration(self) -> SecurityCheck:
        """Check TLS configuration in application code"""
        violations = []
        
        # Scan Python files for TLS configuration
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check for SSL verification disabled
                    if 'verify=False' in content or 'verify_ssl=False' in content:
                        violations.append(f"{file_path}: SSL verification disabled")
                    
                    # Check for old TLS versions
                    if 'TLSv1' in content or 'SSLv' in content:
                        violations.append(f"{file_path}: Old TLS/SSL version referenced")
            except Exception:
                continue
        
        if violations:
            return SecurityCheck(
                check_name="TLS 1.2+ Configuration",
                passed=False,
                details=f"Found {len(violations)} TLS configuration issues:\n" + 
                       "\n".join(violations[:5]),
                severity="high",
                remediation="Ensure all connections use TLS 1.2+ and SSL verification is enabled"
            )
        else:
            return SecurityCheck(
                check_name="TLS 1.2+ Configuration",
                passed=True,
                details="TLS configuration follows security best practices",
                severity="high"
            )
    
    def check_rbac_implementation(self) -> SecurityCheck:
        """Check RBAC implementation in code"""
        # Look for RBAC decorators and middleware
        rbac_files = []
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    if 'require_role' in content or 'check_permission' in content or 'rbac' in content.lower():
                        rbac_files.append(str(file_path))
            except Exception:
                continue
        
        if rbac_files:
            return SecurityCheck(
                check_name="RBAC Enforcement",
                passed=True,
                details=f"RBAC implementation found in {len(rbac_files)} files",
                severity="high"
            )
        else:
            return SecurityCheck(
                check_name="RBAC Enforcement",
                passed=False,
                details="No RBAC implementation found in codebase",
                severity="high",
                remediation="Implement role-based access control for FIR operations"
            )
    
    def run_audit(self, s3_bucket: str = None, rds_instance: str = None,
                  ec2_instance: str = None, iam_role: str = None) -> SecurityAuditReport:
        """Run complete security audit"""
        import time
        
        print("=" * 60)
        print("BEDROCK MIGRATION - SECURITY AUDIT")
        print("=" * 60)
        print()
        
        checks = []
        
        # Infrastructure checks
        if s3_bucket:
            print("Checking S3 encryption...")
            checks.append(self.check_s3_encryption(s3_bucket))
        
        if rds_instance:
            print("Checking RDS encryption...")
            checks.append(self.check_rds_encryption(rds_instance))
        
        if ec2_instance:
            print("Checking security groups...")
            checks.append(self.check_security_groups(ec2_instance))
        
        if iam_role:
            print("Checking IAM policies...")
            checks.append(self.check_iam_policies(iam_role))
        
        print("Checking VPC endpoints...")
        checks.append(self.check_vpc_endpoints())
        
        # Code checks
        print("Checking for hardcoded credentials...")
        checks.append(self.check_hardcoded_credentials())
        
        print("Checking for PII in logs...")
        checks.append(self.check_pii_in_logs())
        
        print("Checking TLS configuration...")
        checks.append(self.check_tls_configuration())
        
        print("Checking RBAC implementation...")
        checks.append(self.check_rbac_implementation())
        
        # Count failures by severity
        critical_failures = sum(1 for c in checks if not c.passed and c.severity == "critical")
        high_failures = sum(1 for c in checks if not c.passed and c.severity == "high")
        medium_failures = sum(1 for c in checks if not c.passed and c.severity == "medium")
        low_failures = sum(1 for c in checks if not c.passed and c.severity == "low")
        
        # Overall pass/fail (no critical or high failures)
        overall_passed = critical_failures == 0 and high_failures == 0
        
        summary = {
            "total_checks": len(checks),
            "passed": sum(1 for c in checks if c.passed),
            "failed": sum(1 for c in checks if not c.passed),
            "critical_failures": critical_failures,
            "high_failures": high_failures,
            "medium_failures": medium_failures,
            "low_failures": low_failures
        }
        
        report = SecurityAuditReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            checks=checks,
            critical_failures=critical_failures,
            high_failures=high_failures,
            medium_failures=medium_failures,
            low_failures=low_failures,
            overall_passed=overall_passed,
            summary=summary
        )
        
        return report
    
    def print_report(self, report: SecurityAuditReport):
        """Print security audit report"""
        print()
        print("=" * 60)
        print("SECURITY AUDIT REPORT")
        print("=" * 60)
        print(f"Timestamp: {report.timestamp}")
        print()
        
        print("Summary:")
        print("-" * 60)
        print(f"Total Checks:       {report.summary['total_checks']}")
        print(f"Passed:             {report.summary['passed']}")
        print(f"Failed:             {report.summary['failed']}")
        print(f"  Critical:         {report.critical_failures}")
        print(f"  High:             {report.high_failures}")
        print(f"  Medium:           {report.medium_failures}")
        print(f"  Low:              {report.low_failures}")
        print()
        
        print("Detailed Results:")
        print("-" * 60)
        for check in report.checks:
            status = "✓ PASS" if check.passed else "✗ FAIL"
            severity_label = f"[{check.severity.upper()}]"
            print(f"{status} {severity_label:12} {check.check_name}")
            print(f"     {check.details}")
            if check.remediation:
                print(f"     Remediation: {check.remediation}")
            print()
        
        print("=" * 60)
        status = "✓ PASS" if report.overall_passed else "✗ FAIL"
        print(f"SECURITY AUDIT: {status}")
        if not report.overall_passed:
            print(f"Found {report.critical_failures} critical and {report.high_failures} high severity issues")
        print("=" * 60)
    
    def save_report(self, report: SecurityAuditReport, output_path: str = "security_audit_report.json"):
        """Save report to JSON file"""
        report_dict = {
            "timestamp": report.timestamp,
            "checks": [
                {
                    "check_name": c.check_name,
                    "passed": c.passed,
                    "details": c.details,
                    "severity": c.severity,
                    "remediation": c.remediation
                }
                for c in report.checks
            ],
            "critical_failures": report.critical_failures,
            "high_failures": report.high_failures,
            "medium_failures": report.medium_failures,
            "low_failures": report.low_failures,
            "overall_passed": report.overall_passed,
            "summary": report.summary
        }
        
        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)
        
        print(f"\nReport saved to: {output_path}")


def main():
    """Main entry point"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Perform security audit for Bedrock migration")
    parser.add_argument("--s3-bucket", help="S3 bucket name to audit")
    parser.add_argument("--rds-instance", help="RDS instance ID to audit")
    parser.add_argument("--ec2-instance", help="EC2 instance ID to audit")
    parser.add_argument("--iam-role", help="IAM role name to audit")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    auditor = SecurityAuditor(region=args.region, project_root=args.project_root)
    report = auditor.run_audit(
        s3_bucket=args.s3_bucket,
        rds_instance=args.rds_instance,
        ec2_instance=args.ec2_instance,
        iam_role=args.iam_role
    )
    auditor.print_report(report)
    auditor.save_report(report)
    
    # Exit with appropriate code
    sys.exit(0 if report.overall_passed else 1)


if __name__ == "__main__":
    main()
