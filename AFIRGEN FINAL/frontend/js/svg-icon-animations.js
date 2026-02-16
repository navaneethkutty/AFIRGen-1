/**
 * SVG Icon Animations Module
 * Provides animated icon transitions and morphing effects
 */

class SVGIconAnimations {
  constructor() {
    this.icons = new Map();
    this.init();
  }

  init() {
    // Initialize icon animations on page load
    this.setupLoadingIcons();
    this.setupSuccessIcons();
    this.setupErrorIcons();
    this.setupMorphingIcons();
  }

  /**
   * Setup loading icon animations (spinner)
   */
  setupLoadingIcons() {
    const loadingIcons = document.querySelectorAll('[data-icon-type="loading"]');
    loadingIcons.forEach(icon => {
      this.animateLoading(icon);
    });
  }

  /**
   * Animate loading spinner icon
   */
  animateLoading(icon) {
    icon.style.animation = 'spin 1s linear infinite';
  }

  /**
   * Setup success icon animations (checkmark)
   */
  setupSuccessIcons() {
    const successIcons = document.querySelectorAll('[data-icon-type="success"]');
    successIcons.forEach(icon => {
      this.animateSuccess(icon);
    });
  }

  /**
   * Animate success checkmark with draw effect
   */
  animateSuccess(icon) {
    const paths = icon.querySelectorAll('path, polyline');
    paths.forEach((path, index) => {
      const length = path.getTotalLength();
      path.style.strokeDasharray = length;
      path.style.strokeDashoffset = length;
      path.style.animation = `draw 0.6s ease-out ${index * 0.1}s forwards`;
    });
  }

  /**
   * Setup error icon animations (X mark)
   */
  setupErrorIcons() {
    const errorIcons = document.querySelectorAll('[data-icon-type="error"]');
    errorIcons.forEach(icon => {
      this.animateError(icon);
    });
  }

  /**
   * Animate error X mark with draw effect
   */
  animateError(icon) {
    const lines = icon.querySelectorAll('line');
    lines.forEach((line, index) => {
      const length = line.getTotalLength();
      line.style.strokeDasharray = length;
      line.style.strokeDashoffset = length;
      line.style.animation = `draw 0.4s ease-out ${index * 0.15}s forwards`;
    });
  }

  /**
   * Setup morphing icon animations
   */
  setupMorphingIcons() {
    const morphingIcons = document.querySelectorAll('[data-icon-morph]');
    morphingIcons.forEach(icon => {
      const targetState = icon.getAttribute('data-icon-morph');
      this.registerMorphingIcon(icon, targetState);
    });
  }

  /**
   * Register an icon for morphing animation
   */
  registerMorphingIcon(icon, targetState) {
    this.icons.set(icon, {
      currentState: 'default',
      targetState: targetState,
      element: icon
    });
  }

  /**
   * Morph icon from one state to another
   */
  morphIcon(icon, fromState, toState) {
    const paths = icon.querySelectorAll('path, polyline, circle, line');
    
    paths.forEach(path => {
      const fromPath = this.getIconPath(fromState, path);
      const toPath = this.getIconPath(toState, path);
      
      if (fromPath && toPath) {
        this.animatePath(path, fromPath, toPath);
      }
    });
  }

  /**
   * Get icon path data for a specific state
   */
  getIconPath(state, element) {
    const pathData = {
      'play': 'M5 3l14 9-14 9V3z',
      'pause': 'M6 4h4v16H6V4zm8 0h4v16h-4V4z',
      'upload': 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12',
      'check': 'M20 6L9 17l-5-5',
      'menu': 'M3 12h18M3 6h18M3 18h18',
      'close': 'M18 6L6 18M6 6l12 12'
    };

    return pathData[state];
  }

  /**
   * Animate path morphing
   */
  animatePath(element, fromPath, toPath) {
    element.style.transition = 'all 0.3s ease-in-out';
    
    if (element.tagName === 'path') {
      element.setAttribute('d', toPath);
    }
  }

  /**
   * Trigger icon animation by type
   */
  triggerAnimation(iconElement, animationType) {
    switch (animationType) {
      case 'loading':
        this.animateLoading(iconElement);
        break;
      case 'success':
        this.animateSuccess(iconElement);
        break;
      case 'error':
        this.animateError(iconElement);
        break;
      case 'pulse':
        this.animatePulse(iconElement);
        break;
      case 'bounce':
        this.animateBounce(iconElement);
        break;
      default:
        console.warn(`Unknown animation type: ${animationType}`);
    }
  }

  /**
   * Pulse animation for icons
   */
  animatePulse(icon) {
    icon.style.animation = 'pulse 1s ease-in-out infinite';
  }

  /**
   * Bounce animation for icons
   */
  animateBounce(icon) {
    icon.style.animation = 'bounce 0.6s ease-in-out';
  }

  /**
   * Stop all animations on an icon
   */
  stopAnimation(icon) {
    icon.style.animation = 'none';
  }

  /**
   * Reset icon to default state
   */
  resetIcon(icon) {
    this.stopAnimation(icon);
    const paths = icon.querySelectorAll('path, polyline, line, circle');
    paths.forEach(path => {
      path.style.strokeDasharray = 'none';
      path.style.strokeDashoffset = '0';
      path.style.animation = 'none';
    });
  }
}

// Initialize on DOM ready
if (typeof window !== 'undefined') {
  window.SVGIconAnimations = SVGIconAnimations;
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.svgIconAnimations = new SVGIconAnimations();
    });
  } else {
    window.svgIconAnimations = new SVGIconAnimations();
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SVGIconAnimations;
}
