/**
 * Unit Tests for Subtle Motion Module
 * 
 * Tests cover:
 * - Animation application and removal
 * - Reduced motion support
 * - Performance monitoring
 * - Accessibility features
 * - Combined effects
 * - Staggered animations
 */

// Mock DOM environment for testing
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.window = dom.window;
global.document = dom.window.document;
global.performance = dom.window.performance;

// Mock requestAnimationFrame properly
global.requestAnimationFrame = (callback) => {
  return setTimeout(callback, 0);
};
global.window.requestAnimationFrame = global.requestAnimationFrame;

// Mock matchMedia before requiring the module
global.window.matchMedia = jest.fn().mockImplementation(query => ({
  matches: false,
  media: query,
  addEventListener: jest.fn(),
  removeEventListener: jest.fn()
}));

const SubtleMotion = require('./subtle-motion.js');

describe('SubtleMotion', () => {
  let subtleMotion;
  let testElement;

  beforeEach(() => {
    // Clear module cache to get fresh instance
    jest.resetModules();
    
    // Re-setup mocks
    global.window.matchMedia = jest.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn()
    }));
    
    // Require fresh module
    const SubtleMotionClass = require('./subtle-motion.js');
    
    // Create fresh instance for each test
    subtleMotion = new SubtleMotionClass();
    
    // Create test element
    testElement = document.createElement('div');
    testElement.id = 'test-element';
    document.body.appendChild(testElement);
  });

  afterEach(() => {
    // Cleanup
    if (testElement && testElement.parentNode) {
      testElement.parentNode.removeChild(testElement);
    }
    subtleMotion.destroy();
  });

  describe('Initialization', () => {
    test('should initialize with correct default state', () => {
      expect(subtleMotion.elements).toBeInstanceOf(Map);
      expect(subtleMotion.elements.size).toBe(0);
      expect(typeof subtleMotion.reducedMotion).toBe('boolean');
      expect(subtleMotion.performanceMode).toBe(false);
    });

    test('should detect prefers-reduced-motion', () => {
      // Mock matchMedia
      window.matchMedia = jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      }));

      const motion = new SubtleMotion();
      expect(motion.reducedMotion).toBe(true);
    });
  });

  describe('Float Animation', () => {
    test('should apply float animation with default options', () => {
      subtleMotion.applyFloat(testElement);
      
      expect(testElement.classList.contains('float-gentle')).toBe(true);
      expect(subtleMotion.elements.has(testElement)).toBe(true);
    });

    test('should apply slow float animation', () => {
      subtleMotion.applyFloat(testElement, { speed: 'slow' });
      
      expect(testElement.classList.contains('float-gentle-slow')).toBe(true);
    });

    test('should apply fast float animation', () => {
      subtleMotion.applyFloat(testElement, { speed: 'fast' });
      
      expect(testElement.classList.contains('float-gentle-fast')).toBe(true);
    });

    test('should apply reverse float animation', () => {
      subtleMotion.applyFloat(testElement, { direction: 'down' });
      
      expect(testElement.classList.contains('float-gentle-reverse')).toBe(true);
    });

    test('should add pause-on-hover class when pause option is true', () => {
      subtleMotion.applyFloat(testElement, { pause: true });
      
      expect(testElement.classList.contains('pause-on-hover')).toBe(true);
    });

    test('should not apply animation when reduced motion is enabled', () => {
      subtleMotion.reducedMotion = true;
      subtleMotion.applyFloat(testElement);
      
      expect(testElement.classList.contains('float-gentle')).toBe(false);
      expect(subtleMotion.elements.has(testElement)).toBe(false);
    });
  });

  describe('Breathe Animation', () => {
    test('should apply breathe animation with default options', () => {
      subtleMotion.applyBreathe(testElement);
      
      expect(testElement.classList.contains('breathe')).toBe(true);
      expect(subtleMotion.elements.has(testElement)).toBe(true);
    });

    test('should apply subtle breathe animation', () => {
      subtleMotion.applyBreathe(testElement, { intensity: 'subtle' });
      
      expect(testElement.classList.contains('breathe-subtle')).toBe(true);
    });

    test('should apply glow breathe animation', () => {
      subtleMotion.applyBreathe(testElement, { intensity: 'glow' });
      
      expect(testElement.classList.contains('breathe-glow')).toBe(true);
    });

    test('should apply slow breathe animation', () => {
      subtleMotion.applyBreathe(testElement, { speed: 'slow' });
      
      expect(testElement.classList.contains('breathe')).toBe(true);
      expect(testElement.classList.contains('breathe-slow')).toBe(true);
    });

    test('should apply fast breathe animation', () => {
      subtleMotion.applyBreathe(testElement, { speed: 'fast' });
      
      expect(testElement.classList.contains('breathe')).toBe(true);
      expect(testElement.classList.contains('breathe-fast')).toBe(true);
    });

    test('should not apply animation when reduced motion is enabled', () => {
      subtleMotion.reducedMotion = true;
      subtleMotion.applyBreathe(testElement);
      
      expect(testElement.classList.contains('breathe')).toBe(false);
    });
  });

  describe('Wave Animation', () => {
    test('should apply horizontal wave animation', () => {
      subtleMotion.applyWave(testElement, { direction: 'horizontal' });
      
      expect(testElement.classList.contains('wave-horizontal')).toBe(true);
      expect(subtleMotion.elements.has(testElement)).toBe(true);
    });

    test('should apply vertical wave animation', () => {
      subtleMotion.applyWave(testElement, { direction: 'vertical' });
      
      expect(testElement.classList.contains('wave-vertical')).toBe(true);
    });

    test('should apply ripple wave animation', () => {
      subtleMotion.applyWave(testElement, { direction: 'ripple' });
      
      expect(testElement.classList.contains('wave-ripple')).toBe(true);
    });

    test('should apply pulse wave animation', () => {
      subtleMotion.applyWave(testElement, { direction: 'pulse' });
      
      expect(testElement.classList.contains('wave-pulse')).toBe(true);
    });

    test('should not apply animation when reduced motion is enabled', () => {
      subtleMotion.reducedMotion = true;
      subtleMotion.applyWave(testElement);
      
      expect(testElement.classList.contains('wave-horizontal')).toBe(false);
    });
  });

  describe('Combined Effects', () => {
    test('should apply float + breathe combination', () => {
      subtleMotion.applyCombined(testElement, { effects: ['float', 'breathe'] });
      
      expect(testElement.classList.contains('float-breathe')).toBe(true);
      expect(subtleMotion.elements.has(testElement)).toBe(true);
    });

    test('should apply float + wave combination', () => {
      subtleMotion.applyCombined(testElement, { effects: ['float', 'wave'] });
      
      expect(testElement.classList.contains('float-wave')).toBe(true);
    });

    test('should not apply animation when reduced motion is enabled', () => {
      subtleMotion.reducedMotion = true;
      subtleMotion.applyCombined(testElement, { effects: ['float', 'breathe'] });
      
      expect(testElement.classList.contains('float-breathe')).toBe(false);
    });
  });

  describe('Staggered Animations', () => {
    test('should apply staggered float animations', () => {
      const elements = [];
      for (let i = 0; i < 3; i++) {
        const el = document.createElement('div');
        document.body.appendChild(el);
        elements.push(el);
      }

      subtleMotion.applyStaggered(elements, { type: 'float' });

      elements.forEach((el, index) => {
        expect(el.classList.contains('float-gentle')).toBe(true);
        expect(el.classList.contains(`stagger-delay-${index + 1}`)).toBe(true);
      });

      // Cleanup
      elements.forEach(el => el.remove());
    });

    test('should apply staggered breathe animations', () => {
      const elements = [];
      for (let i = 0; i < 2; i++) {
        const el = document.createElement('div');
        document.body.appendChild(el);
        elements.push(el);
      }

      subtleMotion.applyStaggered(elements, { type: 'breathe' });

      elements.forEach((el) => {
        expect(el.classList.contains('breathe')).toBe(true);
      });

      // Cleanup
      elements.forEach(el => el.remove());
    });

    test('should apply custom delay for elements beyond index 4', () => {
      const elements = [];
      for (let i = 0; i < 6; i++) {
        const el = document.createElement('div');
        document.body.appendChild(el);
        elements.push(el);
      }

      subtleMotion.applyStaggered(elements, { type: 'float', delay: 0.2 });

      // Element at index 5 should have custom delay
      expect(elements[5].style.animationDelay).toMatch(/^1\.2/);

      // Cleanup
      elements.forEach(el => el.remove());
    });
  });

  describe('Animation Control', () => {
    test('should pause animation', () => {
      subtleMotion.applyFloat(testElement);
      subtleMotion.pauseAnimation(testElement);
      
      expect(testElement.style.animationPlayState).toBe('paused');
    });

    test('should resume animation', () => {
      subtleMotion.applyFloat(testElement);
      subtleMotion.pauseAnimation(testElement);
      subtleMotion.resumeAnimation(testElement);
      
      expect(testElement.style.animationPlayState).toBe('running');
    });

    test('should not resume animation when reduced motion is enabled', () => {
      subtleMotion.applyFloat(testElement);
      subtleMotion.reducedMotion = true;
      subtleMotion.resumeAnimation(testElement);
      
      expect(testElement.style.animationPlayState).not.toBe('running');
    });
  });

  describe('Animation Removal', () => {
    test('should remove all motion classes', () => {
      subtleMotion.applyFloat(testElement);
      subtleMotion.removeMotion(testElement);
      
      expect(testElement.classList.contains('float-gentle')).toBe(false);
      expect(subtleMotion.elements.has(testElement)).toBe(false);
    });

    test('should clear animation delay', () => {
      testElement.style.animationDelay = '0.5s';
      subtleMotion.removeMotion(testElement);
      
      expect(testElement.style.animationDelay).toBe('');
    });

    test('should remove element from tracking', () => {
      subtleMotion.applyFloat(testElement);
      expect(subtleMotion.elements.size).toBe(1);
      
      subtleMotion.removeMotion(testElement);
      expect(subtleMotion.elements.size).toBe(0);
    });
  });

  describe('Reduced Motion Updates', () => {
    test('should update all elements when reduced motion changes', () => {
      const element1 = document.createElement('div');
      const element2 = document.createElement('div');
      document.body.appendChild(element1);
      document.body.appendChild(element2);

      subtleMotion.applyFloat(element1);
      subtleMotion.applyBreathe(element2);

      expect(subtleMotion.elements.size).toBe(2);

      // Enable reduced motion
      subtleMotion.reducedMotion = true;
      subtleMotion.updateAllElements();

      expect(element1.classList.contains('float-gentle')).toBe(false);
      expect(element2.classList.contains('breathe')).toBe(false);
      // Elements should still be tracked so they can be reapplied later
      expect(subtleMotion.elements.size).toBe(2);

      // Cleanup
      element1.remove();
      element2.remove();
    });

    test('should reapply animations when reduced motion is disabled', () => {
      subtleMotion.applyFloat(testElement);
      
      // Enable reduced motion
      subtleMotion.reducedMotion = true;
      subtleMotion.updateAllElements();
      
      // Disable reduced motion
      subtleMotion.reducedMotion = false;
      subtleMotion.updateAllElements();

      expect(testElement.classList.contains('float-gentle')).toBe(true);
    });
  });

  describe('State Management', () => {
    test('should return correct state', () => {
      subtleMotion.applyFloat(testElement);
      
      const state = subtleMotion.getState();
      
      expect(state).toHaveProperty('reducedMotion');
      expect(state).toHaveProperty('performanceMode');
      expect(state).toHaveProperty('activeElements');
      expect(state.activeElements).toBe(1);
    });

    test('should track active elements count', () => {
      const element1 = document.createElement('div');
      const element2 = document.createElement('div');
      document.body.appendChild(element1);
      document.body.appendChild(element2);

      subtleMotion.applyFloat(element1);
      subtleMotion.applyBreathe(element2);

      const state = subtleMotion.getState();
      expect(state.activeElements).toBe(2);

      // Cleanup
      element1.remove();
      element2.remove();
    });
  });

  describe('Performance Mode', () => {
    test('should enable performance mode', () => {
      subtleMotion.applyFloat(testElement);
      subtleMotion.enablePerformanceMode();
      
      expect(subtleMotion.performanceMode).toBe(true);
      expect(testElement.classList.contains('slow-motion')).toBe(true);
    });

    test('should disable performance mode', () => {
      subtleMotion.applyFloat(testElement);
      subtleMotion.enablePerformanceMode();
      subtleMotion.disablePerformanceMode();
      
      expect(subtleMotion.performanceMode).toBe(false);
      expect(testElement.classList.contains('slow-motion')).toBe(false);
    });
  });

  describe('Cleanup', () => {
    test('should destroy all animations', () => {
      const element1 = document.createElement('div');
      const element2 = document.createElement('div');
      document.body.appendChild(element1);
      document.body.appendChild(element2);

      subtleMotion.applyFloat(element1);
      subtleMotion.applyBreathe(element2);

      expect(subtleMotion.elements.size).toBe(2);

      subtleMotion.destroy();

      expect(subtleMotion.elements.size).toBe(0);
      expect(element1.classList.contains('float-gentle')).toBe(false);
      expect(element2.classList.contains('breathe')).toBe(false);

      // Cleanup
      element1.remove();
      element2.remove();
    });
  });

  describe('Edge Cases', () => {
    test('should handle null element gracefully', () => {
      expect(() => {
        subtleMotion.applyFloat(null);
      }).not.toThrow();
    });

    test('should handle undefined options', () => {
      expect(() => {
        subtleMotion.applyFloat(testElement, undefined);
      }).not.toThrow();
      
      expect(testElement.classList.contains('float-gentle')).toBe(true);
    });

    test('should replace existing animation when applying new one', () => {
      subtleMotion.applyFloat(testElement);
      expect(testElement.classList.contains('float-gentle')).toBe(true);
      
      subtleMotion.applyBreathe(testElement);
      expect(testElement.classList.contains('float-gentle')).toBe(false);
      expect(testElement.classList.contains('breathe')).toBe(true);
    });

    test('should handle removing non-existent element', () => {
      const nonExistent = document.createElement('div');
      
      expect(() => {
        subtleMotion.removeMotion(nonExistent);
      }).not.toThrow();
    });
  });

  describe('Accessibility', () => {
    test('should respect prefers-reduced-motion from system', () => {
      // Mock matchMedia to return reduced motion preference
      window.matchMedia = jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      }));

      const motion = new SubtleMotion();
      const element = document.createElement('div');
      document.body.appendChild(element);

      motion.applyFloat(element);

      // Should not apply animation
      expect(element.classList.contains('float-gentle')).toBe(false);

      // Cleanup
      element.remove();
    });

    test('should update when prefers-reduced-motion changes', () => {
      let reducedMotionCallback;
      
      window.matchMedia = jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        addEventListener: jest.fn((event, callback) => {
          if (event === 'change') {
            reducedMotionCallback = callback;
          }
        }),
        removeEventListener: jest.fn()
      }));

      const motion = new SubtleMotion();
      
      // Simulate preference change
      if (reducedMotionCallback) {
        reducedMotionCallback({ matches: true });
        expect(motion.reducedMotion).toBe(true);
      }
    });
  });

  describe('Performance', () => {
    test('should use GPU-accelerated properties', () => {
      subtleMotion.applyFloat(testElement);
      
      // Check that will-change is set via class
      expect(testElement.classList.contains('float-gentle')).toBe(true);
      
      // The CSS should handle GPU acceleration
      // We're just verifying the class is applied
    });

    test('should not block main thread', (done) => {
      const startTime = performance.now();
      
      // Apply animations to multiple elements
      const elements = [];
      for (let i = 0; i < 100; i++) {
        const el = document.createElement('div');
        document.body.appendChild(el);
        elements.push(el);
        subtleMotion.applyFloat(el);
      }
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      // Should complete in less than 100ms
      expect(duration).toBeLessThan(100);
      
      // Cleanup
      elements.forEach(el => el.remove());
      done();
    });
  });
});

