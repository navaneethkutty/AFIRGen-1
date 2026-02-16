/**
 * Hover Effects Module
 * 
 * Provides advanced hover effects including:
 * - Scale and glow effects
 * - Shadow lift effects
 * - Magnetic button effects (mouse tracking)
 * - Smooth color transitions
 * 
 * All effects respect prefers-reduced-motion and are optimized for 60fps
 */

class HoverEffects {
  constructor() {
    this.magneticElements = new Map();
    this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    // Listen for reduced motion preference changes
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
      this.reducedMotion = e.matches;
      if (this.reducedMotion) {
        this.disableAllEffects();
      }
    });
  }

  /**
   * Initialize hover effects on elements
   * @param {string} selector - CSS selector for elements
   * @param {string} effectType - Type of effect ('scale-glow', 'lift', 'magnetic', etc.)
   * @param {Object} options - Additional options
   */
  init(selector, effectType, options = {}) {
    if (this.reducedMotion || this.isTouchDevice) {
      return;
    }

    const elements = document.querySelectorAll(selector);
    
    elements.forEach(element => {
      switch (effectType) {
        case 'scale-glow':
          this.applyScaleGlow(element, options);
          break;
        case 'lift':
          this.applyLift(element, options);
          break;
        case 'magnetic':
          this.applyMagnetic(element, options);
          break;
        case 'color':
          this.applyColorTransition(element, options);
          break;
        case 'lift-glow':
          this.applyLiftGlow(element, options);
          break;
        default:
          console.warn(`Unknown effect type: ${effectType}`);
      }
    });
  }

  /**
   * Apply scale and glow effect
   * @param {HTMLElement} element - Target element
   * @param {Object} options - Effect options
   */
  applyScaleGlow(element, options = {}) {
    const {
      scale = 1.05,
      glowColor = 'rgba(0, 123, 255, 0.5)',
      glowSize = 20
    } = options;

    element.classList.add('hover-scale-glow');
    
    // Store original styles
    const originalTransform = element.style.transform;
    const originalBoxShadow = element.style.boxShadow;

    element.addEventListener('mouseenter', () => {
      if (this.reducedMotion) return;
      
      element.style.transform = `scale(${scale})`;
      element.style.boxShadow = `0 0 ${glowSize}px ${glowColor}, 0 0 ${glowSize * 2}px ${glowColor.replace('0.5', '0.3')}`;
    });

    element.addEventListener('mouseleave', () => {
      element.style.transform = originalTransform;
      element.style.boxShadow = originalBoxShadow;
    });
  }

  /**
   * Apply shadow lift effect
   * @param {HTMLElement} element - Target element
   * @param {Object} options - Effect options
   */
  applyLift(element, options = {}) {
    const {
      liftDistance = 8,
      shadowIntensity = 0.15
    } = options;

    element.classList.add('hover-lift');
    
    const originalTransform = element.style.transform;
    const originalBoxShadow = element.style.boxShadow;

    element.addEventListener('mouseenter', () => {
      if (this.reducedMotion) return;
      
      element.style.transform = `translateY(-${liftDistance}px)`;
      element.style.boxShadow = `0 ${liftDistance * 1.5}px ${liftDistance * 3}px rgba(0, 0, 0, ${shadowIntensity})`;
    });

    element.addEventListener('mouseleave', () => {
      element.style.transform = originalTransform;
      element.style.boxShadow = originalBoxShadow;
    });
  }

  /**
   * Apply magnetic button effect (follows mouse)
   * @param {HTMLElement} element - Target element
   * @param {Object} options - Effect options
   */
  applyMagnetic(element, options = {}) {
    const {
      strength = 0.3,
      maxDistance = 50
    } = options;

    element.classList.add('hover-magnetic');
    
    const rect = element.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const handleMouseMove = (e) => {
      if (this.reducedMotion) return;

      const mouseX = e.clientX;
      const mouseY = e.clientY;

      // Calculate distance from center
      const deltaX = mouseX - centerX;
      const deltaY = mouseY - centerY;
      const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

      // Only apply effect if within maxDistance
      if (distance < maxDistance) {
        const moveX = deltaX * strength;
        const moveY = deltaY * strength;
        
        // Use transform for GPU acceleration
        element.style.transform = `translate(${moveX}px, ${moveY}px)`;
      } else {
        element.style.transform = 'translate(0, 0)';
      }
    };

    const handleMouseLeave = () => {
      element.style.transform = 'translate(0, 0)';
    };

    element.addEventListener('mousemove', handleMouseMove);
    element.addEventListener('mouseleave', handleMouseLeave);

    // Store handlers for cleanup
    this.magneticElements.set(element, { handleMouseMove, handleMouseLeave });
  }

  /**
   * Apply color transition effect
   * @param {HTMLElement} element - Target element
   * @param {Object} options - Effect options
   */
  applyColorTransition(element, options = {}) {
    const {
      hoverColor = '#007bff',
      hoverTextColor = '#ffffff',
      hoverBorderColor = '#007bff'
    } = options;

    const originalBgColor = window.getComputedStyle(element).backgroundColor;
    const originalTextColor = window.getComputedStyle(element).color;
    const originalBorderColor = window.getComputedStyle(element).borderColor;

    element.style.transition = 'background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease';

    element.addEventListener('mouseenter', () => {
      element.style.backgroundColor = hoverColor;
      element.style.color = hoverTextColor;
      element.style.borderColor = hoverBorderColor;
    });

    element.addEventListener('mouseleave', () => {
      element.style.backgroundColor = originalBgColor;
      element.style.color = originalTextColor;
      element.style.borderColor = originalBorderColor;
    });
  }

  /**
   * Apply combined lift and glow effect
   * @param {HTMLElement} element - Target element
   * @param {Object} options - Effect options
   */
  applyLiftGlow(element, options = {}) {
    const {
      liftDistance = 6,
      scale = 1.02,
      glowColor = 'rgba(0, 123, 255, 0.3)',
      glowSize = 20
    } = options;

    element.classList.add('hover-lift-glow');
    
    const originalTransform = element.style.transform;
    const originalBoxShadow = element.style.boxShadow;

    element.addEventListener('mouseenter', () => {
      if (this.reducedMotion) return;
      
      element.style.transform = `translateY(-${liftDistance}px) scale(${scale})`;
      element.style.boxShadow = `0 ${liftDistance * 2}px ${liftDistance * 4}px ${glowColor}, 0 0 ${glowSize}px ${glowColor}`;
    });

    element.addEventListener('mouseleave', () => {
      element.style.transform = originalTransform;
      element.style.boxShadow = originalBoxShadow;
    });
  }

  /**
   * Remove magnetic effect from element
   * @param {HTMLElement} element - Target element
   */
  removeMagnetic(element) {
    const handlers = this.magneticElements.get(element);
    if (handlers) {
      element.removeEventListener('mousemove', handlers.handleMouseMove);
      element.removeEventListener('mouseleave', handlers.handleMouseLeave);
      this.magneticElements.delete(element);
    }
  }

  /**
   * Disable all effects (for reduced motion)
   */
  disableAllEffects() {
    // Remove magnetic effects
    this.magneticElements.forEach((handlers, element) => {
      this.removeMagnetic(element);
    });

    // Reset all transforms
    document.querySelectorAll('.hover-scale-glow, .hover-lift, .hover-magnetic, .hover-lift-glow').forEach(element => {
      element.style.transform = '';
      element.style.boxShadow = '';
    });
  }

  /**
   * Cleanup all effects
   */
  destroy() {
    this.disableAllEffects();
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = HoverEffects;
}

// Auto-initialize on DOM ready
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    window.hoverEffects = new HoverEffects();
  });
}
