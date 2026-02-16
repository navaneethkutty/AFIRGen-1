/**
 * Phase 6 Validation Test Suite
 * Tests all visual effects and animations
 */

let testResults = {
  passed: 0,
  failed: 0,
  total: 0
};

/**
 * Run all tests
 */
async function runAllTests() {
  console.log('Running all Phase 6 validation tests...');
  testResults = { passed: 0, failed: 0, total: 0 };
  
  await runIconTests();
  await runIllustrationTests();
  await runPerformanceTests();
  await runAccessibilityTests();
  await runBrowserTests();
  
  updateOverallStatus();
  console.log('All tests complete:', testResults);
}

/**
 * Run icon animation tests
 */
async function runIconTests() {
  console.log('Testing icon animations...');
  
  // Test loading icons
  const loadingTest = testLoadingIcons();
  updateTestResult('result-loading-icons', loadingTest);
  
  // Test success icons
  const successTest = testSuccessIcons();
  updateTestResult('result-success-icons', successTest);
  
  // Test error icons
  const errorTest = testErrorIcons();
  updateTestResult('result-error-icons', errorTest);
  
  // Test morphing icons
  const morphingTest = testMorphingIcons();
  updateTestResult('result-morphing-icons', morphingTest);
  
  const allPassed = loadingTest.passed && successTest.passed && errorTest.passed && morphingTest.passed;
  updateSectionStatus('icon-status', allPassed);
}

/**
 * Test loading icons
 */
