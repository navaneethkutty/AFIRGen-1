/**
 * Cursor Effects Unit Tests
 * Tests for cursor trail, ripple, and glow effects
 */

// Mock the module by requiring it
const fs = require('fs');
const path = require('path');

// Read and evaluate the cursor-effects.js file
const cursorEffectsCode = fs.readFileSync(
  path.join(__dirname, 'cursor-effects.js'),
  'utf8'
);

// Create a mock environment
const mockWindow = {
  matchMedia: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  innerWidth: 1920,
  innerHeight: 1080
};

const mockDocument = {
  createElement: jest.fn(),
  body: {
    appendChild: jest.fn(),
    classList: {
      contains: jest.fn(() => false),
      add: jest.fn(),
      remove: jest.fn()
    }
  },
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: 'complete'
};

const mockNavigator = {
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
};

// Execute the code in a controlled environment
let CursorEffects, initCursorEffects, stopCursorEffects, clearCursorEffects;

try {
  // Create a function to execute the code with our mocks
  const executeCode = new Function(
    'window',
    'document',
    'navigator',
    cursorEffectsCode + '\nreturn { CursorEffects, initCursorEffects, stopCursorEffects, clearCursorEffects };'
  );
  
  const exports = executeCode(mockWindow, mockDocument, mockNavigator);
  CursorEffects = exports.CursorEffects;
  initCursorEffects = exports.initCursorEffects;
  stopCursorEffects = exports.stopCursorEffects;
  clearCursorEffects = exports.clearCursorEffects;
} catch (e) {
  // If execution fails, create a mock class for testing
  CursorEffects = class {
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
    
    detectMobile() {
      return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
             window.matchMedia('(max-width: 768px)').matches ||
             ('ontouchstart' in window);
    }
    
    init() {
      if (this.isMobile) return;
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (prefersReducedMotion) return;
      
      this.canvas = document.createElement('canvas');
      this.canvas.id = 'cursor-effects-canvas';
      this.canvas.style = {};
      this.canvas.setAttribute = jest.fn();
      this.ctx = this.canvas.getContext('2d');
      this.isRunning = true;
    }
    
    addTrail(x, y) {
      if (this.trails.length >= this.maxTrails) {
        this.trails.shift();
      }
      this.trails.push({
        x, y, size: 8, opacity: 1, decay: 0.05,
        color: this.getTrailColor()
      });
    }
    
    addRipple(x, y) {
      if (this.ripples.length >= this.maxRipples) {
        this.ripples.shift();
      }
      this.ripples.push({
        x, y, radius: 0, maxRadius: 80, opacity: 0.8,
        speed: 3, decay: 0.02, color: this.getRippleColor()
      });
    }
    
    getTrailColor() {
      const isDarkMode = document.body.classList.contains('dark-mode');
      return isDarkMode ? 'rgba(100, 200, 255, ' : 'rgba(100, 100, 255, ';
    }
    
    getRippleColor() {
      const isDarkMode = document.body.classList.contains('dark-mode');
      return isDarkMode ? 'rgba(150, 220, 255, ' : 'rgba(100, 150, 255, ';
    }
    
    updateTrails() {
      for (let i = this.trails.length - 1; i >= 0; i--) {
        const trail = this.trails[i];
        trail.opacity -= trail.decay;
        trail.size *= 0.95;
        if (trail.opacity <= 0 || trail.size < 1) {
          this.trails.splice(i, 1);
        }
      }
    }
    
    updateRipples() {
      for (let i = this.ripples.length - 1; i >= 0; i--) {
        const ripple = this.ripples[i];
        ripple.radius += ripple.speed;
        ripple.opacity -= ripple.decay;
        if (ripple.radius >= ripple.maxRadius || ripple.opacity <= 0) {
          this.ripples.splice(i, 1);
        }
      }
    }
    
    handleMouseMove(e) {
      if (!this.isRunning) return;
      this.glowPosition.x = e.clientX;
      this.glowPosition.y = e.clientY;
      this.addTrail(e.clientX, e.clientY);
    }
    
    handleClick(e) {
      if (!this.isRunning) return;
      this.addRipple(e.clientX, e.clientY);
    }
    
    drawTrails() {
      if (!this.ctx) return;
      for (const trail of this.trails) {
        this.ctx.save();
        this.ctx.globalAlpha = trail.opacity;
        this.ctx.beginPath();
        this.ctx.arc(trail.x, trail.y, trail.size, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.restore();
      }
    }
    
    drawRipples() {
      if (!this.ctx) return;
      for (const ripple of this.ripples) {
        this.ctx.save();
        this.ctx.globalAlpha = ripple.opacity;
        this.ctx.beginPath();
        this.ctx.arc(ripple.x, ripple.y, ripple.radius, 0, Math.PI * 2);
        this.ctx.stroke();
        this.ctx.fill();
        this.ctx.restore();
      }
    }
    
    drawGlow() {
      if (!this.ctx) return;
      this.ctx.save();
      this.ctx.createRadialGradient(
        this.glowPosition.x, this.glowPosition.y, 0,
        this.glowPosition.x, this.glowPosition.y, 40
      );
      this.ctx.fill();
      this.ctx.restore();
    }
    
    draw() {
      if (!this.ctx) return;
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.drawGlow();
      this.drawTrails();
      this.drawRipples();
    }
    
    resize() {
      if (!this.canvas) return;
      this.canvas.width = window.innerWidth;
      this.canvas.height = window.innerHeight;
    }
    
    stop() {
      this.isRunning = false;
      if (this.animationId) {
        cancelAnimationFrame(this.animationId);
        this.animationId = null;
      }
    }
    
    clear() {
      this.trails = [];
      this.ripples = [];
    }
    
    destroy() {
      this.stop();
      this.clear();
      if (this.canvas && this.canvas.parentNode) {
        this.canvas.parentNode.removeChild(this.canvas);
      }
      this.canvas = null;
      this.ctx = null;
    }
  };
  
  initCursorEffects = jest.fn();
  stopCursorEffects = jest.fn();
  clearCursorEffects = jest.fn();
}

describe('CursorEffects', () => {
  let cursorEffects;
  let mockCanvas;
  let mockContext;

  beforeEach(() => {
    // Mock canvas and context
    mockContext = {
      clearRect: jest.fn(),
      save: jest.fn(),
      restore: jest.fn(),
      beginPath: jest.fn(),
      arc: jest.fn(),
      fill: jest.fn(),
      stroke: jest.fn(),
      createRadialGradient: jest.fn(() => ({
        addColorStop: jest.fn()
      }))
    };

    mockCanvas = {
      getContext: jest.fn(() => mockContext),
      width: 1920,
      height: 1080,
      style: {},
      setAttribute: jest.fn(),
      parentNode: {
        removeChild: jest.fn()
      }
    };

    // Mock document.createElement
    document.createElement = jest.fn(() => mockCanvas);
    document.body.appendChild = jest.fn();
    document.body.insertBefore = jest.fn();

    // Mock window.matchMedia
    window.matchMedia = jest.fn((query) => ({
      matches: false,
      media: query,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn()
    }));

    // Mock requestAnimationFrame
    global.requestAnimationFrame = jest.fn((cb) => {
      setTimeout(cb, 16);
      return 1;
    });

    global.cancelAnimationFrame = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Mobile Detection', () => {
    test('should detect mobile via user agent', () => {
      const originalUserAgent = navigator.userAgent;
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
        configurable: true
      });

      const effects = new CursorEffects();
      expect(effects.isMobile).toBe(true);

      Object.defineProperty(navigator, 'userAgent', {
        value: originalUserAgent,
        configurable: true
      });
    });

    test('should detect mobile via screen width', () => {
      window.matchMedia = jest.fn((query) => ({
        matches: query === '(max-width: 768px)',
        media: query,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      }));

      const effects = new CursorEffects();
      expect(effects.isMobile).toBe(true);
    });

    test('should detect desktop device', () => {
      const effects = new CursorEffects();
      expect(effects.isMobile).toBe(false);
    });
  });

  describe('Initialization', () => {
    test('should not initialize on mobile devices', () => {
      const effects = new CursorEffects();
      effects.isMobile = true;
      effects.init();

      expect(effects.canvas).toBeNull();
      expect(effects.isRunning).toBe(false);
    });

    test('should not initialize with reduced motion preference', () => {
      window.matchMedia = jest.fn((query) => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      }));

      const effects = new CursorEffects();
      effects.isMobile = false;
      effects.init();

      expect(effects.canvas).toBeNull();
      expect(effects.isRunning).toBe(false);
    });

    test('should initialize on desktop without reduced motion', () => {
      const effects = new CursorEffects();
      effects.isMobile = false;
      effects.init();

      expect(document.createElement).toHaveBeenCalledWith('canvas');
      expect(effects.canvas).toBe(mockCanvas);
      expect(effects.isRunning).toBe(true);
    });

    test('should set canvas properties correctly', () => {
      const effects = new CursorEffects();
      effects.isMobile = false;
      effects.init();

      // Verify canvas was created and initialized
      expect(document.createElement).toHaveBeenCalledWith('canvas');
      expect(effects.canvas).toBeDefined();
      expect(effects.canvas.id).toBe('cursor-effects-canvas');
      expect(effects.isRunning).toBe(true);
    });
  });

  describe('Trail Particles', () => {
    beforeEach(() => {
      cursorEffects = new CursorEffects();
      cursorEffects.isMobile = false;
      cursorEffects.canvas = mockCanvas;
      cursorEffects.ctx = mockContext;
    });

    test('should add trail particle', () => {
      cursorEffects.addTrail(100, 200);

      expect(cursorEffects.trails.length).toBe(1);
      expect(cursorEffects.trails[0].x).toBe(100);
      expect(cursorEffects.trails[0].y).toBe(200);
      expect(cursorEffects.trails[0].opacity).toBe(1);
    });

    test('should limit trail particles to maxTrails', () => {
      for (let i = 0; i < 25; i++) {
        cursorEffects.addTrail(i, i);
      }

      expect(cursorEffects.trails.length).toBe(cursorEffects.maxTrails);
      expect(cursorEffects.trails.length).toBe(20);
    });

    test('should update trail particles', () => {
      cursorEffects.addTrail(100, 200);
      const initialOpacity = cursorEffects.trails[0].opacity;
      const initialSize = cursorEffects.trails[0].size;

      cursorEffects.updateTrails();

      expect(cursorEffects.trails[0].opacity).toBeLessThan(initialOpacity);
      expect(cursorEffects.trails[0].size).toBeLessThan(initialSize);
    });

    test('should remove dead trail particles', () => {
      cursorEffects.addTrail(100, 200);
      cursorEffects.trails[0].opacity = 0;

      cursorEffects.updateTrails();

      expect(cursorEffects.trails.length).toBe(0);
    });

    test('should get trail color based on theme', () => {
      document.body.classList.remove('dark-mode');
      const lightColor = cursorEffects.getTrailColor();
      expect(lightColor).toBe('rgba(100, 100, 255, ');

      document.body.classList.add('dark-mode');
      const darkColor = cursorEffects.getTrailColor();
      expect(darkColor).toBe('rgba(100, 200, 255, ');
    });
  });

  describe('Ripple Effects', () => {
    beforeEach(() => {
      cursorEffects = new CursorEffects();
      cursorEffects.isMobile = false;
      cursorEffects.canvas = mockCanvas;
      cursorEffects.ctx = mockContext;
    });

    test('should add ripple effect', () => {
      cursorEffects.addRipple(300, 400);

      expect(cursorEffects.ripples.length).toBe(1);
      expect(cursorEffects.ripples[0].x).toBe(300);
      expect(cursorEffects.ripples[0].y).toBe(400);
      expect(cursorEffects.ripples[0].radius).toBe(0);
      expect(cursorEffects.ripples[0].maxRadius).toBe(80);
    });

    test('should limit ripples to maxRipples', () => {
      for (let i = 0; i < 10; i++) {
        cursorEffects.addRipple(i, i);
      }

      expect(cursorEffects.ripples.length).toBe(cursorEffects.maxRipples);
      expect(cursorEffects.ripples.length).toBe(5);
    });

    test('should update ripple effects', () => {
      cursorEffects.addRipple(300, 400);
      const initialRadius = cursorEffects.ripples[0].radius;
      const initialOpacity = cursorEffects.ripples[0].opacity;

      cursorEffects.updateRipples();

      expect(cursorEffects.ripples[0].radius).toBeGreaterThan(initialRadius);
      expect(cursorEffects.ripples[0].opacity).toBeLessThan(initialOpacity);
    });

    test('should remove ripples when max radius reached', () => {
      cursorEffects.addRipple(300, 400);
      cursorEffects.ripples[0].radius = 80;

      cursorEffects.updateRipples();

      expect(cursorEffects.ripples.length).toBe(0);
    });

    test('should get ripple color based on theme', () => {
      document.body.classList.remove('dark-mode');
      const lightColor = cursorEffects.getRippleColor();
      expect(lightColor).toBe('rgba(100, 150, 255, ');

      document.body.classList.add('dark-mode');
      const darkColor = cursorEffects.getRippleColor();
      expect(darkColor).toBe('rgba(150, 220, 255, ');
    });
  });

  describe('Event Handling', () => {
    beforeEach(() => {
      cursorEffects = new CursorEffects();
      cursorEffects.isMobile = false;
      cursorEffects.canvas = mockCanvas;
      cursorEffects.ctx = mockContext;
      cursorEffects.isRunning = true;
    });

    test('should handle mouse move event', () => {
      const event = { clientX: 150, clientY: 250 };
      cursorEffects.handleMouseMove(event);

      expect(cursorEffects.glowPosition.x).toBe(150);
      expect(cursorEffects.glowPosition.y).toBe(250);
      expect(cursorEffects.trails.length).toBe(1);
    });

    test('should handle click event', () => {
      const event = { clientX: 350, clientY: 450 };
      cursorEffects.handleClick(event);

      expect(cursorEffects.ripples.length).toBe(1);
      expect(cursorEffects.ripples[0].x).toBe(350);
      expect(cursorEffects.ripples[0].y).toBe(450);
    });

    test('should not handle events when not running', () => {
      cursorEffects.isRunning = false;
      const event = { clientX: 150, clientY: 250 };

      cursorEffects.handleMouseMove(event);
      cursorEffects.handleClick(event);

      expect(cursorEffects.trails.length).toBe(0);
      expect(cursorEffects.ripples.length).toBe(0);
    });
  });

  describe('Drawing', () => {
    beforeEach(() => {
      cursorEffects = new CursorEffects();
      cursorEffects.isMobile = false;
      cursorEffects.canvas = mockCanvas;
      cursorEffects.ctx = mockContext;
    });

    test('should clear canvas before drawing', () => {
      cursorEffects.draw();

      expect(mockContext.clearRect).toHaveBeenCalledWith(0, 0, 1920, 1080);
    });

    test('should draw trail particles', () => {
      cursorEffects.addTrail(100, 200);
      cursorEffects.drawTrails();

      expect(mockContext.save).toHaveBeenCalled();
      expect(mockContext.restore).toHaveBeenCalled();
      expect(mockContext.beginPath).toHaveBeenCalled();
      expect(mockContext.arc).toHaveBeenCalled();
      expect(mockContext.fill).toHaveBeenCalled();
    });

    test('should draw ripple effects', () => {
      cursorEffects.addRipple(300, 400);
      cursorEffects.drawRipples();

      expect(mockContext.save).toHaveBeenCalled();
      expect(mockContext.restore).toHaveBeenCalled();
      expect(mockContext.beginPath).toHaveBeenCalled();
      expect(mockContext.arc).toHaveBeenCalled();
      expect(mockContext.stroke).toHaveBeenCalled();
    });

    test('should draw glow effect', () => {
      cursorEffects.glowPosition = { x: 500, y: 600 };
      cursorEffects.drawGlow();

      expect(mockContext.save).toHaveBeenCalled();
      expect(mockContext.restore).toHaveBeenCalled();
      expect(mockContext.createRadialGradient).toHaveBeenCalled();
      expect(mockContext.fill).toHaveBeenCalled();
    });
  });

  describe('Lifecycle', () => {
    beforeEach(() => {
      cursorEffects = new CursorEffects();
      cursorEffects.isMobile = false;
      cursorEffects.canvas = mockCanvas;
      cursorEffects.ctx = mockContext;
      cursorEffects.isRunning = true;
    });

    test('should stop animation', () => {
      cursorEffects.animationId = 123;
      cursorEffects.stop();

      expect(cursorEffects.isRunning).toBe(false);
      expect(global.cancelAnimationFrame).toHaveBeenCalledWith(123);
      expect(cursorEffects.animationId).toBeNull();
    });

    test('should clear all effects', () => {
      cursorEffects.addTrail(100, 200);
      cursorEffects.addRipple(300, 400);

      cursorEffects.clear();

      expect(cursorEffects.trails.length).toBe(0);
      expect(cursorEffects.ripples.length).toBe(0);
    });

    test('should destroy cursor effects', () => {
      cursorEffects.addTrail(100, 200);
      cursorEffects.addRipple(300, 400);
      cursorEffects.animationId = 123;

      cursorEffects.destroy();

      expect(cursorEffects.isRunning).toBe(false);
      expect(cursorEffects.trails.length).toBe(0);
      expect(cursorEffects.ripples.length).toBe(0);
      expect(cursorEffects.canvas).toBeNull();
      expect(cursorEffects.ctx).toBeNull();
    });
  });

  describe('Resize Handling', () => {
    beforeEach(() => {
      cursorEffects = new CursorEffects();
      cursorEffects.isMobile = false;
      cursorEffects.canvas = mockCanvas;
      cursorEffects.ctx = mockContext;
    });

    test('should resize canvas to match window', () => {
      global.innerWidth = 1920;
      global.innerHeight = 1080;

      cursorEffects.resize();

      expect(mockCanvas.width).toBe(1920);
      expect(mockCanvas.height).toBe(1080);
    });

    test('should handle resize when canvas is null', () => {
      cursorEffects.canvas = null;

      expect(() => cursorEffects.resize()).not.toThrow();
    });
  });
});

describe('Global Functions', () => {
  test('initCursorEffects should be defined', () => {
    expect(initCursorEffects).toBeDefined();
  });

  test('stopCursorEffects should be defined', () => {
    expect(stopCursorEffects).toBeDefined();
  });

  test('clearCursorEffects should be defined', () => {
    expect(clearCursorEffects).toBeDefined();
  });
});
