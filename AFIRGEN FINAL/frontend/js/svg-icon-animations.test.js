/**
 * Unit tests for SVG Icon Animations
 */

const SVGIconAnimations = require('./svg-icon-animations');

describe('SVGIconAnimations', () => {
  let svgIconAnimations;
  let mockIcon;

  beforeEach(() => {
    // Setup DOM
    document.body.innerHTML = `
      <svg data-icon-type="loading" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10"></circle>
      </svg>
      <svg data-icon-type="success" viewBox="0 0 24 24">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <svg data-icon-type="error" viewBox="0 0 24 24">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
      <svg data-icon-morph="play" viewBox="0 0 24 24">
        <path d="M5 3l14 9-14 9V3z"></path>
      </svg>
    `;

    svgIconAnimations = new SVGIconAnimations();
    mockIcon = document.querySelector('[data-icon-type="loading"]');
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe('Initialization', () => {
    test('should initialize without errors', () => {
      expect(svgIconAnimations).toBeDefined();
      expect(svgIconAnimations.icons).toBeInstanceOf(Map);
    });

    test('should setup loading icons on init', () => {
      const loadingIcon = document.querySelector('[data-icon-type="loading"]');
      expect(loadingIcon.style.animation).toContain('spin');
    });

    test('should setup morphing icons on init', () => {
      const morphingIcon = document.querySelector('[data-icon-morph]');
      expect(svgIconAnimations.icons.has(morphingIcon)).toBe(true);
    });
  });

  describe('Loading Animations', () => {
    test('should animate loading icon with spin', () => {
      const icon = document.querySelector('[data-icon-type="loading"]');
      svgIconAnimations.animateLoading(icon);
      expect(icon.style.animation).toContain('spin');
    });
  });

  describe('Success Animations', () => {
    test('should animate success icon with draw effect', () => {
      const icon = document.querySelector('[data-icon-type="success"]');
      const polyline = icon.querySelector('polyline');
      
      // Mock getTotalLength
      polyline.getTotalLength = jest.fn(() => 100);
      
      svgIconAnimations.animateSuccess(icon);
      
      expect(polyline.style.strokeDasharray).toBe('100');
      expect(polyline.style.strokeDashoffset).toBe('100');
      expect(polyline.style.animation).toContain('draw');
    });

    test('should handle multiple paths in success icon', () => {
      document.body.innerHTML = `
        <svg data-icon-type="success" viewBox="0 0 24 24">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
      `;
      
      const icon = document.querySelector('[data-icon-type="success"]');
      const paths = icon.querySelectorAll('path, polyline');
      
      paths.forEach(path => {
        path.getTotalLength = jest.fn(() => 100);
      });
      
      svgIconAnimations.animateSuccess(icon);
      
      paths.forEach(path => {
        expect(path.style.animation).toContain('draw');
      });
    });
  });

  describe('Error Animations', () => {
    test('should animate error icon with draw effect', () => {
      const icon = document.querySelector('[data-icon-type="error"]');
      const lines = icon.querySelectorAll('line');
      
      lines.forEach(line => {
        line.getTotalLength = jest.fn(() => 50);
      });
      
      svgIconAnimations.animateError(icon);
      
      lines.forEach(line => {
        expect(line.style.strokeDasharray).toBe('50');
        expect(line.style.strokeDashoffset).toBe('50');
        expect(line.style.animation).toContain('draw');
      });
    });
  });

  describe('Morphing Animations', () => {
    test('should register morphing icon', () => {
      const icon = document.querySelector('[data-icon-morph]');
      svgIconAnimations.registerMorphingIcon(icon, 'pause');
      
      const iconData = svgIconAnimations.icons.get(icon);
      expect(iconData).toBeDefined();
      expect(iconData.targetState).toBe('pause');
    });

    test('should get icon path data for known states', () => {
      const playPath = svgIconAnimations.getIconPath('play');
      const pausePath = svgIconAnimations.getIconPath('pause');
      
      expect(playPath).toBeDefined();
      expect(pausePath).toBeDefined();
      expect(playPath).not.toBe(pausePath);
    });

    test('should return undefined for unknown states', () => {
      const unknownPath = svgIconAnimations.getIconPath('unknown');
      expect(unknownPath).toBeUndefined();
    });
  });

  describe('Animation Triggers', () => {
    test('should trigger loading animation', () => {
      const icon = document.createElement('svg');
      svgIconAnimations.triggerAnimation(icon, 'loading');
      expect(icon.style.animation).toContain('spin');
    });

    test('should trigger pulse animation', () => {
      const icon = document.createElement('svg');
      svgIconAnimations.triggerAnimation(icon, 'pulse');
      expect(icon.style.animation).toContain('pulse');
    });

    test('should trigger bounce animation', () => {
      const icon = document.createElement('svg');
      svgIconAnimations.triggerAnimation(icon, 'bounce');
      expect(icon.style.animation).toContain('bounce');
    });

    test('should warn on unknown animation type', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      const icon = document.createElement('svg');
      
      svgIconAnimations.triggerAnimation(icon, 'unknown');
      
      expect(consoleSpy).toHaveBeenCalledWith('Unknown animation type: unknown');
      consoleSpy.mockRestore();
    });
  });

  describe('Animation Control', () => {
    test('should stop animation on icon', () => {
      const icon = document.createElement('svg');
      icon.style.animation = 'spin 1s linear infinite';
      
      svgIconAnimations.stopAnimation(icon);
      
      expect(icon.style.animation).toBe('none');
    });

    test('should reset icon to default state', () => {
      const icon = document.createElement('svg');
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      icon.appendChild(path);
      
      path.style.strokeDasharray = '100';
      path.style.strokeDashoffset = '100';
      path.style.animation = 'draw 0.6s ease-out forwards';
      
      svgIconAnimations.resetIcon(icon);
      
      expect(icon.style.animation).toBe('none');
      expect(path.style.strokeDasharray).toBe('none');
      expect(path.style.strokeDashoffset).toBe('0');
      expect(path.style.animation).toBe('none');
    });
  });

  describe('Performance', () => {
    test('should handle multiple icons efficiently', () => {
      const iconCount = 100;
      const icons = [];
      
      for (let i = 0; i < iconCount; i++) {
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        icon.setAttribute('data-icon-type', 'loading');
        document.body.appendChild(icon);
        icons.push(icon);
      }
      
      const startTime = performance.now();
      icons.forEach(icon => svgIconAnimations.animateLoading(icon));
      const endTime = performance.now();
      
      expect(endTime - startTime).toBeLessThan(100); // Should complete in <100ms
    });
  });

  describe('Accessibility', () => {
    test('should not interfere with aria attributes', () => {
      const icon = document.createElement('svg');
      icon.setAttribute('aria-hidden', 'true');
      icon.setAttribute('role', 'img');
      
      svgIconAnimations.animateLoading(icon);
      
      expect(icon.getAttribute('aria-hidden')).toBe('true');
      expect(icon.getAttribute('role')).toBe('img');
    });
  });
});
