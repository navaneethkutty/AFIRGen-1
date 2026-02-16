/**
 * Visual Effects Accessibility Module
 * Ensures visual effects respect user preferences and accessibility requirements
 */

class VisualEffectsAccessibility {
  constructor() {
    this.prefersReducedMotion = false;
    this.animationsEnabled = true;
    this.init();
  }

  init() {
    this.detectMotionPreference();
    this.setupAnimationToggle();
    this.preventSeizureTriggers();
    this.ensureScreenReaderCompatibility();
  }

  /**
   * Detect prefers-reduced-motion preference
   */
  detectMotionPreference() {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    this.prefersReducedMotion = mediaQuery.matches;
    
    if (this.prefersReducedMotion) {
      this.disableAllAnimations();
    }
    
    // Listen for changes
    mediaQuery.addEventListener('change', (e) => {
      this.prefersReducedMotion = e.matches;
      if (e.matches) {
        this.disableAllAnimations();
      } else {
        this.enableAllAnimations();
      }
    });
  }

  /**
   * Setup animation toggle control
   */
  setupAnimationToggle() {
    // Create toggle button if it doesn't exist
    let toggle = document.getElementById('animation-toggle');
    
    if (!toggle) {
      toggle = this.createAnimationToggle();
      document.body.appendChild(toggle);
    }
    
    toggle.addEventListener('click', () => {
      this.toggleAnimations();
    });
  }

