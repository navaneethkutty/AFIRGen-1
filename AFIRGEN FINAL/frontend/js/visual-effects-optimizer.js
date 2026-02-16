/**
 * Visual Effects Performance Optimizer
 * Optimizes animations and visual effects for smooth 60fps performance
 */

class VisualEffectsOptimizer {
  constructor() {
    this.isLowEndDevice = false;
    this.prefersReducedMotion = false;
    this.animationFrameId = null;
    this.observers = new Map();
    this.init();
  }

  init() {
    this.detectDeviceCapabilities();
    this.detectMotionPreference();
    this.setupIntersectionObserver();
    this.optimizeAnimations();
  }

  /**
   * Detect device capabilities
   */
  detectDeviceCapabilities() {
    // Check for low-end device indicators
    const hardwareConcurrency = navigator.hardwareConcurrency || 2;
    const deviceMemory = navigator.deviceMemory || 4;
    
    this.isLowEndDevice = hardwareConcurrency <= 2 || deviceMemory <= 2;
    
    // Check for GPU acceleration
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    this.hasGPU = !!gl;
    
    console.log('Device capabilities:', {
      isLowEndDevice: this.isLowEndDevice,
      hardwareConcurrency,
      deviceMemory,
      hasGPU: this.hasGPU
    });
  }

  /**
   * Detect user motion preference
   */
  detectMotionPreference() {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    this.prefersReducedMotion = mediaQuery.matches;
    
    // Listen for changes
    mediaQuery.addEventListener('change', (e) => {
      this.prefersReducedMotion = e.matches;
      this.optimizeAnimations();
    });
  }

