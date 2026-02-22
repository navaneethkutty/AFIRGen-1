/**
 * Bug Condition Exploration Test for Bug 2.2 - Inconsistent File Type Validation
 * 
 * **Validates: Requirements 2.9**
 * 
 * Property 1: Fault Condition - Validation Inconsistency
 * 
 * CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
 * DO NOT attempt to fix the test or the code when it fails.
 * GOAL: Surface counterexamples that demonstrate validation inconsistency exists.
 * 
 * Bug Description:
 * The frontend has inconsistent file type validation across modules:
 * - validation.js line 83 defines default allowedTypes: ['.jpg', '.jpeg', '.png', '.pdf', '.wav', '.mp3']
 * - app.js letter upload (line 415) uses: ['.jpg', '.jpeg', '.png'] (no .pdf)
 * - app.js audio upload (line 456) uses: ['.mp3', '.wav']
 * 
 * This creates confusion because:
 * 1. The validation module's default includes .pdf
 * 2. But the actual letter upload handler explicitly excludes .pdf
 * 3. If someone calls validateFileType() without parameters, it would accept .pdf
 * 4. But the app.js handler would reject it
 * 
 * Expected Behavior (After Fix):
 * All frontend modules should use consistent file type validation:
 * - validation.js default should match what app.js actually uses
 * - Letter files: ['.jpg', '.jpeg', '.png'] (no .pdf)
 * - Audio files: ['.mp3', '.wav']
 * - No .pdf in any default allowedTypes
 * 
 * Current Behavior (Unfixed):
 * validation.js default includes .pdf, but app.js letter upload excludes it.
 * This inconsistency can lead to bugs if code uses the default validation.
 */

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