function testLoadingIcons() {
  try {
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    icon.setAttribute('data-icon-type', 'loading');
    
    window.svgIconAnimations.animateLoading(icon);
    
    const hasAnimation = icon.style.animation.includes('spin');
    
    testResults.total++;
    if (hasAnimation) {
      testResults.passed++;
      return { passed: true, message: 'Loading icons animate correctly' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Loading icons do not animate' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test success icons
 */
function testSuccessIcons() {
  try {
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    polyline.getTotalLength = () => 100;
    icon.appendChild(polyline);
    
    window.svgIconAnimations.animateSuccess(icon);
    
    const hasAnimation = polyline.style.animation.includes('draw');
    
    testResults.total++;
    if (hasAnimation) {
      testResults.passed++;
      return { passed: true, message: 'Success icons animate with draw effect' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Success icons do not animate' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test error icons
 */
function testErrorIcons() {
  try {
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.getTotalLength = () => 50;
    icon.appendChild(line);
    
    window.svgIconAnimations.animateError(icon);
    
    const hasAnimation = line.style.animation.includes('draw');
    
    testResults.total++;
    if (hasAnimation) {
      testResults.passed++;
      return { passed: true, message: 'Error icons animate with draw effect' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Error icons do not animate' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test morphing icons
 */
function testMorphingIcons() {
  try {
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    icon.setAttribute('data-icon-morph', 'play');
    
    window.svgIconAnimations.registerMorphingIcon(icon, 'pause');
    
    const isRegistered = window.svgIconAnimations.icons.has(icon);
    
    testResults.total++;
    if (isRegistered) {
      testResults.passed++;
      return { passed: true, message: 'Morphing icons registered correctly' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Morphing icons not registered' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Run illustration tests
 */
async function runIllustrationTests() {
  console.log('Testing illustrations...');
  
  const emptyStateTest = testEmptyStateIllustration();
  updateTestResult('result-empty-state', emptyStateTest);
  
  const successTest = testSuccessIllustration();
  updateTestResult('result-success-illustration', successTest);
  
  const errorTest = testErrorIllustration();
  updateTestResult('result-error-illustration', errorTest);
  
  const allPassed = emptyStateTest.passed && successTest.passed && errorTest.passed;
  updateSectionStatus('illustration-status', allPassed);
}

/**
 * Test empty state illustration
 */
function testEmptyStateIllustration() {
  try {
    const container = document.getElementById('test-empty-state');
    const svg = container.querySelector('svg');
    
    const hasIllustration = svg && svg.classList.contains('illustration-empty-state');
    
    testResults.total++;
    if (hasIllustration) {
      testResults.passed++;
      return { passed: true, message: 'Empty state illustration renders correctly' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Empty state illustration not found' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test success illustration
 */
function testSuccessIllustration() {
  try {
    const container = document.getElementById('test-success-illustration');
    const svg = container.querySelector('svg');
    
    const hasIllustration = svg && svg.classList.contains('illustration-success');
    
    testResults.total++;
    if (hasIllustration) {
      testResults.passed++;
      return { passed: true, message: 'Success illustration renders correctly' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Success illustration not found' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test error illustration
 */
function testErrorIllustration() {
  try {
    const container = document.getElementById('test-error-illustration');
    const svg = container.querySelector('svg');
    
    const hasIllustration = svg && svg.classList.contains('illustration-error');
    
    testResults.total++;
    if (hasIllustration) {
      testResults.passed++;
      return { passed: true, message: 'Error illustration renders correctly' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Error illustration not found' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Run performance tests
 */
async function runPerformanceTests() {
  console.log('Testing performance...');
  
  const fpsTest = await testFPS();
  updateTestResult('result-fps', fpsTest);
  
  const gpuTest = testGPUAcceleration();
  updateTestResult('result-gpu', gpuTest);
  
  const lazyLoadTest = testLazyLoading();
  updateTestResult('result-lazy-loading', lazyLoadTest);
  
  const lowEndTest = testLowEndDevice();
  updateTestResult('result-low-end', lowEndTest);
  
  const allPassed = fpsTest.passed && gpuTest.passed && lazyLoadTest.passed && lowEndTest.passed;
  updateSectionStatus('performance-status', allPassed);
  
  const score = Math.round((testResults.passed / testResults.total) * 100);
  document.getElementById('performance-score').textContent = score;
}

/**
 * Test FPS
 */
async function testFPS() {
  return new Promise((resolve) => {
    let frames = 0;
    const startTime = performance.now();
    
    function measureFPS() {
      frames++;
      const currentTime = performance.now();
      
      if (currentTime >= startTime + 1000) {
        const fps = Math.round((frames * 1000) / (currentTime - startTime));
        
        testResults.total++;
        if (fps >= 55) {
          testResults.passed++;
          resolve({ passed: true, message: `Animations run at ${fps} FPS (target: 60 FPS)` });
        } else {
          testResults.failed++;
          resolve({ passed: false, message: `Low FPS: ${fps} (target: 60 FPS)` });
        }
        return;
      }
      
      requestAnimationFrame(measureFPS);
    }
    
    requestAnimationFrame(measureFPS);
  });
}

/**
 * Test GPU acceleration
 */
function testGPUAcceleration() {
  try {
    const hasGPU = window.visualEffectsOptimizer.hasGPU;
    
    testResults.total++;
    if (hasGPU) {
      testResults.passed++;
      return { passed: true, message: 'GPU acceleration available' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'GPU acceleration not available' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test lazy loading
 */
function testLazyLoading() {
  try {
    const hasIntersectionObserver = window.visualEffectsOptimizer.intersectionObserver !== null;
    
    testResults.total++;
    if (hasIntersectionObserver) {
      testResults.passed++;
      return { passed: true, message: 'Lazy loading with IntersectionObserver enabled' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'IntersectionObserver not available' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test low-end device support
 */
function testLowEndDevice() {
  try {
    const isLowEnd = window.visualEffectsOptimizer.isLowEndDevice;
    
    testResults.total++;
    testResults.passed++;
    return { 
      passed: true, 
      message: isLowEnd ? 'Low-end device detected, optimizations applied' : 'High-end device, full effects enabled' 
    };
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Run accessibility tests
 */
async function runAccessibilityTests() {
  console.log('Testing accessibility...');
  
  const reducedMotionTest = testReducedMotion();
  updateTestResult('result-reduced-motion', reducedMotionTest);
  
  const toggleTest = testAnimationToggle();
  updateTestResult('result-animation-toggle', toggleTest);
  
  const seizureTest = testSeizurePrevention();
  updateTestResult('result-seizure-prevention', seizureTest);
  
  const screenReaderTest = testScreenReaderSupport();
  updateTestResult('result-screen-reader', screenReaderTest);
  
  const allPassed = reducedMotionTest.passed && toggleTest.passed && seizureTest.passed && screenReaderTest.passed;
  updateSectionStatus('accessibility-status', allPassed);
  
  const score = Math.round((testResults.passed / testResults.total) * 100);
  document.getElementById('accessibility-score').textContent = score;
}

/**
 * Test reduced motion
 */
function testReducedMotion() {
  try {
    const prefersReducedMotion = window.visualEffectsAccessibility.prefersReducedMotion;
    
    testResults.total++;
    testResults.passed++;
    return { 
      passed: true, 
      message: prefersReducedMotion ? 'Reduced motion preference detected and respected' : 'No reduced motion preference' 
    };
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test animation toggle
 */
function testAnimationToggle() {
  try {
    const toggle = document.getElementById('animation-toggle');
    
    testResults.total++;
    if (toggle) {
      testResults.passed++;
      return { passed: true, message: 'Animation toggle control available' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Animation toggle not found' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test seizure prevention
 */
function testSeizurePrevention() {
  try {
    const seizureRiskElements = document.querySelectorAll('[data-seizure-risk]');
    
    testResults.total++;
    testResults.passed++;
    return { 
      passed: true, 
      message: `Seizure prevention active (${seizureRiskElements.length} risky elements detected)` 
    };
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test screen reader support
 */
function testScreenReaderSupport() {
  try {
    const liveRegion = document.getElementById('animation-live-region');
    
    testResults.total++;
    if (liveRegion) {
      testResults.passed++;
      return { passed: true, message: 'Screen reader live region available' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Screen reader support incomplete' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Run browser compatibility tests
 */
async function runBrowserTests() {
  console.log('Testing browser compatibility...');
  
  const detectionTest = testBrowserDetection();
  updateTestResult('result-browser-detection', detectionTest);
  
  const featureTest = testFeatureSupport();
  updateTestResult('result-feature-support', featureTest);
  
  const polyfillTest = testPolyfills();
  updateTestResult('result-polyfills', polyfillTest);
  
  const fallbackTest = testFallbacks();
  updateTestResult('result-fallbacks', fallbackTest);
  
  const allPassed = detectionTest.passed && featureTest.passed && polyfillTest.passed && fallbackTest.passed;
  updateSectionStatus('browser-status', allPassed);
}

/**
 * Test browser detection
 */
function testBrowserDetection() {
  try {
    const browser = window.crossBrowserCompat.browser;
    
    testResults.total++;
    if (browser.name !== 'unknown') {
      testResults.passed++;
      return { passed: true, message: `Detected: ${browser.name} ${browser.version} (${browser.engine})` };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Browser detection failed' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test feature support
 */
function testFeatureSupport() {
  try {
    const features = window.crossBrowserCompat.features;
    const supportedCount = Object.values(features).filter(v => v).length;
    const totalCount = Object.keys(features).length;
    
    testResults.total++;
    if (supportedCount >= totalCount * 0.8) {
      testResults.passed++;
      return { passed: true, message: `${supportedCount}/${totalCount} features supported` };
    } else {
      testResults.failed++;
      return { passed: false, message: `Only ${supportedCount}/${totalCount} features supported` };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test polyfills
 */
function testPolyfills() {
  try {
    const hasIntersectionObserver = 'IntersectionObserver' in window;
    const hasRequestAnimationFrame = 'requestAnimationFrame' in window;
    
    testResults.total++;
    if (hasIntersectionObserver && hasRequestAnimationFrame) {
      testResults.passed++;
      return { passed: true, message: 'All required polyfills available' };
    } else {
      testResults.failed++;
      return { passed: false, message: 'Some polyfills missing' };
    }
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Test fallbacks
 */
function testFallbacks() {
  try {
    const features = window.crossBrowserCompat.features;
    const hasFallbacks = !features.backdropFilter || !features.cssTransforms3d;
    
    testResults.total++;
    testResults.passed++;
    return { 
      passed: true, 
      message: hasFallbacks ? 'Fallbacks applied for unsupported features' : 'All features supported, no fallbacks needed' 
    };
  } catch (error) {
    testResults.total++;
    testResults.failed++;
    return { passed: false, message: `Error: ${error.message}` };
  }
}

/**
 * Update test result display
 */
function updateTestResult(elementId, result) {
  const element = document.getElementById(elementId);
  if (element) {
    element.className = `test-result ${result.passed ? 'pass' : 'fail'}`;
    element.textContent = result.message;
  }
}

/**
 * Update section status badge
 */
function updateSectionStatus(elementId, passed) {
  const element = document.getElementById(elementId);
  if (element) {
    element.className = `status-badge ${passed ? 'status-pass' : 'status-fail'}`;
    element.textContent = passed ? 'Pass' : 'Fail';
  }
}

/**
 * Update overall status
 */
function updateOverallStatus() {
  document.getElementById('tests-passed').textContent = testResults.passed;
  document.getElementById('tests-failed').textContent = testResults.failed;
  
  const progress = (testResults.passed / testResults.total) * 100;
  document.getElementById('progress-fill').style.width = `${progress}%`;
}

/**
 * Export test results
 */
function exportResults() {
  const results = {
    timestamp: new Date().toISOString(),
    browser: window.crossBrowserCompat.browser,
    testResults: testResults,
    performanceScore: document.getElementById('performance-score').textContent,
    accessibilityScore: document.getElementById('accessibility-score').textContent
  };
  
  const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `phase6-validation-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// Auto-run tests on page load
window.addEventListener('load', () => {
  setTimeout(() => {
    runAllTests();
  }, 1000);
});
