"""
Pytest configuration and fixtures for AFIRGEN tests.

This file patches chromadb and reliability modules to work around Python 3.14 compatibility issues.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Set required environment variables for testing
os.environ.setdefault("MYSQL_USER", "test_user")
os.environ.setdefault("MYSQL_PASSWORD", "test_password")
os.environ.setdefault("MYSQL_DB", "test_db")
os.environ.setdefault("FIR_AUTH_KEY", "test-auth-key-123")
os.environ.setdefault("API_KEY", "test-key-123")
os.environ.setdefault("XRAY_ENABLED", "false")

# Add infrastructure directory to path for input_validation imports
backend_dir = Path(__file__).parent.parent
infrastructure_dir = backend_dir / "infrastructure"
if str(infrastructure_dir) not in sys.path:
    sys.path.insert(0, str(infrastructure_dir))

# Patch chromadb before any imports that might use it
# This works around the pydantic v1 incompatibility with Python 3.14
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.config'] = MagicMock()
sys.modules['chromadb.utils'] = MagicMock()
sys.modules['chromadb.utils.embedding_functions'] = MagicMock()

# Patch reliability module if it doesn't exist
try:
    import reliability
except ModuleNotFoundError:
    # Create mock reliability module with required classes
    reliability_mock = MagicMock()
    reliability_mock.CircuitBreaker = MagicMock
    reliability_mock.RetryPolicy = MagicMock
    reliability_mock.HealthMonitor = MagicMock
    reliability_mock.GracefulShutdown = MagicMock
    reliability_mock.AutoRecovery = MagicMock
    reliability_mock.DependencyHealthCheck = MagicMock
    sys.modules['reliability'] = reliability_mock

# Patch aws_xray_sdk module if it doesn't exist
try:
    import aws_xray_sdk
except ModuleNotFoundError:
    # Create mock aws_xray_sdk module with all required submodules
    xray_mock = MagicMock()
    xray_core_mock = MagicMock()
    xray_context_mock = MagicMock()
    xray_ext_mock = MagicMock()
    xray_fastapi_mock = MagicMock()
    xray_middleware_mock = MagicMock()
    xray_models_mock = MagicMock()
    xray_segment_mock = MagicMock()
    xray_subsegment_mock = MagicMock()
    
    xray_core_mock.xray_recorder = MagicMock()
    xray_core_mock.patch_all = MagicMock()
    xray_core_mock.context = xray_context_mock
    xray_core_mock.models = xray_models_mock
    xray_context_mock.Context = MagicMock
    
    xray_segment_mock.Segment = MagicMock
    xray_subsegment_mock.Subsegment = MagicMock
    xray_models_mock.segment = xray_segment_mock
    xray_models_mock.subsegment = xray_subsegment_mock
    
    xray_middleware_mock.XRayMiddleware = MagicMock
    xray_fastapi_mock.middleware = xray_middleware_mock
    xray_ext_mock.fastapi = xray_fastapi_mock
    
    xray_mock.core = xray_core_mock
    xray_mock.ext = xray_ext_mock
    
    sys.modules['aws_xray_sdk'] = xray_mock
    sys.modules['aws_xray_sdk.core'] = xray_core_mock
    sys.modules['aws_xray_sdk.core.context'] = xray_context_mock
    sys.modules['aws_xray_sdk.core.models'] = xray_models_mock
    sys.modules['aws_xray_sdk.core.models.segment'] = xray_segment_mock
    sys.modules['aws_xray_sdk.core.models.subsegment'] = xray_subsegment_mock
    sys.modules['aws_xray_sdk.ext'] = xray_ext_mock
    sys.modules['aws_xray_sdk.ext.fastapi'] = xray_fastapi_mock
    sys.modules['aws_xray_sdk.ext.fastapi.middleware'] = xray_middleware_mock
