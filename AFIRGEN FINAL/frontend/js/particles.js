/**
 * Particle Effects Module
 * Provides particle system for page load, floating background particles, and confetti effects
 */

class ParticleSystem {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.particles = [];
    this.animationId = null;
    this.isRunning = false;
    this.particleTypes = {
      FLOAT: 'float',
      CONFETTI: 'confetti',
      LOAD: 'load'
    };
  }

  /**
   * Initialize particle canvas
   */
  init() {
    // Create canvas element
    this.canvas = document.createElement('canvas');
    this.canvas.id = 'particle-canvas';
    this.canvas.style.position = 'fixed';
    this.canvas.style.top = '0';
    this.canvas.style.left = '0';
    this.canvas.style.width = '100%';
    this.canvas.style.height = '100%';
    this.canvas.style.pointerEvents = 'none';
    this.canvas.style.zIndex = '1';
    this.canvas.setAttribute('aria-hidden', 'true');

    // Insert canvas after body::before
    document.body.insertBefore(this.canvas, document.body.firstChild);

    this.ctx = this.canvas.getContext('2d');
    this.resize();

    // Handle window resize
    window.addEventListener('resize', () => this.resize());

    // Check for reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      console.log('Particle effects disabled due to prefers-reduced-motion');
      return;
    }

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
   * Create floating background particles
   * @param {number} count - Number of particles to create
   */
  createFloatingParticles(count = 50) {
    for (let i = 0; i < count; i++) {
      this.particles.push({
        type: this.particleTypes.FLOAT,
        x: Math.random() * this.canvas.width,
        y: Math.random() * this.canvas.height,
        size: Math.random() * 3 + 1,
        speedX: (Math.random() - 0.5) * 0.5,
        speedY: (Math.random() - 0.5) * 0.5,
        opacity: Math.random() * 0.5 + 0.2,
        color: this.getRandomColor(),
        life: Infinity
      });
    }
  }

  /**
   * Create page load particles (burst effect)
   * @param {number} count - Number of particles to create
   */
  createLoadParticles(count = 100) {
    const centerX = this.canvas.width / 2;
    const centerY = this.canvas.height / 2;

    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 * i) / count;
      const speed = Math.random() * 3 + 2;

      this.particles.push({
        type: this.particleTypes.LOAD,
        x: centerX,
        y: centerY,
        size: Math.random() * 4 + 2,
        speedX: Math.cos(angle) * speed,
        speedY: Math.sin(angle) * speed,
        opacity: 1,
        color: this.getRandomColor(),
        life: 120, // frames
        decay: 0.01
      });
    }
  }

  /**
   * Create confetti effect for success actions
   * @param {number} x - X position (default: center)
   * @param {number} y - Y position (default: top)
   * @param {number} count - Number of confetti pieces
   */
  createConfetti(x = null, y = null, count = 150) {
    const startX = x !== null ? x : this.canvas.width / 2;
    const startY = y !== null ? y : 0;

    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 8 + 4;
      const size = Math.random() * 8 + 4;

      this.particles.push({
        type: this.particleTypes.CONFETTI,
        x: startX + (Math.random() - 0.5) * 100,
        y: startY,
        size: size,
        speedX: Math.cos(angle) * speed,
        speedY: Math.sin(angle) * speed - 5, // Initial upward velocity
        opacity: 1,
        color: this.getRandomConfettiColor(),
        rotation: Math.random() * 360,
        rotationSpeed: (Math.random() - 0.5) * 10,
        gravity: 0.3,
        life: 180, // frames
        decay: 0.005,
        shape: Math.random() > 0.5 ? 'rect' : 'circle'
      });
    }
  }

  /**
   * Get random color for particles
   * @returns {string} RGB color string
   */
  getRandomColor() {
    const colors = [
      'rgba(100, 100, 255, ',
      'rgba(100, 255, 255, ',
      'rgba(255, 100, 255, ',
      'rgba(255, 255, 100, '
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  }

  /**
   * Get random confetti color
   * @returns {string} RGB color string
   */
  getRandomConfettiColor() {
    const colors = [
      'rgba(255, 87, 87, ',   // Red
      'rgba(255, 195, 0, ',   // Yellow
      'rgba(0, 230, 118, ',   // Green
      'rgba(0, 184, 255, ',   // Blue
      'rgba(255, 0, 255, ',   // Magenta
      'rgba(255, 128, 0, '    // Orange
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  }

  /**
   * Update particle positions and properties
   */
  update() {
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];

      // Update position
      p.x += p.speedX;
      p.y += p.speedY;

      // Apply gravity for confetti
      if (p.type === this.particleTypes.CONFETTI && p.gravity) {
        p.speedY += p.gravity;
        p.rotation += p.rotationSpeed;
      }

      // Update opacity
      if (p.decay) {
        p.opacity -= p.decay;
      }

      // Decrease life
      if (p.life !== Infinity) {
        p.life--;
      }

      // Wrap floating particles around screen
      if (p.type === this.particleTypes.FLOAT) {
        if (p.x < 0) p.x = this.canvas.width;
        if (p.x > this.canvas.width) p.x = 0;
        if (p.y < 0) p.y = this.canvas.height;
        if (p.y > this.canvas.height) p.y = 0;
      }

      // Remove dead particles
      if (p.life <= 0 || p.opacity <= 0 || 
          (p.type !== this.particleTypes.FLOAT && 
           (p.y > this.canvas.height + 50 || p.x < -50 || p.x > this.canvas.width + 50))) {
        this.particles.splice(i, 1);
      }
    }
  }

  /**
   * Draw particles on canvas
   */
  draw() {
    if (!this.ctx) return;

    // Clear canvas
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw each particle
    for (const p of this.particles) {
      this.ctx.save();

      // Set opacity
      this.ctx.globalAlpha = p.opacity;

      if (p.type === this.particleTypes.CONFETTI) {
        // Draw confetti with rotation
        this.ctx.translate(p.x, p.y);
        this.ctx.rotate((p.rotation * Math.PI) / 180);

        if (p.shape === 'rect') {
          this.ctx.fillStyle = p.color + p.opacity + ')';
          this.ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
        } else {
          this.ctx.fillStyle = p.color + p.opacity + ')';
          this.ctx.beginPath();
          this.ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
          this.ctx.fill();
        }
      } else {
        // Draw regular particles (circles)
        this.ctx.fillStyle = p.color + p.opacity + ')';
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        this.ctx.fill();
      }

      this.ctx.restore();
    }
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
   * Stop particle system
   */
  stop() {
    this.isRunning = false;
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  /**
   * Clear all particles
   */
  clear() {
    this.particles = [];
  }

  /**
   * Destroy particle system
   */
  destroy() {
    this.stop();
    this.clear();
    if (this.canvas && this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
    this.canvas = null;
    this.ctx = null;
  }
}

// Global particle system instance
let particleSystem = null;

/**
 * Initialize particle system on page load
 */
function initParticles() {
  // Check if already initialized
  if (particleSystem) {
    return;
  }

  // Check for reduced motion preference
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) {
    console.log('Particle effects disabled due to prefers-reduced-motion');
    return;
  }

  particleSystem = new ParticleSystem();
  particleSystem.init();

  // Store reference on canvas for testing
  if (particleSystem.canvas) {
    particleSystem.canvas.__particleSystem = particleSystem;
  }

  // Create page load burst effect
  particleSystem.createLoadParticles(80);

  // After load animation, add floating particles
  setTimeout(() => {
    particleSystem.createFloatingParticles(30);
  }, 2000);
}

/**
 * Show confetti effect
 * @param {number} x - X position (optional)
 * @param {number} y - Y position (optional)
 */
function showConfetti(x = null, y = null) {
  if (!particleSystem) {
    initParticles();
  }

  if (particleSystem) {
    particleSystem.createConfetti(x, y, 150);
  }
}

/**
 * Stop particle effects
 */
function stopParticles() {
  if (particleSystem) {
    particleSystem.stop();
  }
}

/**
 * Clear all particles
 */
function clearParticles() {
  if (particleSystem) {
    particleSystem.clear();
  }
}

// Initialize on DOM content loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initParticles);
} else {
  initParticles();
}

// Export functions for use in other modules
if (typeof window !== 'undefined') {
  window.particleSystem = particleSystem;
  window.initParticles = initParticles;
  window.showConfetti = showConfetti;
  window.stopParticles = stopParticles;
  window.clearParticles = clearParticles;
}
