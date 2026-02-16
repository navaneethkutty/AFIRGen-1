/**
 * Cross-Browser Compatibility Module
 * Ensures visual effects work across Chrome, Firefox, Safari, and Edge
 */

class CrossBrowserCompat {
  constructor() {
    this.browser = this.detectBrowser();
    this.features = {};
    this.init();
  }

  init() {
    this.detectFeatures();
    this.applyPolyfills();
    this.applyBrowserSpecificFixes();
  }

  /**
   * Detect browser type and version
   */
  detectBrowser() {
    const ua = navigator.userAgent;
    let browser = {
      name: 'unknown',
      version: 0,
      engine: 'unknown'
    };

    // Chrome
    if (ua.indexOf('Chrome') > -1 && ua.indexOf('Edg') === -1) {
      browser.name = 'chrome';
      browser.version = parseInt(ua.match(/Chrome\/(\d+)/)[1]);
      browser.engine = 'blink';
    }
    // Edge (Chromium)
    else if (ua.indexOf('Edg') > -1) {
      browser.name = 'edge';
      browser.version = parseInt(ua.match(/Edg\/(\d+)/)[1]);
      browser.engine = 'blink';
    }
    // Firefox
    else if (ua.indexOf('Firefox') > -1) {
      browser.name = 'firefox';
      browser.version = parseInt(ua.match(/Firefox\/(\d+)/)[1]);
      browser.engine = 'gecko';
    }
    // Safari
    else if (ua.indexOf('Safari') > -1 && ua.indexOf('Chrome') === -1) {
      browser.name = 'safari';
      const match = ua.match(/Version\/(\d+)/);
      browser.version = match ? parseInt(match[1]) : 0;
      browser.engine = 'webkit';
    }

    console.log('Detected browser:', browser);
    return browser;
  }

  /**
   * Detect feature support
   */
  detectFeatures() {
    // CSS features
    this.features.cssGrid = CSS.supports('display', 'grid');
    this.features.cssCustomProperties = CSS.supports('--test', '0');
    this.features.backdropFilter = CSS.supports('backdrop-filter', 'blur(10px)');
    this.features.clipPath = CSS.supports('clip-path', 'circle(50%)');
    this.features.cssTransforms3d = CSS.supports('transform', 'translateZ(0)');
    
    // JS features
    this.features.intersectionObserver = 'IntersectionObserver' in window;
    this.features.resizeObserver = 'ResizeObserver' in window;
    this.features.requestAnimationFrame = 'requestAnimationFrame' in window;
    this.features.webGL = this.detectWebGL();
    
    // Animation features
    this.features.cssAnimations = CSS.supports('animation', 'test 1s');
    this.features.cssTransitions = CSS.supports('transition', 'all 1s');
    
    console.log('Feature support:', this.features);
  }

  /**
   * Detect WebGL support
   */
  detectWebGL() {
    try {
      const canvas = document.createElement('canvas');
      return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
    } catch (e) {
      return false;
    }
  }

  /**
   * Apply polyfills for missing features
   */
  applyPolyfills() {
    // IntersectionObserver polyfill
    if (!this.features.intersectionObserver) {
      console.warn('IntersectionObserver not supported, using fallback');
      this.polyfillIntersectionObserver();
    }

    // requestAnimationFrame polyfill
    if (!this.features.requestAnimationFrame) {
      this.polyfillRequestAnimationFrame();
    }

    // CSS custom properties fallback
    if (!this.features.cssCustomProperties) {
      this.fallbackCSSCustomProperties();
    }
  }

  /**
   * Polyfill IntersectionObserver
   */
  polyfillIntersectionObserver() {
    window.IntersectionObserver = class {
      constructor(callback) {
        this.callback = callback;
        this.elements = new Set();
      }

      observe(element) {
        this.elements.add(element);
        // Immediately trigger callback
        this.callback([{
          target: element,
          isIntersecting: true
        }]);
      }

      unobserve(element) {
        this.elements.delete(element);
      }

      disconnect() {
        this.elements.clear();
      }
    };
  }

  /**
   * Polyfill requestAnimationFrame
   */
  polyfillRequestAnimationFrame() {
    let lastTime = 0;
    window.requestAnimationFrame = function(callback) {
      const currentTime = new Date().getTime();
      const timeToCall = Math.max(0, 16 - (currentTime - lastTime));
      const id = window.setTimeout(() => {
        callback(currentTime + timeToCall);
      }, timeToCall);
      lastTime = currentTime + timeToCall;
      return id;
    };

    window.cancelAnimationFrame = function(id) {
      clearTimeout(id);
    };
  }

  /**
   * Fallback for CSS custom properties
   */
  fallbackCSSCustomProperties() {
    // Add fallback values for critical custom properties
    const style = document.createElement('style');
    style.textContent = `
      :root {
        /* Fallback colors */
        --primary-color: #667eea;
        --secondary-color: #764ba2;
        --text-color: #ffffff;
        --bg-color: #000000;
      }
    `;
    document.head.appendChild(style);
  }

