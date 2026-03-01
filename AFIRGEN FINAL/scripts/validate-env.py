#!/usr/bin/env python3
"""
Environment Variable Validation Script for AFIRGen Bedrock Migration

This script validates that all required environment variables are present
and properly configured for the Bedrock architecture.

Usage:
    python scripts/validate-env.py [--env-file .env.bedrock]
"""

import os
import sys
import argparse
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class ValidationResult:
    """Stores validation results"""
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.passed: int = 0
        self.failed: int = 0


def load_env_file(env_file: str) -> Dict[str, str]:
    """Load environment variables from a file"""
    env_vars = {}
    
    if not os.path.exists(env_file):
        print(f"{Colors.RED}Error: Environment file '{env_file}' not found{Colors.END}")
        sys.exit(1)
    
    with open(env_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                env_vars[key] = value
    
    return env_vars


def validate_required_variable(
    env_vars: Dict[str, str],
    var_name: str,
    result: ValidationResult,
    allow_empty: bool = False
) -> bool:
    """Validate that a required variable exists and is not empty"""
    if var_name not in env_vars:
        result.errors.append(f"Missing required variable: {var_name}")
        result.failed += 1
        return False
    
    value = env_vars[var_name]
    if not allow_empty and not value:
        result.errors.append(f"Variable {var_name} is empty")
        result.failed += 1
        return False
    
    result.passed += 1
    return True


def validate_choice_variable(
    env_vars: Dict[str, str],
    var_name: str,
    valid_choices: List[str],
    result: ValidationResult
) -> bool:
    """Validate that a variable has one of the valid choices"""
    if not validate_required_variable(env_vars, var_name, result):
        return False
    
    value = env_vars[var_name]
    if value not in valid_choices:
        result.errors.append(
            f"Invalid value for {var_name}: '{value}'. "
            f"Must be one of: {', '.join(valid_choices)}"
        )
        result.failed += 1
        result.passed -= 1  # Undo the pass from validate_required_variable
        return False
    
    return True


def validate_boolean_variable(
    env_vars: Dict[str, str],
    var_name: str,
    result: ValidationResult
) -> bool:
    """Validate that a variable is a boolean (true/false)"""
    if not validate_required_variable(env_vars, var_name, result):
        return False
    
    value = env_vars[var_name].lower()
    if value not in ['true', 'false']:
        result.errors.append(
            f"Invalid value for {var_name}: '{value}'. Must be 'true' or 'false'"
        )
        result.failed += 1
        result.passed -= 1
        return False
    
    return True


def validate_integer_variable(
    env_vars: Dict[str, str],
    var_name: str,
    result: ValidationResult,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None
) -> bool:
    """Validate that a variable is an integer within optional bounds"""
    if not validate_required_variable(env_vars, var_name, result):
        return False
    
    value = env_vars[var_name]
    try:
        int_value = int(value)
        
        if min_value is not None and int_value < min_value:
            result.errors.append(
                f"Value for {var_name} ({int_value}) is below minimum ({min_value})"
            )
            result.failed += 1
            result.passed -= 1
            return False
        
        if max_value is not None and int_value > max_value:
            result.errors.append(
                f"Value for {var_name} ({int_value}) is above maximum ({max_value})"
            )
            result.failed += 1
            result.passed -= 1
            return False
        
        return True
    except ValueError:
        result.errors.append(
            f"Invalid value for {var_name}: '{value}'. Must be an integer"
        )
        result.failed += 1
        result.passed -= 1
        return False


def validate_aws_region(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> bool:
    """Validate AWS region format"""
    if not validate_required_variable(env_vars, 'AWS_REGION', result):
        return False
    
    region = env_vars['AWS_REGION']
    
    # Basic AWS region format validation
    valid_prefixes = ['us-', 'eu-', 'ap-', 'sa-', 'ca-', 'me-', 'af-']
    if not any(region.startswith(prefix) for prefix in valid_prefixes):
        result.warnings.append(
            f"AWS_REGION '{region}' does not match standard AWS region format"
        )
    
    return True


def validate_bedrock_config(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> None:
    """Validate Bedrock-specific configuration"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Validating Bedrock Configuration...{Colors.END}")
    
    # Feature flag
    validate_boolean_variable(env_vars, 'ENABLE_BEDROCK', result)
    
    # AWS Region
    validate_aws_region(env_vars, result)
    
    # S3 Bucket
    validate_required_variable(env_vars, 'S3_BUCKET_NAME', result)
    
    # Bedrock Model IDs
    validate_required_variable(env_vars, 'BEDROCK_MODEL_ID', result)
    validate_required_variable(env_vars, 'BEDROCK_EMBEDDINGS_MODEL_ID', result)
    
    # Bedrock settings
    validate_integer_variable(env_vars, 'BEDROCK_MAX_CONCURRENT_CALLS', result, min_value=1, max_value=100)
    validate_integer_variable(env_vars, 'BEDROCK_TIMEOUT', result, min_value=10, max_value=300)
    
    # Check if model IDs match expected values
    if env_vars.get('BEDROCK_MODEL_ID') != 'anthropic.claude-3-sonnet-20240229-v1:0':
        result.warnings.append(
            f"BEDROCK_MODEL_ID is set to '{env_vars.get('BEDROCK_MODEL_ID')}'. "
            "Expected: 'anthropic.claude-3-sonnet-20240229-v1:0'"
        )
    
    if env_vars.get('BEDROCK_EMBEDDINGS_MODEL_ID') != 'amazon.titan-embed-text-v1':
        result.warnings.append(
            f"BEDROCK_EMBEDDINGS_MODEL_ID is set to '{env_vars.get('BEDROCK_EMBEDDINGS_MODEL_ID')}'. "
            "Expected: 'amazon.titan-embed-text-v1'"
        )


def validate_transcribe_config(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> None:
    """Validate Transcribe configuration"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Validating Transcribe Configuration...{Colors.END}")
    
    validate_required_variable(env_vars, 'TRANSCRIBE_LANGUAGES', result)
    validate_required_variable(env_vars, 'TRANSCRIBE_DEFAULT_LANGUAGE', result)
    validate_integer_variable(env_vars, 'TRANSCRIBE_TIMEOUT', result, min_value=60, max_value=600)
    
    # Validate language codes
    supported_languages = [
        'hi-IN', 'en-IN', 'ta-IN', 'te-IN', 'bn-IN',
        'mr-IN', 'gu-IN', 'kn-IN', 'ml-IN', 'pa-IN'
    ]
    
    if 'TRANSCRIBE_LANGUAGES' in env_vars:
        languages = [lang.strip() for lang in env_vars['TRANSCRIBE_LANGUAGES'].split(',')]
        for lang in languages:
            if lang not in supported_languages:
                result.warnings.append(
                    f"Language code '{lang}' in TRANSCRIBE_LANGUAGES may not be supported. "
                    f"Supported: {', '.join(supported_languages)}"
                )


def validate_textract_config(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> None:
    """Validate Textract configuration"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Validating Textract Configuration...{Colors.END}")
    
    validate_integer_variable(env_vars, 'TEXTRACT_TIMEOUT', result, min_value=10, max_value=300)
    validate_boolean_variable(env_vars, 'TEXTRACT_EXTRACT_FORMS', result)


def validate_vector_db_config(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> None:
    """Validate vector database configuration"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Validating Vector Database Configuration...{Colors.END}")
    
    # Vector DB type
    if not validate_choice_variable(
        env_vars, 'VECTOR_DB_TYPE', ['opensearch', 'aurora_pgvector'], result
    ):
        return
    
    db_type = env_vars['VECTOR_DB_TYPE']
    
    # Common settings
    validate_required_variable(env_vars, 'VECTOR_DB_INDEX_NAME', result)
    validate_integer_variable(env_vars, 'VECTOR_DB_EMBEDDING_DIMENSION', result, min_value=1)
    validate_integer_variable(env_vars, 'VECTOR_DB_TOP_K', result, min_value=1, max_value=100)
    
    # Check embedding dimension
    if env_vars.get('VECTOR_DB_EMBEDDING_DIMENSION') != '1536':
        result.warnings.append(
            f"VECTOR_DB_EMBEDDING_DIMENSION is set to '{env_vars.get('VECTOR_DB_EMBEDDING_DIMENSION')}'. "
            "Titan Embeddings generates 1536-dimensional vectors"
        )
    
    # Type-specific validation
    if db_type == 'opensearch':
        validate_opensearch_config(env_vars, result)
    elif db_type == 'aurora_pgvector':
        validate_aurora_config(env_vars, result)


def validate_opensearch_config(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> None:
    """Validate OpenSearch Serverless configuration"""
    print(f"  {Colors.BLUE}Validating OpenSearch Serverless settings...{Colors.END}")
    
    validate_required_variable(env_vars, 'OPENSEARCH_ENDPOINT', result)
    validate_required_variable(env_vars, 'OPENSEARCH_INDEX_NAME', result)
    validate_integer_variable(env_vars, 'OPENSEARCH_TIMEOUT', result, min_value=10, max_value=120)
    
    # Check endpoint format
    if 'OPENSEARCH_ENDPOINT' in env_vars:
        endpoint = env_vars['OPENSEARCH_ENDPOINT']
        if not endpoint.startswith('https://'):
            result.errors.append(
                f"OPENSEARCH_ENDPOINT must start with 'https://'. Got: '{endpoint}'"
            )
            result.failed += 1
        elif 'your-opensearch-collection' in endpoint:
            result.warnings.append(
                "OPENSEARCH_ENDPOINT contains placeholder value. Update with actual endpoint"
            )


def validate_aurora_config(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> None:
    """Validate Aurora PostgreSQL with pgvector configuration"""
    print(f"  {Colors.BLUE}Validating Aurora PostgreSQL settings...{Colors.END}")
    
    validate_required_variable(env_vars, 'AURORA_HOST', result)
    validate_integer_variable(env_vars, 'AURORA_PORT', result, min_value=1, max_value=65535)
    validate_required_variable(env_vars, 'AURORA_DATABASE', result)
    validate_required_variable(env_vars, 'AURORA_USER', result)
    validate_required_variable(env_vars, 'AURORA_PASSWORD', result)
    validate_required_variable(env_vars, 'AURORA_TABLE_NAME', result)
    validate_integer_variable(env_vars, 'AURORA_POOL_SIZE', result, min_value=1, max_value=100)
    validate_integer_variable(env_vars, 'AURORA_TIMEOUT', result, min_value=10, max_value=120)
    validate_boolean_variable(env_vars, 'AURORA_SSL', result)
    
    # Check for placeholder values
    if 'AURORA_HOST' in env_vars:
        host = env_vars['AURORA_HOST']
        if 'your-aurora-cluster' in host:
            result.warnings.append(
                "AURORA_HOST contains placeholder value. Update with actual cluster endpoint"
            )
    
    if 'AURORA_PASSWORD' in env_vars:
        password = env_vars['AURORA_PASSWORD']
        if password == 'your-secure-password':
            result.errors.append(
                "AURORA_PASSWORD contains placeholder value. Update with actual password"
            )
            result.failed += 1


def validate_retry_config(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> None:
    """Validate retry and resilience configuration"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Validating Retry and Resilience Configuration...{Colors.END}")
    
    validate_integer_variable(env_vars, 'MAX_RETRIES', result, min_value=0, max_value=10)
    validate_integer_variable(env_vars, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', result, min_value=1, max_value=20)
    validate_integer_variable(env_vars, 'CIRCUIT_BREAKER_RECOVERY_TIMEOUT', result, min_value=10, max_value=300)
    validate_integer_variable(env_vars, 'CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS', result, min_value=1, max_value=10)


def validate_monitoring_config(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> None:
    """Validate monitoring and observability configuration"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Validating Monitoring Configuration...{Colors.END}")
    
    validate_required_variable(env_vars, 'CLOUDWATCH_NAMESPACE', result)
    validate_boolean_variable(env_vars, 'ENABLE_XRAY_TRACING', result)
    validate_boolean_variable(env_vars, 'ENABLE_STRUCTURED_LOGGING', result)
    validate_choice_variable(
        env_vars, 'LOG_LEVEL', ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], result
    )


def validate_security_config(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> None:
    """Validate security configuration"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Validating Security Configuration...{Colors.END}")
    
    # KMS key is optional
    validate_required_variable(env_vars, 'KMS_KEY_ID', result, allow_empty=True)
    validate_boolean_variable(env_vars, 'USE_VPC_ENDPOINTS', result)
    
    # Check API key length
    if 'API_KEY' in env_vars:
        api_key = env_vars['API_KEY']
        if len(api_key) < 32:
            result.warnings.append(
                f"API_KEY length is {len(api_key)} characters. Recommended minimum: 32 characters"
            )
        if api_key == 'your-secure-api-key-here-min-32-chars':
            result.errors.append(
                "API_KEY contains placeholder value. Update with actual secure key"
            )
            result.failed += 1


def validate_performance_config(
    env_vars: Dict[str, str],
    result: ValidationResult
) -> None:
    """Validate performance configuration"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Validating Performance Configuration...{Colors.END}")
    
    validate_integer_variable(env_vars, 'MAX_AUDIO_FILE_SIZE_MB', result, min_value=1, max_value=500)
    validate_integer_variable(env_vars, 'MAX_IMAGE_FILE_SIZE_MB', result, min_value=1, max_value=100)
    validate_integer_variable(env_vars, 'S3_LIFECYCLE_DAYS', result, min_value=1, max_value=365)
    validate_integer_variable(env_vars, 'IPC_CACHE_SIZE', result, min_value=10, max_value=1000)
    validate_integer_variable(env_vars, 'CACHE_TTL', result, min_value=60, max_value=86400)


def print_summary(result: ValidationResult) -> None:
    """Print validation summary"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Validation Summary{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}")
    
    print(f"\n{Colors.GREEN}✓ Passed: {result.passed}{Colors.END}")
    print(f"{Colors.RED}✗ Failed: {result.failed}{Colors.END}")
    print(f"{Colors.YELLOW}⚠ Warnings: {len(result.warnings)}{Colors.END}")
    
    if result.errors:
        print(f"\n{Colors.RED}{Colors.BOLD}Errors:{Colors.END}")
        for error in result.errors:
            print(f"  {Colors.RED}✗ {error}{Colors.END}")
    
    if result.warnings:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}Warnings:{Colors.END}")
        for warning in result.warnings:
            print(f"  {Colors.YELLOW}⚠ {warning}{Colors.END}")
    
    if result.info:
        print(f"\n{Colors.BLUE}{Colors.BOLD}Info:{Colors.END}")
        for info in result.info:
            print(f"  {Colors.BLUE}ℹ {info}{Colors.END}")
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    
    if result.failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ All validations passed!{Colors.END}")
        if result.warnings:
            print(f"{Colors.YELLOW}Note: There are {len(result.warnings)} warnings to review{Colors.END}")
        return True
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Validation failed with {result.failed} errors{Colors.END}")
        return False


def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(
        description='Validate AFIRGen Bedrock environment configuration'
    )
    parser.add_argument(
        '--env-file',
        default='.env.bedrock',
        help='Path to environment file (default: .env.bedrock)'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors'
    )
    
    args = parser.parse_args()
    
    print(f"{Colors.BOLD}AFIRGen Bedrock Environment Validation{Colors.END}")
    print(f"Environment file: {args.env_file}\n")
    
    # Load environment variables
    env_vars = load_env_file(args.env_file)
    print(f"{Colors.GREEN}✓ Loaded {len(env_vars)} environment variables{Colors.END}")
    
    # Create result object
    result = ValidationResult()
    
    # Run validations
    validate_bedrock_config(env_vars, result)
    validate_transcribe_config(env_vars, result)
    validate_textract_config(env_vars, result)
    validate_vector_db_config(env_vars, result)
    validate_retry_config(env_vars, result)
    validate_monitoring_config(env_vars, result)
    validate_security_config(env_vars, result)
    validate_performance_config(env_vars, result)
    
    # Print summary
    success = print_summary(result)
    
    # Exit with appropriate code
    if not success:
        sys.exit(1)
    elif args.strict and result.warnings:
        print(f"\n{Colors.RED}Strict mode: Treating warnings as errors{Colors.END}")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