  /**
   * Setup Intersection Observer for lazy animation loading
   */
  setupIntersectionObserver() {
    const options = {
      root: null,
      rootMargin: '50px',
      threshold: 0.1
    };

    this.intersectionObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          this.activateAnimation(entry.target);
        } else {
          this.deactivateAnimation(entry.target);
        }
      });
    }, options);
  }

  /**
   * Observe element for lazy animation
   */
  observeElement(element) {
    if (this.intersectionObserver) {
      this.intersectionObserver.observe(element);
    }
  }

  /**
   * Unobserve element
   */
  unobserveElement(element) {
    if (this.intersectionObserver) {
      this.intersectionObserver.unobserve(element);
    }
  }

  /**
   * Activate animation when element is visible
   */
  activateAnimation(element) {
    if (this.prefersReducedMotion) {
      return;
    }

    element.classList.add('animate-active');
    
    // Use will-change for GPU acceleration
    if (this.hasGPU && !this.isLowEndDevice) {
      element.style.willChange = 'transform, opacity';
    }
  }

  /**
   * Deactivate animation when element is not visible
   */
  deactivateAnimation(element) {
    element.classList.remove('animate-active');
    element.style.willChange = 'auto';
  }

  /**
   * Optimize all animations based on device capabilities
   */
  optimizeAnimations() {
    const animatedElements = document.querySelectorAll('[data-animate]');
    
    animatedElements.forEach(element => {
      if (this.prefersReducedMotion) {
        this.disableAnimation(element);
      } else if (this.isLowEndDevice) {
        this.simplifyAnimation(element);
      } else {
        this.enableAnimation(element);
      }
    });
  }

  /**
   * Disable animation completely
   */
  disableAnimation(element) {
    element.style.animation = 'none';
    element.style.transition = 'none';
    element.classList.add('no-animation');
  }

  /**
   * Simplify animation for low-end devices
   */
  simplifyAnimation(element) {
    // Reduce animation duration
    const currentDuration = parseFloat(getComputedStyle(element).animationDuration) || 1;
    element.style.animationDuration = `${currentDuration * 0.5}s`;
    
    // Reduce transition duration
    const currentTransition = parseFloat(getComputedStyle(element).transitionDuration) || 0.3;
    element.style.transitionDuration = `${currentTransition * 0.5}s`;
    
    // Remove complex effects
    element.classList.add('simplified-animation');
  }

  /**
   * Enable full animation
   */
  enableAnimation(element) {
    element.classList.remove('no-animation', 'simplified-animation');
    
    // Use GPU acceleration
    if (this.hasGPU) {
      element.style.willChange = 'transform, opacity';
    }
  }

  /**
   * Throttle animation frame updates
   */
  throttleAnimation(callback, fps = 60) {
    const interval = 1000 / fps;
    let lastTime = 0;

    return (currentTime) => {
      if (currentTime - lastTime >= interval) {
        lastTime = currentTime;
        callback(currentTime);
      }
    };
  }

  /**
   * Request animation frame with fallback
   */
  requestAnimationFrame(callback) {
    this.animationFrameId = window.requestAnimationFrame(callback);
    return this.animationFrameId;
  }

  /**
   * Cancel animation frame
   */
  cancelAnimationFrame() {
    if (this.animationFrameId) {
      window.cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  /**
   * Batch DOM reads and writes
   */
  batchDOMOperations(reads, writes) {
    // Perform all reads first
    const readResults = reads.map(read => read());
    
    // Then perform all writes
    requestAnimationFrame(() => {
      writes.forEach((write, index) => {
        write(readResults[index]);
      });
    });
  }

  /**
   * Debounce function for performance
   */
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  /**
   * Optimize particle effects
   */
  optimizeParticles(particleSystem) {
    if (this.isLowEndDevice) {
      // Reduce particle count
      particleSystem.maxParticles = Math.floor(particleSystem.maxParticles * 0.3);
    } else if (!this.hasGPU) {
      // Reduce particle count for devices without GPU
      particleSystem.maxParticles = Math.floor(particleSystem.maxParticles * 0.5);
    }
    
    if (this.prefersReducedMotion) {
      // Disable particles completely
      particleSystem.maxParticles = 0;
    }
  }

  /**
   * Optimize blur effects
   */
  optimizeBlur(element) {
    if (this.isLowEndDevice) {
      // Reduce blur amount
      const currentBlur = parseFloat(getComputedStyle(element).backdropFilter) || 10;
      element.style.backdropFilter = `blur(${Math.max(currentBlur * 0.5, 2)}px)`;
    }
    
    if (this.prefersReducedMotion) {
      // Remove blur completely
      element.style.backdropFilter = 'none';
    }
  }

  /**
   * Optimize shadow effects
   */
  optimizeShadow(element) {
    if (this.isLowEndDevice) {
      // Simplify shadows
      element.style.boxShadow = 'none';
      element.style.filter = 'none';
    }
  }

  /**
   * Monitor performance
   */
  monitorPerformance() {
    if (!window.performance || !window.performance.now) {
      return;
    }

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

        // Adjust quality if FPS drops
        if (fps < 30) {
          console.warn('Low FPS detected:', fps);
          this.reduceQuality();
        } else if (fps >= 55 && this.isLowEndDevice) {
          console.log('Good FPS, can increase quality:', fps);
        }
      }

      requestAnimationFrame(measureFPS);
    };

    measureFPS();
  }

  /**
   * Reduce quality when performance drops
   */
  reduceQuality() {
    // Disable heavy effects
    const heavyEffects = document.querySelectorAll('.particle-effect, .blur-effect, .glow-effect');
    heavyEffects.forEach(element => {
      element.style.display = 'none';
    });

    // Simplify remaining animations
    const animatedElements = document.querySelectorAll('[data-animate]');
    animatedElements.forEach(element => {
      this.simplifyAnimation(element);
    });
  }

  /**
   * Get optimization recommendations
   */
  getRecommendations() {
    const recommendations = [];

    if (this.isLowEndDevice) {
      recommendations.push('Reduce particle count');
      recommendations.push('Simplify animations');
      recommendations.push('Remove blur effects');
    }

    if (!this.hasGPU) {
      recommendations.push('Avoid 3D transforms');
      recommendations.push('Use CSS animations over JS');
    }

    if (this.prefersReducedMotion) {
      recommendations.push('Disable all animations');
      recommendations.push('Use instant transitions');
    }

    return recommendations;
  }
}

// Initialize on DOM ready
if (typeof window !== 'undefined') {
  window.VisualEffectsOptimizer = VisualEffectsOptimizer;
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.visualEffectsOptimizer = new VisualEffectsOptimizer();
      window.visualEffectsOptimizer.monitorPerformance();
    });
  } else {
    window.visualEffectsOptimizer = new VisualEffectsOptimizer();
    window.visualEffectsOptimizer.monitorPerformance();
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = VisualEffectsOptimizer;
}
