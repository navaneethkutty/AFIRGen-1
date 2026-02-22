/**
 * Bug Condition Exploration Test for Bug 2.1 - Frontend UX Issue
 * 
 * **Validates: Requirements 2.8**
 * 
 * Property 1: Fault Condition - Poor UX
 * 
 * CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
 * DO NOT attempt to fix the test or the code when it fails.
 * GOAL: Surface counterexamples that demonstrate the UX bug exists.
 * 
 * Bug Description:
 * When a user selects both a letter file and an audio file in the frontend UI,
 * the system ALLOWS the selection but then:
 * 1. Disables the generate button
 * 2. Shows error message: "Error: Please select only one input type"
 * 
 * This is POOR UX - the frontend should PREVENT selecting both files in the first place,
 * not allow it and then show an error after the fact.
 * 
 * Expected Behavior (After Fix):
 * The frontend should prevent selecting the second file when one is already selected,
 * OR clear the first file when the second is selected, OR show a modal/dialog
 * asking which file to keep. The user should never see an error message for
 * something the UI allowed them to do.
 * 
 * Current Behavior (Unfixed):
 * The frontend allows both files to be selected, then shows an error message
 * and disables the button. This creates confusion and poor user experience.
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

test.describe('Bug 2.1: Frontend Allows Both Files Then Shows Error (UX Bug)', () => {
  
  test('Property 1: Frontend allows both files, then shows error - POOR UX', async ({ page }) => {
    /**
     * This test demonstrates the UNFIXED frontend's poor UX:
     * 1. User can select both letter and audio files (no prevention)
     * 2. Frontend then shows error message
     * 3. Generate button is disabled
     * 
     * EXPECTED: This test FAILS on unfixed code (error message is shown)
     * This failure CONFIRMS the UX bug exists.
     * 
     * After fix: Test should pass (frontend prevents selection OR handles it gracefully)
     */
    
    // Navigate to the application
    await page.goto('/');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Create test files
    const letterFile = createTestImageFile('test_letter.jpg');
    const audioFile = createTestAudioFile('test_audio.wav');
    
    try {
      // Get file inputs
      const letterInput = page.locator('#letter-upload');
      const audioInput = page.locator('#audio-upload');
      
      // Verify inputs exist
      await expect(letterInput).toBeAttached();
      await expect(audioInput).toBeAttached();
      
      // Select letter file first
      await letterInput.setInputFiles(letterFile);
      await page.waitForTimeout(500);
      
      // Verify letter file was selected
      const letterText = page.locator('#letter-text');
      await expect(letterText).toContainText('test_letter.jpg');
      
      // Now select audio file (this should be prevented in good UX)
      await audioInput.setInputFiles(audioFile);
      await page.waitForTimeout(500);
      
      // Verify audio file was selected (BUG: both files are now selected)
      const audioText = page.locator('#audio-text');
      await expect(audioText).toContainText('test_audio.wav');
      
      // Check for error message in status-ready element
      const statusReady = page.locator('#status-ready');
      await expect(statusReady).toBeVisible();
      
      const statusText = await statusReady.textContent();
      const statusColor = await statusReady.evaluate(el => el.style.color);
      
      // BUG CONDITION: On unfixed code, error message is shown
      // This is POOR UX - the frontend allowed the selection, then shows an error
      const hasErrorMessage = statusText.includes('Error: Please select only one input type');
      const isRedColor = statusColor === 'red';
      
      console.log('\n=== BUG 2.1 DOCUMENTATION ===');
      console.log('Status Text:', statusText);
      console.log('Status Color:', statusColor);
      console.log('Has Error Message:', hasErrorMessage);
      console.log('Is Red Color:', isRedColor);
      console.log('Letter File Selected:', await letterText.textContent());
      console.log('Audio File Selected:', await audioText.textContent());
      
      // CRITICAL ASSERTION: This should FAIL on unfixed code
      // The error message should NOT be shown because the UI should prevent this state
      expect(hasErrorMessage).toBeFalsy();
      
      if (hasErrorMessage) {
        console.log('\n❌ BUG CONFIRMED: Frontend shows error message after allowing both files to be selected');
        console.log('This is POOR UX - the frontend should prevent this selection, not show an error after');
        console.log('========================\n');
        
        throw new Error(
          'BUG 2.1 CONFIRMED: Frontend allows both letter and audio files to be selected, ' +
          'then shows error message "' + statusText + '". ' +
          'This is poor UX - the frontend should prevent selecting both files in the first place, ' +
          'not allow it and then show an error.'
        );
      }
      
      // Also verify the generate button is disabled (part of the poor UX)
      const generateBtn = page.locator('#generate-btn');
      const isDisabled = await generateBtn.isDisabled();
      const ariaDisabled = await generateBtn.getAttribute('aria-disabled');
      
      console.log('Generate Button Disabled:', isDisabled);
      console.log('Generate Button aria-disabled:', ariaDisabled);
      
      // On unfixed code, button should be disabled
      if (hasErrorMessage && (!isDisabled && ariaDisabled !== 'true')) {
        console.log('⚠️  WARNING: Error message shown but button not disabled - inconsistent state');
      }
      
    } finally {
      // Cleanup test files
      cleanupTestFile(letterFile);
      cleanupTestFile(audioFile);
    }
  });
  
  test('Property 1 - Variant: Error shown regardless of selection order', async ({ page }) => {
    /**
     * Test that the UX bug exists regardless of which file is selected first
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const letterFile = createTestImageFile('order_letter.jpg');
    const audioFile = createTestAudioFile('order_audio.wav');
    
    try {
      // Test: Audio first, then letter
      await page.locator('#audio-upload').setInputFiles(audioFile);
      await page.waitForTimeout(300);
      
      await page.locator('#letter-upload').setInputFiles(letterFile);
      await page.waitForTimeout(300);
      
      // Check for error message
      const statusReady = page.locator('#status-ready');
      const statusText = await statusReady.textContent();
      const hasErrorMessage = statusText.includes('Error: Please select only one input type');
      
      console.log('\n=== Selection Order Test (Audio First) ===');
      console.log('Status Text:', statusText);
      console.log('Has Error Message:', hasErrorMessage);
      
      // Should NOT show error message (good UX would prevent this)
      expect(hasErrorMessage).toBeFalsy();
      
      if (hasErrorMessage) {
        throw new Error(
          'BUG 2.1 CONFIRMED (Audio First): Error message shown after allowing both files. ' +
          'Status: "' + statusText + '"'
        );
      }
      
    } finally {
      cleanupTestFile(letterFile);
      cleanupTestFile(audioFile);
    }
  });
  
  test('Document: Current behavior creates user confusion', async ({ page }) => {
    /**
     * This test documents the user experience issue:
     * The UI allows an action (selecting both files) but then punishes the user
     * with an error message. This creates confusion and frustration.
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const letterFile = createTestImageFile('doc_letter.jpg');
    const audioFile = createTestAudioFile('doc_audio.wav');
    
    try {
      // Simulate user workflow
      console.log('\n=== USER EXPERIENCE DOCUMENTATION ===');
      console.log('Step 1: User selects letter file');
      await page.locator('#letter-upload').setInputFiles(letterFile);
      await page.waitForTimeout(300);
      
      let statusReady = page.locator('#status-ready');
      let statusText = await statusReady.textContent();
      console.log('  Status:', statusText);
      console.log('  User sees: "Ready to generate FIR" - positive feedback');
      
      console.log('\nStep 2: User decides to also add audio file');
      await page.locator('#audio-upload').setInputFiles(audioFile);
      await page.waitForTimeout(300);
      
      statusText = await statusReady.textContent();
      const statusColor = await statusReady.evaluate(el => el.style.color);
      console.log('  Status:', statusText);
      console.log('  Color:', statusColor);
      
      if (statusText.includes('Error')) {
        console.log('  User sees: ERROR MESSAGE in red - negative feedback');
        console.log('\n❌ PROBLEM: UI allowed the action but then shows error');
        console.log('This creates confusion: "Why did the UI let me select both if it\'s not allowed?"');
        console.log('\n✅ BETTER UX OPTIONS:');
        console.log('  1. Disable/hide audio upload when letter is selected (and vice versa)');
        console.log('  2. Auto-clear first file when second is selected');
        console.log('  3. Show modal: "Replace letter with audio?" [Yes] [No]');
        console.log('  4. Allow both files (if backend supports it)');
        console.log('=====================================\n');
      }
      
      const generateBtn = page.locator('#generate-btn');
      const isDisabled = await generateBtn.isDisabled();
      console.log('Generate Button Disabled:', isDisabled);
      
      if (isDisabled && statusText.includes('Error')) {
        console.log('\n⚠️  UX ISSUE CONFIRMED:');
        console.log('- Both files are selected (UI allowed it)');
        console.log('- Error message is shown (UI punishes user)');
        console.log('- Button is disabled (user cannot proceed)');
        console.log('- User is confused and frustrated');
      }
      
    } finally {
      cleanupTestFile(letterFile);
      cleanupTestFile(audioFile);
    }
  });
  
  test('Demonstrate: Single file selection shows positive feedback', async ({ page }) => {
    /**
     * This test shows that single file selection works correctly with positive feedback.
     * This is the CORRECT behavior that should be maintained.
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const letterFile = createTestImageFile('single_letter.jpg');
    
    try {
      await page.locator('#letter-upload').setInputFiles(letterFile);
      await page.waitForTimeout(500);
      
      const statusReady = page.locator('#status-ready');
      const statusText = await statusReady.textContent();
      const statusColor = await statusReady.evaluate(el => el.style.color);
      
      console.log('\n=== CORRECT BEHAVIOR (Single File) ===');
      console.log('Status Text:', statusText);
      console.log('Status Color:', statusColor || 'default');
      
      // Should show positive message, not error
      expect(statusText).toContain('Ready to generate FIR');
      expect(statusText).not.toContain('Error');
      
      // Button should be enabled
      const generateBtn = page.locator('#generate-btn');
      const isDisabled = await generateBtn.isDisabled();
      expect(isDisabled).toBeFalsy();
      
      console.log('Generate Button Enabled:', !isDisabled);
      console.log('✅ This is GOOD UX - positive feedback, enabled button');
      console.log('=====================================\n');
      
    } finally {
      cleanupTestFile(letterFile);
    }
  });
  
  test('Edge Case: Rapidly selecting both files', async ({ page }) => {
    /**
     * Test that the bug exists even when files are selected rapidly
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const letterFile = createTestImageFile('rapid_letter.jpg');
    const audioFile = createTestAudioFile('rapid_audio.wav');
    
    try {
      // Select both files rapidly without waiting
      await page.locator('#letter-upload').setInputFiles(letterFile);
      await page.locator('#audio-upload').setInputFiles(audioFile);
      
      // Wait for UI to update
      await page.waitForTimeout(800);
      
      // Check for error message
      const statusReady = page.locator('#status-ready');
      const statusText = await statusReady.textContent();
      const hasErrorMessage = statusText.includes('Error: Please select only one input type');
      
      console.log('\n=== Rapid Selection Test ===');
      console.log('Status Text:', statusText);
      console.log('Has Error Message:', hasErrorMessage);
      
      // Should NOT show error message
      expect(hasErrorMessage).toBeFalsy();
      
      if (hasErrorMessage) {
        throw new Error(
          'BUG 2.1 CONFIRMED (Rapid Selection): Error message shown. ' +
          'Even with rapid selection, the UX issue persists.'
        );
      }
      
    } finally {
      cleanupTestFile(letterFile);
      cleanupTestFile(audioFile);
    }
  });
});
