"""
Performance tests for AFIRGen Bedrock migration.

This package contains performance tests that measure:
- End-to-end FIR generation latency
- Individual component latencies (Transcribe, Textract, Bedrock, vector search)
- Concurrent request handling
- System performance under load
- Comparison with GGUF baseline

Run with: pytest tests/performance/ --integration
"""