  /**
   * Apply browser-specific fixes
   */
  applyBrowserSpecificFixes() {
    switch (this.browser.name) {
      case 'safari':
        this.applySafariFixes();
        break;
      case 'firefox':
        this.applyFirefoxFixes();
        break;
      case 'edge':
        this.applyEdgeFixes();
        break;
      case 'chrome':
        this.applyChromeFixes();
        break;
    }
  }

  /**
   * Safari-specific fixes
   */
  applySafariFixes() {
    document.body.classList.add('browser-safari');

    // Fix backdrop-filter
    if (!this.features.backdropFilter) {
      const blurElements = document.querySelectorAll('[style*="backdrop-filter"]');
      blurElements.forEach(element => {
        element.style.backdropFilter = 'none';
        element.style.background = 'rgba(0, 0, 0, 0.8)';
      });
    }

    // Fix smooth scrolling
    document.documentElement.style.scrollBehavior = 'smooth';

    // Fix flexbox gap
    if (this.browser.version < 14) {
      this.fixFlexboxGap();
    }
  }

  /**
   * Firefox-specific fixes
   */
  applyFirefoxFixes() {
    document.body.classList.add('browser-firefox');

    // Fix backdrop-filter performance
    const blurElements = document.querySelectorAll('[style*="backdrop-filter"]');
    blurElements.forEach(element => {
      element.style.willChange = 'backdrop-filter';
    });

    // Fix smooth scrolling
    document.documentElement.style.scrollBehavior = 'smooth';
  }

  /**
   * Edge-specific fixes
   */
  applyEdgeFixes() {
    document.body.classList.add('browser-edge');

    // Most Edge issues are resolved in Chromium-based version
    if (this.browser.version < 79) {
      console.warn('Old Edge detected, some features may not work');
    }
  }

  /**
   * Chrome-specific fixes
   */
  applyChromeFixes() {
    document.body.classList.add('browser-chrome');

    // Chrome-specific optimizations
    const animatedElements = document.querySelectorAll('[data-animate]');
    animatedElements.forEach(element => {
      element.style.willChange = 'transform, opacity';
    });
  }

  /**
   * Fix flexbox gap for older browsers
   */
  fixFlexboxGap() {
    const style = document.createElement('style');
    style.textContent = `
      .flex-gap > * {
        margin-right: 1rem;
        margin-bottom: 1rem;
      }
      .flex-gap > *:last-child {
        margin-right: 0;
      }
    `;
    document.head.appendChild(style);
  }

  /**
   * Test animation performance
   */
  testAnimationPerformance() {
    const testElement = document.createElement('div');
    testElement.style.cssText = `
      position: fixed;
      top: -100px;
      left: -100px;
      width: 50px;
      height: 50px;
      background: red;
      animation: test-animation 1s linear infinite;
    `;

    const style = document.createElement('style');
    style.textContent = `
      @keyframes test-animation {
        from { transform: translateX(0); }
        to { transform: translateX(100px); }
      }
    `;

    document.head.appendChild(style);
    document.body.appendChild(testElement);

    let frames = 0;
    let lastTime = performance.now();

    const measureFPS = () => {
      frames++;
      const currentTime = performance.now();

      if (currentTime >= lastTime + 1000) {
        const fps = Math.round((frames * 1000) / (currentTime - lastTime));
        console.log('Animation FPS:', fps);
        
        // Cleanup
        document.body.removeChild(testElement);
        document.head.removeChild(style);
        
        return fps;
      }

      requestAnimationFrame(measureFPS);
    };

    requestAnimationFrame(measureFPS);
  }

  /**
   * Get compatibility report
   */
  getCompatibilityReport() {
    return {
      browser: this.browser,
      features: this.features,
      recommendations: this.getRecommendations()
    };
  }

  /**
   * Get browser-specific recommendations
   */
  getRecommendations() {
    const recommendations = [];

    if (!this.features.backdropFilter) {
      recommendations.push('Use solid backgrounds instead of backdrop-filter');
    }

    if (!this.features.cssTransforms3d) {
      recommendations.push('Avoid 3D transforms, use 2D transforms instead');
    }

    if (!this.features.intersectionObserver) {
      recommendations.push('IntersectionObserver polyfill applied');
    }

    if (this.browser.name === 'safari' && this.browser.version < 14) {
      recommendations.push('Update Safari for better performance');
    }

    return recommendations;
  }
}

// Initialize on DOM ready
if (typeof window !== 'undefined') {
  window.CrossBrowserCompat = CrossBrowserCompat;
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.crossBrowserCompat = new CrossBrowserCompat();
    });
  } else {
    window.crossBrowserCompat = new CrossBrowserCompat();
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CrossBrowserCompat;
}
