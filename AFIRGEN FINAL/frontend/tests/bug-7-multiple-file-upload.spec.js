/**
 * Bug Condition Exploration Test for High Priority Bug 7 - Multiple File Upload Allowed
 * 
 * **Validates: Requirements 1.7, 2.7**
 * 
 * Property 1: Fault Condition - Frontend Allows Multiple File Selection
 * 
 * CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
 * DO NOT attempt to fix the test or the code when it fails.
 * GOAL: Surface counterexamples that demonstrate the bug exists.
 * 
 * Bug Description:
 * When a user selects both a letter file and an audio file in the frontend UI,
 * the system allows generation to proceed, but the backend rejects multiple inputs
 * (lines 1716-1719 in agentv5.py), causing unexpected failure after upload.
 * 
 * Expected Behavior (After Fix):
 * The frontend should disable the generation button or show a validation error
 * preventing submission when both file types are selected.
 * 
 * Current Behavior (Unfixed):
 * The frontend allows submission when both files are selected, leading to backend rejection.
 */

const { test, expect } = require('@playwright/test');
const path = require('path');
const fs = require('fs');
const os = require('os');

/**
 * Helper function to create a minimal valid JPEG file
 */
function createTestImageFile(filename) {
  const filepath = path.join(os.tmpdir(), filename);
  // Minimal valid JPEG file header
  const jpegHeader = Buffer.from([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
    0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
    0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9
  ]);
  fs.writeFileSync(filepath, jpegHeader);
  return filepath;
}

/**
 * Helper function to create a minimal valid WAV file
 */
function createTestAudioFile(filename) {
  const filepath = path.join(os.tmpdir(), filename);
  // Minimal valid WAV file header
  const wavHeader = Buffer.from([
    0x52, 0x49, 0x46, 0x46,  // "RIFF"
    0x24, 0x00, 0x00, 0x00,  // File size - 8
    0x57, 0x41, 0x56, 0x45,  // "WAVE"
    0x66, 0x6D, 0x74, 0x20,  // "fmt "
    0x10, 0x00, 0x00, 0x00,  // Chunk size
    0x01, 0x00,              // Audio format (PCM)
    0x01, 0x00,              // Number of channels
    0x44, 0xAC, 0x00, 0x00,  // Sample rate
    0x88, 0x58, 0x01, 0x00,  // Byte rate
    0x02, 0x00,              // Block align
    0x10, 0x00,              // Bits per sample
    0x64, 0x61, 0x74, 0x61,  // "data"
    0x00, 0x00, 0x00, 0x00   // Data size
  ]);
  fs.writeFileSync(filepath, wavHeader);
  return filepath;
}

/**
 * Cleanup helper
 */
function cleanupTestFile(filepath) {
  if (fs.existsSync(filepath)) {
    fs.unlinkSync(filepath);
  }
}

