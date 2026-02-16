/**
 * Cursor Effects Module
 * Provides custom cursor trail, ripple effects on clicks, and glow effect
 * Disabled on mobile devices for performance
 */

class CursorEffects {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.trails = [];
    this.ripples = [];
    this.glowPosition = { x: 0, y: 0 };
    this.animationId = null;
    this.isRunning = false;
    this.isMobile = this.detectMobile();
    this.maxTrails = 20;
    this.maxRipples = 5;
  }

  /**
   * Detect if device is mobile
   * @returns {boolean} True if mobile device
   */
  detectMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
           window.matchMedia('(max-width: 768px)').matches ||
           ('ontouchstart' in window);
  }

  /**
   * Initialize cursor effects
   */
  init() {
    // Skip on mobile devices
    if (this.isMobile) {
      console.log('Cursor effects disabled on mobile devices');
      return;
    }

    // Check for reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      console.log('Cursor effects disabled due to prefers-reduced-motion');
      return;
    }

    // Create canvas element
    this.canvas = document.createElement('canvas');
    this.canvas.id = 'cursor-effects-canvas';
    this.canvas.style.position = 'fixed';
    this.canvas.style.top = '0';
    this.canvas.style.left = '0';
    this.canvas.style.width = '100%';
    this.canvas.style.height = '100%';
    this.canvas.style.pointerEvents = 'none';
    this.canvas.style.zIndex = '9999';
    this.canvas.setAttribute('aria-hidden', 'true');

    document.body.appendChild(this.canvas);

    this.ctx = this.canvas.getContext('2d');
    this.resize();

    // Event listeners
    window.addEventListener('resize', () => this.resize());
    document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    document.addEventListener('click', (e) => this.handleClick(e));

    this.isRunning = true;
    this.animate();
  }

  /**
   * Resize canvas to match window size
   */
  resize() {
    if (!this.canvas) return;
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  /**
   * Handle mouse move event
   * @param {MouseEvent} e - Mouse event
   */
  handleMouseMove(e) {
    if (!this.isRunning) return;

    // Update glow position
    this.glowPosition.x = e.clientX;
    this.glowPosition.y = e.clientY;

    // Add trail particle
    this.addTrail(e.clientX, e.clientY);
  }

  /**
   * Handle click event
   * @param {MouseEvent} e - Mouse event
   */
  handleClick(e) {
    if (!this.isRunning) return;

    // Create ripple effect
    this.addRipple(e.clientX, e.clientY);
  }

  /**
   * Add cursor trail particle
   * @param {number} x - X position
   * @param {number} y - Y position
   */
  addTrail(x, y) {
    // Limit number of trail particles
    if (this.trails.length >= this.maxTrails) {
      this.trails.shift();
    }

    this.trails.push({
      x: x,
      y: y,
      size: 8,
      opacity: 1,
      decay: 0.05,
      color: this.getTrailColor()
    });
  }

  /**
   * Add ripple effect
   * @param {number} x - X position
   * @param {number} y - Y position
   */
  addRipple(x, y) {
    // Limit number of ripples
    if (this.ripples.length >= this.maxRipples) {
      this.ripples.shift();
    }

    this.ripples.push({
      x: x,
      y: y,
      radius: 0,
      maxRadius: 80,
      opacity: 0.8,
      speed: 3,
      decay: 0.02,
      color: this.getRippleColor()
    });
  }

  /**
   * Get trail color based on theme
   * @returns {string} RGB color string
   */
  getTrailColor() {
    const isDarkMode = document.body.classList.contains('dark-mode');
    if (isDarkMode) {
      return 'rgba(100, 200, 255, ';
    }
    return 'rgba(100, 100, 255, ';
  }

  /**
   * Get ripple color based on theme
   * @returns {string} RGB color string
   */
  getRippleColor() {
    const isDarkMode = document.body.classList.contains('dark-mode');
    if (isDarkMode) {
      return 'rgba(150, 220, 255, ';
    }
    return 'rgba(100, 150, 255, ';
  }

  /**
   * Update trail particles
   */
  updateTrails() {
    for (let i = this.trails.length - 1; i >= 0; i--) {
      const trail = this.trails[i];
      
      // Fade out
      trail.opacity -= trail.decay;
      trail.size *= 0.95;

      // Remove dead trails
      if (trail.opacity <= 0 || trail.size < 1) {
        this.trails.splice(i, 1);
      }
    }
  }

  /**
   * Update ripples
   */
  updateRipples() {
    for (let i = this.ripples.length - 1; i >= 0; i--) {
      const ripple = this.ripples[i];
      
      // Expand ripple
      ripple.radius += ripple.speed;
      
      // Fade out
      ripple.opacity -= ripple.decay;

      // Remove dead ripples
      if (ripple.radius >= ripple.maxRadius || ripple.opacity <= 0) {
        this.ripples.splice(i, 1);
      }
    }
  }

  /**
   * Draw cursor trail
   */
  drawTrails() {
    if (!this.ctx) return;

    for (let i = 0; i < this.trails.length; i++) {
      const trail = this.trails[i];
      
      this.ctx.save();
      this.ctx.globalAlpha = trail.opacity;
      
      // Draw trail particle with gradient
      const gradient = this.ctx.createRadialGradient(
        trail.x, trail.y, 0,
        trail.x, trail.y, trail.size
      );
      gradient.addColorStop(0, trail.color + trail.opacity + ')');
      gradient.addColorStop(0.5, trail.color + (trail.opacity * 0.5) + ')');
      gradient.addColorStop(1, trail.color + '0)');
      
      this.ctx.fillStyle = gradient;
      this.ctx.beginPath();
      this.ctx.arc(trail.x, trail.y, trail.size, 0, Math.PI * 2);
      this.ctx.fill();
      
      this.ctx.restore();
    }
  }

  /**
   * Draw ripple effects
   */
  drawRipples() {
    if (!this.ctx) return;

    for (const ripple of this.ripples) {
      this.ctx.save();
      this.ctx.globalAlpha = ripple.opacity;
      
      // Draw ripple ring
      this.ctx.strokeStyle = ripple.color + ripple.opacity + ')';
      this.ctx.lineWidth = 3;
      this.ctx.beginPath();
      this.ctx.arc(ripple.x, ripple.y, ripple.radius, 0, Math.PI * 2);
      this.ctx.stroke();
      
      // Draw inner glow
      const gradient = this.ctx.createRadialGradient(
        ripple.x, ripple.y, ripple.radius * 0.8,
        ripple.x, ripple.y, ripple.radius
      );
      gradient.addColorStop(0, ripple.color + '0)');
      gradient.addColorStop(1, ripple.color + (ripple.opacity * 0.3) + ')');
      
      this.ctx.fillStyle = gradient;
      this.ctx.beginPath();
      this.ctx.arc(ripple.x, ripple.y, ripple.radius, 0, Math.PI * 2);
      this.ctx.fill();
      
      this.ctx.restore();
    }
  }

  /**
   * Draw cursor glow effect
   */
  drawGlow() {
    if (!this.ctx) return;

    const glowSize = 40;
    
    this.ctx.save();
    
    // Draw glow with radial gradient
    const gradient = this.ctx.createRadialGradient(
      this.glowPosition.x, this.glowPosition.y, 0,
      this.glowPosition.x, this.glowPosition.y, glowSize
    );
    
    const isDarkMode = document.body.classList.contains('dark-mode');
    const glowColor = isDarkMode ? 'rgba(150, 220, 255, ' : 'rgba(100, 150, 255, ';
    
    gradient.addColorStop(0, glowColor + '0.3)');
    gradient.addColorStop(0.5, glowColor + '0.1)');
    gradient.addColorStop(1, glowColor + '0)');
    
    this.ctx.fillStyle = gradient;
    this.ctx.beginPath();
    this.ctx.arc(this.glowPosition.x, this.glowPosition.y, glowSize, 0, Math.PI * 2);
    this.ctx.fill();
    
    this.ctx.restore();
  }

  /**
   * Update all effects
   */
  update() {
    this.updateTrails();
    this.updateRipples();
  }

  /**
   * Draw all effects
   */
  draw() {
    if (!this.ctx) return;

    // Clear canvas
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw effects in order
    this.drawGlow();
    this.drawTrails();
    this.drawRipples();
  }

  /**
   * Animation loop
   */
  animate() {
    if (!this.isRunning) return;

    this.update();
    this.draw();

    this.animationId = requestAnimationFrame(() => this.animate());
  }

  /**
   * Stop cursor effects
   */
  stop() {
    this.isRunning = false;
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  /**
   * Clear all effects
   */
  clear() {
    this.trails = [];
    this.ripples = [];
  }

  /**
   * Destroy cursor effects
   */
  destroy() {
    this.stop();
    this.clear();
    
    // Remove event listeners
    document.removeEventListener('mousemove', this.handleMouseMove);
    document.removeEventListener('click', this.handleClick);
    window.removeEventListener('resize', this.resize);
    
    if (this.canvas && this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
    this.canvas = null;
    this.ctx = null;
  }
}

// Global cursor effects instance
let cursorEffects = null;

/**
 * Initialize cursor effects on page load
 */
function initCursorEffects() {
  // Check if already initialized
  if (cursorEffects) {
    return;
  }

  cursorEffects = new CursorEffects();
  cursorEffects.init();

  // Store reference on canvas for testing
  if (cursorEffects.canvas) {
    cursorEffects.canvas.__cursorEffects = cursorEffects;
  }
}

/**
 * Stop cursor effects
 */
function stopCursorEffects() {
  if (cursorEffects) {
    cursorEffects.stop();
  }
}

/**
 * Clear all cursor effects
 */
function clearCursorEffects() {
  if (cursorEffects) {
    cursorEffects.clear();
  }
}

// Initialize on DOM content loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCursorEffects);
} else {
  initCursorEffects();
}

// Export functions for use in other modules
if (typeof window !== 'undefined') {
  window.cursorEffects = cursorEffects;
  window.initCursorEffects = initCursorEffects;
  window.stopCursorEffects = stopCursorEffects;
  window.clearCursorEffects = clearCursorEffects;
}
