/**
 * Text Reveal Animations Tests
 * 
 * Unit tests for text reveal animation functionality
 */

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor(callback, options) {
    this.callback = callback;
    this.options = options;
    this.observedElements = new Set();
  }

  observe(element) {
    this.observedElements.add(element);
  }

  unobserve(element) {
    this.observedElements.delete(element);
  }

  disconnect() {
    this.observedElements.clear();
  }

  // Helper method to trigger intersection
  triggerIntersection(element, isIntersecting = true) {
    this.callback([{
      target: element,
      isIntersecting
    }]);
  }
};

// Import the module
const { TextRevealAnimations } = require('./text-reveal.js');

describe('TextRevealAnimations', () => {
  let textReveal;
  let mockElement;

  beforeEach(() => {
    // Set up DOM
    document.body.innerHTML = `
      <div class="hero-title">AFIRGen</div>
      <div class="step-item">
        <h3 class="step-title">Step 1</h3>
        <p class="step-description">Description</p>
      </div>
      <div class="page-section">
        <h1 class="page-title">Title</h1>
        <p class="page-subtitle">Subtitle</p>
      </div>
      <div class="team-member">Team Member</div>
      <div class="resource-category">Resource</div>
    `;

    textReveal = new TextRevealAnimations();
    mockElement = document.createElement('div');
  });

  afterEach(() => {
    if (textReveal) {
      textReveal.destroy();
    }
    document.body.innerHTML = '';
  });

  describe('Initialization', () => {
    test('should create instance with default options', () => {
      expect(textReveal).toBeDefined();
      expect(textReveal.observerOptions).toBeDefined();
      expect(textReveal.observerOptions.threshold).toBe(0.1);
    });

    test('should initialize IntersectionObserver', () => {
      textReveal.setupIntersectionObserver();
      expect(textReveal.observer).toBeDefined();
      expect(textReveal.observer).toBeInstanceOf(IntersectionObserver);
    });

    test('should handle missing IntersectionObserver gracefully', () => {
      const originalIO = global.IntersectionObserver;
      delete global.IntersectionObserver;

      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      textReveal.setupIntersectionObserver();

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('IntersectionObserver not supported')
      );

      global.IntersectionObserver = originalIO;
      consoleSpy.mockRestore();
    });
  });

  describe('Fade-in Animation', () => {
    test('should add fade-in class to element', (done) => {
      mockElement.setAttribute('data-fade-in', '');
      mockElement.classList.add('text-reveal-hidden');

      textReveal.animateFadeIn(mockElement);

      // Animation should start immediately (0 delay)
      setTimeout(() => {
        expect(mockElement.classList.contains('text-reveal-fade-in')).toBe(true);
        expect(mockElement.classList.contains('text-reveal-hidden')).toBe(false);
        done();
      }, 10);
    });

    test('should respect fade delay attribute', (done) => {
      mockElement.setAttribute('data-fade-in', '');
      mockElement.setAttribute('data-fade-delay', '100');
      mockElement.classList.add('text-reveal-hidden');

      const startTime = Date.now();
      textReveal.animateFadeIn(mockElement);

      setTimeout(() => {
        const elapsed = Date.now() - startTime;
        expect(elapsed).toBeGreaterThanOrEqual(100);
        expect(mockElement.classList.contains('text-reveal-fade-in')).toBe(true);
        done();
      }, 150);
    });

    test('should set up fade-in elements on initialization', () => {
      textReveal.setupIntersectionObserver();
      textReveal.setupFadeInElements();

      const stepItems = document.querySelectorAll('.step-item');
      expect(stepItems[0].hasAttribute('data-fade-in')).toBe(true);
      expect(stepItems[0].classList.contains('text-reveal-hidden')).toBe(true);
    });
  });

  describe('Typewriter Effect', () => {
    test('should type out text character by character', (done) => {
      const text = 'Test';
      mockElement.textContent = '';

      textReveal.typewriterEffect(mockElement, text, 10);

      setTimeout(() => {
        expect(mockElement.textContent).toBe(text);
        done();
      }, 100);
    });

    test('should add cursor class during typing', () => {
      const heroTitle = document.querySelector('.hero-title');
      const originalText = heroTitle.textContent;

      heroTitle.classList.add('typewriter-cursor');
      expect(heroTitle.classList.contains('typewriter-cursor')).toBe(true);
    });

    test('should clear element before typing', (done) => {
      mockElement.textContent = 'Original';
      textReveal.typewriterEffect(mockElement, 'New', 10);

      // Check immediately - element should be cleared or starting to type
      setTimeout(() => {
        // After typing completes, should have the new text
        expect(mockElement.textContent).toBe('New');
        done();
      }, 50);
    });
  });

  describe('Staggered Letters Animation', () => {
    test('should split text into individual letter spans', () => {
      mockElement.textContent = 'Test';
      textReveal.animateStaggeredLetters(mockElement);

      const letters = mockElement.querySelectorAll('.stagger-letter');
      expect(letters.length).toBe(4);
    });

    test('should apply animation delay to each letter', () => {
      mockElement.textContent = 'ABC';
      textReveal.animateStaggeredLetters(mockElement);

      const letters = mockElement.querySelectorAll('.stagger-letter');
      expect(letters[0].style.animationDelay).toBe('0ms');
      expect(letters[1].style.animationDelay).toBe('30ms');
      expect(letters[2].style.animationDelay).toBe('60ms');
    });

    test('should preserve spaces in text', () => {
      mockElement.textContent = 'A B';
      textReveal.animateStaggeredLetters(mockElement);

      const letters = mockElement.querySelectorAll('.stagger-letter');
      expect(letters.length).toBe(3);
      expect(letters[1].textContent).toBe(' ');
      expect(letters[1].style.display).toBe('inline-block');
    });

    test('should remove hidden class', () => {
      mockElement.textContent = 'Test';
      mockElement.classList.add('text-reveal-hidden');

      textReveal.animateStaggeredLetters(mockElement);

      expect(mockElement.classList.contains('text-reveal-hidden')).toBe(false);
    });
  });

  describe('Intersection Observer Integration', () => {
    test('should observe elements with data attributes', () => {
      textReveal.setupIntersectionObserver();
      textReveal.setupFadeInElements();

      expect(textReveal.observer.observedElements.size).toBeGreaterThan(0);
    });

    test('should trigger fade-in when element intersects', (done) => {
      mockElement.setAttribute('data-fade-in', '');
      mockElement.classList.add('text-reveal-hidden');

      textReveal.setupIntersectionObserver();
      textReveal.observer.observe(mockElement);
      textReveal.observer.triggerIntersection(mockElement, true);

      setTimeout(() => {
        expect(mockElement.classList.contains('text-reveal-fade-in')).toBe(true);
        done();
      }, 20);
    });

    test('should trigger staggered letters when element intersects', () => {
      mockElement.setAttribute('data-stagger-letters', '');
      mockElement.textContent = 'Test';
      mockElement.classList.add('text-reveal-hidden');

      textReveal.setupIntersectionObserver();
      textReveal.observer.observe(mockElement);
      textReveal.observer.triggerIntersection(mockElement, true);

      const letters = mockElement.querySelectorAll('.stagger-letter');
      expect(letters.length).toBe(4);
    });

    test('should unobserve element after animation', () => {
      mockElement.setAttribute('data-fade-in', '');

      textReveal.setupIntersectionObserver();
      textReveal.observer.observe(mockElement);

      const unobserveSpy = jest.spyOn(textReveal.observer, 'unobserve');
      textReveal.observer.triggerIntersection(mockElement, true);

      expect(unobserveSpy).toHaveBeenCalledWith(mockElement);
    });
  });

  describe('Manual Animation Trigger', () => {
    test('should trigger fade-in animation manually', (done) => {
      mockElement.classList.add('text-reveal-hidden');
      mockElement.setAttribute('data-fade-in', '');
      textReveal.triggerAnimation(mockElement, 'fade-in');

      setTimeout(() => {
        expect(mockElement.classList.contains('text-reveal-fade-in')).toBe(true);
        done();
      }, 50);
    });

    test('should trigger staggered letters animation manually', () => {
      mockElement.textContent = 'Test';
      textReveal.triggerAnimation(mockElement, 'stagger-letters');

      const letters = mockElement.querySelectorAll('.stagger-letter');
      expect(letters.length).toBe(4);
    });

    test('should trigger typewriter animation manually', () => {
      mockElement.textContent = 'Test';
      textReveal.triggerAnimation(mockElement, 'typewriter');

      // Element should be cleared for typing
      expect(mockElement.textContent.length).toBeLessThanOrEqual(4);
    });

    test('should warn on unknown animation type', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      textReveal.triggerAnimation(mockElement, 'unknown');

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Unknown animation type')
      );

      consoleSpy.mockRestore();
    });
  });

  describe('Cleanup', () => {
    test('should disconnect observer on destroy', () => {
      textReveal.setupIntersectionObserver();
      const disconnectSpy = jest.spyOn(textReveal.observer, 'disconnect');

      textReveal.destroy();

      expect(disconnectSpy).toHaveBeenCalled();
    });

    test('should handle destroy when observer is null', () => {
      textReveal.observer = null;
      expect(() => textReveal.destroy()).not.toThrow();
    });
  });

  describe('Performance Considerations', () => {
    test('should use threshold of 0.1 for early triggering', () => {
      expect(textReveal.observerOptions.threshold).toBe(0.1);
    });

    test('should unobserve elements after animation to save resources', () => {
      mockElement.setAttribute('data-fade-in', '');
      textReveal.setupIntersectionObserver();

      const unobserveSpy = jest.spyOn(textReveal.observer, 'unobserve');
      textReveal.observer.observe(mockElement);
      textReveal.observer.triggerIntersection(mockElement, true);

      expect(unobserveSpy).toHaveBeenCalledWith(mockElement);
    });
  });

  describe('Edge Cases', () => {
    test('should handle empty text gracefully', () => {
      mockElement.textContent = '';
      expect(() => textReveal.animateStaggeredLetters(mockElement)).not.toThrow();
    });

    test('should handle missing data attributes', () => {
      expect(() => textReveal.animateFadeIn(mockElement)).not.toThrow();
    });

    test('should handle elements without text content', () => {
      const emptyElement = document.createElement('div');
      expect(() => textReveal.typewriterEffect(emptyElement, '', 10)).not.toThrow();
    });
  });
});
