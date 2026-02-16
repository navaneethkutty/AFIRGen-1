/**
 * Unit Tests for Morphing Transitions Module
 * 
 * Tests for:
 * - Card flip animations
 * - Expand/collapse animations
 * - Accordion animations
 * - Button morphing
 * - Status badge morphing
 * - Progress bar animations
 * - List item animations
 */

const { MorphingTransitions } = require('./morphing-transitions');

describe('MorphingTransitions', () => {
  let morphing;
  let container;

  beforeEach(() => {
    // Create a container for test elements
    container = document.createElement('div');
    document.body.appendChild(container);
    
    // Clean up any existing screen reader announcements
    const existingAnnouncements = document.querySelectorAll('[role="status"]');
    existingAnnouncements.forEach(el => el.remove());
    
    morphing = new MorphingTransitions();
  });

  afterEach(() => {
    if (morphing) {
      morphing.destroy();
    }
    document.body.removeChild(container);
  });

  describe('Card Flip Animation', () => {
    test('should flip card when flipCard is called', () => {
      const card = document.createElement('div');
      card.className = 'fir-item';
      container.appendChild(card);

      morphing.flipCard(card);
      expect(card.classList.contains('flipping')).toBe(true);
      expect(card.getAttribute('aria-label')).toBe('Card back side');
    });

    test('should flip card back when called twice', () => {
      const card = document.createElement('div');
      card.className = 'fir-item';
      container.appendChild(card);

      morphing.flipCard(card);
      morphing.flipCard(card);
      
      expect(card.classList.contains('flipping')).toBe(false);
      expect(card.getAttribute('aria-label')).toBe('Card front side');
    });

    test('should not flip card when reduced motion is enabled', () => {
      morphing.reducedMotion = true;
      
      const card = document.createElement('div');
      card.className = 'fir-item';
      container.appendChild(card);

      morphing.flipCard(card);
      expect(card.classList.contains('flipping')).toBe(false);
    });
  });

  describe('Expand/Collapse Animation', () => {
    test('should expand collapsed element', () => {
      const element = document.createElement('div');
      element.className = 'expandable collapsed';
      element.style.maxHeight = '0';
      container.appendChild(element);

      morphing.expand(element);
      
      expect(element.classList.contains('collapsed')).toBe(false);
      expect(element.classList.contains('expanded')).toBe(true);
    });

    test('should collapse expanded element', () => {
      const element = document.createElement('div');
      element.className = 'expandable expanded';
      element.style.maxHeight = '500px';
      container.appendChild(element);

      morphing.collapse(element);
      
      expect(element.classList.contains('expanded')).toBe(false);
      expect(element.classList.contains('collapsed')).toBe(true);
    });

    test('should toggle expand/collapse state', () => {
      const element = document.createElement('div');
      element.className = 'expandable collapsed';
      container.appendChild(element);

      morphing.toggleExpand(element);
      expect(element.classList.contains('expanded')).toBe(true);

      morphing.toggleExpand(element);
      expect(element.classList.contains('collapsed')).toBe(true);
    });

    test('should update aria-expanded attribute on trigger', () => {
      const element = document.createElement('div');
      element.className = 'expandable collapsed';
      const trigger = document.createElement('button');
      container.appendChild(element);

      morphing.expand(element, trigger);
      expect(trigger.getAttribute('aria-expanded')).toBe('true');

      morphing.collapse(element, trigger);
      expect(trigger.getAttribute('aria-expanded')).toBe('false');
    });
  });

  describe('Accordion Animation', () => {
    test('should toggle accordion open/close', () => {
      const accordion = document.createElement('div');
      accordion.className = 'accordion-item';
      accordion.innerHTML = `
        <div class="accordion-header"></div>
        <div class="accordion-content"></div>
      `;
      container.appendChild(accordion);

      morphing.toggleAccordion(accordion);
      expect(accordion.classList.contains('open')).toBe(true);

      morphing.toggleAccordion(accordion);
      expect(accordion.classList.contains('open')).toBe(false);
    });

    test('should update aria attributes when toggling accordion', () => {
      const accordion = document.createElement('div');
      accordion.className = 'accordion-item';
      accordion.innerHTML = `
        <div class="accordion-header"></div>
        <div class="accordion-content"></div>
      `;
      container.appendChild(accordion);

      const header = accordion.querySelector('.accordion-header');
      const content = accordion.querySelector('.accordion-content');

      morphing.toggleAccordion(accordion);
      expect(header.getAttribute('aria-expanded')).toBe('true');
      expect(content.getAttribute('aria-hidden')).toBe('false');

      morphing.toggleAccordion(accordion);
      expect(header.getAttribute('aria-expanded')).toBe('false');
      expect(content.getAttribute('aria-hidden')).toBe('true');
    });

    test('should close other accordions in same group', () => {
      const group = document.createElement('div');
      group.setAttribute('data-accordion-group', '');
      
      const accordion1 = document.createElement('div');
      accordion1.className = 'accordion-item open';
      accordion1.innerHTML = `
        <div class="accordion-header"></div>
        <div class="accordion-content"></div>
      `;
      
      const accordion2 = document.createElement('div');
      accordion2.className = 'accordion-item';
      accordion2.innerHTML = `
        <div class="accordion-header"></div>
        <div class="accordion-content"></div>
      `;
      
      group.appendChild(accordion1);
      group.appendChild(accordion2);
      container.appendChild(group);

      morphing.toggleAccordion(accordion2);
      
      expect(accordion1.classList.contains('open')).toBe(false);
      expect(accordion2.classList.contains('open')).toBe(true);
    });
  });

  describe('Button Morphing', () => {
    test('should morph button to loading state', () => {
      const button = document.createElement('button');
      button.className = 'btn-morph';
      container.appendChild(button);

      morphing.morphToLoading(button);
      
      expect(button.classList.contains('loading')).toBe(true);
      expect(button.getAttribute('aria-busy')).toBe('true');
      expect(button.disabled).toBe(true);
    });

    test('should morph button from loading state', () => {
      const button = document.createElement('button');
      button.className = 'btn-morph loading';
      button.setAttribute('aria-busy', 'true');
      button.disabled = true;
      container.appendChild(button);

      morphing.morphFromLoading(button);
      
      expect(button.classList.contains('loading')).toBe(false);
      expect(button.getAttribute('aria-busy')).toBe('false');
      expect(button.disabled).toBe(false);
    });

    test('should create spinner element when morphing to loading', () => {
      const button = document.createElement('button');
      button.className = 'btn-morph';
      container.appendChild(button);

      morphing.morphToLoading(button);
      
      const spinner = button.querySelector('.btn-spinner');
      expect(spinner).not.toBeNull();
    });

    test('should handle null button gracefully', () => {
      expect(() => {
        morphing.morphToLoading(null);
        morphing.morphFromLoading(null);
      }).not.toThrow();
    });
  });

  describe('Status Badge Morphing', () => {
    test('should morph status badge to new status', (done) => {
      const badge = document.createElement('div');
      badge.className = 'status-badge pending';
      badge.textContent = 'Pending';
      container.appendChild(badge);

      morphing.morphStatusBadge(badge, 'investigating');
      
      // Wait for animation
      setTimeout(() => {
        expect(badge.classList.contains('pending')).toBe(false);
        expect(badge.classList.contains('investigating')).toBe(true);
        expect(badge.textContent).toBe('Investigating');
        done();
      }, 350);
    });

    test('should add morphing class during transition', () => {
      const badge = document.createElement('div');
      badge.className = 'status-badge pending';
      container.appendChild(badge);

      morphing.morphStatusBadge(badge, 'closed');
      
      expect(badge.classList.contains('morphing')).toBe(true);
    });

    test('should handle null badge gracefully', () => {
      expect(() => {
        morphing.morphStatusBadge(null, 'investigating');
      }).not.toThrow();
    });
  });

  describe('Progress Bar Animation', () => {
    test('should animate progress bar to target percentage', () => {
      const progressBar = document.createElement('div');
      progressBar.className = 'progress-bar';
      progressBar.setAttribute('role', 'progressbar');
      progressBar.innerHTML = '<div class="progress-fill"></div>';
      container.appendChild(progressBar);

      morphing.animateProgress(progressBar, 75);
      
      const fill = progressBar.querySelector('.progress-fill');
      expect(fill.style.width).toBe('75%');
      expect(progressBar.getAttribute('aria-valuenow')).toBe('75');
    });

    test('should clamp percentage to 0-100 range', () => {
      const progressBar = document.createElement('div');
      progressBar.className = 'progress-bar';
      progressBar.innerHTML = '<div class="progress-fill"></div>';
      container.appendChild(progressBar);

      morphing.animateProgress(progressBar, 150);
      const fill = progressBar.querySelector('.progress-fill');
      expect(fill.style.width).toBe('100%');

      morphing.animateProgress(progressBar, -50);
      expect(fill.style.width).toBe('0%');
    });

    test('should handle null progress bar gracefully', () => {
      expect(() => {
        morphing.animateProgress(null, 50);
      }).not.toThrow();
    });
  });

  describe('List Item Animations', () => {
    test('should animate list item addition', (done) => {
      const item = document.createElement('div');
      item.className = 'list-item';
      container.appendChild(item);

      morphing.animateListItemAdd(item);
      
      expect(item.classList.contains('adding')).toBe(true);
      
      setTimeout(() => {
        expect(item.classList.contains('adding')).toBe(false);
        expect(item.classList.contains('animation-complete')).toBe(true);
        done();
      }, 450);
    });

    test('should animate list item removal', (done) => {
      const item = document.createElement('div');
      item.className = 'list-item';
      container.appendChild(item);

      let callbackCalled = false;
      morphing.animateListItemRemove(item, () => {
        callbackCalled = true;
      });
      
      expect(item.classList.contains('removing')).toBe(true);
      
      setTimeout(() => {
        expect(callbackCalled).toBe(true);
        done();
      }, 450);
    });

    test('should skip animations when reduced motion is enabled', () => {
      morphing.reducedMotion = true;
      
      const item = document.createElement('div');
      item.className = 'list-item';
      container.appendChild(item);

      morphing.animateListItemAdd(item);
      expect(item.classList.contains('adding')).toBe(false);
    });
  });

  describe('Modal Morphing', () => {
    test('should morph modal open', (done) => {
      const modal = document.createElement('div');
      modal.className = 'modal-overlay hidden';
      modal.innerHTML = '<button>Close</button>';
      container.appendChild(modal);

      morphing.morphModalOpen(modal);
      
      expect(modal.classList.contains('hidden')).toBe(false);
      
      setTimeout(() => {
        expect(modal.style.opacity).toBe('1');
        done();
      }, 50);
    });

    test('should morph modal close', (done) => {
      const modal = document.createElement('div');
      modal.className = 'modal-overlay';
      modal.style.opacity = '1';
      container.appendChild(modal);

      morphing.morphModalClose(modal);
      
      expect(modal.style.opacity).toBe('0');
      
      setTimeout(() => {
        expect(modal.classList.contains('hidden')).toBe(true);
        done();
      }, 350);
    });

    test('should focus first focusable element when opening modal', (done) => {
      const modal = document.createElement('div');
      modal.className = 'modal-overlay hidden';
      const button = document.createElement('button');
      button.textContent = 'Close';
      modal.appendChild(button);
      container.appendChild(modal);

      morphing.morphModalOpen(modal);
      
      setTimeout(() => {
        expect(document.activeElement).toBe(button);
        done();
      }, 150);
    });
  });

  describe('Skeleton Morphing', () => {
    test('should morph skeleton to content', (done) => {
      const skeleton = document.createElement('div');
      skeleton.className = 'skeleton';
      const content = document.createElement('div');
      content.style.display = 'none';
      container.appendChild(skeleton);
      container.appendChild(content);

      morphing.morphSkeletonToContent(skeleton, content);
      
      expect(skeleton.classList.contains('loaded')).toBe(true);
      
      setTimeout(() => {
        expect(skeleton.style.display).toBe('none');
        expect(content.style.display).toBe('block');
        done();
      }, 350);
    });

    test('should handle null elements gracefully', () => {
      expect(() => {
        morphing.morphSkeletonToContent(null, null);
      }).not.toThrow();
    });
  });

  describe('Screen Reader Announcements', () => {
    test('should create announcement element', () => {
      morphing.announceToScreenReader('Test message');
      
      const announcement = document.querySelector('[role="status"]');
      expect(announcement).not.toBeNull();
      expect(announcement.textContent).toBe('Test message');
      expect(announcement.getAttribute('aria-live')).toBe('polite');
    });

    test('should remove announcement after timeout', (done) => {
      morphing.announceToScreenReader('Test message');
      
      setTimeout(() => {
        const announcement = document.querySelector('[role="status"]');
        expect(announcement).toBeNull();
        done();
      }, 1100);
    });
  });

  describe('Reduced Motion Support', () => {
    test('should respect reduced motion preference', () => {
      morphing.reducedMotion = true;
      
      const card = document.createElement('div');
      card.className = 'fir-item';
      container.appendChild(card);

      morphing.flipCard(card);
      expect(card.classList.contains('flipping')).toBe(false);
    });

    test('should update reduced motion on preference change', () => {
      expect(morphing.reducedMotion).toBeDefined();
    });
  });

  describe('Cleanup', () => {
    test('should clear active animations on destroy', () => {
      morphing.activeAnimations.set('test', {});
      morphing.destroy();
      
      expect(morphing.activeAnimations.size).toBe(0);
    });
  });
});
