/**
 * Subtle Motion Module
 * 
 * Provides programmatic control for subtle motion effects:
 * - Apply/remove motion effects dynamically
 * - Respect user preferences (prefers-reduced-motion)
 * - Performance monitoring
 * - Accessibility features
 * 
 * All effects are GPU-accelerated and optimized for 60fps
 */

class SubtleMotion {
  constructor() {
    this.elements = new Map();
    this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.performanceMode = false;
    
    // Listen for reduced motion preference changes
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
      this.reducedMotion = e.matches;
      this.updateAllElements();
    });

    // Monitor performance
    this.initPerformanceMonitoring();
  }

  /**
   * Apply floating animation to element
   * @param {HTMLElement} element - Element to animate
   * @param {Object} options - Animation options
   */
  applyFloat(element, options = {}) {
    if (!element) return;
    
    const {
      speed = 'normal', // 'slow', 'normal', 'fast'
      direction = 'up', // 'up', 'down'
      pause = false
    } = options;

    if (this.reducedMotion) {
      return;
    }

    // Remove existing animation classes
    this.removeAllMotionClasses(element);

    // Apply appropriate class
    let className = 'float-gentle';
    if (speed === 'slow') className = 'float-gentle-slow';
    if (speed === 'fast') className = 'float-gentle-fast';
    if (direction === 'down') className = 'float-gentle-reverse';

    element.classList.add(className);
    if (pause) element.classList.add('pause-on-hover');

    // Store reference
    this.elements.set(element, { type: 'float', options });

    return element;
  }

  /**
   * Apply breathing animation to element
   * @param {HTMLElement} element - Element to animate
   * @param {Object} options - Animation options
   */
  applyBreathe(element, options = {}) {
    if (!element) return;
    
    const {
      intensity = 'normal', // 'subtle', 'normal', 'glow'
      speed = 'normal', // 'slow', 'normal', 'fast'
      pause = false
    } = options;

    if (this.reducedMotion) {
      return;
    }

    // Remove existing animation classes
    this.removeAllMotionClasses(element);

    // Apply appropriate class
    let className = 'breathe';
    if (intensity === 'subtle') className = 'breathe-subtle';
    if (intensity === 'glow') className = 'breathe-glow';
    if (speed === 'slow') className += ' breathe-slow';
    if (speed === 'fast') className += ' breathe-fast';

    element.classList.add(...className.split(' '));
    if (pause) element.classList.add('pause-on-hover');

    // Store reference
    this.elements.set(element, { type: 'breathe', options });

    return element;
  }

  /**
   * Apply wave animation to element
   * @param {HTMLElement} element - Element to animate
   * @param {Object} options - Animation options
   */
  applyWave(element, options = {}) {
    if (!element) return;
    
    const {
      direction = 'horizontal', // 'horizontal', 'vertical', 'ripple', 'pulse'
      pause = false
    } = options;

    if (this.reducedMotion) {
      return;
    }

    // Remove existing animation classes
    this.removeAllMotionClasses(element);

    // Apply appropriate class
    let className = 'wave-horizontal';
    if (direction === 'vertical') className = 'wave-vertical';
    if (direction === 'ripple') className = 'wave-ripple';
    if (direction === 'pulse') className = 'wave-pulse';

    element.classList.add(className);
    if (pause) element.classList.add('pause-on-hover');

    // Store reference
    this.elements.set(element, { type: 'wave', options });

    return element;
  }

  /**
   * Apply combined effects
   * @param {HTMLElement} element - Element to animate
   * @param {Object} options - Animation options
   */
  applyCombined(element, options = {}) {
    if (!element) return;
    
    const {
      effects = ['float', 'breathe'], // Array of effects to combine
      pause = false
    } = options;

    if (this.reducedMotion) {
      return;
    }

    // Remove existing animation classes
    this.removeAllMotionClasses(element);

    // Apply combined class
    if (effects.includes('float') && effects.includes('breathe')) {
      element.classList.add('float-breathe');
    } else if (effects.includes('float') && effects.includes('wave')) {
      element.classList.add('float-wave');
    }

    if (pause) element.classList.add('pause-on-hover');

    // Store reference
    this.elements.set(element, { type: 'combined', options });

    return element;
  }

  /**
   * Apply staggered animation to multiple elements
   * @param {NodeList|Array} elements - Elements to animate
   * @param {Object} options - Animation options
   */
  applyStaggered(elements, options = {}) {
    const {
      type = 'float', // 'float', 'breathe', 'wave'
      delay = 0.1 // Delay between each element in seconds
    } = options;

    if (this.reducedMotion) {
      return;
    }

    elements.forEach((element, index) => {
      // Apply base animation
      switch (type) {
        case 'float':
          this.applyFloat(element, options);
          break;
        case 'breathe':
          this.applyBreathe(element, options);
          break;
        case 'wave':
          this.applyWave(element, options);
          break;
      }

      // Add stagger delay
      const delayClass = `stagger-delay-${Math.min(index + 1, 5)}`;
      element.classList.add(delayClass);

      // Custom delay if needed
      if (index > 4) {
        element.style.animationDelay = `${(index + 1) * delay}s`;
      }
    });

    return elements;
  }

  /**
   * Remove all motion effects from element
   * @param {HTMLElement} element - Element to clean
   */
  removeMotion(element) {
    this.removeAllMotionClasses(element);
    element.style.animationDelay = '';
    this.elements.delete(element);
  }

  /**
   * Remove all motion classes from element
   * @param {HTMLElement} element - Element to clean
   * @private
   */
  removeAllMotionClasses(element) {
    const motionClasses = [
      'float-gentle', 'float-gentle-reverse', 'float-gentle-slow', 'float-gentle-fast',
      'breathe', 'breathe-subtle', 'breathe-glow', 'breathe-slow', 'breathe-fast',
      'wave-horizontal', 'wave-vertical', 'wave-ripple', 'wave-pulse',
      'float-breathe', 'float-wave',
      'pause-on-hover', 'slow-motion', 'fast-motion',
      'stagger-delay-1', 'stagger-delay-2', 'stagger-delay-3', 'stagger-delay-4', 'stagger-delay-5'
    ];

    element.classList.remove(...motionClasses);
  }

  /**
   * Pause animation on element
   * @param {HTMLElement} element - Element to pause
   */
  pauseAnimation(element) {
    element.style.animationPlayState = 'paused';
  }

  /**
   * Resume animation on element
   * @param {HTMLElement} element - Element to resume
   */
  resumeAnimation(element) {
    if (!this.reducedMotion) {
      element.style.animationPlayState = 'running';
    }
  }

  /**
   * Update all elements based on current preferences
   * @private
   */
  updateAllElements() {
    // Create a copy of the elements map to avoid modification during iteration
    const elementsCopy = new Map(this.elements);
    
    elementsCopy.forEach((data, element) => {
      if (this.reducedMotion) {
        // Remove animation classes but keep tracking
        this.removeAllMotionClasses(element);
        element.style.animationDelay = '';
      } else {
        // Reapply animation
        switch (data.type) {
          case 'float':
            this.applyFloat(element, data.options);
            break;
          case 'breathe':
            this.applyBreathe(element, data.options);
            break;
          case 'wave':
            this.applyWave(element, data.options);
            break;
          case 'combined':
            this.applyCombined(element, data.options);
            break;
        }
      }
    });
  }

  /**
   * Initialize performance monitoring
   * @private
   */
  initPerformanceMonitoring() {
    if (!window.requestAnimationFrame) return;

    let lastTime = performance.now();
    let frames = 0;
    let fps = 60;

    const measureFPS = () => {
      const currentTime = performance.now();
      frames++;

      if (currentTime >= lastTime + 1000) {
        fps = Math.round((frames * 1000) / (currentTime - lastTime));
        frames = 0;
        lastTime = currentTime;

        // Enable performance mode if FPS drops below 30
        if (fps < 30 && !this.performanceMode) {
          this.enablePerformanceMode();
        } else if (fps >= 50 && this.performanceMode) {
          this.disablePerformanceMode();
        }
      }

      requestAnimationFrame(measureFPS);
    };

    requestAnimationFrame(measureFPS);
  }

  /**
   * Enable performance mode (reduce animations)
   * @private
   */
  enablePerformanceMode() {
    this.performanceMode = true;
    console.warn('SubtleMotion: Performance mode enabled (low FPS detected)');
    
    // Reduce animation complexity
    this.elements.forEach((data, element) => {
      element.classList.add('slow-motion');
    });
  }

  /**
   * Disable performance mode
   * @private
   */
  disablePerformanceMode() {
    this.performanceMode = false;
    console.log('SubtleMotion: Performance mode disabled');
    
    // Restore normal animation speed
    this.elements.forEach((data, element) => {
      element.classList.remove('slow-motion');
    });
  }

  /**
   * Get current state
   * @returns {Object} Current state information
   */
  getState() {
    return {
      reducedMotion: this.reducedMotion,
      performanceMode: this.performanceMode,
      activeElements: this.elements.size
    };
  }

  /**
   * Cleanup all animations
   */
  destroy() {
    this.elements.forEach((data, element) => {
      this.removeMotion(element);
    });
    this.elements.clear();
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SubtleMotion;
}

// Auto-initialize on DOM ready
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    window.subtleMotion = new SubtleMotion();
  });
}

