"""
Regression Test: S3 SSE-KMS Encryption (BUG-0001)
Tests that all S3 buckets have SSE-KMS encryption enabled.
"""

import boto3
import pytest
from botocore.exceptions import ClientError


class TestS3Encryption:
    """Test S3 bucket encryption configuration."""

    @pytest.fixture(scope="class")
    def s3_client(self):
        """Create S3 client."""
        return boto3.client('s3', region_name='us-east-1')

    @pytest.fixture(scope="class")
    def account_id(self):
        """Get AWS account ID."""
        sts = boto3.client('sts')
        return sts.get_caller_identity()['Account']

    @pytest.fixture(scope="class")
    def bucket_names(self, account_id):
        """Get expected bucket names."""
        return {
            'frontend': f'afirgen-frontend-{account_id}',
            'models': f'afirgen-models-{account_id}',
            'temp': f'afirgen-temp-{account_id}',
            'backups': f'afirgen-backups-{account_id}'
        }

    def test_frontend_bucket_encryption(self, s3_client, bucket_names):
        """Test frontend bucket has SSE-KMS encryption."""
        bucket = bucket_names['frontend']
        
        try:
            response = s3_client.get_bucket_encryption(Bucket=bucket)
            rules = response['ServerSideEncryptionConfiguration']['Rules']
            
            assert len(rules) > 0, f"No encryption rules found for {bucket}"
            
            rule = rules[0]
            encryption = rule['ApplyServerSideEncryptionByDefault']
            
            assert encryption['SSEAlgorithm'] == 'aws:kms', \
                f"Expected aws:kms, got {encryption['SSEAlgorithm']}"
            assert 'KMSMasterKeyID' in encryption, \
                "KMS key ID not specified"
            assert rule.get('BucketKeyEnabled', False), \
                "Bucket key not enabled"
            
            print(f"✅ {bucket}: SSE-KMS encryption verified")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                pytest.fail(f"❌ {bucket}: No encryption configuration found (BUG-0001)")
            raise

    def test_models_bucket_encryption(self, s3_client, bucket_names):
        """Test models bucket has SSE-KMS encryption."""
        bucket = bucket_names['models']
        
        try:
            response = s3_client.get_bucket_encryption(Bucket=bucket)
            rules = response['ServerSideEncryptionConfiguration']['Rules']
            
            assert len(rules) > 0, f"No encryption rules found for {bucket}"
            
            rule = rules[0]
            encryption = rule['ApplyServerSideEncryptionByDefault']
            
            assert encryption['SSEAlgorithm'] == 'aws:kms', \
                f"Expected aws:kms, got {encryption['SSEAlgorithm']}"
            assert 'KMSMasterKeyID' in encryption, \
                "KMS key ID not specified"
            assert rule.get('BucketKeyEnabled', False), \
                "Bucket key not enabled"
            
            print(f"✅ {bucket}: SSE-KMS encryption verified")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                pytest.fail(f"❌ {bucket}: No encryption configuration found (BUG-0001)")
            raise

    def test_temp_bucket_encryption(self, s3_client, bucket_names):
        """Test temp bucket has SSE-KMS encryption (CRITICAL for sensitive data)."""
        bucket = bucket_names['temp']
        
        try:
            response = s3_client.get_bucket_encryption(Bucket=bucket)
            rules = response['ServerSideEncryptionConfiguration']['Rules']
            
            assert len(rules) > 0, f"No encryption rules found for {bucket}"
            
            rule = rules[0]
            encryption = rule['ApplyServerSideEncryptionByDefault']
            
            assert encryption['SSEAlgorithm'] == 'aws:kms', \
                f"Expected aws:kms, got {encryption['SSEAlgorithm']}"
            assert 'KMSMasterKeyID' in encryption, \
                "KMS key ID not specified"
            assert rule.get('BucketKeyEnabled', False), \
                "Bucket key not enabled"
            
            print(f"✅ {bucket}: SSE-KMS encryption verified (CRITICAL)")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                pytest.fail(f"❌ {bucket}: No encryption configuration found (BUG-0001 CRITICAL)")
            raise

    def test_backups_bucket_encryption(self, s3_client, bucket_names):
        """Test backups bucket has SSE-KMS encryption."""
        bucket = bucket_names['backups']
        
        try:
            response = s3_client.get_bucket_encryption(Bucket=bucket)
            rules = response['ServerSideEncryptionConfiguration']['Rules']
            
            assert len(rules) > 0, f"No encryption rules found for {bucket}"
            
            rule = rules[0]
            encryption = rule['ApplyServerSideEncryptionByDefault']
            
            assert encryption['SSEAlgorithm'] == 'aws:kms', \
                f"Expected aws:kms, got {encryption['SSEAlgorithm']}"
            assert 'KMSMasterKeyID' in encryption, \
                "KMS key ID not specified"
            assert rule.get('BucketKeyEnabled', False), \
                "Bucket key not enabled"
            
            print(f"✅ {bucket}: SSE-KMS encryption verified")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                pytest.fail(f"❌ {bucket}: No encryption configuration found (BUG-0001)")
            raise

    def test_all_buckets_encryption_summary(self, s3_client, bucket_names):
        """Summary test: Verify all buckets have encryption."""
        results = {}
        
        for name, bucket in bucket_names.items():
            try:
                response = s3_client.get_bucket_encryption(Bucket=bucket)
                rules = response['ServerSideEncryptionConfiguration']['Rules']
                
                if len(rules) > 0:
                    encryption = rules[0]['ApplyServerSideEncryptionByDefault']
                    results[name] = {
                        'encrypted': True,
                        'algorithm': encryption['SSEAlgorithm'],
                        'bucket_key': rules[0].get('BucketKeyEnabled', False)
                    }
                else:
                    results[name] = {'encrypted': False}
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                    results[name] = {'encrypted': False}
                else:
                    results[name] = {'error': str(e)}
        
        # Print summary
        print("\n" + "="*60)
        print("S3 ENCRYPTION STATUS SUMMARY")
        print("="*60)
        
        all_encrypted = True
        for name, status in results.items():
            bucket = bucket_names[name]
            if status.get('encrypted'):
                print(f"✅ {bucket}")
                print(f"   Algorithm: {status['algorithm']}")
                print(f"   Bucket Key: {status['bucket_key']}")
            else:
                print(f"❌ {bucket}: NOT ENCRYPTED (BUG-0001)")
                all_encrypted = False
        
        print("="*60)
        
        assert all_encrypted, "Not all buckets have encryption enabled (BUG-0001)"
        print("✅ All S3 buckets have SSE-KMS encryption enabled")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
