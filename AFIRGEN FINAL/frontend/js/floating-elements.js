/**
 * Floating Elements Module
 * 
 * Provides floating UI elements including:
 * - Floating Action Buttons (FAB) with expand/collapse
 * - Floating Labels for input fields
 * - Floating Tooltips with animations
 * 
 * All effects respect prefers-reduced-motion and are optimized for 60fps
 */

class FloatingElements {
  constructor() {
    this.fabs = new Map();
    this.tooltips = new Map();
    this.floatingLabels = new Map();
    this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    // Listen for reduced motion preference changes
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
      this.reducedMotion = e.matches;
    });
  }

  /**
   * Create a Floating Action Button (FAB)
   * @param {Object} options - FAB configuration
   * @returns {HTMLElement} The created FAB element
   */
  createFAB(options = {}) {
    const {
      position = 'bottom-right',
      icon = '✚',
      ariaLabel = 'Floating action button',
      actions = [],
      color = '#007bff',
      size = 56
    } = options;

    // Create main FAB button
    const fab = document.createElement('button');
    fab.className = `fab fab-${position}`;
    fab.innerHTML = icon;
    fab.setAttribute('aria-label', ariaLabel);
    fab.setAttribute('aria-expanded', 'false');
    fab.style.width = `${size}px`;
    fab.style.height = `${size}px`;
    fab.style.backgroundColor = color;

    // Create actions container
    const actionsContainer = document.createElement('div');
    actionsContainer.className = 'fab-actions';
    actionsContainer.setAttribute('role', 'menu');
    actionsContainer.setAttribute('aria-hidden', 'true');

    // Create action buttons
    actions.forEach((action, index) => {
      const actionBtn = document.createElement('button');
      actionBtn.className = 'fab-action';
      actionBtn.innerHTML = action.icon || '•';
      actionBtn.setAttribute('aria-label', action.label || `Action ${index + 1}`);
      actionBtn.setAttribute('role', 'menuitem');
      actionBtn.style.transitionDelay = this.reducedMotion ? '0s' : `${index * 0.05}s`;
      
      if (action.onClick) {
        actionBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          action.onClick(e);
          this.collapseFAB(fab);
        });
      }

      actionsContainer.appendChild(actionBtn);
    });

    // Toggle FAB on click
    let isExpanded = false;
    fab.addEventListener('click', () => {
      isExpanded = !isExpanded;
      if (isExpanded) {
        this.expandFAB(fab);
      } else {
        this.collapseFAB(fab);
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isExpanded) {
        this.collapseFAB(fab);
        isExpanded = false;
      }
    });

    // Append to container
    const container = document.createElement('div');
    container.className = 'fab-container';
    container.appendChild(fab);
    container.appendChild(actionsContainer);

    // Store reference
    this.fabs.set(fab, { container, actionsContainer, isExpanded });

    return container;
  }

  /**
   * Expand FAB to show actions
   * @param {HTMLElement} fab - FAB button element
   */
  expandFAB(fab) {
    const fabData = this.fabs.get(fab);
    if (!fabData) return;

    fab.setAttribute('aria-expanded', 'true');
    fabData.actionsContainer.setAttribute('aria-hidden', 'false');
    fabData.actionsContainer.classList.add('fab-actions-expanded');
    fab.classList.add('fab-expanded');
    fabData.isExpanded = true;

    // Rotate icon
    if (!this.reducedMotion) {
      fab.style.transform = 'rotate(45deg)';
    }
  }

  /**
   * Collapse FAB to hide actions
   * @param {HTMLElement} fab - FAB button element
   */
  collapseFAB(fab) {
    const fabData = this.fabs.get(fab);
    if (!fabData) return;

    fab.setAttribute('aria-expanded', 'false');
    fabData.actionsContainer.setAttribute('aria-hidden', 'true');
    fabData.actionsContainer.classList.remove('fab-actions-expanded');
    fab.classList.remove('fab-expanded');
    fabData.isExpanded = false;

    // Reset rotation
    fab.style.transform = 'rotate(0deg)';
  }

  /**
   * Initialize floating labels for input fields
   * @param {string} selector - CSS selector for input containers
   */
  initFloatingLabels(selector) {
    const containers = document.querySelectorAll(selector);

    containers.forEach(container => {
      const input = container.querySelector('input, textarea, select');
      const label = container.querySelector('label');

      if (!input || !label) return;

      // Add floating label class
      container.classList.add('floating-label-container');
      label.classList.add('floating-label');

      // Check if input has value on init
      if (input.value) {
        label.classList.add('floating-label-active');
      }

      // Handle focus
      input.addEventListener('focus', () => {
        label.classList.add('floating-label-active');
        container.classList.add('floating-label-focused');
      });

      // Handle blur
      input.addEventListener('blur', () => {
        container.classList.remove('floating-label-focused');
        if (!input.value) {
          label.classList.remove('floating-label-active');
        }
      });

      // Handle input change
      input.addEventListener('input', () => {
        if (input.value) {
          label.classList.add('floating-label-active');
        } else {
          label.classList.remove('floating-label-active');
        }
      });

      // Store reference
      this.floatingLabels.set(input, { container, label });
    });
  }

  /**
   * Create a floating tooltip
   * @param {HTMLElement} element - Element to attach tooltip to
   * @param {Object} options - Tooltip configuration
   */
  createTooltip(element, options = {}) {
    const {
      content = '',
      position = 'top',
      delay = 300,
      ariaLabel = content
    } = options;

    // Create tooltip element
    const tooltip = document.createElement('div');
    tooltip.className = `floating-tooltip floating-tooltip-${position}`;
    tooltip.textContent = content;
    tooltip.setAttribute('role', 'tooltip');
    tooltip.setAttribute('aria-hidden', 'true');

    // Add aria-describedby to element
    const tooltipId = `tooltip-${Math.random().toString(36).substr(2, 9)}`;
    tooltip.id = tooltipId;
    element.setAttribute('aria-describedby', tooltipId);

    let showTimeout;
    let hideTimeout;

    // Show tooltip on hover
    element.addEventListener('mouseenter', () => {
      clearTimeout(hideTimeout);
      showTimeout = setTimeout(() => {
        this.showTooltip(element, tooltip);
      }, this.reducedMotion ? 0 : delay);
    });

    // Hide tooltip on leave
    element.addEventListener('mouseleave', () => {
      clearTimeout(showTimeout);
      hideTimeout = setTimeout(() => {
        this.hideTooltip(tooltip);
      }, this.reducedMotion ? 0 : 100);
    });

    // Show on focus (keyboard navigation)
    element.addEventListener('focus', () => {
      clearTimeout(hideTimeout);
      this.showTooltip(element, tooltip);
    });

    // Hide on blur
    element.addEventListener('blur', () => {
      clearTimeout(showTimeout);
      this.hideTooltip(tooltip);
    });

    // Append tooltip to body
    document.body.appendChild(tooltip);

    // Store reference
    this.tooltips.set(element, tooltip);

    return tooltip;
  }

  /**
   * Show tooltip
   * @param {HTMLElement} element - Element the tooltip is attached to
   * @param {HTMLElement} tooltip - Tooltip element
   */
  showTooltip(element, tooltip) {
    // Position tooltip
    const rect = element.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();

    // Get position from class
    const position = Array.from(tooltip.classList)
      .find(cls => cls.startsWith('floating-tooltip-'))
      ?.replace('floating-tooltip-', '') || 'top';

    let top, left;

    switch (position) {
      case 'top':
        top = rect.top - tooltipRect.height - 8;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
        break;
      case 'bottom':
        top = rect.bottom + 8;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
        break;
      case 'left':
        top = rect.top + (rect.height - tooltipRect.height) / 2;
        left = rect.left - tooltipRect.width - 8;
        break;
      case 'right':
        top = rect.top + (rect.height - tooltipRect.height) / 2;
        left = rect.right + 8;
        break;
      default:
        top = rect.top - tooltipRect.height - 8;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
    }

    // Keep tooltip within viewport
    const padding = 8;
    top = Math.max(padding, Math.min(top, window.innerHeight - tooltipRect.height - padding));
    left = Math.max(padding, Math.min(left, window.innerWidth - tooltipRect.width - padding));

    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;
    tooltip.classList.add('floating-tooltip-visible');
    tooltip.setAttribute('aria-hidden', 'false');
  }

  /**
   * Hide tooltip
   * @param {HTMLElement} tooltip - Tooltip element
   */
  hideTooltip(tooltip) {
    tooltip.classList.remove('floating-tooltip-visible');
    tooltip.setAttribute('aria-hidden', 'true');
  }

  /**
   * Remove FAB
   * @param {HTMLElement} fab - FAB button element
   */
  removeFAB(fab) {
    const fabData = this.fabs.get(fab);
    if (fabData) {
      fabData.container.remove();
      this.fabs.delete(fab);
    }
  }

  /**
   * Remove tooltip
   * @param {HTMLElement} element - Element the tooltip is attached to
   */
  removeTooltip(element) {
    const tooltip = this.tooltips.get(element);
    if (tooltip) {
      tooltip.remove();
      this.tooltips.delete(element);
    }
  }

  /**
   * Cleanup all floating elements
   */
  destroy() {
    // Remove all FABs
    this.fabs.forEach((fabData) => {
      fabData.container.remove();
    });
    this.fabs.clear();

    // Remove all tooltips
    this.tooltips.forEach((tooltip) => {
      tooltip.remove();
    });
    this.tooltips.clear();

    // Clear floating labels
    this.floatingLabels.clear();
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FloatingElements;
}

// Auto-initialize on DOM ready
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    window.floatingElements = new FloatingElements();
  });
}