test.describe('Bug 7: Multiple File Upload Allowed (Bug Condition Exploration)', () => {
  
  test('Property 1: Frontend allows multiple file selection - BUG CONDITION', async ({ page }) => {
    /**
     * This test demonstrates that the UNFIXED frontend allows users to select
     * both a letter file and an audio file, and does NOT disable the generate button.
     * 
     * EXPECTED: This test FAILS on unfixed code (generate button remains enabled)
     * This failure CONFIRMS the bug exists.
     * 
     * After fix: Test should pass (generate button disabled when both files selected)
     */
    
    // Navigate to the application
    await page.goto('/');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Create test files
    const letterFile = createTestImageFile('test_letter.jpg');
    const audioFile = createTestAudioFile('test_audio.wav');
    
    try {
      // Get file inputs (they are hidden by CSS, which is normal)
      const letterInput = page.locator('#letter-upload');
      const audioInput = page.locator('#audio-upload');
      
      // Verify inputs exist in DOM (they won't be visible due to display:none)
      await expect(letterInput).toBeAttached();
      await expect(audioInput).toBeAttached();
      
      // Select letter file
      await letterInput.setInputFiles(letterFile);
      await page.waitForTimeout(500); // Wait for file processing
      
      // Verify letter file was selected
      const letterText = page.locator('#letter-text');
      await expect(letterText).toContainText('test_letter.jpg');
      
      // Select audio file
      await audioInput.setInputFiles(audioFile);
      await page.waitForTimeout(500); // Wait for file processing
      
      // Verify audio file was selected
      const audioText = page.locator('#audio-text');
      await expect(audioText).toContainText('test_audio.wav');
      
      // Check generate button state
      const generateBtn = page.locator('#generate-btn');
      await expect(generateBtn).toBeVisible();
      
      // BUG CONDITION: On unfixed code, the button should be ENABLED
      // This assertion will FAIL on unfixed code, confirming the bug
      const isDisabled = await generateBtn.isDisabled();
      const ariaDisabled = await generateBtn.getAttribute('aria-disabled');
      
      // CRITICAL ASSERTION: This should FAIL on unfixed code
      // The button should be disabled when both files are selected, but it's not
      expect(isDisabled || ariaDisabled === 'true').toBeTruthy();
      
      // If we reach here on unfixed code, the test fails with this message:
      if (!isDisabled && ariaDisabled !== 'true') {
        throw new Error(
          'BUG CONFIRMED: Generate button is ENABLED when both letter and audio ' +
          'files are selected. The frontend should prevent this by disabling the ' +
          'button or showing a validation error.'
        );
      }
      
      // Additional check: Look for validation error message
      // On unfixed code, there should be NO error message
      const errorToast = page.locator('.toast-error');
      const errorCount = await errorToast.count();
      
      // After fix, there should be an error message OR the button should be disabled
      if (!isDisabled && ariaDisabled !== 'true') {
        expect(errorCount).toBeGreaterThan(0);
        
        if (errorCount === 0) {
          throw new Error(
            'BUG CONFIRMED: No validation error shown when both letter and audio ' +
            'files are selected. The frontend should display an error message ' +
            'preventing submission.'
          );
        }
      }
      
    } finally {
      // Cleanup test files
      cleanupTestFile(letterFile);
      cleanupTestFile(audioFile);
    }
  });
  
  test('Property 1 - Variant: Test with different file types', async ({ page }) => {
    /**
     * Test the bug with different valid file type combinations
     * to ensure the bug exists across all supported file types.
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const testCases = [
      { letter: 'test1.jpg', audio: 'test1.wav' },
      { letter: 'test2.jpeg', audio: 'test2.mp3' },
      { letter: 'test3.png', audio: 'test3.wav' }
    ];
    
    for (const testCase of testCases) {
      const letterFile = createTestImageFile(testCase.letter);
      const audioFile = createTestAudioFile(testCase.audio);
      
      try {
        // Select both files
        await page.locator('#letter-upload').setInputFiles(letterFile);
        await page.waitForTimeout(300);
        await page.locator('#audio-upload').setInputFiles(audioFile);
        await page.waitForTimeout(300);
        
        // Check if prevention mechanism is active
        const generateBtn = page.locator('#generate-btn');
        const isDisabled = await generateBtn.isDisabled();
        const ariaDisabled = await generateBtn.getAttribute('aria-disabled');
        const errorToast = page.locator('.toast-error');
        const hasError = await errorToast.count() > 0;
        
        // At least ONE prevention mechanism should be active
        const preventionActive = isDisabled || ariaDisabled === 'true' || hasError;
        
        // CRITICAL ASSERTION: This should FAIL on unfixed code
        expect(preventionActive).toBeTruthy();
        
        if (!preventionActive) {
          throw new Error(
            `BUG CONFIRMED for ${testCase.letter} + ${testCase.audio}: ` +
            `No prevention mechanism active when both files selected. ` +
            `Button disabled: ${isDisabled}, aria-disabled: ${ariaDisabled}, ` +
            `Error shown: ${hasError}`
          );
        }
        
        // Clear files for next iteration
        await page.locator('#letter-upload').setInputFiles([]);
        await page.locator('#audio-upload').setInputFiles([]);
        await page.waitForTimeout(300);
        
      } finally {
        cleanupTestFile(letterFile);
        cleanupTestFile(audioFile);
      }
    }
  });
  
  test('Demonstrate: Single file selection should work correctly', async ({ page }) => {
    /**
     * This test verifies that selecting ONLY a letter file OR ONLY an audio file
     * works correctly (button should be enabled). This is NOT the bug - this should pass.
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Test 1: Only letter file
    const letterFile = createTestImageFile('single_letter.jpg');
    
    try {
      await page.locator('#letter-upload').setInputFiles(letterFile);
      await page.waitForTimeout(500);
      
      const generateBtn = page.locator('#generate-btn');
      const isDisabled = await generateBtn.isDisabled();
      
      // Button should be ENABLED for single file
      expect(isDisabled).toBeFalsy();
      
      // Clear file
      await page.locator('#letter-upload').setInputFiles([]);
      await page.waitForTimeout(300);
      
    } finally {
      cleanupTestFile(letterFile);
    }
    
    // Test 2: Only audio file
    const audioFile = createTestAudioFile('single_audio.wav');
    
    try {
      await page.locator('#audio-upload').setInputFiles(audioFile);
      await page.waitForTimeout(500);
      
      const generateBtn = page.locator('#generate-btn');
      const isDisabled = await generateBtn.isDisabled();
      
      // Button should be ENABLED for single file
      expect(isDisabled).toBeFalsy();
      
    } finally {
      cleanupTestFile(audioFile);
    }
  });
  
  test('Document: Current behavior shows frontend-backend mismatch', async ({ page }) => {
    /**
     * This test documents the current behavior: frontend allows submission,
     * but backend would reject it. This demonstrates the mismatch.
     * 
     * Note: This test doesn't actually submit to backend (to avoid side effects),
     * but documents the expected backend behavior based on the bug description.
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const letterFile = createTestImageFile('doc_letter.jpg');
    const audioFile = createTestAudioFile('doc_audio.wav');
    
    try {
      // Select both files
      await page.locator('#letter-upload').setInputFiles(letterFile);
      await page.waitForTimeout(300);
      await page.locator('#audio-upload').setInputFiles(audioFile);
      await page.waitForTimeout(300);
      
      const generateBtn = page.locator('#generate-btn');
      const isEnabled = !(await generateBtn.isDisabled());
      
      // Document the bug: If button is enabled (unfixed code), this is the mismatch
      if (isEnabled) {
        console.log('\n=== BUG DOCUMENTATION ===');
        console.log('Frontend State: Generate button is ENABLED');
        console.log('Files Selected: Letter (test_letter.jpg) + Audio (test_audio.wav)');
        console.log('Expected Backend Behavior: Would reject with 400 error (lines 1716-1719)');
        console.log('Issue: Frontend allows submission but backend rejects multiple inputs');
        console.log('Required Fix: Frontend must prevent submission when both files selected');
        console.log('========================\n');
      }
      
      // The fix should make the button disabled or show an error
      // After fix, isEnabled should be false
      
    } finally {
      cleanupTestFile(letterFile);
      cleanupTestFile(audioFile);
    }
  });
  
  test('Edge Case: Selecting files in different order', async ({ page }) => {
    /**
     * Test that the bug exists regardless of the order files are selected
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Test 1: Audio first, then letter
    const letterFile1 = createTestImageFile('order1_letter.jpg');
    const audioFile1 = createTestAudioFile('order1_audio.wav');
    
    try {
      // Select audio FIRST
      await page.locator('#audio-upload').setInputFiles(audioFile1);
      await page.waitForTimeout(300);
      
      // Then select letter
      await page.locator('#letter-upload').setInputFiles(letterFile1);
      await page.waitForTimeout(300);
      
      const generateBtn = page.locator('#generate-btn');
      const isDisabled = await generateBtn.isDisabled();
      const ariaDisabled = await generateBtn.getAttribute('aria-disabled');
      
      // Should be prevented regardless of order
      expect(isDisabled || ariaDisabled === 'true').toBeTruthy();
      
      if (!isDisabled && ariaDisabled !== 'true') {
        throw new Error(
          'BUG CONFIRMED: Button enabled when audio selected first, then letter'
        );
      }
      
    } finally {
      cleanupTestFile(letterFile1);
      cleanupTestFile(audioFile1);
    }
  });
  
  test('Edge Case: Replacing one file while other is selected', async ({ page }) => {
    /**
     * Test behavior when user replaces one file while the other is already selected
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const letterFile1 = createTestImageFile('replace_letter1.jpg');
    const letterFile2 = createTestImageFile('replace_letter2.jpg');
    const audioFile = createTestAudioFile('replace_audio.wav');
    
    try {
      // Select letter file
      await page.locator('#letter-upload').setInputFiles(letterFile1);
      await page.waitForTimeout(300);
      
      // Select audio file (now both are selected - bug condition)
      await page.locator('#audio-upload').setInputFiles(audioFile);
      await page.waitForTimeout(300);
      
      // Replace letter file with another letter file
      await page.locator('#letter-upload').setInputFiles(letterFile2);
      await page.waitForTimeout(300);
      
      // Bug should still exist - both files still selected
      const generateBtn = page.locator('#generate-btn');
      const isDisabled = await generateBtn.isDisabled();
      const ariaDisabled = await generateBtn.getAttribute('aria-disabled');
      
      expect(isDisabled || ariaDisabled === 'true').toBeTruthy();
      
      if (!isDisabled && ariaDisabled !== 'true') {
        throw new Error(
          'BUG CONFIRMED: Button enabled after replacing letter file while audio selected'
        );
      }
      
    } finally {
      cleanupTestFile(letterFile1);
      cleanupTestFile(letterFile2);
      cleanupTestFile(audioFile);
    }
  });
});
