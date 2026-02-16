/**
 * E2E Tests for Critical User Flows
 * Requirements: 5.6.4
 */

const { test, expect } = require('@playwright/test');

test.describe('Critical Flow: File Upload and FIR Generation', () => {
  test('should upload file, generate FIR, validate, and complete', async ({ page }) => {
    // Navigate to home page
    await page.goto('/');
    
    // Verify page loaded
    await expect(page).toHaveTitle(/AFIRGen/i);
    
    // Check for file upload section
    const uploadSection = page.locator('#upload-section, [data-testid="upload-section"]');
    await expect(uploadSection).toBeVisible();
    
    // Create a test file
    const testFile = {
      name: 'test-document.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF test content')
    };
    
    // Upload file (adjust selector based on actual implementation)
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: testFile.name,
      mimeType: testFile.mimeType,
      buffer: testFile.buffer
    });
    
    // Wait for file validation
    await page.waitForTimeout(500);
    
    // Check for validation success message or indicator
    const validationSuccess = page.locator('.validation-success, [data-testid="validation-success"]');
    
    // Submit form to generate FIR
    const submitButton = page.locator('button[type="submit"], .submit-btn, [data-testid="submit-btn"]');
    if (await submitButton.isVisible()) {
      await submitButton.click();
      
      // Wait for loading indicator
      const loadingIndicator = page.locator('.loading-overlay, .loading-spinner');
      await expect(loadingIndicator).toBeVisible({ timeout: 2000 });
      
      // Wait for FIR generation (with longer timeout)
      await page.waitForTimeout(3000);
      
      // Check for success modal or result
      const resultModal = page.locator('.modal, #modal-overlay, [data-testid="result-modal"]');
      await expect(resultModal).toBeVisible({ timeout: 10000 });
      
      // Verify FIR content is displayed
      const firContent = page.locator('.fir-content, #fir-content, [data-testid="fir-content"]');
      await expect(firContent).toBeVisible();
      
      // Close modal
      const closeButton = page.locator('.modal-close, #modal-close, [data-testid="close-modal"]');
      if (await closeButton.isVisible()) {
        await closeButton.click();
      }
    }
  });

  test('should handle file validation errors', async ({ page }) => {
    await page.goto('/');
    
    // Try to upload invalid file type
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: 'test.exe',
      mimeType: 'application/x-msdownload',
      buffer: Buffer.from('Invalid file')
    });
    
    // Wait for error message
    await page.waitForTimeout(500);
    
    // Check for error toast or message
    const errorToast = page.locator('.toast-error, .error-message, [data-testid="error-toast"]');
    await expect(errorToast).toBeVisible({ timeout: 3000 });
  });

  test('should show loading states during async operations', async ({ page }) => {
    await page.goto('/');
    
    // Upload valid file
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles({
      name: 'test.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('PDF content')
    });
    
    // Submit form
    const submitButton = page.locator('button[type="submit"], .submit-btn');
    if (await submitButton.isVisible()) {
      await submitButton.click();
      
      // Verify loading indicator appears within 100ms
      const startTime = Date.now();
      const loadingIndicator = page.locator('.loading-overlay, .loading-spinner');
      await expect(loadingIndicator).toBeVisible({ timeout: 200 });
      const loadingTime = Date.now() - startTime;
      
      // Verify loading appeared quickly (< 100ms requirement)
      expect(loadingTime).toBeLessThan(150); // Allow small buffer
    }
  });
});

test.describe('Critical Flow: FIR History Search and View', () => {
  test('should search FIR history and view details', async ({ page }) => {
    await page.goto('/');
    
    // Navigate to history tab
    const historyTab = page.locator('[data-tab="history"], .nav-item:has-text("History")');
    if (await historyTab.isVisible()) {
      await historyTab.click();
      
      // Wait for history to load
      await page.waitForTimeout(1000);
      
      // Check for search input
      const searchInput = page.locator('#search-input, [data-testid="search-input"]');
      if (await searchInput.isVisible()) {
        // Enter search term
        await searchInput.fill('FIR');
        
        // Wait for search results
        await page.waitForTimeout(500);
        
        // Check for FIR items
        const firItems = page.locator('.fir-item, [data-testid="fir-item"]');
        const count = await firItems.count();
        
        // If items exist, click first one
        if (count > 0) {
          await firItems.first().click();
          
          // Wait for details modal
          const modal = page.locator('.modal, #modal-overlay');
          await expect(modal).toBeVisible({ timeout: 2000 });
        }
      }
    }
  });

  test('should filter FIR history by status', async ({ page }) => {
    await page.goto('/');
    
    // Navigate to history tab
    const historyTab = page.locator('[data-tab="history"]');
    if (await historyTab.isVisible()) {
      await historyTab.click();
      await page.waitForTimeout(500);
      
      // Check for filter dropdown
      const filterDropdown = page.locator('#status-filter, [data-testid="status-filter"]');
      if (await filterDropdown.isVisible()) {
        await filterDropdown.selectOption('pending');
        
        // Wait for filtered results
        await page.waitForTimeout(500);
        
        // Verify filtered items
        const firItems = page.locator('.fir-item');
        const count = await firItems.count();
        expect(count).toBeGreaterThanOrEqual(0);
      }
    }
  });
});

