#!/usr/bin/env python3
"""
Cost Validation Script for Bedrock Migration

Validates that the Bedrock architecture achieves cost reduction goals
compared to GPU instance (g5.2xlarge at $1.21/hour = $29.04/day).

Tracks costs for:
- Amazon Transcribe
- Amazon Textract
- Amazon Bedrock (Claude 3 Sonnet)
- Amazon Bedrock (Titan Embeddings)
- Vector Database (OpenSearch Serverless or Aurora pgvector)
- EC2 (t3.small/medium)
- S3 storage
- Data transfer
"""

import json
import time
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import boto3


@dataclass
class ServiceCost:
    """Cost for a specific AWS service"""
    service: str
    cost_usd: float
    usage_details: Dict[str, Any]


@dataclass
class CostReport:
    """Complete cost validation report"""
    timestamp: str
    period_hours: float
    baseline_cost_usd: float  # GPU instance cost
    total_cost_usd: float  # Bedrock architecture cost
    cost_savings_usd: float
    cost_savings_percent: float
    service_costs: List[ServiceCost]
    cost_breakdown: Dict[str, float]
    optimization_opportunities: List[str]
    passed: bool


class CostValidator:
    """Validates Bedrock architecture cost reduction goals"""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.ce = boto3.client('ce', region_name=region)  # Cost Explorer
        
        # Pricing (as of 2024, subject to change)
        self.pricing = {
            # GPU baseline
            "g5_2xlarge_hourly": 1.21,
            
            # Transcribe (per minute)
            "transcribe_per_minute": 0.024,
            
            # Textract (per page)
            "textract_per_page": 0.0015,
            
            # Bedrock Claude 3 Sonnet (per 1K tokens)
            "bedrock_claude_input_per_1k": 0.003,
            "bedrock_claude_output_per_1k": 0.015,
            
            # Bedrock Titan Embeddings (per 1K tokens)
            "bedrock_titan_per_1k": 0.0001,
            
            # OpenSearch Serverless (per OCU-hour)
            "opensearch_ocu_hourly": 0.24,
            
            # Aurora Serverless v2 (per ACU-hour)
            "aurora_acu_hourly": 0.12,
            
            # EC2 t3.small (per hour)
            "t3_small_hourly": 0.0208,
            
            # EC2 t3.medium (per hour)
            "t3_medium_hourly": 0.0416,
            
            # S3 Standard (per GB-month)
            "s3_storage_per_gb_month": 0.023,
            
            # S3 PUT requests (per 1K requests)
            "s3_put_per_1k": 0.005,
            
            # S3 GET requests (per 1K requests)
            "s3_get_per_1k": 0.0004,
        }
    
    def get_cloudwatch_metrics(self, namespace: str, metric_name: str, 
                               start_time: datetime, end_time: datetime,
                               statistic: str = "Sum") -> float:
        """Get CloudWatch metric value"""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour
                Statistics=[statistic]
            )
            
            if response['Datapoints']:
                return sum(dp[statistic] for dp in response['Datapoints'])
            return 0.0
        except Exception as e:
            print(f"Warning: Could not fetch metric {metric_name}: {e}")
            return 0.0
    
    def calculate_transcribe_cost(self, start_time: datetime, end_time: datetime) -> ServiceCost:
        """Calculate Amazon Transcribe costs"""
        # Get total minutes transcribed from CloudWatch
        total_minutes = self.get_cloudwatch_metrics(
            "AFIRGen/Bedrock",
            "TranscribeMinutesProcessed",
            start_time,
            end_time
        )
        
        cost = total_minutes * self.pricing["transcribe_per_minute"]
        
        return ServiceCost(
            service="Amazon Transcribe",
            cost_usd=cost,
            usage_details={
                "total_minutes": total_minutes,
                "rate_per_minute": self.pricing["transcribe_per_minute"]
            }
        )
    
    def calculate_textract_cost(self, start_time: datetime, end_time: datetime) -> ServiceCost:
        """Calculate Amazon Textract costs"""
        # Get total pages processed from CloudWatch
        total_pages = self.get_cloudwatch_metrics(
            "AFIRGen/Bedrock",
            "TextractPagesProcessed",
            start_time,
            end_time
        )
        
        cost = total_pages * self.pricing["textract_per_page"]
        
        return ServiceCost(
            service="Amazon Textract",
            cost_usd=cost,
            usage_details={
                "total_pages": total_pages,
                "rate_per_page": self.pricing["textract_per_page"]
            }
        )
    
    def calculate_bedrock_cost(self, start_time: datetime, end_time: datetime) -> ServiceCost:
        """Calculate Amazon Bedrock costs (Claude + Titan)"""
        # Get token usage from CloudWatch
        input_tokens = self.get_cloudwatch_metrics(
            "AFIRGen/Bedrock",
            "BedrockInputTokens",
            start_time,
            end_time
        )
        
        output_tokens = self.get_cloudwatch_metrics(
            "AFIRGen/Bedrock",
            "BedrockOutputTokens",
            start_time,
            end_time
        )
        
        embedding_tokens = self.get_cloudwatch_metrics(
            "AFIRGen/Bedrock",
            "TitanEmbeddingTokens",
            start_time,
            end_time
        )
        
        # Calculate costs
        claude_input_cost = (input_tokens / 1000) * self.pricing["bedrock_claude_input_per_1k"]
        claude_output_cost = (output_tokens / 1000) * self.pricing["bedrock_claude_output_per_1k"]
        titan_cost = (embedding_tokens / 1000) * self.pricing["bedrock_titan_per_1k"]
        
        total_cost = claude_input_cost + claude_output_cost + titan_cost
        
        return ServiceCost(
            service="Amazon Bedrock",
            cost_usd=total_cost,
            usage_details={
                "claude_input_tokens": input_tokens,
                "claude_output_tokens": output_tokens,
                "titan_embedding_tokens": embedding_tokens,
                "claude_input_cost": claude_input_cost,
                "claude_output_cost": claude_output_cost,
                "titan_cost": titan_cost
            }
        )
    
    def calculate_vector_db_cost(self, start_time: datetime, end_time: datetime,
                                 db_type: str = "opensearch") -> ServiceCost:
        """Calculate vector database costs"""
        hours = (end_time - start_time).total_seconds() / 3600
        
        if db_type == "opensearch":
            # Assume minimum 2 OCUs (1 for indexing, 1 for search)
            ocu_count = 2
            cost = hours * ocu_count * self.pricing["opensearch_ocu_hourly"]
            
            return ServiceCost(
                service="OpenSearch Serverless",
                cost_usd=cost,
                usage_details={
                    "hours": hours,
                    "ocu_count": ocu_count,
                    "rate_per_ocu_hour": self.pricing["opensearch_ocu_hourly"]
                }
            )
        else:  # aurora_pgvector
            # Assume minimum 0.5 ACU
            acu_count = 0.5
            cost = hours * acu_count * self.pricing["aurora_acu_hourly"]
            
            return ServiceCost(
                service="Aurora PostgreSQL (pgvector)",
                cost_usd=cost,
                usage_details={
                    "hours": hours,
                    "acu_count": acu_count,
                    "rate_per_acu_hour": self.pricing["aurora_acu_hourly"]
                }
            )
    
    def calculate_ec2_cost(self, start_time: datetime, end_time: datetime,
                          instance_type: str = "t3.small") -> ServiceCost:
        """Calculate EC2 instance costs"""
        hours = (end_time - start_time).total_seconds() / 3600
        
        rate_key = f"{instance_type}_hourly"
        hourly_rate = self.pricing.get(rate_key, self.pricing["t3_small_hourly"])
        cost = hours * hourly_rate
        
        return ServiceCost(
            service=f"EC2 ({instance_type})",
            cost_usd=cost,
            usage_details={
                "hours": hours,
                "instance_type": instance_type,
                "hourly_rate": hourly_rate
            }
        )
    
    def calculate_s3_cost(self, start_time: datetime, end_time: datetime) -> ServiceCost:
        """Calculate S3 storage and request costs"""
        # Get S3 metrics from CloudWatch
        put_requests = self.get_cloudwatch_metrics(
            "AFIRGen/Bedrock",
            "S3PutRequests",
            start_time,
            end_time
        )
        
        get_requests = self.get_cloudwatch_metrics(
            "AFIRGen/Bedrock",
            "S3GetRequests",
            start_time,
            end_time
        )
        
        # Estimate storage (assume 1GB average for temp files)
        hours = (end_time - start_time).total_seconds() / 3600
        storage_gb_hours = 1.0 * hours
        storage_gb_months = storage_gb_hours / (24 * 30)  # Convert to GB-months
        
        # Calculate costs
        put_cost = (put_requests / 1000) * self.pricing["s3_put_per_1k"]
        get_cost = (get_requests / 1000) * self.pricing["s3_get_per_1k"]
        storage_cost = storage_gb_months * self.pricing["s3_storage_per_gb_month"]
        
        total_cost = put_cost + get_cost + storage_cost
        
        return ServiceCost(
            service="Amazon S3",
            cost_usd=total_cost,
            usage_details={
                "put_requests": put_requests,
                "get_requests": get_requests,
                "storage_gb_months": storage_gb_months,
                "put_cost": put_cost,
                "get_cost": get_cost,
                "storage_cost": storage_cost
            }
        )
    
    def identify_optimization_opportunities(self, service_costs: List[ServiceCost],
                                           total_cost: float) -> List[str]:
        """Identify cost optimization opportunities"""
        opportunities = []
        
        # Find highest cost services
        sorted_costs = sorted(service_costs, key=lambda x: x.cost_usd, reverse=True)
        
        for cost in sorted_costs:
            percentage = (cost.cost_usd / total_cost * 100) if total_cost > 0 else 0
            
            if cost.service == "Amazon Bedrock" and percentage > 40:
                opportunities.append(
                    f"Bedrock costs are {percentage:.1f}% of total. Consider:\n"
                    "  - Implementing more aggressive caching for IPC sections\n"
                    "  - Optimizing prompt lengths to reduce token usage\n"
                    "  - Using Claude Haiku for simpler tasks"
                )
            
            if cost.service == "OpenSearch Serverless" and percentage > 30:
                opportunities.append(
                    f"OpenSearch costs are {percentage:.1f}% of total. Consider:\n"
                    "  - Switching to Aurora pgvector for lower costs\n"
                    "  - Reducing OCU count if query volume is low"
                )
            
            if cost.service == "Amazon Transcribe" and percentage > 25:
                opportunities.append(
                    f"Transcribe costs are {percentage:.1f}% of total. Consider:\n"
                    "  - Implementing audio compression before transcription\n"
                    "  - Batching transcription requests"
                )
        
        # General recommendations
        if not opportunities:
            opportunities.append(
                "Cost distribution is well-balanced. Continue monitoring for anomalies."
            )
        
        return opportunities
    
    def run_validation(self, period_hours: float = 24.0,
                      vector_db_type: str = "opensearch",
                      ec2_instance_type: str = "t3.small") -> CostReport:
        """Run complete cost validation"""
        print("=" * 60)
        print("BEDROCK MIGRATION - COST VALIDATION")
        print("=" * 60)
        print()
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=period_hours)
        
        print(f"Analysis Period: {start_time} to {end_time}")
        print(f"Duration: {period_hours} hours")
        print()
        
        # Calculate baseline GPU cost
        baseline_cost = period_hours * self.pricing["g5_2xlarge_hourly"]
        
        # Calculate Bedrock architecture costs
        service_costs = []
        
        print("Calculating service costs...")
        service_costs.append(self.calculate_transcribe_cost(start_time, end_time))
        service_costs.append(self.calculate_textract_cost(start_time, end_time))
        service_costs.append(self.calculate_bedrock_cost(start_time, end_time))
        service_costs.append(self.calculate_vector_db_cost(start_time, end_time, vector_db_type))
        service_costs.append(self.calculate_ec2_cost(start_time, end_time, ec2_instance_type))
        service_costs.append(self.calculate_s3_cost(start_time, end_time))
        
        total_cost = sum(sc.cost_usd for sc in service_costs)
        cost_savings = baseline_cost - total_cost
        cost_savings_percent = (cost_savings / baseline_cost * 100) if baseline_cost > 0 else 0
        
        # Cost breakdown
        cost_breakdown = {sc.service: sc.cost_usd for sc in service_costs}
        
        # Identify optimization opportunities
        opportunities = self.identify_optimization_opportunities(service_costs, total_cost)
        
        # Determine if cost goals are met (should be cheaper than GPU)
        passed = total_cost < baseline_cost
        
        report = CostReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            period_hours=period_hours,
            baseline_cost_usd=baseline_cost,
            total_cost_usd=total_cost,
            cost_savings_usd=cost_savings,
            cost_savings_percent=cost_savings_percent,
            service_costs=service_costs,
            cost_breakdown=cost_breakdown,
            optimization_opportunities=opportunities,
            passed=passed
        )
        
        return report
    
    def print_report(self, report: CostReport):
        """Print cost validation report"""
        print()
        print("=" * 60)
        print("COST VALIDATION REPORT")
        print("=" * 60)
        print(f"Timestamp: {report.timestamp}")
        print(f"Period: {report.period_hours} hours")
        print()
        
        print("Cost Comparison:")
        print("-" * 60)
        print(f"GPU Baseline (g5.2xlarge): ${report.baseline_cost_usd:.2f}")
        print(f"Bedrock Architecture:       ${report.total_cost_usd:.2f}")
        print(f"Cost Savings:               ${report.cost_savings_usd:.2f} ({report.cost_savings_percent:.1f}%)")
        print()
        
        print("Service Cost Breakdown:")
        print("-" * 60)
        for service_cost in report.service_costs:
            percentage = (service_cost.cost_usd / report.total_cost_usd * 100) if report.total_cost_usd > 0 else 0
            print(f"{service_cost.service:30} ${service_cost.cost_usd:8.2f} ({percentage:5.1f}%)")
        print("-" * 60)
        print(f"{'TOTAL':30} ${report.total_cost_usd:8.2f}")
        print()
        
        print("Optimization Opportunities:")
        print("-" * 60)
        for i, opportunity in enumerate(report.optimization_opportunities, 1):
            print(f"{i}. {opportunity}")
        print()
        
        print("=" * 60)
        status = "✓ PASS" if report.passed else "✗ FAIL"
        print(f"COST VALIDATION: {status}")
        if report.passed:
            print(f"Bedrock architecture is ${report.cost_savings_usd:.2f} cheaper than GPU baseline")
        else:
            print(f"Bedrock architecture is ${abs(report.cost_savings_usd):.2f} more expensive than GPU baseline")
        print("=" * 60)
    
    def save_report(self, report: CostReport, output_path: str = "cost_validation_report.json"):
        """Save report to JSON file"""
        report_dict = {
            "timestamp": report.timestamp,
            "period_hours": report.period_hours,
            "baseline_cost_usd": report.baseline_cost_usd,
            "total_cost_usd": report.total_cost_usd,
            "cost_savings_usd": report.cost_savings_usd,
            "cost_savings_percent": report.cost_savings_percent,
            "service_costs": [
                {
                    "service": sc.service,
                    "cost_usd": sc.cost_usd,
                    "usage_details": sc.usage_details
                }
                for sc in report.service_costs
            ],
            "cost_breakdown": report.cost_breakdown,
            "optimization_opportunities": report.optimization_opportunities,
            "passed": report.passed
        }
        
        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)
        
        print(f"\nReport saved to: {output_path}")


def main():
    """Main entry point"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Bedrock migration costs")
    parser.add_argument("--period-hours", type=float, default=24.0,
                       help="Analysis period in hours (default: 24)")
    parser.add_argument("--vector-db", choices=["opensearch", "aurora_pgvector"],
                       default="opensearch", help="Vector database type")
    parser.add_argument("--ec2-instance", default="t3.small",
                       help="EC2 instance type (default: t3.small)")
    parser.add_argument("--region", default="us-east-1",
                       help="AWS region (default: us-east-1)")
    
    args = parser.parse_args()
    
    validator = CostValidator(region=args.region)
    report = validator.run_validation(
        period_hours=args.period_hours,
        vector_db_type=args.vector_db,
        ec2_instance_type=args.ec2_instance
    )
    validator.print_report(report)
    validator.save_report(report)
    
    # Exit with appropriate code
    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
