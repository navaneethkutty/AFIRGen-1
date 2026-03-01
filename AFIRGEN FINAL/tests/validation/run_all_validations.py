#!/usr/bin/env python3
"""
Master Validation Runner for Bedrock Migration

Runs all validation scripts in sequence:
1. Performance Validation
2. Cost Validation
3. Security Audit
4. Bug Triage Report

Generates a comprehensive validation report.
"""

import asyncio
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime


class ValidationRunner:
    """Runs all validation scripts and generates comprehensive report"""
    
    def __init__(self, base_url: str = "http://localhost:8000",
                 s3_bucket: str = None, rds_instance: str = None,
                 ec2_instance: str = None, iam_role: str = None,
                 region: str = "us-east-1"):
        self.base_url = base_url
        self.s3_bucket = s3_bucket
        self.rds_instance = rds_instance
        self.ec2_instance = ec2_instance
        self.iam_role = iam_role
        self.region = region
        self.results = {}
    
    def run_performance_validation(self) -> dict:
        """Run performance validation"""
        print("\n" + "=" * 60)
        print("RUNNING PERFORMANCE VALIDATION")
        print("=" * 60)
        
        try:
            result = subprocess.run(
                [sys.executable, "performance_validation.py", self.base_url],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            
            # Load report
            report_path = Path(__file__).parent / "performance_validation_report.json"
            if report_path.exists():
                with open(report_path, 'r') as f:
                    report = js