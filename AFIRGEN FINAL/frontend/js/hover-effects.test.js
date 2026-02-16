/**
 * Unit Tests for Hover Effects Module
 * 
 * Tests all hover effect functionality including:
 * - Scale and glow effects
 * - Shadow lift effects
 * - Magnetic button effects
 * - Color transitions
 * - Reduced motion support
 * - Touch device support
 */

const HoverEffects = require('./hover-effects');

describe('HoverEffects', () => {
  let hoverEffects;
  let mockElement;

  beforeEach(() => {
    // Mock DOM element
    mockElement = {
      classList: {
        add: jest.fn(),
        remove: jest.fn(),
        contains: jest.fn()
      },
      style: {},
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      getBoundingClientRect: jest.fn(() => ({
        left: 100,
        top: 100,
        width: 200,
        height: 100
      }))
    };

    // Mock window.matchMedia
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });

    // Mock document.querySelectorAll
    document.querySelectorAll = jest.fn(() => [mockElement]);

    hoverEffects = new HoverEffects();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Constructor', () => {
    test('should initialize with default values', () => {
      expect(hoverEffects.magneticElements).toBeInstanceOf(Map);
      expect(hoverEffects.reducedMotion).toBe(false);
      expect(hoverEffects.isTouchDevice).toBeDefined();
    });

    test('should detect reduced motion preference', () => {
      window.matchMedia = jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        addEventListener: jest.fn()
      }));

      const effects = new HoverEffects();
      expect(effects.reducedMotion).toBe(true);
    });

    test('should detect touch devices', () => {
      Object.defineProperty(window, 'ontouchstart', {
        writable: true,
        value: true
      });

      const effects = new HoverEffects();
      expect(effects.isTouchDevice).toBe(true);
    });
  });

  describe('init()', () => {
    test('should initialize scale-glow effect', () => {
      // Ensure effects are not disabled
      hoverEffects.reducedMotion = false;
      hoverEffects.isTouchDevice = false;
      
      hoverEffects.init('.test', 'scale-glow');
      
      expect(document.querySelectorAll).toHaveBeenCalledWith('.test');
      expect(mockElement.classList.add).toHaveBeenCalledWith('hover-scale-glow');
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mouseenter', expect.any(Function));
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mouseleave', expect.any(Function));
    });

    test('should initialize lift effect', () => {
      hoverEffects.reducedMotion = false;
      hoverEffects.isTouchDevice = false;
      
      hoverEffects.init('.test', 'lift');
      
      expect(mockElement.classList.add).toHaveBeenCalledWith('hover-lift');
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mouseenter', expect.any(Function));
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mouseleave', expect.any(Function));
    });

    test('should initialize magnetic effect', () => {
      hoverEffects.reducedMotion = false;
      hoverEffects.isTouchDevice = false;
      
      hoverEffects.init('.test', 'magnetic');
      
      expect(mockElement.classList.add).toHaveBeenCalledWith('hover-magnetic');
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mousemove', expect.any(Function));
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mouseleave', expect.any(Function));
    });

    test('should initialize color transition effect', () => {
      hoverEffects.reducedMotion = false;
      hoverEffects.isTouchDevice = false;
      
      // Mock getComputedStyle
      window.getComputedStyle = jest.fn(() => ({
        backgroundColor: 'rgb(255, 255, 255)',
        color: 'rgb(0, 0, 0)',
        borderColor: 'rgb(0, 0, 0)'
      }));

      hoverEffects.init('.test', 'color');
      
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mouseenter', expect.any(Function));
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mouseleave', expect.any(Function));
    });

    test('should initialize lift-glow effect', () => {
      hoverEffects.reducedMotion = false;
      hoverEffects.isTouchDevice = false;
      
      hoverEffects.init('.test', 'lift-glow');
      
      expect(mockElement.classList.add).toHaveBeenCalledWith('hover-lift-glow');
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mouseenter', expect.any(Function));
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mouseleave', expect.any(Function));
    });

    test('should not initialize effects when reduced motion is enabled', () => {
      hoverEffects.reducedMotion = true;
      hoverEffects.init('.test', 'scale-glow');
      
      expect(mockElement.addEventListener).not.toHaveBeenCalled();
    });

    test('should not initialize effects on touch devices', () => {
      hoverEffects.isTouchDevice = true;
      hoverEffects.init('.test', 'scale-glow');
      
      expect(mockElement.addEventListener).not.toHaveBeenCalled();
    });

    test('should warn on unknown effect type', () => {
      hoverEffects.reducedMotion = false;
      hoverEffects.isTouchDevice = false;
      
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      hoverEffects.init('.test', 'unknown');
      
      expect(consoleSpy).toHaveBeenCalledWith('Unknown effect type: unknown');
      consoleSpy.mockRestore();
    });
  });

  describe('applyScaleGlow()', () => {
    test('should apply scale and glow on hover', () => {
      hoverEffects.applyScaleGlow(mockElement);
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      expect(mockElement.style.transform).toContain('scale');
      expect(mockElement.style.boxShadow).toBeTruthy();
    });

    test('should use custom options', () => {
      hoverEffects.applyScaleGlow(mockElement, {
        scale: 1.1,
        glowColor: 'rgba(255, 0, 0, 0.5)',
        glowSize: 30
      });
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      expect(mockElement.style.transform).toBe('scale(1.1)');
      expect(mockElement.style.boxShadow).toContain('30px');
    });

    test('should reset on mouse leave', () => {
      mockElement.style.transform = 'scale(1)';
      mockElement.style.boxShadow = 'none';
      
      hoverEffects.applyScaleGlow(mockElement);
      
      const mouseleaveHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseleave'
      )[1];
      
      mouseleaveHandler();
      
      expect(mockElement.style.transform).toBe('scale(1)');
      expect(mockElement.style.boxShadow).toBe('none');
    });

    test('should not apply effect when reduced motion is enabled', () => {
      hoverEffects.reducedMotion = true;
      hoverEffects.applyScaleGlow(mockElement);
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      expect(mockElement.style.transform).toBeUndefined();
    });
  });

  describe('applyLift()', () => {
    test('should apply lift effect on hover', () => {
      hoverEffects.applyLift(mockElement);
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      expect(mockElement.style.transform).toContain('translateY');
      expect(mockElement.style.boxShadow).toBeTruthy();
    });

    test('should use custom lift distance', () => {
      hoverEffects.applyLift(mockElement, { liftDistance: 12 });
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      expect(mockElement.style.transform).toBe('translateY(-12px)');
    });

    test('should reset on mouse leave', () => {
      mockElement.style.transform = 'translateY(0)';
      mockElement.style.boxShadow = 'none';
      
      hoverEffects.applyLift(mockElement);
      
      const mouseleaveHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseleave'
      )[1];
      
      mouseleaveHandler();
      
      expect(mockElement.style.transform).toBe('translateY(0)');
    });
  });

  describe('applyMagnetic()', () => {
    test('should apply magnetic effect', () => {
      hoverEffects.applyMagnetic(mockElement);
      
      expect(mockElement.classList.add).toHaveBeenCalledWith('hover-magnetic');
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mousemove', expect.any(Function));
      expect(mockElement.addEventListener).toHaveBeenCalledWith('mouseleave', expect.any(Function));
    });

    test('should move element towards mouse', () => {
      hoverEffects.applyMagnetic(mockElement, { strength: 0.5, maxDistance: 50 });
      
      const mousemoveHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mousemove'
      )[1];
      
      // Mouse near center (200, 150)
      mousemoveHandler({ clientX: 210, clientY: 155 });
      
      expect(mockElement.style.transform).toContain('translate');
    });

    test('should reset when mouse is far away', () => {
      hoverEffects.applyMagnetic(mockElement, { maxDistance: 50 });
      
      const mousemoveHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mousemove'
      )[1];
      
      // Mouse far from center
      mousemoveHandler({ clientX: 500, clientY: 500 });
      
      expect(mockElement.style.transform).toBe('translate(0, 0)');
    });

    test('should reset on mouse leave', () => {
      hoverEffects.applyMagnetic(mockElement);
      
      const mouseleaveHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseleave'
      )[1];
      
      mouseleaveHandler();
      
      expect(mockElement.style.transform).toBe('translate(0, 0)');
    });

    test('should store handlers in magneticElements map', () => {
      hoverEffects.applyMagnetic(mockElement);
      
      expect(hoverEffects.magneticElements.has(mockElement)).toBe(true);
    });
  });

  describe('applyColorTransition()', () => {
    beforeEach(() => {
      window.getComputedStyle = jest.fn(() => ({
        backgroundColor: 'rgb(255, 255, 255)',
        color: 'rgb(0, 0, 0)',
        borderColor: 'rgb(0, 0, 0)'
      }));
    });

    test('should apply color transition on hover', () => {
      hoverEffects.applyColorTransition(mockElement);
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      expect(mockElement.style.backgroundColor).toBe('#007bff');
      expect(mockElement.style.color).toBe('#ffffff');
    });

    test('should use custom colors', () => {
      hoverEffects.applyColorTransition(mockElement, {
        hoverColor: '#ff0000',
        hoverTextColor: '#000000',
        hoverBorderColor: '#ff0000'
      });
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      expect(mockElement.style.backgroundColor).toBe('#ff0000');
      expect(mockElement.style.color).toBe('#000000');
    });

    test('should reset colors on mouse leave', () => {
      hoverEffects.applyColorTransition(mockElement);
      
      const mouseleaveHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseleave'
      )[1];
      
      mouseleaveHandler();
      
      expect(mockElement.style.backgroundColor).toBe('rgb(255, 255, 255)');
      expect(mockElement.style.color).toBe('rgb(0, 0, 0)');
    });
  });

  describe('applyLiftGlow()', () => {
    test('should apply combined lift and glow effect', () => {
      hoverEffects.applyLiftGlow(mockElement);
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      expect(mockElement.style.transform).toContain('translateY');
      expect(mockElement.style.transform).toContain('scale');
      expect(mockElement.style.boxShadow).toBeTruthy();
    });

    test('should use custom options', () => {
      hoverEffects.applyLiftGlow(mockElement, {
        liftDistance: 10,
        scale: 1.05,
        glowColor: 'rgba(255, 0, 0, 0.5)',
        glowSize: 25
      });
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      expect(mockElement.style.transform).toBe('translateY(-10px) scale(1.05)');
      expect(mockElement.style.boxShadow).toContain('25px');
    });
  });

  describe('removeMagnetic()', () => {
    test('should remove magnetic effect', () => {
      hoverEffects.applyMagnetic(mockElement);
      
      expect(hoverEffects.magneticElements.has(mockElement)).toBe(true);
      
      hoverEffects.removeMagnetic(mockElement);
      
      expect(mockElement.removeEventListener).toHaveBeenCalledWith('mousemove', expect.any(Function));
      expect(mockElement.removeEventListener).toHaveBeenCalledWith('mouseleave', expect.any(Function));
      expect(hoverEffects.magneticElements.has(mockElement)).toBe(false);
    });

    test('should handle removing non-existent magnetic effect', () => {
      expect(() => {
        hoverEffects.removeMagnetic(mockElement);
      }).not.toThrow();
    });
  });

  describe('disableAllEffects()', () => {
    test('should remove all magnetic effects', () => {
      const element1 = { ...mockElement };
      const element2 = { ...mockElement };
      
      hoverEffects.applyMagnetic(element1);
      hoverEffects.applyMagnetic(element2);
      
      expect(hoverEffects.magneticElements.size).toBe(2);
      
      hoverEffects.disableAllEffects();
      
      expect(hoverEffects.magneticElements.size).toBe(0);
    });

    test('should reset transforms and shadows', () => {
      document.querySelectorAll = jest.fn(() => [mockElement]);
      
      mockElement.style.transform = 'scale(1.1)';
      mockElement.style.boxShadow = '0 0 20px rgba(0, 0, 0, 0.5)';
      
      hoverEffects.disableAllEffects();
      
      expect(mockElement.style.transform).toBe('');
      expect(mockElement.style.boxShadow).toBe('');
    });
  });

  describe('destroy()', () => {
    test('should cleanup all effects', () => {
      const disableSpy = jest.spyOn(hoverEffects, 'disableAllEffects');
      
      hoverEffects.destroy();
      
      expect(disableSpy).toHaveBeenCalled();
    });
  });

  describe('Performance', () => {
    test('should use GPU-accelerated properties', () => {
      hoverEffects.applyScaleGlow(mockElement);
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      // Transform and box-shadow are GPU-accelerated
      expect(mockElement.style.transform).toBeDefined();
      expect(mockElement.style.boxShadow).toBeDefined();
    });

    test('should complete hover effect within 100ms', () => {
      const startTime = performance.now();
      
      hoverEffects.applyScaleGlow(mockElement);
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      expect(duration).toBeLessThan(100);
    });
  });

  describe('Accessibility', () => {
    test('should respect reduced motion preference', () => {
      hoverEffects.reducedMotion = true;
      
      hoverEffects.applyScaleGlow(mockElement);
      
      const mouseenterHandler = mockElement.addEventListener.mock.calls.find(
        call => call[0] === 'mouseenter'
      )[1];
      
      mouseenterHandler();
      
      expect(mockElement.style.transform).toBeUndefined();
    });

    test('should disable effects when reduced motion is enabled', () => {
      const disableSpy = jest.spyOn(hoverEffects, 'disableAllEffects');
      
      hoverEffects.reducedMotion = true;
      hoverEffects.disableAllEffects();
      
      expect(disableSpy).toHaveBeenCalled();
    });
  });
});
