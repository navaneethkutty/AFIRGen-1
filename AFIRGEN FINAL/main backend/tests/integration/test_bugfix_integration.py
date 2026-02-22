"""
Integration Tests for Bug Fixes - Phase 5

Tests verify complete workflows after all bug fixes:
- Text-only FIR generation flow (Bugs 3, 4, 6, 9)
- Audio file FIR generation flow (Preservation)
- Image file FIR generation flow (Preservation)
- Regeneration workflow (Bug 5)
- File upload validation (Bugs 7, 8)
- Graceful shutdown (Bug 10)
- Authentication and health check (Preservation)

**Validates: Requirements 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 3.1-3.8**
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys
import io
import wave
import struct
from PIL import Image
import json

# Add parent directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from agentv5 import app, session_manager
from infrastructure.input_validation import ValidationConstants

# Create test client
client = TestClient(app)

# Test API key
TEST_API_KEY = "test-api-key-12345"


# ============================================================================
# Helper Functions
# ============================================================================

def create_valid_wav_audio(duration_seconds: float = 1.0) -> bytes:
    """Create a valid WAV audio file."""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        num_frames = int(duration_seconds * 16000)
        for i in range(num_frames):
            wav_file.writeframes(struct.pack('<h', 0))
    buffer.seek(0)
    return buffer.read()


def create_valid_image() -> bytes:
    """Create a valid PNG image file."""
    buffer = io.BytesIO()
    img = Image.new('RGB', (100, 100), color='white')
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.read()