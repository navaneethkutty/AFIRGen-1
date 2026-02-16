/**
 * Morphing Transitions Module
 * 
 * Implements smooth morphing transitions and animations:
 * - Card flip animations for FIR items
 * - Expanding/collapsing animations
 * - Smooth state transitions
 * - Button morphing effects
 * 
 * Optimized for 60fps performance using CSS transforms
 */

class MorphingTransitions {
  constructor() {
    this.activeAnimations = new Map();
    this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    // Listen for reduced motion preference changes
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
      this.reducedMotion = e.matches;
    });
  }

  /**
   * Initialize all morphing transitions
   */
  init() {
    this.setupCardFlips();
    this.setupExpandCollapse();
    this.setupAccordions();
    this.setupButtonMorphs();
    this.setupListAnimations();
    this.setupSearchMorph();
  }

  /**
   * Set up card flip animations for FIR items
   */
  setupCardFlips() {
    const firItems = document.querySelectorAll('.fir-item');
    
    firItems.forEach(item => {
      // Add double-click to flip
      item.addEventListener('dblclick', () => {
        this.flipCard(item);
      });
      
      // Add keyboard support (Enter key to flip)
      item.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.repeat) {
          this.flipCard(item);
        }
      });
    });
  }

  /**
   * Flip a card element
   * @param {HTMLElement} card - Card element to flip
   */
  flipCard(card) {
    if (this.reducedMotion) {
      return;
    }

    const isFlipped = card.classList.contains('flipping');
    
    if (isFlipped) {
      card.classList.remove('flipping');
      card.setAttribute('aria-label', 'Card front side');
    } else {
      card.classList.add('flipping');
      card.setAttribute('aria-label', 'Card back side');
    }

    // Announce to screen readers
    this.announceToScreenReader(
      isFlipped ? 'Card flipped to front' : 'Card flipped to back'
    );
  }

  /**
   * Set up expand/collapse animations
   */
  setupExpandCollapse() {
    const expandables = document.querySelectorAll('[data-expandable]');
    
    expandables.forEach(element => {
      const trigger = element.querySelector('[data-expand-trigger]');
      const content = element.querySelector('[data-expand-content]');
      
      if (!trigger || !content) {
        return;
      }

      // Set initial state
      content.classList.add('expandable', 'collapsed');
      
      trigger.addEventListener('click', () => {
        this.toggleExpand(content, trigger);
      });
    });
  }

  /**
   * Toggle expand/collapse state
   * @param {HTMLElement} content - Content element to expand/collapse
   * @param {HTMLElement} trigger - Trigger element (optional)
   */
  toggleExpand(content, trigger = null) {
    const isCollapsed = content.classList.contains('collapsed');
    
    if (isCollapsed) {
      this.expand(content, trigger);
    } else {
      this.collapse(content, trigger);
    }
  }

  /**
   * Expand an element
   * @param {HTMLElement} element - Element to expand
   * @param {HTMLElement} trigger - Trigger element (optional)
   */
  expand(element, trigger = null) {
    if (this.reducedMotion) {
      element.classList.remove('collapsed');
      element.classList.add('expanded');
      if (trigger) {
        trigger.setAttribute('aria-expanded', 'true');
      }
      return;
    }

    // Get the natural height
    element.style.maxHeight = 'none';
    const height = element.scrollHeight;
    element.style.maxHeight = '0';
    
    // Force reflow
    element.offsetHeight;
    
    // Animate to natural height
    element.classList.remove('collapsed');
    element.classList.add('expanded');
    element.style.maxHeight = `${height}px`;
    
    if (trigger) {
      trigger.setAttribute('aria-expanded', 'true');
    }

    // Remove inline style after animation
    setTimeout(() => {
      element.style.maxHeight = '';
      element.classList.add('animation-complete');
    }, 400);

    this.announceToScreenReader('Section expanded');
  }

  /**
   * Collapse an element
   * @param {HTMLElement} element - Element to collapse
   * @param {HTMLElement} trigger - Trigger element (optional)
   */
  collapse(element, trigger = null) {
    if (this.reducedMotion) {
      element.classList.remove('expanded');
      element.classList.add('collapsed');
      if (trigger) {
        trigger.setAttribute('aria-expanded', 'false');
      }
      return;
    }

    // Set current height
    const height = element.scrollHeight;
    element.style.maxHeight = `${height}px`;
    
    // Force reflow
    element.offsetHeight;
    
    // Animate to 0
    element.classList.remove('expanded');
    element.classList.add('collapsed');
    element.style.maxHeight = '0';
    
    if (trigger) {
      trigger.setAttribute('aria-expanded', 'false');
    }

    // Remove inline style after animation
    setTimeout(() => {
      element.style.maxHeight = '';
      element.classList.add('animation-complete');
    }, 400);

    this.announceToScreenReader('Section collapsed');
  }

  /**
   * Set up accordion animations
   */
  setupAccordions() {
    const accordions = document.querySelectorAll('.accordion-item');
    
    accordions.forEach(accordion => {
      const header = accordion.querySelector('.accordion-header');
      const content = accordion.querySelector('.accordion-content');
      
      if (!header || !content) {
        return;
      }

      header.addEventListener('click', () => {
        this.toggleAccordion(accordion);
      });

      // Keyboard support
      header.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.toggleAccordion(accordion);
        }
      });
    });
  }

  /**
   * Toggle accordion state
   * @param {HTMLElement} accordion - Accordion element
   */
  toggleAccordion(accordion) {
    const isOpen = accordion.classList.contains('open');
    const header = accordion.querySelector('.accordion-header');
    const content = accordion.querySelector('.accordion-content');
    
    if (isOpen) {
      accordion.classList.remove('open');
      header.setAttribute('aria-expanded', 'false');
      content.setAttribute('aria-hidden', 'true');
      this.announceToScreenReader('Accordion collapsed');
    } else {
      // Close other accordions in the same group (optional)
      const group = accordion.closest('[data-accordion-group]');
      if (group) {
        const siblings = group.querySelectorAll('.accordion-item.open');
        siblings.forEach(sibling => {
          if (sibling !== accordion) {
            this.toggleAccordion(sibling);
          }
        });
      }
      
      accordion.classList.add('open');
      header.setAttribute('aria-expanded', 'true');
      content.setAttribute('aria-hidden', 'false');
      this.announceToScreenReader('Accordion expanded');
    }
  }

  /**
   * Set up button morphing effects
   */
  setupButtonMorphs() {
    const buttons = document.querySelectorAll('.btn-morph');
    
    buttons.forEach(button => {
      button.addEventListener('click', (e) => {
        this.createRipple(e, button);
      });
    });
  }

  /**
   * Create ripple effect on button click
   * @param {Event} event - Click event
   * @param {HTMLElement} button - Button element
   */
  createRipple(event, button) {
    if (this.reducedMotion) {
      return;
    }

    const ripple = document.createElement('span');
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;

    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    ripple.classList.add('ripple');

    button.appendChild(ripple);

    setTimeout(() => {
      ripple.remove();
    }, 600);
  }

  /**
   * Morph button to loading state
   * @param {HTMLElement} button - Button element
   */
  morphToLoading(button) {
    if (!button) {
      return;
    }

    button.classList.add('loading');
    button.setAttribute('aria-busy', 'true');
    button.disabled = true;

    // Create spinner if it doesn't exist
    if (!button.querySelector('.btn-spinner')) {
      const spinner = document.createElement('span');
      spinner.classList.add('btn-spinner');
      spinner.innerHTML = '<div class="spinner-small"></div>';
      button.appendChild(spinner);
    }
  }

  /**
   * Morph button back from loading state
   * @param {HTMLElement} button - Button element
   */
  morphFromLoading(button) {
    if (!button) {
      return;
    }

    button.classList.remove('loading');
    button.setAttribute('aria-busy', 'false');
    button.disabled = false;
  }

  /**
   * Set up list item animations
   */
  setupListAnimations() {
    // Observe list containers for added/removed items
    const listContainers = document.querySelectorAll('[data-animated-list]');
    
    listContainers.forEach(container => {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
          mutation.addedNodes.forEach(node => {
            if (node.nodeType === 1 && node.classList.contains('list-item')) {
              this.animateListItemAdd(node);
            }
          });
          
          mutation.removedNodes.forEach(node => {
            if (node.nodeType === 1 && node.classList.contains('list-item')) {
              // Item already removed, but we can track it for future
            }
          });
        });
      });

      observer.observe(container, {
        childList: true,
        subtree: false
      });
    });
  }

  /**
   * Animate list item addition
   * @param {HTMLElement} item - List item element
   */
  animateListItemAdd(item) {
    if (this.reducedMotion) {
      return;
    }

    item.classList.add('adding');
    
    setTimeout(() => {
      item.classList.remove('adding');
      item.classList.add('animation-complete');
    }, 400);
  }

  /**
   * Animate list item removal
   * @param {HTMLElement} item - List item element
   * @param {Function} callback - Callback after animation
   */
  animateListItemRemove(item, callback) {
    if (this.reducedMotion) {
      if (callback) callback();
      return;
    }

    item.classList.add('removing');
    
    setTimeout(() => {
      if (callback) callback();
    }, 400);
  }

  /**
   * Set up search bar morphing
   */
  setupSearchMorph() {
    const searchContainers = document.querySelectorAll('.search-container');
    
    searchContainers.forEach(container => {
      const input = container.querySelector('.search-input');
      
      if (!input) {
        return;
      }

      input.addEventListener('focus', () => {
        container.classList.add('focused');
      });

      input.addEventListener('blur', () => {
        container.classList.remove('focused');
      });

      input.addEventListener('input', () => {
        if (input.value.length > 0) {
          container.classList.add('has-value');
        } else {
          container.classList.remove('has-value');
        }
      });
    });
  }

  /**
   * Morph modal open
   * @param {HTMLElement} modal - Modal element
   */
  morphModalOpen(modal) {
    if (!modal) {
      return;
    }

    modal.classList.remove('hidden');
    
    // Force reflow
    modal.offsetHeight;
    
    // Trigger animation
    requestAnimationFrame(() => {
      modal.style.opacity = '1';
    });

    // Focus management
    const firstFocusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (firstFocusable) {
      setTimeout(() => firstFocusable.focus(), 100);
    }

    this.announceToScreenReader('Modal opened');
  }

  /**
   * Morph modal close
   * @param {HTMLElement} modal - Modal element
   */
  morphModalClose(modal) {
    if (!modal) {
      return;
    }

    modal.style.opacity = '0';
    
    setTimeout(() => {
      modal.classList.add('hidden');
    }, 300);

    this.announceToScreenReader('Modal closed');
  }

  /**
   * Morph status badge
   * @param {HTMLElement} badge - Badge element
   * @param {string} newStatus - New status value
   */
  morphStatusBadge(badge, newStatus) {
    if (!badge) {
      return;
    }

    badge.classList.add('morphing');
    
    setTimeout(() => {
      // Remove old status classes
      badge.classList.remove('pending', 'investigating', 'closed');
      
      // Add new status class
      badge.classList.add(newStatus);
      
      // Update text
      badge.textContent = newStatus.charAt(0).toUpperCase() + newStatus.slice(1);
      
      setTimeout(() => {
        badge.classList.remove('morphing');
      }, 150);
    }, 150);

    this.announceToScreenReader(`Status changed to ${newStatus}`);
  }

  /**
   * Animate progress bar
   * @param {HTMLElement} progressBar - Progress bar element
   * @param {number} percentage - Target percentage (0-100)
   */
  animateProgress(progressBar, percentage) {
    if (!progressBar) {
      return;
    }

    const fill = progressBar.querySelector('.progress-fill');
    if (!fill) {
      return;
    }

    const clampedPercentage = Math.max(0, Math.min(100, percentage));
    fill.style.width = `${clampedPercentage}%`;
    
    progressBar.setAttribute('aria-valuenow', clampedPercentage);
    this.announceToScreenReader(`Progress: ${clampedPercentage}%`);
  }

  /**
   * Morph skeleton to content
   * @param {HTMLElement} skeleton - Skeleton element
   * @param {HTMLElement} content - Content element to show
   */
  morphSkeletonToContent(skeleton, content) {
    if (!skeleton || !content) {
      return;
    }

    skeleton.classList.add('loaded');
    
    setTimeout(() => {
      skeleton.style.display = 'none';
      content.style.display = 'block';
      content.classList.add('adding');
      
      setTimeout(() => {
        content.classList.remove('adding');
      }, 400);
    }, 300);
  }

  /**
   * Announce message to screen readers
   * @param {string} message - Message to announce
   */
  announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    setTimeout(() => {
      announcement.remove();
    }, 1000);
  }

  /**
   * Clean up and remove event listeners
   */
  destroy() {
    this.activeAnimations.clear();
  }
}

// Initialize morphing transitions when DOM is ready
let morphingInstance = null;

function initMorphingTransitions() {
  if (morphingInstance) {
    morphingInstance.destroy();
  }
  
  morphingInstance = new MorphingTransitions();
  morphingInstance.init();
}

// Auto-initialize on DOM ready (only in browser, not in tests)
if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMorphingTransitions);
  } else {
    initMorphingTransitions();
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { MorphingTransitions, initMorphingTransitions };
}

// Make available globally for other scripts (only in browser)
if (typeof window !== 'undefined') {
  window.MorphingTransitions = MorphingTransitions;
  window.morphingInstance = morphingInstance;
}