test.describe('Bug 2.2: Inconsistent File Type Validation Across Frontend Modules', () => {
  
  test('Property 1: Document validation inconsistency between modules', async () => {
    /**
     * This test documents the inconsistency by reading the source files directly.
     * 
     * EXPECTED: This test FAILS on unfixed code (inconsistency exists)
     * This failure CONFIRMS the bug exists.
     * 
     * After fix: Test should pass (all modules use consistent validation)
     */
    
    // Read validation.js to check default allowedTypes
    const validationJsPath = path.join(__dirname, '../js/validation.js');
    const validationJsContent = fs.readFileSync(validationJsPath, 'utf-8');
    
    // Read app.js to check actual allowedTypes used
    const appJsPath = path.join(__dirname, '../js/app.js');
    const appJsContent = fs.readFileSync(appJsPath, 'utf-8');
    
    console.log('\n=== BUG 2.2 DOCUMENTATION: Validation Inconsistency ===');
    
    // Extract default allowedTypes from validation.js
    // Looking for: function validateFileType(file, allowedTypes = ['.jpg', '.jpeg', '.png', '.pdf', '.wav', '.mp3'])
    const validationDefaultMatch = validationJsContent.match(
      /function validateFileType\([^)]+allowedTypes\s*=\s*\[([^\]]+)\]/
    );
    
    let validationDefault = null;
    if (validationDefaultMatch) {
      validationDefault = validationDefaultMatch[1]
        .split(',')
        .map(s => s.trim().replace(/['"]/g, ''))
        .filter(s => s.length > 0);
      
      console.log('\nvalidation.js default allowedTypes:');
      console.log('  ', validationDefault.join(', '));
    } else {
      console.log('\n⚠️  Could not extract default allowedTypes from validation.js');
    }
    
    // Extract letter upload allowedTypes from app.js
    // Looking for: allowedTypes: ['.jpg', '.jpeg', '.png']
    const letterUploadMatches = appJsContent.match(
      /letterUpload\.addEventListener.*?allowedTypes:\s*\[([^\]]+)\]/s
    );
    
    let letterAllowedTypes = null;
    if (letterUploadMatches) {
      letterAllowedTypes = letterUploadMatches[1]
        .split(',')
        .map(s => s.trim().replace(/['"]/g, ''))
        .filter(s => s.length > 0);
      
      console.log('\napp.js letter upload allowedTypes:');
      console.log('  ', letterAllowedTypes.join(', '));
    } else {
      console.log('\n⚠️  Could not extract letter upload allowedTypes from app.js');
    }
    
    // Extract audio upload allowedTypes from app.js
    const audioUploadMatches = appJsContent.match(
      /audioUpload\.addEventListener.*?allowedTypes:\s*\[([^\]]+)\]/s
    );
    
    let audioAllowedTypes = null;
    if (audioUploadMatches) {
      audioAllowedTypes = audioUploadMatches[1]
        .split(',')
        .map(s => s.trim().replace(/['"]/g, ''))
        .filter(s => s.length > 0);
      
      console.log('\napp.js audio upload allowedTypes:');
      console.log('  ', audioAllowedTypes.join(', '));
    } else {
      console.log('\n⚠️  Could not extract audio upload allowedTypes from app.js');
    }
    
    // Check for inconsistencies
    const inconsistencies = [];
    
    if (validationDefault && letterAllowedTypes && audioAllowedTypes) {
      // Check if validation.js default includes .pdf
      const validationIncludesPdf = validationDefault.includes('.pdf');
      const letterIncludesPdf = letterAllowedTypes.includes('.pdf');
      
      if (validationIncludesPdf && !letterIncludesPdf) {
        inconsistencies.push({
          issue: 'validation.js default includes .pdf, but app.js letter upload excludes it',
          validationDefault: validationDefault,
          letterActual: letterAllowedTypes
        });
      }
      
      // Check if all letter types in validation default match app.js
      const validationImageTypes = validationDefault.filter(t => 
        ['.jpg', '.jpeg', '.png', '.pdf'].includes(t)
      );
      const letterTypesMatch = JSON.stringify(validationImageTypes.sort()) === 
                               JSON.stringify(letterAllowedTypes.sort());
      
      if (!letterTypesMatch) {
        inconsistencies.push({
          issue: 'validation.js image types do not match app.js letter upload types',
          validationImageTypes: validationImageTypes,
          letterActual: letterAllowedTypes
        });
      }
      
      // Check if all audio types in validation default match app.js
      const validationAudioTypes = validationDefault.filter(t => 
        ['.wav', '.mp3', '.m4a', '.ogg'].includes(t)
      );
      const audioTypesMatch = JSON.stringify(validationAudioTypes.sort()) === 
                              JSON.stringify(audioAllowedTypes.sort());
      
      if (!audioTypesMatch) {
        inconsistencies.push({
          issue: 'validation.js audio types do not match app.js audio upload types',
          validationAudioTypes: validationAudioTypes,
          audioActual: audioAllowedTypes
        });
      }
    }
    
    // Document findings
    if (inconsistencies.length > 0) {
      console.log('\n❌ INCONSISTENCIES FOUND:');
      inconsistencies.forEach((inc, idx) => {
        console.log(`\n${idx + 1}. ${inc.issue}`);
        if (inc.validationDefault) {
          console.log('   validation.js default:', inc.validationDefault.join(', '));
        }
        if (inc.validationImageTypes) {
          console.log('   validation.js image types:', inc.validationImageTypes.join(', '));
        }
        if (inc.validationAudioTypes) {
          console.log('   validation.js audio types:', inc.validationAudioTypes.join(', '));
        }
        if (inc.letterActual) {
          console.log('   app.js letter actual:', inc.letterActual.join(', '));
        }
        if (inc.audioActual) {
          console.log('   app.js audio actual:', inc.audioActual.join(', '));
        }
      });
      
      console.log('\n⚠️  PROBLEM: Inconsistent validation rules across modules');
      console.log('This can lead to bugs if code uses validation.js default instead of explicit types');
      
      console.log('\n✅ REQUIRED FIX:');
      console.log('Update validation.js default allowedTypes to match app.js:');
      console.log('  - Remove .pdf from default (backend does not support it)');
      console.log('  - Ensure default matches actual usage in app.js');
      console.log('  - Letter: [.jpg, .jpeg, .png]');
      console.log('  - Audio: [.mp3, .wav]');
      console.log('================================================\n');
    } else {
      console.log('\n✅ No inconsistencies found - validation is consistent across modules');
      console.log('================================================\n');
    }
    
    // CRITICAL ASSERTION: This should FAIL on unfixed code
    // There should be NO inconsistencies
    expect(inconsistencies.length).toBe(0);
    
    if (inconsistencies.length > 0) {
      throw new Error(
        `BUG 2.2 CONFIRMED: Found ${inconsistencies.length} validation inconsistencies. ` +
        `First issue: ${inconsistencies[0].issue}`
      );
    }
  });
  
  test('Property 1: Verify validation.js default includes .pdf (BUG)', async () => {
    /**
     * This test specifically checks if validation.js default includes .pdf
     * which is the core of the inconsistency bug.
     */
    
    const validationJsPath = path.join(__dirname, '../js/validation.js');
    const validationJsContent = fs.readFileSync(validationJsPath, 'utf-8');
    
    // Check if default allowedTypes includes .pdf
    const validationDefaultMatch = validationJsContent.match(
      /function validateFileType\([^)]+allowedTypes\s*=\s*\[([^\]]+)\]/
    );
    
    let includesPdf = false;
    if (validationDefaultMatch) {
      const defaultTypes = validationDefaultMatch[1]
        .split(',')
        .map(s => s.trim().replace(/['"]/g, ''))
        .filter(s => s.length > 0);
      
      includesPdf = defaultTypes.includes('.pdf');
      
      console.log('\n=== PDF in validation.js default ===');
      console.log('Default allowedTypes:', defaultTypes.join(', '));
      console.log('Includes .pdf:', includesPdf);
    }
    
    // CRITICAL ASSERTION: This should FAIL on unfixed code
    // validation.js default should NOT include .pdf (backend doesn't support it)
    expect(includesPdf).toBeFalsy();
    
    if (includesPdf) {
      throw new Error(
        'BUG 2.2 CONFIRMED: validation.js default allowedTypes includes .pdf, ' +
        'but backend does not support .pdf files. This creates inconsistency.'
      );
    }
  });
  
  test('Property 1: Verify app.js letter upload excludes .pdf (CORRECT)', async () => {
    /**
     * This test verifies that app.js letter upload correctly excludes .pdf.
     * This is the CORRECT behavior that should be maintained.
     */
    
    const appJsPath = path.join(__dirname, '../js/app.js');
    const appJsContent = fs.readFileSync(appJsPath, 'utf-8');
    
    // Extract letter upload allowedTypes
    const letterUploadMatches = appJsContent.match(
      /letterUpload\.addEventListener.*?allowedTypes:\s*\[([^\]]+)\]/s
    );
    
    let letterIncludesPdf = false;
    if (letterUploadMatches) {
      const letterTypes = letterUploadMatches[1]
        .split(',')
        .map(s => s.trim().replace(/['"]/g, ''))
        .filter(s => s.length > 0);
      
      letterIncludesPdf = letterTypes.includes('.pdf');
      
      console.log('\n=== app.js letter upload validation ===');
      console.log('Letter allowedTypes:', letterTypes.join(', '));
      console.log('Includes .pdf:', letterIncludesPdf);
      console.log('✅ This is CORRECT - app.js excludes .pdf');
    }
    
    // This should always pass - app.js correctly excludes .pdf
    expect(letterIncludesPdf).toBeFalsy();
  });
  
  test('Document: Impact of validation inconsistency', async () => {
    /**
     * This test documents the potential impact of the validation inconsistency.
     * It shows scenarios where the bug could cause issues.
     */
    
    console.log('\n=== IMPACT ANALYSIS: Validation Inconsistency ===');
    
    console.log('\nScenario 1: Developer uses validateFileType() without parameters');
    console.log('  Code: validateFileType(pdfFile)');
    console.log('  Expected: Reject .pdf (backend does not support it)');
    console.log('  Actual: Accept .pdf (default includes .pdf)');
    console.log('  Result: ❌ File accepted by validation, rejected by backend');
    
    console.log('\nScenario 2: Developer explicitly passes allowedTypes');
    console.log('  Code: validateFileType(pdfFile, [\'.jpg\', \'.jpeg\', \'.png\'])');
    console.log('  Expected: Reject .pdf');
    console.log('  Actual: Reject .pdf');
    console.log('  Result: ✅ Works correctly');
    
    console.log('\nScenario 3: New feature uses validation module');
    console.log('  Developer adds new file upload feature');
    console.log('  Uses validateFileType() with default parameters');
    console.log('  Assumes default is correct and matches backend');
    console.log('  Result: ❌ Bug introduced - .pdf files accepted but backend rejects');
    
    console.log('\nScenario 4: Drag-drop module uses validation');
    console.log('  If drag-drop.js uses validateFileType() without explicit types');
    console.log('  It would accept .pdf files');
    console.log('  Result: ❌ Inconsistent behavior between upload methods');
    
    console.log('\n⚠️  ROOT CAUSE:');
    console.log('The validation.js default allowedTypes does not match backend capabilities');
    console.log('This creates a "pit of failure" where using the default is incorrect');
    
    console.log('\n✅ SOLUTION:');
    console.log('Update validation.js default to match backend-supported types:');
    console.log('  allowedTypes = [\'.jpg\', \'.jpeg\', \'.png\', \'.wav\', \'.mp3\']');
    console.log('Remove .pdf from default since backend does not support it');
    console.log('This creates a "pit of success" where default is correct');
    console.log('================================================\n');
  });
  
  test('Edge Case: Check if drag-drop module has consistent validation', async () => {
    /**
     * Check if drag-drop.js (if it exists) uses consistent validation
     */
    
    const dragDropPath = path.join(__dirname, '../js/drag-drop.js');
    
    if (!fs.existsSync(dragDropPath)) {
      console.log('\n=== drag-drop.js not found - skipping ===');
      return;
    }
    
    const dragDropContent = fs.readFileSync(dragDropPath, 'utf-8');
    
    console.log('\n=== Checking drag-drop.js validation ===');
    
    // Check if drag-drop uses validateFileType
    const usesValidateFileType = dragDropContent.includes('validateFileType');
    console.log('Uses validateFileType:', usesValidateFileType);
    
    if (usesValidateFileType) {
      // Check if it passes explicit allowedTypes or uses default
      const hasExplicitTypes = dragDropContent.match(/validateFileType\([^)]+,\s*\[/);
      
      if (hasExplicitTypes) {
        console.log('✅ drag-drop.js passes explicit allowedTypes');
      } else {
        console.log('⚠️  drag-drop.js may use default allowedTypes');
        console.log('This could be affected by the validation inconsistency bug');
      }
    }
    
    console.log('================================================\n');
  });
});
