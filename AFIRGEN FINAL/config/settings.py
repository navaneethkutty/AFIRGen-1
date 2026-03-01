"""
Configuration management system.
Loads and validates all environment variables with defaults.
"""

import os
import sys
import logging
from typing import Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class AWSConfig:
    """AWS service configuration."""
    region: str
    s3_bucket: str
    kms_key_id: Optional[str]


@dataclass
class BedrockConfig:
    """Bedrock service configuration."""
    model_id: str
    embeddings_model_id: str
    max_concurrent_calls: int
    max_retries: int


@dataclass
class VectorDBConfig:
    """Vector database configuration."""
    db_type: str  # 'opensearch' or 'aurora_pgvector'
    
    # OpenSearch config
    opensearch_endpoint: Optional[str]
    opensearch_index: str
    
    # Aurora config
    aurora_host: Optional[str]
    aurora_port: int
    aurora_database: Optional[str]
    aurora_user: Optional[str]
    aurora_password: Optional[str]
    aurora_table: str


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    enable_metrics: bool
    enable_xray: bool
    enable_structured_logging: bool
    log_level: str


class Settings:
    """
    Application settings loaded from environment variables.
    Validates configuration on initialization.
    """
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # Feature flag to toggle between GGUF and Bedrock implementations
        self.enable_bedrock = self._get_bool('ENABLE_BEDROCK', True)
        
        # Log which implementation is active
        implementation = "Bedrock (AWS managed services)" if self.enable_bedrock else "GGUF (self-hosted models)"
        logger.info(f"Active implementation: {implementation}")
        
        # AWS Configuration (required only if Bedrock is enabled)
        if self.enable_bedrock:
            self.aws = AWSConfig(
                region=self._get_required('AWS_REGION'),
                s3_bucket=self._get_required('S3_BUCKET_NAME'),
                kms_key_id=os.getenv('KMS_KEY_ID')
            )
        else:
            # Provide defaults for GGUF mode (not used but needed for structure)
            self.aws = AWSConfig(
                region=os.getenv('AWS_REGION', 'us-east-1'),
                s3_bucket=os.getenv('S3_BUCKET_NAME', 'not-configured'),
                kms_key_id=None
            )
        
        # Bedrock Configuration
        self.bedrock = BedrockConfig(
            model_id=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0'),
            embeddings_model_id=os.getenv('BEDROCK_EMBEDDINGS_MODEL_ID', 'amazon.titan-embed-text-v1'),
            max_concurrent_calls=int(os.getenv('BEDROCK_MAX_CONCURRENT', '10')),
            max_retries=int(os.getenv('BEDROCK_MAX_RETRIES', '3'))
        )
        
        # Vector Database Configuration (only required if Bedrock is enabled)
        vector_db_type = os.getenv('VECTOR_DB_TYPE', 'opensearch')
        
        if self.enable_bedrock:
            self._validate_vector_db_type(vector_db_type)
        
        self.vector_db = VectorDBConfig(
            db_type=vector_db_type,
            opensearch_endpoint=os.getenv('OPENSEARCH_ENDPOINT'),
            opensearch_index=os.getenv('OPENSEARCH_INDEX_NAME', 'ipc_sections'),
            aurora_host=os.getenv('AURORA_HOST'),
            aurora_port=int(os.getenv('AURORA_PORT', '5432')),
            aurora_database=os.getenv('AURORA_DATABASE'),
            aurora_user=os.getenv('AURORA_USER'),
            aurora_password=os.getenv('AURORA_PASSWORD'),
            aurora_table=os.getenv('AURORA_TABLE_NAME', 'ipc_sections')
        )
        
        # Validate vector DB specific config only if Bedrock is enabled
        if self.enable_bedrock:
            self._validate_vector_db_config()
        
        # Monitoring Configuration
        self.monitoring = MonitoringConfig(
            enable_metrics=self._get_bool('ENABLE_CLOUDWATCH_METRICS', True),
            enable_xray=self._get_bool('ENABLE_XRAY', True),
            enable_structured_logging=self._get_bool('ENABLE_STRUCTURED_LOGGING', True),
            log_level=os.getenv('LOG_LEVEL', 'INFO')
        )
        
        # Application Configuration
        self.app_name = os.getenv('APP_NAME', 'AFIRGen')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = self._get_bool('DEBUG', False)
        
        # Cache Configuration
        self.cache_max_size = int(os.getenv('CACHE_MAX_SIZE', '1000'))
        self.cache_ttl_seconds = int(os.getenv('CACHE_TTL_SECONDS', '3600'))
        
        # Rate Limiting
        self.rate_limit_per_minute = int(os.getenv('RATE_LIMIT_PER_MINUTE', '100'))
        
        # Log configuration (excluding sensitive values)
        self._log_configuration()
    
    def _get_required(self, key: str) -> str:
        """
        Get required environment variable.
        
        Args:
            key: Environment variable name
        
        Returns:
            Variable value
        
        Raises:
            SystemExit: If variable not set
        """
        value = os.getenv(key)
        if not value:
            logger.error(f"Required environment variable not set: {key}")
            sys.exit(1)
        return value
    
    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _validate_vector_db_type(self, db_type: str) -> None:
        """Validate vector database type."""
        valid_types = ['opensearch', 'aurora_pgvector']
        if db_type not in valid_types:
            logger.error(
                f"Invalid VECTOR_DB_TYPE: {db_type}. "
                f"Must be one of: {', '.join(valid_types)}"
            )
            sys.exit(1)
    
    def _validate_vector_db_config(self) -> None:
        """Validate vector database specific configuration."""
        if self.vector_db.db_type == 'opensearch':
            if not self.vector_db.opensearch_endpoint:
                logger.error("OPENSEARCH_ENDPOINT required when VECTOR_DB_TYPE=opensearch")
                sys.exit(1)
        
        elif self.vector_db.db_type == 'aurora_pgvector':
            missing = []
            if not self.vector_db.aurora_host:
                missing.append('AURORA_HOST')
            if not self.vector_db.aurora_database:
                missing.append('AURORA_DATABASE')
            if not self.vector_db.aurora_user:
                missing.append('AURORA_USER')
            if not self.vector_db.aurora_password:
                missing.append('AURORA_PASSWORD')
            
            if missing:
                logger.error(
                    f"Missing required Aurora configuration: {', '.join(missing)}"
                )
                sys.exit(1)
    
    def _log_configuration(self) -> None:
        """Log configuration (excluding sensitive values)."""
        logger.info("=" * 60)
        logger.info(f"Application: {self.app_name}")
        logger.info(f"Environment: {self.environment}")
        
        # Log active implementation prominently
        implementation = "Bedrock (AWS managed services)" if self.enable_bedrock else "GGUF (self-hosted models)"
        logger.info(f"ACTIVE IMPLEMENTATION: {implementation}")
        logger.info(f"Feature Flag ENABLE_BEDROCK: {self.enable_bedrock}")
        
        logger.info(f"AWS Region: {self.aws.region}")
        logger.info(f"S3 Bucket: {self.aws.s3_bucket}")
        
        if self.enable_bedrock:
            logger.info(f"Bedrock Model: {self.bedrock.model_id}")
            logger.info(f"Embeddings Model: {self.bedrock.embeddings_model_id}")
            logger.info(f"Vector DB Type: {self.vector_db.db_type}")
            
            if self.vector_db.db_type == 'opensearch':
                logger.info(f"OpenSearch Endpoint: {self.vector_db.opensearch_endpoint}")
            else:
                logger.info(f"Aurora Host: {self.vector_db.aurora_host}")
        else:
            logger.info("Using GGUF model servers (legacy implementation)")
        
        logger.info(f"CloudWatch Metrics: {self.monitoring.enable_metrics}")
        logger.info(f"X-Ray Tracing: {self.monitoring.enable_xray}")
        logger.info(f"Structured Logging: {self.monitoring.enable_structured_logging}")
        logger.info(f"Log Level: {self.monitoring.log_level}")
        logger.info("=" * 60)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create global settings instance.
    
    Returns:
        Settings instance
    """
    global _settings
    
    if _settings is None:
        _settings = Settings()
    
    return _settings
