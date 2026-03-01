"""
Regression Test: VPC Endpoints (BUG-0002)
Tests that VPC endpoints are created for Bedrock, Transcribe, and Textract.
"""

import boto3
import pytest
from botocore.exceptions import ClientError


class TestVPCEndpoints:
    """Test VPC endpoint configuration."""

    @pytest.fixture(scope="class")
    def ec2_client(self):
        """Create EC2 client."""
        return boto3.client('ec2', region_name='us-east-1')

    @pytest.fixture(scope="class")
    def required_services(self):
        """List of required VPC endpoint services."""
        return {
            'bedrock-runtime': 'com.amazonaws.us-east-1.bedrock-runtime',
            'transcribe': 'com.amazonaws.us-east-1.transcribe',
            'textract': 'com.amazonaws.us-east-1.textract',
            's3': 'com.amazonaws.us-east-1.s3'  # Gateway endpoint
        }

    def test_vpc_endpoints_exist(self, ec2_client, required_services):
        """Test that all required VPC endpoints exist."""
        try:
            response = ec2_client.describe_vpc_endpoints()
            endpoints = response['VpcEndpoints']
            
            # Get service names of existing endpoints
            existing_services = {ep['ServiceName'] for ep in endpoints}
            
            print("\n" + "="*60)
            print("VPC ENDPOINTS STATUS")
            print("="*60)
            
            missing_services = []
            for name, service in required_services.items():
                if service in existing_services:
                    # Find the endpoint details
                    endpoint = next(ep for ep in endpoints if ep['ServiceName'] == service)
                    print(f"✅ {name}: {endpoint['VpcEndpointId']}")
                    print(f"   Service: {service}")
                    print(f"   State: {endpoint['State']}")
                    print(f"   Type: {endpoint['VpcEndpointType']}")
                else:
                    print(f"❌ {name}: NOT FOUND (BUG-0002)")
                    missing_services.append(name)
            
            print("="*60)
            
            if missing_services:
                pytest.fail(
                    f"Missing VPC endpoints: {', '.join(missing_services)} (BUG-0002)"
                )
            
            print("✅ All required VPC endpoints exist")
            
        except ClientError as e:
            pytest.fail(f"Error checking VPC endpoints: {e}")

    def test_bedrock_runtime_endpoint(self, ec2_client):
        """Test Bedrock Runtime VPC endpoint specifically."""
        service_name = 'com.amazonaws.us-east-1.bedrock-runtime'
        
        try:
            response = ec2_client.describe_vpc_endpoints(
                Filters=[
                    {'Name': 'service-name', 'Values': [service_name]}
                ]
            )
            
            endpoints = response['VpcEndpoints']
            assert len(endpoints) > 0, \
                f"Bedrock Runtime VPC endpoint not found (BUG-0002)"
            
            endpoint = endpoints[0]
            assert endpoint['State'] == 'available', \
                f"Bedrock endpoint not available: {endpoint['State']}"
            assert endpoint['VpcEndpointType'] == 'Interface', \
                f"Expected Interface endpoint, got {endpoint['VpcEndpointType']}"
            assert endpoint.get('PrivateDnsEnabled', False), \
                "Private DNS not enabled"
            
            print(f"✅ Bedrock Runtime endpoint: {endpoint['VpcEndpointId']}")
            
        except ClientError as e:
            pytest.fail(f"Error checking Bedrock endpoint: {e}")

    def test_transcribe_endpoint(self, ec2_client):
        """Test Transcribe VPC endpoint specifically."""
        service_name = 'com.amazonaws.us-east-1.transcribe'
        
        try:
            response = ec2_client.describe_vpc_endpoints(
                Filters=[
                    {'Name': 'service-name', 'Values': [service_name]}
                ]
            )
            
            endpoints = response['VpcEndpoints']
            assert len(endpoints) > 0, \
                f"Transcribe VPC endpoint not found (BUG-0002)"
            
            endpoint = endpoints[0]
            assert endpoint['State'] == 'available', \
                f"Transcribe endpoint not available: {endpoint['State']}"
            assert endpoint['VpcEndpointType'] == 'Interface', \
                f"Expected Interface endpoint, got {endpoint['VpcEndpointType']}"
            assert endpoint.get('PrivateDnsEnabled', False), \
                "Private DNS not enabled"
            
            print(f"✅ Transcribe endpoint: {endpoint['VpcEndpointId']}")
            
        except ClientError as e:
            pytest.fail(f"Error checking Transcribe endpoint: {e}")

    def test_textract_endpoint(self, ec2_client):
        """Test Textract VPC endpoint specifically."""
        service_name = 'com.amazonaws.us-east-1.textract'
        
        try:
            response = ec2_client.describe_vpc_endpoints(
                Filters=[
                    {'Name': 'service-name', 'Values': [service_name]}
                ]
            )
            
            endpoints = response['VpcEndpoints']
            assert len(endpoints) > 0, \
                f"Textract VPC endpoint not found (BUG-0002)"
            
            endpoint = endpoints[0]
            assert endpoint['State'] == 'available', \
                f"Textract endpoint not available: {endpoint['State']}"
            assert endpoint['VpcEndpointType'] == 'Interface', \
                f"Expected Interface endpoint, got {endpoint['VpcEndpointType']}"
            assert endpoint.get('PrivateDnsEnabled', False), \
                "Private DNS not enabled"
            
            print(f"✅ Textract endpoint: {endpoint['VpcEndpointId']}")
            
        except ClientError as e:
            pytest.fail(f"Error checking Textract endpoint: {e}")

    def test_s3_gateway_endpoint(self, ec2_client):
        """Test S3 Gateway VPC endpoint."""
        service_name = 'com.amazonaws.us-east-1.s3'
        
        try:
            response = ec2_client.describe_vpc_endpoints(
                Filters=[
                    {'Name': 'service-name', 'Values': [service_name]}
                ]
            )
            
            endpoints = response['VpcEndpoints']
            assert len(endpoints) > 0, \
                f"S3 Gateway VPC endpoint not found"
            
            endpoint = endpoints[0]
            assert endpoint['State'] == 'available', \
                f"S3 endpoint not available: {endpoint['State']}"
            assert endpoint['VpcEndpointType'] == 'Gateway', \
                f"Expected Gateway endpoint, got {endpoint['VpcEndpointType']}"
            
            print(f"✅ S3 Gateway endpoint: {endpoint['VpcEndpointId']}")
            
        except ClientError as e:
            pytest.fail(f"Error checking S3 endpoint: {e}")

    def test_endpoint_security_groups(self, ec2_client):
        """Test that interface endpoints have security groups attached."""
        interface_services = [
            'com.amazonaws.us-east-1.bedrock-runtime',
            'com.amazonaws.us-east-1.transcribe',
            'com.amazonaws.us-east-1.textract'
        ]
        
        print("\n" + "="*60)
        print("VPC ENDPOINT SECURITY GROUPS")
        print("="*60)
        
        for service in interface_services:
            try:
                response = ec2_client.describe_vpc_endpoints(
                    Filters=[
                        {'Name': 'service-name', 'Values': [service]}
                    ]
                )
                
                if response['VpcEndpoints']:
                    endpoint = response['VpcEndpoints'][0]
                    security_groups = endpoint.get('Groups', [])
                    
                    assert len(security_groups) > 0, \
                        f"{service}: No security groups attached"
                    
                    print(f"✅ {service.split('.')[-1]}: {len(security_groups)} security group(s)")
                    for sg in security_groups:
                        print(f"   - {sg['GroupId']}: {sg.get('GroupName', 'N/A')}")
                        
            except ClientError as e:
                pytest.fail(f"Error checking security groups for {service}: {e}")
        
        print("="*60)

    def test_endpoint_subnets(self, ec2_client):
        """Test that interface endpoints are in multiple subnets (HA)."""
        interface_services = [
            'com.amazonaws.us-east-1.bedrock-runtime',
            'com.amazonaws.us-east-1.transcribe',
            'com.amazonaws.us-east-1.textract'
        ]
        
        print("\n" + "="*60)
        print("VPC ENDPOINT SUBNET CONFIGURATION")
        print("="*60)
        
        for service in interface_services:
            try:
                response = ec2_client.describe_vpc_endpoints(
                    Filters=[
                        {'Name': 'service-name', 'Values': [service]}
                    ]
                )
                
                if response['VpcEndpoints']:
                    endpoint = response['VpcEndpoints'][0]
                    subnets = endpoint.get('SubnetIds', [])
                    
                    # Recommend at least 2 subnets for HA
                    if len(subnets) >= 2:
                        print(f"✅ {service.split('.')[-1]}: {len(subnets)} subnets (HA)")
                    else:
                        print(f"⚠️  {service.split('.')[-1]}: {len(subnets)} subnet (consider adding more for HA)")
                    
                    for subnet in subnets:
                        print(f"   - {subnet}")
                        
            except ClientError as e:
                pytest.fail(f"Error checking subnets for {service}: {e}")
        
        print("="*60)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
