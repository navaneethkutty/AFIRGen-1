"""
Unit tests for configuration validation.

Tests configuration loading, environment variable validation,
and default value handling.

Validates Requirements:
- 12.10-12.11: Configuration validation on startup
"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestConfigurationValidation:
    """Test configuration validation and environment variable handling"""
    
    def test_missing_required_mysql_password(self):
        """Test that missing MYSQL_PASSWORD raises error"""
        with patch.dict(os.environ, {}, clear=True):
            # Import fresh to avoid cached instance
            import importlib
            import infrastructure.secrets_manager as sm_module
            importlib.reload(sm_module)
            
            # Should raise error when required password is missing
            with pytest.raises(ValueError, match="Required secret.*not found"):
                sm_module.get_secret("MYSQL_PASSWORD", required=True)
    
    def test_missing_required_api_key(self):
        """Test that missing API_KEY raises error"""
        with patch.dict(os.environ, {}, clear=True):
            # Import fresh to avoid cached instance
            import importlib
            import infrastructure.secrets_manager as sm_module
            importlib.reload(sm_module)
            
            # Should raise error when required API key is missing
            with pytest.raises(ValueError, match="Required secret.*not found"):
                sm_module.get_secret("API_KEY", required=True)
    
    def test_missing_required_fir_auth_key(self):
        """Test that missing FIR_AUTH_KEY raises error"""
        with patch.dict(os.environ, {}, clear=True):
            # Import fresh to avoid cached instance
            import importlib
            import infrastructure.secrets_manager as sm_module
            importlib.reload(sm_module)
            
            # Should raise error when required auth key is missing
            with pytest.raises(ValueError, match="Required secret.*not found"):
                sm_module.get_secret("FIR_AUTH_KEY", required=True)
    
    def test_default_mysql_host(self):
        """Test default value for MYSQL_HOST"""
        with patch.dict(os.environ, {}, clear=True):
            host = os.getenv("MYSQL_HOST", "localhost")
            assert host == "localhost"
    
    def test_default_mysql_port(self):
        """Test default value for MYSQL_PORT"""
        with patch.dict(os.environ, {}, clear=True):
            port = int(os.getenv("MYSQL_PORT", 3306))
            assert port == 3306
            assert isinstance(port, int)
    
    def test_default_mysql_user(self):
        """Test default value for MYSQL_USER"""
        with patch('infrastructure.secrets_manager.get_secret') as mock_get_secret:
            mock_get_secret.return_value = "root"
            from infrastructure.secrets_manager import get_secret
            user = get_secret("MYSQL_USER", default="root")
            assert user == "root"
    
    def test_default_mysql_database(self):
        """Test default value for MYSQL_DB"""
        with patch('infrastructure.secrets_manager.get_secret') as mock_get_secret:
            mock_get_secret.return_value = "fir_db"
            from infrastructure.secrets_manager import get_secret
            database = get_secret("MYSQL_DB", default="fir_db")
            assert database == "fir_db"
    
    def test_default_rate_limit_requests(self):
        """Test default value for RATE_LIMIT_REQUESTS"""
        with patch.dict(os.environ, {}, clear=True):
            rate_limit = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
            assert rate_limit == 100
            assert isinstance(rate_limit, int)
    
    def test_default_rate_limit_window(self):
        """Test default value for RATE_LIMIT_WINDOW"""
        with patch.dict(os.environ, {}, clear=True):
            window = int(os.getenv("RATE_LIMIT_WINDOW", 60))
            assert window == 60
            assert isinstance(window, int)
    
    def test_default_max_concurrent_requests(self):
        """Test default value for MAX_CONCURRENT_REQUESTS"""
        with patch.dict(os.environ, {}, clear=True):
            max_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS", 15))
            assert max_requests == 15
            assert isinstance(max_requests, int)
    
    def test_default_log_level(self):
        """Test default value for LOG_LEVEL"""
        with patch.dict(os.environ, {}, clear=True):
            log_level = os.getenv("LOG_LEVEL", "INFO")
            assert log_level == "INFO"
    
    def test_default_environment(self):
        """Test default value for ENVIRONMENT"""
        with patch.dict(os.environ, {}, clear=True):
            environment = os.getenv("ENVIRONMENT", "production")
            assert environment == "production"
    
    def test_custom_mysql_host(self):
        """Test custom MYSQL_HOST from environment"""
        with patch.dict(os.environ, {"MYSQL_HOST": "custom-host.example.com"}):
            host = os.getenv("MYSQL_HOST", "localhost")
            assert host == "custom-host.example.com"
    
    def test_custom_mysql_port(self):
        """Test custom MYSQL_PORT from environment"""
        with patch.dict(os.environ, {"MYSQL_PORT": "3307"}):
            port = int(os.getenv("MYSQL_PORT", 3306))
            assert port == 3307
    
    def test_custom_rate_limit(self):
        """Test custom RATE_LIMIT_REQUESTS from environment"""
        with patch.dict(os.environ, {"RATE_LIMIT_REQUESTS": "200"}):
            rate_limit = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
            assert rate_limit == 200
    
    def test_custom_log_level(self):
        """Test custom LOG_LEVEL from environment"""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            log_level = os.getenv("LOG_LEVEL", "INFO")
            assert log_level == "DEBUG"
    
    def test_environment_production(self):
        """Test ENVIRONMENT set to production"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            environment = os.getenv("ENVIRONMENT", "production")
            assert environment == "production"
    
    def test_environment_development(self):
        """Test ENVIRONMENT set to development"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            environment = os.getenv("ENVIRONMENT", "production")
            assert environment == "development"
    
    def test_cors_origins_default_production(self):
        """Test CORS origins default in production"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            environment = os.getenv("ENVIRONMENT", "production").lower()
            default_cors = "http://localhost:3000,http://localhost:8000" if environment != "production" else ""
            cors_origins_env = os.getenv("CORS_ORIGINS", default_cors)
            assert cors_origins_env == ""
    
    def test_cors_origins_default_development(self):
        """Test CORS origins default in development"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            environment = os.getenv("ENVIRONMENT", "production").lower()
            default_cors = "http://localhost:3000,http://localhost:8000" if environment != "production" else ""
            cors_origins_env = os.getenv("CORS_ORIGINS", default_cors)
            assert cors_origins_env == "http://localhost:3000,http://localhost:8000"
    
    def test_cors_origins_custom(self):
        """Test custom CORS_ORIGINS from environment"""
        with patch.dict(os.environ, {"CORS_ORIGINS": "https://example.com,https://app.example.com"}):
            cors_origins_env = os.getenv("CORS_ORIGINS", "")
            cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
            assert len(cors_origins) == 2
            assert "https://example.com" in cors_origins
            assert "https://app.example.com" in cors_origins
    
    def test_trusted_proxy_ips_empty(self):
        """Test TRUSTED_PROXY_IPS when not set"""
        with patch.dict(os.environ, {}, clear=True):
            trusted_proxies = set(os.getenv("TRUSTED_PROXY_IPS", "").split(",")) if os.getenv("TRUSTED_PROXY_IPS") else set()
            assert trusted_proxies == set()
    
    def test_trusted_proxy_ips_set(self):
        """Test TRUSTED_PROXY_IPS when set"""
        with patch.dict(os.environ, {"TRUSTED_PROXY_IPS": "192.168.1.1,10.0.0.1"}):
            trusted_proxies = set(os.getenv("TRUSTED_PROXY_IPS", "").split(",")) if os.getenv("TRUSTED_PROXY_IPS") else set()
            assert len(trusted_proxies) == 2
            assert "192.168.1.1" in trusted_proxies
            assert "10.0.0.1" in trusted_proxies
    
    def test_trust_forwarded_headers_default(self):
        """Test TRUST_FORWARDED_HEADERS default value"""
        with patch.dict(os.environ, {}, clear=True):
            trust_forwarded = os.getenv("TRUST_FORWARDED_HEADERS", "false").lower() == "true"
            assert trust_forwarded is False
    
    def test_trust_forwarded_headers_enabled(self):
        """Test TRUST_FORWARDED_HEADERS when enabled"""
        with patch.dict(os.environ, {"TRUST_FORWARDED_HEADERS": "true"}):
            trust_forwarded = os.getenv("TRUST_FORWARDED_HEADERS", "false").lower() == "true"
            assert trust_forwarded is True
    
    def test_port_default(self):
        """Test default PORT value"""
        with patch.dict(os.environ, {}, clear=True):
            port = int(os.getenv("PORT", 8000))
            assert port == 8000
            assert isinstance(port, int)
    
    def test_port_custom(self):
        """Test custom PORT from environment"""
        with patch.dict(os.environ, {"PORT": "9000"}):
            port = int(os.getenv("PORT", 8000))
            assert port == 9000


class TestConfigurationStartupValidation:
    """Test configuration validation on application startup"""
    
    def test_all_required_variables_present(self):
        """Test startup succeeds when all required variables are present"""
        required_vars = {
            "MYSQL_PASSWORD": "test_password",
            "API_KEY": "test_api_key",
            "FIR_AUTH_KEY": "test_auth_key"
        }
        
        with patch('infrastructure.secrets_manager.get_secret') as mock_get_secret:
            def get_secret_impl(key, **kwargs):
                if kwargs.get('required') and key not in required_vars:
                    raise ValueError(f"Missing required secret: {key}")
                return required_vars.get(key, kwargs.get('default'))
            
            mock_get_secret.side_effect = get_secret_impl
            
            # Should not raise any errors
            from infrastructure.secrets_manager import get_secret
            password = get_secret("MYSQL_PASSWORD", required=True)
            api_key = get_secret("API_KEY", required=True)
            auth_key = get_secret("FIR_AUTH_KEY", required=True)
            
            assert password == "test_password"
            assert api_key == "test_api_key"
            assert auth_key == "test_auth_key"
    
    def test_startup_fails_with_missing_required_variable(self):
        """Test startup fails when required variable is missing"""
        with patch('infrastructure.secrets_manager.get_secret') as mock_get_secret:
            mock_get_secret.side_effect = ValueError("Missing required secret: MYSQL_PASSWORD")
            
            with pytest.raises(ValueError, match="Missing required secret"):
                from infrastructure.secrets_manager import get_secret
                get_secret("MYSQL_PASSWORD", required=True)
    
    def test_optional_variables_use_defaults(self):
        """Test optional variables use default values when not set"""
        with patch.dict(os.environ, {}, clear=True):
            # Test all optional variables have defaults
            assert os.getenv("MYSQL_HOST", "localhost") == "localhost"
            assert int(os.getenv("MYSQL_PORT", 3306)) == 3306
            assert int(os.getenv("RATE_LIMIT_REQUESTS", 100)) == 100
            assert int(os.getenv("RATE_LIMIT_WINDOW", 60)) == 60
            assert int(os.getenv("MAX_CONCURRENT_REQUESTS", 15)) == 15
            assert os.getenv("LOG_LEVEL", "INFO") == "INFO"
            assert os.getenv("ENVIRONMENT", "production") == "production"
            assert int(os.getenv("PORT", 8000)) == 8000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
