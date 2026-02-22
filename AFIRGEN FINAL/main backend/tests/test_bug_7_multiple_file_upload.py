"""
Bug Condition Exploration Test for High Priority Bug 7 - Multiple File Upload Allowed

**Validates: Requirements 1.7, 2.7**

Property 1: Fault Condition - Frontend Allows Multiple File Selection

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.
GOAL: Surface counterexamples that demonstrate the bug exists.

Bug Description:
When a user selects both a letter file and an audio file in the frontend UI,
the system allows generation to proceed, but the backend rejects multiple inputs
(lines 1716-1719 in agentv5.py), causing unexpected failure after upload.

Expected Behavior (After Fix):
The frontend should disable the generation button or show a validation error
preventing submission when both file types are selected.

Current Behavior (Unfixed):
The frontend allows submission when both files are selected, leading to backend rejection.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from playwright.sync_api import sync_playwright, expect
import time
import os


# Strategy for generating file paths
@st.composite
def file_pair_strategy(draw):
    """Generate pairs of letter and audio files to test multiple file selection."""
    # Create temporary test files
    letter_extensions = ['.jpg', '.jpeg', '.png']
    audio_extensions = ['.mp3', '.wav']
    
    letter_ext = draw(st.sampled_from(letter_extensions))
    audio_ext = draw(st.sampled_from(audio_extensions))
    
    return {
        'letter_name': f'test_letter{letter_ext}',
        'audio_name': f'test_audio{audio_ext}',
        'letter_ext': letter_ext,
        'audio_ext': audio_ext
    }


class TestBug7MultipleFileUpload:
    """
    Bug Condition Exploration Test for Bug 7 - Multiple File Upload Allowed
    
    This test verifies that the frontend CURRENTLY ALLOWS (bug) selecting both
    letter and audio files simultaneously, which should be prevented.
    
    EXPECTED OUTCOME: Test FAILS because frontend allows submission (proves bug exists)
    """
    
    @pytest.fixture(scope="class")
    def browser_context(self):
        """Set up browser context for testing."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            yield context
            context.close()
            browser.close()
    
    @pytest.fixture
    def page(self, browser_context):
        """Create a new page for each test."""
        page = browser_context.new_page()
        yield page
        page.close()
    
    def create_test_file(self, filename, file_type='image'):
        """Create a temporary test file with appropriate content."""
        import tempfile
        
        # Create temp directory if it doesn't exist
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, filename)
        
        if file_type == 'image':
            # Create a minimal valid JPEG file
            jpeg_header = bytes([
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
                0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
                0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9
            ])
            with open(filepath, 'wb') as f:
                f.write(jpeg_header)
        elif file_type == 'audio':
            # Create a minimal valid WAV file
            wav_header = bytes([
                0x52, 0x49, 0x46, 0x46,  # "RIFF"
                0x24, 0x00, 0x00, 0x00,  # File size - 8
                0x57, 0x41, 0x56, 0x45,  # "WAVE"
                0x66, 0x6D, 0x74, 0x20,  # "fmt "
                0x10, 0x00, 0x00, 0x00,  # Chunk size
                0x01, 0x00,              # Audio format (PCM)
                0x01, 0x00,              # Number of channels
                0x44, 0xAC, 0x00, 0x00,  # Sample rate
                0x88, 0x58, 0x01, 0x00,  # Byte rate
                0x02, 0x00,              # Block align
                0x10, 0x00,              # Bits per sample
                0x64, 0x61, 0x74, 0x61,  # "data"
                0x00, 0x00, 0x00, 0x00   # Data size
            ])
            with open(filepath, 'wb') as f:
                f.write(wav_header)
        
        return filepath
    
    def test_multiple_file_selection_allowed_bug(self, page):
        """
        Property 1: Fault Condition - Frontend Allows Multiple File Selection
        
        This test demonstrates that the UNFIXED frontend allows users to select
        both a letter file and an audio file, and does NOT disable the generate button.
        
        EXPECTED: This test FAILS on unfixed code (generate button remains enabled)
        This failure CONFIRMS the bug exists.
        
        After fix: Test should pass (generate button disabled when both files selected)
        """
        # Navigate to the frontend (adjust URL as needed)
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        
        try:
            page.goto(frontend_url, timeout=5000)
        except Exception as e:
            pytest.skip(f"Frontend not available at {frontend_url}: {e}")
        
        # Create test files
        letter_file = self.create_test_file('test_letter.jpg', 'image')
        audio_file = self.create_test_file('test_audio.wav', 'audio')
        
        try:
            # Wait for page to load
            page.wait_for_selector('#letter-upload', timeout=5000)
            
            # Select letter file
            letter_input = page.locator('#letter-upload')
            letter_input.set_input_files(letter_file)
            
            # Wait a bit for the file to be processed
            page.wait_for_timeout(500)
            
            # Select audio file
            audio_input = page.locator('#audio-upload')
            audio_input.set_input_files(audio_file)
            
            # Wait a bit for the file to be processed
            page.wait_for_timeout(500)
            
            # Check if generate button exists
            generate_btn = page.locator('#generate-btn')
            
            # BUG CONDITION: On unfixed code, the button should be ENABLED
            # This assertion will FAIL on unfixed code, confirming the bug
            is_disabled = generate_btn.get_attribute('disabled')
            is_aria_disabled = generate_btn.get_attribute('aria-disabled')
            
            # CRITICAL ASSERTION: This should FAIL on unfixed code
            # The button should be disabled when both files are selected, but it's not
            assert is_disabled is not None or is_aria_disabled == 'true', (
                "BUG CONFIRMED: Generate button is ENABLED when both letter and audio "
                "files are selected. The frontend should prevent this by disabling the "
                "button or showing a validation error."
            )
            
            # Additional check: Look for validation error message
            # On unfixed code, there should be NO error message
            error_messages = page.locator('.toast-error, .error-message, [role="alert"]')
            error_count = error_messages.count()
            
            assert error_count > 0, (
                "BUG CONFIRMED: No validation error shown when both letter and audio "
                "files are selected. The frontend should display an error message "
                "preventing submission."
            )
            
        finally:
            # Cleanup test files
            if os.path.exists(letter_file):
                os.remove(letter_file)
            if os.path.exists(audio_file):
                os.remove(audio_file)
    
    @given(file_pair_strategy())
    @settings(
        max_examples=5,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_multiple_files_should_be_prevented(self, file_pair):
        """
        Property-Based Test: Multiple File Selection Should Be Prevented
        
        For ANY combination of letter file and audio file, when BOTH are selected,
        the frontend SHALL prevent submission by either:
        1. Disabling the generate button, OR
        2. Showing a validation error message
        
        EXPECTED: This test FAILS on unfixed code (neither prevention mechanism exists)
        This failure CONFIRMS the bug exists across various file combinations.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            
            try:
                page.goto(frontend_url, timeout=5000)
            except Exception:
                pytest.skip(f"Frontend not available at {frontend_url}")
            
            # Create test files based on generated strategy
            letter_file = self.create_test_file(
                file_pair['letter_name'],
                'image'
            )
            audio_file = self.create_test_file(
                file_pair['audio_name'],
                'audio'
            )
            
            try:
                # Wait for page to load
                page.wait_for_selector('#letter-upload', timeout=5000)
                
                # Select both files
                page.locator('#letter-upload').set_input_files(letter_file)
                page.wait_for_timeout(300)
                page.locator('#audio-upload').set_input_files(audio_file)
                page.wait_for_timeout(300)
                
                # Check prevention mechanisms
                generate_btn = page.locator('#generate-btn')
                is_disabled = generate_btn.get_attribute('disabled')
                is_aria_disabled = generate_btn.get_attribute('aria-disabled')
                
                error_messages = page.locator('.toast-error, .error-message, [role="alert"]')
                has_error = error_messages.count() > 0
                
                # At least ONE prevention mechanism should be active
                prevention_active = (
                    is_disabled is not None or 
                    is_aria_disabled == 'true' or 
                    has_error
                )
                
                # CRITICAL ASSERTION: This should FAIL on unfixed code
                assert prevention_active, (
                    f"BUG CONFIRMED for {file_pair['letter_name']} + {file_pair['audio_name']}: "
                    f"No prevention mechanism active when both files selected. "
                    f"Button disabled: {is_disabled}, aria-disabled: {is_aria_disabled}, "
                    f"Error shown: {has_error}"
                )
                
            finally:
                # Cleanup
                if os.path.exists(letter_file):
                    os.remove(letter_file)
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                page.close()
                context.close()
                browser.close()
    
    def test_backend_rejection_when_multiple_files_submitted(self, page):
        """
        Demonstrate Backend Rejection of Multiple Files
        
        This test shows that when the frontend DOES allow submission (the bug),
        the backend correctly rejects the request with a 400 error.
        
        This confirms the mismatch between frontend and backend behavior.
        """
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        
        try:
            page.goto(frontend_url, timeout=5000)
        except Exception as e:
            pytest.skip(f"Frontend not available at {frontend_url}: {e}")
        
        # Create test files
        letter_file = self.create_test_file('test_letter.jpg', 'image')
        audio_file = self.create_test_file('test_audio.wav', 'audio')
        
        try:
            # Wait for page to load
            page.wait_for_selector('#letter-upload', timeout=5000)
            
            # Select both files
            page.locator('#letter-upload').set_input_files(letter_file)
            page.wait_for_timeout(300)
            page.locator('#audio-upload').set_input_files(audio_file)
            page.wait_for_timeout(300)
            
            # Set up network monitoring to catch the backend error
            responses = []
            
            def handle_response(response):
                if '/process' in response.url:
                    responses.append({
                        'status': response.status,
                        'url': response.url
                    })
            
            page.on('response', handle_response)
            
            # Try to submit (if button is enabled - which it shouldn't be after fix)
            generate_btn = page.locator('#generate-btn')
            
            if not generate_btn.get_attribute('disabled'):
                # Button is enabled (BUG), try to click it
                generate_btn.click()
                
                # Wait for response
                page.wait_for_timeout(2000)
                
                # Check if backend rejected the request
                process_responses = [r for r in responses if '/process' in r['url']]
                
                if process_responses:
                    # Backend should return 400 error
                    assert any(r['status'] == 400 for r in process_responses), (
                        "Backend should reject multiple file uploads with 400 error"
                    )
                    
                    print(f"\nBackend correctly rejected multiple files: {process_responses}")
                    print("This confirms the frontend-backend mismatch (Bug 7)")
            
        finally:
            # Cleanup
            if os.path.exists(letter_file):
                os.remove(letter_file)
            if os.path.exists(audio_file):
                os.remove(audio_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
