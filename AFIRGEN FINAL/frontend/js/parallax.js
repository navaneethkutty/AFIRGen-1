/**
 * Parallax Scrolling Module
 * Provides smooth parallax scrolling effects for hero section and background elements
 * Optimized for 60fps performance
 */

class ParallaxEffect {
  constructor() {
    this.layers = [];
    this.isRunning = false;
    this.ticking = false;
    this.scrollY = 0;
    this.prefersReducedMotion = false;
  }

  /**
   * Initialize parallax effect
   */
  init() {
    // Check for reduced motion preference
    this.prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    if (this.prefersReducedMotion) {
      console.log('Parallax effects disabled due to prefers-reduced-motion');
      return;
    }

    // Create parallax layers
    this.createLayers();

    // Set up scroll listener with requestAnimationFrame for smooth 60fps
    window.addEventListener('scroll', () => this.onScroll(), { passive: true });

    // Handle window resize
    window.addEventListener('resize', () => this.onResize());

    this.isRunning = true;
    
    // Initial update
    this.update();
  }

  /**
   * Create depth layers for parallax effect
   */
  createLayers() {
    const heroSection = document.querySelector('.hero-section');
    if (!heroSection) return;

    // Create background layers container
    const layersContainer = document.createElement('div');
    layersContainer.className = 'parallax-layers';
    layersContainer.setAttribute('aria-hidden', 'true');
    
    // Insert at the beginning of hero section
    heroSection.insertBefore(layersContainer, heroSection.firstChild);

    // Create 3 depth layers with different speeds
    const layerConfigs = [
      { depth: 1, speed: 0.1, opacity: 0.15, size: 'large' },
      { depth: 2, speed: 0.25, opacity: 0.2, size: 'medium' },
      { depth: 3, speed: 0.4, opacity: 0.25, size: 'small' }
    ];

    layerConfigs.forEach(config => {
      const layer = this.createLayer(config);
      layersContainer.appendChild(layer);
      
      this.layers.push({
        element: layer,
        speed: config.speed,
        depth: config.depth
      });
    });
  }

  /**
   * Create a single parallax layer
   * @param {Object} config - Layer configuration
   * @returns {HTMLElement} Layer element
   */
  createLayer(config) {
    const layer = document.createElement('div');
    layer.className = `parallax-layer parallax-layer-${config.depth}`;
    layer.style.opacity = config.opacity;
    
    // Add decorative shapes to the layer
    const shapeCount = config.size === 'large' ? 3 : config.size === 'medium' ? 5 : 8;
    
    for (let i = 0; i < shapeCount; i++) {
      const shape = document.createElement('div');
      shape.className = 'parallax-shape';
      
      // Random positioning
      shape.style.left = `${Math.random() * 100}%`;
      shape.style.top = `${Math.random() * 100}%`;
      
      // Random size based on layer
      const baseSize = config.size === 'large' ? 200 : config.size === 'medium' ? 120 : 60;
      const size = baseSize + Math.random() * 100;
      shape.style.width = `${size}px`;
      shape.style.height = `${size}px`;
      
      // Random shape type
      const shapeType = Math.random();
      if (shapeType < 0.33) {
        shape.style.borderRadius = '50%'; // Circle
      } else if (shapeType < 0.66) {
        shape.style.borderRadius = '20%'; // Rounded square
      } else {
        shape.style.borderRadius = '0'; // Square
        shape.style.transform = `rotate(${Math.random() * 45}deg)`;
      }
      
      layer.appendChild(shape);
    }
    
    return layer;
  }

  /**
   * Handle scroll event
   */
  onScroll() {
    this.scrollY = window.pageYOffset || document.documentElement.scrollTop;
    
    if (!this.ticking) {
      requestAnimationFrame(() => this.update());
      this.ticking = true;
    }
  }

  /**
   * Handle resize event
   */
  onResize() {
    if (!this.ticking) {
      requestAnimationFrame(() => this.update());
      this.ticking = true;
    }
  }

  /**
   * Update parallax layer positions
   */
  update() {
    if (!this.isRunning || this.prefersReducedMotion) {
      this.ticking = false;
      return;
    }

    // Update each layer based on scroll position and speed
    this.layers.forEach(layer => {
      const offset = this.scrollY * layer.speed;
      
      // Use transform for GPU acceleration
      layer.element.style.transform = `translate3d(0, ${offset}px, 0)`;
    });

    this.ticking = false;
  }

  /**
   * Stop parallax effect
   */
  stop() {
    this.isRunning = false;
  }

  /**
   * Start parallax effect
   */
  start() {
    if (this.prefersReducedMotion) return;
    this.isRunning = true;
    this.update();
  }

  /**
   * Destroy parallax effect
   */
  destroy() {
    this.stop();
    
    // Remove layers
    const layersContainer = document.querySelector('.parallax-layers');
    if (layersContainer && layersContainer.parentNode) {
      layersContainer.parentNode.removeChild(layersContainer);
    }
    
    this.layers = [];
  }
}

// Global parallax instance
let parallaxEffect = null;

/**
 * Initialize parallax effect on page load
 */
function initParallax() {
  // Check if already initialized
  if (parallaxEffect) {
    return;
  }

  // Check for reduced motion preference
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) {
    console.log('Parallax effects disabled due to prefers-reduced-motion');
    return;
  }

  parallaxEffect = new ParallaxEffect();
  parallaxEffect.init();
}

/**
 * Stop parallax effect
 */
function stopParallax() {
  if (parallaxEffect) {
    parallaxEffect.stop();
  }
}

/**
 * Start parallax effect
 */
function startParallax() {
  if (parallaxEffect) {
    parallaxEffect.start();
  }
}

/**
 * Destroy parallax effect
 */
function destroyParallax() {
  if (parallaxEffect) {
    parallaxEffect.destroy();
    parallaxEffect = null;
  }
}

// Initialize on DOM content loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initParallax);
} else {
  initParallax();
}

// Export functions for use in other modules
if (typeof window !== 'undefined') {
  window.parallaxEffect = parallaxEffect;
  window.initParallax = initParallax;
  window.stopParallax = stopParallax;
  window.startParallax = startParallax;
  window.destroyParallax = destroyParallax;
}
