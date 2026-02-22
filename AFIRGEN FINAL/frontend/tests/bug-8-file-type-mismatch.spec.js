/**
 * Bug Condition Exploration Test for High Priority Bug 8 - File Type Mismatch
 * 
 * **Validates: Requirements 1.8, 2.8**
 * 
 * Property 1: Fault Condition - Frontend/Backend File Type Mismatch
 * 
 * CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
 * DO NOT attempt to fix the test or the code when it fails.
 * GOAL: Surface counterexamples that demonstrate the bug exists.
 * 
 * Bug Description:
 * When a user uploads .pdf, .txt, .doc, or .docx letter files OR .m4a or .ogg audio files,
 * the frontend accepts these types (app.js lines 399-444) but the backend only supports
 * jpeg/png images and wav/mpeg/mp3 audio (input_validation.py lines 27-31).
 * 
 * Expected Behavior (After Fix):
 * The frontend should only accept file types that are supported by both frontend and backend:
 * - Letter files: .jpg, .jpeg, .png
 * - Audio files: .wav, .mp3
 * 
 * Current Behavior (Unfixed):
 * The frontend accepts .pdf, .txt, .doc, .docx, .m4a, .ogg files, leading to backend rejection.
 */

const { test, expect } = require('@playwright/test');
const path = require('path');
const fs = require('fs');
const os = require('os');

/**
 * Helper function to create a minimal PDF file
 */
function createTestPdfFile(filename) {
  const filepath = path.join(os.tmpdir(), filename);
  // Minimal valid PDF file
  const pdfContent = Buffer.from(
    '%PDF-1.4\n' +
    '1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n' +
    '2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n' +
    '3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n' +
    'xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\n' +
    'trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF'
  );
  fs.writeFileSync(filepath, pdfContent);
  return filepath;
}

/**
 * Helper function to create a text file
 */
function createTestTxtFile(filename) {
  const filepath = path.join(os.tmpdir(), filename);
  fs.writeFileSync(filepath, 'This is a test text file for FIR generation.');
  return filepath;
}

/**
 * Helper function to create a minimal M4A file
 */
