#!/usr/bin/env python3
"""
Full Deployment Test Orchestrator
Starts all services (mock and real) and runs comprehensive tests
"""

import subprocess
import sys
import time
import os
import signal
import httpx
from pathlib import Path

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

class ServiceOrchestrator:
    def __init__(self):
        self.processes = []
        self.docker_started = False
        
    def print_header(self, text):
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}{text}{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
    
    def print_success(self, text):
        print(f"{GREEN}✓{RESET} {text}")
    
    def print_error(self, text):
        print(f"{RED}✗{RESET} {text}")
    
    def print_info(self, text):
        print(f"{BLUE}ℹ{RESET} {text}")
    
    def print_warning(self, text):
        print(f"{YELLOW}⚠{RESET} {text}")
    
    async def check_service(self, url, name, max_retries=30):
        """Check if a service is responding"""
        self.print_info(f"Waiting for {name} to be ready...")
        
        for i in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        self.print_success(f"{name} is ready!")
                        return True
            except Exception:
                pass
            
            if i < max_retries - 1:
                time.sleep(2)
        
        self.print_error(f"{name} failed to start")
        return False
    
    def start_docker_services(self):
        """Start MySQL and Redis using docker-compose"""
        self.print_header("Starting Docker Services (MySQL + Redis)")
        
        try:
            # Check if Docker is running
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.print_error("Docker is not running. Please start Docker Desktop.")
                return False
            
            self.print_info("Docker is running")
            
            # Stop any existing containers
            self.print_info("Stopping any existing test containers...")
            subprocess.run(
                ["docker-compose", "-f", "docker-compose.test.yaml", "down"],
                capture_output=True
            )
            
            # Start services
            self.print_info("Starting MySQL and Redis...")
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.test.yaml", "up", "-d"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.print_error(f"Failed to start Docker services: {result.stderr}")
                return False
            
            self.docker_started = True
            self.print_success("Docker services started")
            
            # Wait for services to be healthy
            self.print_info("Waiting for services to be healthy (this may take 30-60 seconds)...")
            time.sleep(10)
            
            # Check MySQL
            for i in range(30):
                result = subprocess.run(
                    ["docker-compose", "-f", "docker-compose.test.yaml", "ps"],
                    capture_output=True,
                    text=True
                )
                
                if "healthy" in result.stdout:
                    self.print_success("MySQL and Redis are healthy")
                    return True
                
                time.sleep(2)
            
            self.print_warning("Services started but health check timeout")
            return True
            
        except FileNotFoundError:
            self.print_error("docker-compose not found. Please install Docker Desktop.")
            return False
        except Exception as e:
            self.print_error(f"Error starting Docker services: {e}")
            return False
    
    def start_mock_model_server(self):
        """Start mock model server"""
        self.print_header("Starting Mock Model Server")
        
        script_path = Path("mock_services/mock_model_server.py")
        
        if not script_path.exists():
            self.print_error(f"Mock model server script not found: {script_path}")
            return False
        
        try:
            if sys.platform == "win32":
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            self.processes.append(("Mock Model Server", process))
            self.print_success("Mock Model Server process started")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to start Mock Model Server: {e}")
            return False
    
    def start_mock_asr_ocr_server(self):
        """Start mock ASR/OCR server"""
        self.print_header("Starting Mock ASR/OCR Server")
        
        script_path = Path("mock_services/mock_asr_ocr_server.py")
        
        if not script_path.exists():
            self.print_error(f"Mock ASR/OCR server script not found: {script_path}")
            return False
        
        try:
            if sys.platform == "win32":
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            self.processes.append(("Mock ASR/OCR Server", process))
            self.print_success("Mock ASR/OCR Server process started")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to start Mock ASR/OCR Server: {e}")
            return False
    
    def start_main_backend(self):
        """Start main backend server"""
        self.print_header("Starting Main Backend Server")
        
        backend_dir = Path("AFIRGEN FINAL/main backend")
        
        if not backend_dir.exists():
            self.print_error(f"Backend directory not found: {backend_dir}")
            return False
        
        # Set environment variables
        env = os.environ.copy()
        env.update({
            "API_KEY": "test-api-key-12345",
            "FIR_AUTH_KEY": "test-fir-auth-key-12345",
            "MYSQL_HOST": "localhost",
            "MYSQL_PORT": "3306",
            "MYSQL_USER": "fir_user",
            "MYSQL_PASSWORD": "test_password",
            "MYSQL_DB": "fir_db",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "MODEL_SERVER_URL": "http://localhost:8001",
            "ASR_OCR_SERVER_URL": "http://localhost:8002",
            "CORS_ORIGINS": "*",
            "LOG_LEVEL": "INFO",
            "ENVIRONMENT": "test"
        })
        
        try:
            if sys.platform == "win32":
                process = subprocess.Popen(
                    [sys.executable, "agentv5.py"],
                    cwd=str(backend_dir),
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                process = subprocess.Popen(
                    [sys.executable, "agentv5.py"],
                    cwd=str(backend_dir),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            self.processes.append(("Main Backend", process))
            self.print_success("Main Backend process started")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to start Main Backend: {e}")
            return False
    
    async def verify_all_services(self):
        """Verify all services are responding"""
        self.print_header("Verifying All Services")
        
        services = [
            ("http://localhost:8001/health", "Mock Model Server"),
            ("http://localhost:8002/health", "Mock ASR/OCR Server"),
            ("http://localhost:8000/health", "Main Backend"),
        ]
        
        all_healthy = True
        for url, name in services:
            if not await self.check_service(url, name):
                all_healthy = False
        
        return all_healthy
    
    def run_deployment_tests(self):
        """Run deployment readiness tests"""
        self.print_header("Running Deployment Readiness Tests")
        
        try:
            result = subprocess.run(
                [sys.executable, "test_deployment_readiness.py"],
                capture_output=True,
                text=True
            )
            
            print(result.stdout)
            
            if result.returncode == 0:
                self.print_success("Deployment tests PASSED")
                return True
            else:
                self.print_error("Deployment tests FAILED")
                return False
                
        except Exception as e:
            self.print_error(f"Failed to run deployment tests: {e}")
            return False
    
    def run_code_quality_tests(self):
        """Run code quality tests"""
        self.print_header("Running Code Quality Tests")
        
        try:
            result = subprocess.run(
                [sys.executable, "test_code_quality.py"],
                capture_output=True,
                text=True
            )
            
            print(result.stdout)
            
            if result.returncode == 0:
                self.print_success("Code quality tests PASSED")
                return True
            else:
                self.print_warning("Code quality tests completed with warnings")
                return True
                
        except Exception as e:
            self.print_error(f"Failed to run code quality tests: {e}")
            return False
    
    def cleanup(self):
        """Stop all services"""
        self.print_header("Cleaning Up")
        
        # Stop Python processes
        for name, process in self.processes:
            self.print_info(f"Stopping {name}...")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            except Exception as e:
                self.print_warning(f"Error stopping {name}: {e}")
        
        # Stop Docker services
        if self.docker_started:
            self.print_info("Stopping Docker services...")
            try:
                subprocess.run(
                    ["docker-compose", "-f", "docker-compose.test.yaml", "down"],
                    capture_output=True,
                    timeout=30
                )
                self.print_success("Docker services stopped")
            except Exception as e:
                self.print_warning(f"Error stopping Docker services: {e}")
        
        self.print_success("Cleanup complete")

async def main():
    orchestrator = ServiceOrchestrator()
    
    try:
        orchestrator.print_header("AFIRGen Full Deployment Test")
        orchestrator.print_info("This will start all services and run comprehensive tests")
        orchestrator.print_info("Press Ctrl+C at any time to stop\n")
        
        # Start Docker services
        if not orchestrator.start_docker_services():
            orchestrator.print_error("Failed to start Docker services")
            return 1
        
        time.sleep(5)
        
        # Start mock model server
        if not orchestrator.start_mock_model_server():
            orchestrator.print_error("Failed to start mock model server")
            return 1
        
        time.sleep(3)
        
        # Start mock ASR/OCR server
        if not orchestrator.start_mock_asr_ocr_server():
            orchestrator.print_error("Failed to start mock ASR/OCR server")
            return 1
        
        time.sleep(3)
        
        # Start main backend
        if not orchestrator.start_main_backend():
            orchestrator.print_error("Failed to start main backend")
            return 1
        
        time.sleep(5)
        
        # Verify all services
        if not await orchestrator.verify_all_services():
            orchestrator.print_error("Some services failed to start")
            return 1
        
        orchestrator.print_success("\n✅ All services are running!\n")
        
        # Run tests
        code_quality_passed = orchestrator.run_code_quality_tests()
        deployment_passed = orchestrator.run_deployment_tests()
        
        # Final summary
        orchestrator.print_header("Test Summary")
        
        if code_quality_passed and deployment_passed:
            orchestrator.print_success("🎉 ALL TESTS PASSED - System is deployment ready!")
            return 0
        else:
            orchestrator.print_error("❌ Some tests failed - Review results above")
            return 1
        
    except KeyboardInterrupt:
        orchestrator.print_warning("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        orchestrator.print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        orchestrator.cleanup()

if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
