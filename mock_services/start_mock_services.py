#!/usr/bin/env python3
"""
Start all mock services for deployment testing
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def start_service(script_name, service_name):
    """Start a mock service in the background"""
    script_path = Path(__file__).parent / script_name
    
    print(f"🚀 Starting {service_name}...")
    
    if sys.platform == "win32":
        # Windows
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        # Unix-like
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    
    return process

def main():
    print("=" * 60)
    print("Starting Mock Services for Deployment Testing")
    print("=" * 60)
    print()
    
    services = []
    
    try:
        # Start mock model server
        model_server = start_service("mock_model_server.py", "Mock GGUF Model Server (port 8001)")
        services.append(("Model Server", model_server))
        time.sleep(2)
        
        # Start mock ASR/OCR server
        asr_ocr_server = start_service("mock_asr_ocr_server.py", "Mock ASR/OCR Server (port 8002)")
        services.append(("ASR/OCR Server", asr_ocr_server))
        time.sleep(2)
        
        print()
        print("✅ All mock services started successfully!")
        print()
        print("Services running:")
        print("  - Mock Model Server: http://localhost:8001")
        print("  - Mock ASR/OCR Server: http://localhost:8002")
        print()
        print("Press Ctrl+C to stop all services")
        print()
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all services...")
        for name, process in services:
            print(f"  Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("✅ All services stopped")

if __name__ == "__main__":
    main()