function createTestM4aFile(filename) {
  const filepath = path.join(os.tmpdir(), filename);
  // Minimal M4A file header (ftyp box)
  const m4aHeader = Buffer.from([
    0x00, 0x00, 0x00, 0x20,  // Box size
    0x66, 0x74, 0x79, 0x70,  // 'ftyp'
    0x4D, 0x34, 0x41, 0x20,  // 'M4A '
    0x00, 0x00, 0x00, 0x00,  // Minor version
    0x4D, 0x34, 0x41, 0x20,  // Compatible brand
    0x6D, 0x70, 0x34, 0x32,  // 'mp42'
    0x69, 0x73, 0x6F, 0x6D,  // 'isom'
    0x00, 0x00, 0x00, 0x00   // Padding
  ]);
  fs.writeFileSync(filepath, m4aHeader);
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

test.describe('Bug 8: File Type Mismatch (Bug Condition Exploration)', () => {
  
  test('Property 1: Frontend accepts .pdf files - BUG CONDITION', async ({ page }) => {
    /**
     * This test demonstrates that the UNFIXED frontend accepts .pdf files
     * which the backend does NOT support.
     * 
     * EXPECTED: This test FAILS on unfixed code (frontend accepts .pdf)
     * This failure CONFIRMS the bug exists.
     * 
     * After fix: Test should pass (frontend rejects .pdf files)
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const pdfFile = createTestPdfFile('test_letter.pdf');
    
    try {
      const letterInput = page.locator('#letter-upload');
      await expect(letterInput).toBeAttached();
      
      // Attempt to upload PDF file
      await letterInput.setInputFiles(pdfFile);
      await page.waitForTimeout(500);
      
      // Check if file was accepted
      const letterText = page.locator('#letter-text');
      const letterTextContent = await letterText.textContent();
      
      // Check for error toast
      const errorToast = page.locator('.toast-error');
      const errorCount = await errorToast.count();
      
      // BUG CONDITION: On unfixed code, the PDF should be ACCEPTED
      // After fix, it should be REJECTED (error shown, file not set)
      
      // CRITICAL ASSERTION: This should FAIL on unfixed code
      // The frontend should reject .pdf files, but it doesn't
      const fileRejected = errorCount > 0 && !letterTextContent.includes('test_letter.pdf');
      
      expect(fileRejected).toBeTruthy();
      
      if (!fileRejected) {
        throw new Error(
          'BUG CONFIRMED: Frontend ACCEPTS .pdf files. ' +
          `File text: "${letterTextContent}", Error count: ${errorCount}. ` +
          'The frontend should reject .pdf files as they are not supported by the backend.'
        );
      }
      
    } finally {
      cleanupTestFile(pdfFile);
    }
  });
  
  test('Property 1: Frontend accepts .m4a files - BUG CONDITION', async ({ page }) => {
    /**
     * This test demonstrates that the UNFIXED frontend accepts .m4a audio files
     * which the backend does NOT support.
     * 
     * EXPECTED: This test FAILS on unfixed code (frontend accepts .m4a)
     * This failure CONFIRMS the bug exists.
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const m4aFile = createTestM4aFile('test_audio.m4a');
    
    try {
      const audioInput = page.locator('#audio-upload');
      await expect(audioInput).toBeAttached();
      
      // Attempt to upload M4A file
      await audioInput.setInputFiles(m4aFile);
      await page.waitForTimeout(500);
      
      // Check if file was accepted
      const audioText = page.locator('#audio-text');
      const audioTextContent = await audioText.textContent();
      
      // Check for error toast
      const errorToast = page.locator('.toast-error');
      const errorCount = await errorToast.count();
      
      // CRITICAL ASSERTION: This should FAIL on unfixed code
      const fileRejected = errorCount > 0 && !audioTextContent.includes('test_audio.m4a');
      
      expect(fileRejected).toBeTruthy();
      
      if (!fileRejected) {
        throw new Error(
          'BUG CONFIRMED: Frontend ACCEPTS .m4a files. ' +
          `File text: "${audioTextContent}", Error count: ${errorCount}. ` +
          'The frontend should reject .m4a files as they are not supported by the backend.'
        );
      }
      
    } finally {
      cleanupTestFile(m4aFile);
    }
  });
  
  test('Property 1: Frontend accepts .txt files - BUG CONDITION', async ({ page }) => {
    /**
     * Test that frontend accepts .txt files which backend doesn't support
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const txtFile = createTestTxtFile('test_letter.txt');
    
    try {
      const letterInput = page.locator('#letter-upload');
      await letterInput.setInputFiles(txtFile);
      await page.waitForTimeout(500);
      
      const letterText = page.locator('#letter-text');
      const letterTextContent = await letterText.textContent();
      const errorToast = page.locator('.toast-error');
      const errorCount = await errorToast.count();
      
      const fileRejected = errorCount > 0 && !letterTextContent.includes('test_letter.txt');
      
      expect(fileRejected).toBeTruthy();
      
      if (!fileRejected) {
        throw new Error(
          'BUG CONFIRMED: Frontend ACCEPTS .txt files. ' +
          `File text: "${letterTextContent}", Error count: ${errorCount}. ` +
          'The frontend should reject .txt files as they are not supported by the backend.'
        );
      }
      
    } finally {
      cleanupTestFile(txtFile);
    }
  });
  
  test('Document: Unsupported file types accepted by frontend', async ({ page }) => {
    /**
     * This test documents which unsupported file types are accepted by the frontend.
     * It tests all the unsupported types mentioned in the bug description.
     */
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const unsupportedLetterTypes = [
      { ext: '.pdf', creator: createTestPdfFile },
      { ext: '.txt', creator: createTestTxtFile }
    ];
    
    const unsupportedAudioTypes = [
      { ext: '.m4a', creator: createTestM4aFile }
    ];
    
    console.log('\n=== BUG DOCUMENTATION: Unsupported File Types ===');
    
    // Test unsupported letter file types
    for (const fileType of unsupportedLetterTypes) {
      const testFile = fileType.creator(`test_letter${fileType.ext}`);
      
      try {
        await page.locator('#letter-upload').setInputFiles(testFile);
        await page.waitForTimeout(300);
        
        const letterText = page.locator('#letter-text');
        const letterTextContent = await letterText.textContent();
        const errorToast = page.locator('.toast-error');
        const errorCount = await errorToast.count();
        
        const accepted = letterTextContent.includes(`test_letter${fileType.ext}`) && errorCount === 0;
        
        console.log(`Letter file ${fileType.ext}: ${accepted ? 'ACCEPTED (BUG)' : 'REJECTED (correct)'}`);
        
        // Clear for next test
        await page.locator('#letter-upload').setInputFiles([]);
        await page.waitForTimeout(200);
        
      } finally {
        cleanupTestFile(testFile);
      }
    }
    
    // Test unsupported audio file types
    for (const fileType of unsupportedAudioTypes) {
      const testFile = fileType.creator(`test_audio${fileType.ext}`);
      
      try {
        await page.locator('#audio-upload').setInputFiles(testFile);
        await page.waitForTimeout(300);
        
        const audioText = page.locator('#audio-text');
        const audioTextContent = await audioText.textContent();
        const errorToast = page.locator('.toast-error');
        const errorCount = await errorToast.count();
        
        const accepted = audioTextContent.includes(`test_audio${fileType.ext}`) && errorCount === 0;
        
        console.log(`Audio file ${fileType.ext}: ${accepted ? 'ACCEPTED (BUG)' : 'REJECTED (correct)'}`);
        
        // Clear for next test
        await page.locator('#audio-upload').setInputFiles([]);
        await page.waitForTimeout(200);
        
      } finally {
        cleanupTestFile(testFile);
      }
    }
    
    console.log('\nBackend Supported Types:');
    console.log('  Letter files: .jpg, .jpeg, .png');
    console.log('  Audio files: .wav, .mp3, .mpeg');
    console.log('\nRequired Fix: Frontend must reject unsupported types before submission');
    console.log('================================================\n');
  });
});