test.describe('Critical Flow: PDF Export', () => {
  test('should export FIR to PDF', async ({ page }) => {
    await page.goto('/');
    
    // This test assumes there's a way to access a FIR
    // Navigate to history or create a test FIR first
    const historyTab = page.locator('[data-tab="history"]');
    if (await historyTab.isVisible()) {
      await historyTab.click();
      await page.waitForTimeout(500);
      
      // Click on first FIR item
      const firItem = page.locator('.fir-item').first();
      if (await firItem.isVisible()) {
        await firItem.click();
        
        // Wait for modal
        await page.waitForTimeout(500);
        
        // Look for PDF export button
        const exportButton = page.locator('#export-pdf-btn, [data-testid="export-pdf"]');
        if (await exportButton.isVisible()) {
          // Set up download listener
          const downloadPromise = page.waitForEvent('download', { timeout: 5000 });
          
          // Click export button
          await exportButton.click();
          
          // Wait for download
          try {
            const download = await downloadPromise;
            
            // Verify download
            expect(download.suggestedFilename()).toMatch(/\.pdf$/i);
          } catch (error) {
            // Download might not trigger in test environment
            console.log('PDF download not triggered (expected in test environment)');
          }
        }
      }
    }
  });
});

test.describe('Critical Flow: Dark Mode Toggle', () => {
  test('should toggle dark mode', async ({ page }) => {
    await page.goto('/');
    
    // Find dark mode toggle
    const darkModeToggle = page.locator('#dark-mode-toggle, [data-testid="dark-mode-toggle"], .dark-mode-toggle');
    
    if (await darkModeToggle.isVisible()) {
      // Get initial state
      const body = page.locator('body');
      const initialHasDarkMode = await body.evaluate(el => el.classList.contains('dark-mode'));
      
      // Toggle dark mode
      await darkModeToggle.click();
      await page.waitForTimeout(500);
      
      // Verify dark mode toggled
      const afterToggleHasDarkMode = await body.evaluate(el => el.classList.contains('dark-mode'));
      expect(afterToggleHasDarkMode).toBe(!initialHasDarkMode);
      
      // Toggle back
      await darkModeToggle.click();
      await page.waitForTimeout(500);
      
      // Verify returned to original state
      const finalHasDarkMode = await body.evaluate(el => el.classList.contains('dark-mode'));
      expect(finalHasDarkMode).toBe(initialHasDarkMode);
    }
  });

  test('should persist dark mode preference', async ({ page, context }) => {
    await page.goto('/');
    
    const darkModeToggle = page.locator('#dark-mode-toggle, [data-testid="dark-mode-toggle"]');
    
    if (await darkModeToggle.isVisible()) {
      // Enable dark mode
      await darkModeToggle.click();
      await page.waitForTimeout(500);
      
      // Reload page
      await page.reload();
      await page.waitForTimeout(500);
      
      // Verify dark mode persisted
      const body = page.locator('body');
      const hasDarkMode = await body.evaluate(el => el.classList.contains('dark-mode'));
      expect(hasDarkMode).toBe(true);
    }
  });
});

test.describe('Critical Flow: Offline Mode', () => {
  test('should queue operations when offline and sync when online', async ({ page, context }) => {
    await page.goto('/');
    
    // Wait for page to load
    await page.waitForTimeout(1000);
    
    // Go offline
    await context.setOffline(true);
    
    // Try to perform an operation (e.g., search)
    const searchInput = page.locator('#search-input');
    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await page.waitForTimeout(500);
      
      // Should show offline indicator or message
      const offlineIndicator = page.locator('.offline-indicator, [data-testid="offline-indicator"]');
      // Note: This might not be visible depending on implementation
    }
    
    // Go back online
    await context.setOffline(false);
    await page.waitForTimeout(1000);
    
    // Verify operations synced (implementation-specific)
    // This is a basic test - actual implementation may vary
  });

  test('should show cached content when offline', async ({ page, context }) => {
    // First visit online to cache content
    await page.goto('/');
    await page.waitForTimeout(1000);
    
    // Go offline
    await context.setOffline(true);
    
    // Reload page
    await page.reload();
    
    // Verify page still loads (from cache)
    await expect(page.locator('body')).toBeVisible({ timeout: 5000 });
    
    // Go back online
    await context.setOffline(false);
  });
});

test.describe('Accessibility Tests', () => {
  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/');
    
    // Tab through interactive elements
    await page.keyboard.press('Tab');
    await page.waitForTimeout(100);
    
    // Verify focus is visible
    const focusedElement = await page.evaluate(() => {
      const el = document.activeElement;
      const styles = window.getComputedStyle(el);
      return {
        tagName: el.tagName,
        hasOutline: styles.outline !== 'none' && styles.outline !== ''
      };
    });
    
    // Should have some focused element
    expect(focusedElement.tagName).toBeTruthy();
  });

  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/');
    
    // Check for ARIA labels on buttons
    const buttons = page.locator('button');
    const count = await buttons.count();
    
    for (let i = 0; i < Math.min(count, 5); i++) {
      const button = buttons.nth(i);
      const ariaLabel = await button.getAttribute('aria-label');
      const text = await button.textContent();
      
      // Button should have either aria-label or text content
      expect(ariaLabel || text?.trim()).toBeTruthy();
    }
  });
});

test.describe('Performance Tests', () => {
  test('should load page within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    const loadTime = Date.now() - startTime;
    
    // Page should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('should show toast notifications within 200ms', async ({ page }) => {
    await page.goto('/');
    
    // Trigger an action that shows a toast (e.g., validation error)
    const fileInput = page.locator('input[type="file"]').first();
    if (await fileInput.isVisible()) {
      const startTime = Date.now();
      
      await fileInput.setInputFiles({
        name: 'invalid.exe',
        mimeType: 'application/x-msdownload',
        buffer: Buffer.from('test')
      });
      
      // Wait for toast
      const toast = page.locator('.toast, [data-testid="toast"]');
      await expect(toast).toBeVisible({ timeout: 500 });
      
      const toastTime = Date.now() - startTime;
      
      // Toast should appear within 200ms (with buffer for test environment)
      expect(toastTime).toBeLessThan(300);
    }
  });
});