  /**
   * Create animation toggle button
   */
  createAnimationToggle() {
    const button = document.createElement('button');
    button.id = 'animation-toggle';
    button.className = 'animation-toggle-btn';
    button.setAttribute('aria-label', 'Toggle animations');
    button.setAttribute('aria-pressed', this.animationsEnabled);
    button.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
      </svg>
      <span class="sr-only">Toggle animations</span>
    `;
    
    return button;
  }

  /**
   * Toggle animations on/off
   */
  toggleAnimations() {
    this.animationsEnabled = !this.animationsEnabled;
    
    const toggle = document.getElementById('animation-toggle');
    if (toggle) {
      toggle.setAttribute('aria-pressed', this.animationsEnabled);
    }
    
    if (this.animationsEnabled) {
      this.enableAllAnimations();
    } else {
      this.disableAllAnimations();
    }
    
    // Announce to screen readers
    this.announceToScreenReader(
      this.animationsEnabled ? 'Animations enabled' : 'Animations disabled'
    );
  }

  /**
   * Disable all animations
   */
  disableAllAnimations() {
    document.body.classList.add('no-animations');
    
    // Disable CSS animations
    const style = document.createElement('style');
    style.id = 'disable-animations';
    style.textContent = `
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
      }
    `;
    
    if (!document.getElementById('disable-animations')) {
      document.head.appendChild(style);
    }
    
    // Disable JS animations
    const animatedElements = document.querySelectorAll('[data-animate]');
    animatedElements.forEach(element => {
      element.style.animation = 'none';
      element.style.transition = 'none';
    });
  }

  /**
   * Enable all animations
   */
  enableAllAnimations() {
    document.body.classList.remove('no-animations');
    
    // Remove disable style
    const disableStyle = document.getElementById('disable-animations');
    if (disableStyle) {
      disableStyle.remove();
    }
    
    // Re-enable JS animations
    const animatedElements = document.querySelectorAll('[data-animate]');
    animatedElements.forEach(element => {
      element.style.animation = '';
      element.style.transition = '';
    });
  }

  /**
   * Prevent seizure-triggering effects
   */
  preventSeizureTriggers() {
    // Check for rapid flashing
    const flashingElements = document.querySelectorAll('[data-flash], .flash-effect');
    
    flashingElements.forEach(element => {
      const animationDuration = parseFloat(getComputedStyle(element).animationDuration) || 1;
      const animationIterationCount = getComputedStyle(element).animationIterationCount;
      
      // Prevent flashing more than 3 times per second
      if (animationDuration < 0.33 && animationIterationCount === 'infinite') {
        console.warn('Potential seizure trigger detected:', element);
        element.style.animation = 'none';
        element.setAttribute('data-seizure-risk', 'true');
      }
    });
    
    // Check for high contrast flashing
    this.monitorContrastFlashing();
  }

  /**
   * Monitor for high contrast flashing
   */
  monitorContrastFlashing() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach(mutation => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
          const element = mutation.target;
          this.checkContrastFlashing(element);
        }
      });
    });
    
    // Observe all animated elements
    const animatedElements = document.querySelectorAll('[data-animate]');
    animatedElements.forEach(element => {
      observer.observe(element, { attributes: true });
    });
  }

  /**
   * Check for contrast flashing
   */
  checkContrastFlashing(element) {
    const bgColor = getComputedStyle(element).backgroundColor;
    const color = getComputedStyle(element).color;
    
    // Calculate contrast ratio
    const contrast = this.calculateContrastRatio(bgColor, color);
    
    // If high contrast and rapid animation, warn
    if (contrast > 7 && element.style.animation) {
      const duration = parseFloat(getComputedStyle(element).animationDuration) || 1;
      if (duration < 0.5) {
        console.warn('High contrast rapid animation detected:', element);
      }
    }
  }

  /**
   * Calculate contrast ratio between two colors
   */
  calculateContrastRatio(color1, color2) {
    const rgb1 = this.parseRGB(color1);
    const rgb2 = this.parseRGB(color2);
    
    const l1 = this.relativeLuminance(rgb1);
    const l2 = this.relativeLuminance(rgb2);
    
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    
    return (lighter + 0.05) / (darker + 0.05);
  }

  /**
   * Parse RGB color string
   */
  parseRGB(colorString) {
    const match = colorString.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (match) {
      return {
        r: parseInt(match[1]),
        g: parseInt(match[2]),
        b: parseInt(match[3])
      };
    }
    return { r: 0, g: 0, b: 0 };
  }

  /**
   * Calculate relative luminance
   */
  relativeLuminance(rgb) {
    const rsRGB = rgb.r / 255;
    const gsRGB = rgb.g / 255;
    const bsRGB = rgb.b / 255;
    
    const r = rsRGB <= 0.03928 ? rsRGB / 12.92 : Math.pow((rsRGB + 0.055) / 1.055, 2.4);
    const g = gsRGB <= 0.03928 ? gsRGB / 12.92 : Math.pow((gsRGB + 0.055) / 1.055, 2.4);
    const b = bsRGB <= 0.03928 ? bsRGB / 12.92 : Math.pow((bsRGB + 0.055) / 1.055, 2.4);
    
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  /**
   * Ensure screen reader compatibility
   */
  ensureScreenReaderCompatibility() {
    // Hide decorative animations from screen readers
    const decorativeAnimations = document.querySelectorAll('[data-animate][data-decorative]');
    decorativeAnimations.forEach(element => {
      element.setAttribute('aria-hidden', 'true');
    });
    
    // Add live regions for important animations
    const importantAnimations = document.querySelectorAll('[data-animate][data-announce]');
    importantAnimations.forEach(element => {
      const message = element.getAttribute('data-announce');
      this.createLiveRegion(message);
    });
  }

  /**
   * Create ARIA live region
   */
  createLiveRegion(message) {
    let liveRegion = document.getElementById('animation-live-region');
    
    if (!liveRegion) {
      liveRegion = document.createElement('div');
      liveRegion.id = 'animation-live-region';
      liveRegion.setAttribute('role', 'status');
      liveRegion.setAttribute('aria-live', 'polite');
      liveRegion.setAttribute('aria-atomic', 'true');
      liveRegion.className = 'sr-only';
      document.body.appendChild(liveRegion);
    }
    
    liveRegion.textContent = message;
  }

  /**
   * Announce to screen reader
   */
  announceToScreenReader(message) {
    this.createLiveRegion(message);
  }

  /**
   * Add focus indicators to animated elements
   */
  addFocusIndicators() {
    const interactiveAnimations = document.querySelectorAll('[data-animate][tabindex]');
    
    interactiveAnimations.forEach(element => {
      element.addEventListener('focus', () => {
        element.classList.add('animation-focused');
      });
      
      element.addEventListener('blur', () => {
        element.classList.remove('animation-focused');
      });
    });
  }

  /**
   * Provide alternative content for animations
   */
  provideAlternativeContent(element, altContent) {
    const alt = document.createElement('div');
    alt.className = 'animation-alt-content sr-only';
    alt.textContent = altContent;
    element.appendChild(alt);
  }

  /**
   * Get accessibility status
   */
  getAccessibilityStatus() {
    return {
      prefersReducedMotion: this.prefersReducedMotion,
      animationsEnabled: this.animationsEnabled,
      seizureRiskElements: document.querySelectorAll('[data-seizure-risk]').length
    };
  }
}

// Initialize on DOM ready
if (typeof window !== 'undefined') {
  window.VisualEffectsAccessibility = VisualEffectsAccessibility;
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.visualEffectsAccessibility = new VisualEffectsAccessibility();
    });
  } else {
    window.visualEffectsAccessibility = new VisualEffectsAccessibility();
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = VisualEffectsAccessibility;
}
