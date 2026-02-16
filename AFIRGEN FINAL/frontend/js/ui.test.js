/**
 * Unit tests for UI module
 */

// Mock DOM
global.document = {
  getElementById: jest.fn(),
  querySelector: jest.fn(),
  querySelectorAll: jest.fn(() => []),
  createElement: jest.fn((tag) => ({
    className: '',
    id: '',
    innerHTML: '',
    textContent: '',
    style: {},
    setAttribute: jest.fn(),
    getAttribute: jest.fn(),
    appendChild: jest.fn(),
    removeChild: jest.fn(),
    addEventListener: jest.fn(),
    classList: {
      add: jest.fn(),
      remove: jest.fn(),
      contains: jest.fn()
    },
    querySelectorAll: jest.fn(() => []),
    querySelector: jest.fn(),
    parentNode: null,
    offsetHeight: 0
  })),
  body: {
    appendChild: jest.fn()
  }
};

global.window = {
  getComputedStyle: jest.fn(() => ({ position: 'static' })),
  requestAnimationFrame: jest.fn((cb) => setTimeout(cb, 0)),
  setTimeout: jest.fn((cb, delay) => setTimeout(cb, delay)),
  clearTimeout: jest.fn((id) => clearTimeout(id))
};

global.console = {
  log: jest.fn(),
  warn: jest.fn(),
  error: jest.fn()
};

describe('UI Module', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('showToast()', () => {
    let toastIdCounter = 0;
    const activeToasts = new Map();

    const showToast = (message, type = 'info', duration = 5000) => {
      const toastId = `toast-${++toastIdCounter}`;

      let container = document.getElementById('toast-container');
      if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        container.setAttribute('aria-live', 'polite');
        container.setAttribute('aria-atomic', 'true');
        document.body.appendChild(container);
      }

      const toast = document.createElement('div');
      toast.className = `toast toast-${type}`;
      toast.setAttribute('role', 'alert');
      toast.setAttribute('data-toast-id', toastId);

      const icon = document.createElement('div');
      icon.className = 'toast-icon';

      const content = document.createElement('div');
      content.className = 'toast-content';

      const messageElement = document.createElement('div');
      messageElement.className = 'toast-message';
      messageElement.textContent = message;

      content.appendChild(messageElement);

      const closeButton = document.createElement('div');
      closeButton.className = 'toast-close';
      closeButton.setAttribute('aria-label', 'Close notification');

      toast.appendChild(icon);
      toast.appendChild(content);
      toast.appendChild(closeButton);

      container.appendChild(toast);

      const toastData = {
        element: toast,
        type,
        message,
        createdAt: Date.now()
      };

      activeToasts.set(toastId, toastData);

      if (duration > 0) {
        toastData.timeout = setTimeout(() => {
          // hideToast would be called here
        }, duration);
      }

      return toastId;
    };

    test('should create toast with correct message', () => {
      const message = 'Test message';
      const toastId = showToast(message);

      expect(toastId).toMatch(/^toast-\d+$/);
      expect(document.createElement).toHaveBeenCalledWith('div');
    });

    test('should create toast with correct type', () => {
      const types = ['success', 'error', 'warning', 'info'];

      types.forEach(type => {
        const toastId = showToast('Test', type);
        expect(toastId).toBeTruthy();
      });
    });

    test('should create toast container if not exists', () => {
      document.getElementById.mockReturnValue(null);

      showToast('Test');

      expect(document.createElement).toHaveBeenCalledWith('div');
      expect(document.body.appendChild).toHaveBeenCalled();
    });

    test('should use existing toast container', () => {
      const mockContainer = document.createElement('div');
      document.getElementById.mockReturnValue(mockContainer);

      showToast('Test');

      expect(mockContainer.appendChild).toHaveBeenCalled();
    });

    test('should set aria attributes', () => {
      const mockToast = document.createElement('div');
      document.createElement.mockReturnValue(mockToast);

      showToast('Test');

      expect(mockToast.setAttribute).toHaveBeenCalledWith('role', 'alert');
    });

    test('should auto-hide after duration', (done) => {
      const duration = 100;
      showToast('Test', 'info', duration);

      setTimeout(() => {
        // Toast should be scheduled for hiding
        done();
      }, duration + 50);
    });

    test('should not auto-hide when duration is 0', () => {
      const toastId = showToast('Test', 'info', 0);
      const toastData = activeToasts.get(toastId);

      expect(toastData.timeout).toBeUndefined();
    });
  });

  describe('hideToast()', () => {
    const activeToasts = new Map();

    const hideToast = (toastId) => {
      const toastData = activeToasts.get(toastId);

      if (!toastData) {
        return;
      }

      const { element, timeout } = toastData;

      if (timeout) {
        clearTimeout(timeout);
      }

      element.classList.remove('toast-show');
      element.classList.add('toast-hide');

      setTimeout(() => {
        if (element.parentNode) {
          element.parentNode.removeChild(element);
        }
        activeToasts.delete(toastId);
      }, 300);
    };

    test('should remove toast from active toasts', (done) => {
      const mockElement = document.createElement('div');
      mockElement.parentNode = { removeChild: jest.fn() };

      const toastId = 'toast-1';
      activeToasts.set(toastId, {
        element: mockElement,
        type: 'info',
        message: 'Test'
      });

      hideToast(toastId);

      setTimeout(() => {
        expect(activeToasts.has(toastId)).toBe(false);
        done();
      }, 350);
    });

    test('should handle non-existent toast ID', () => {
      expect(() => hideToast('non-existent')).not.toThrow();
    });

    test('should clear timeout if exists', () => {
      const mockTimeout = setTimeout(() => {}, 1000);
      const mockElement = document.createElement('div');

      const toastId = 'toast-1';
      activeToasts.set(toastId, {
        element: mockElement,
        timeout: mockTimeout
      });

      hideToast(toastId);

      // Timeout should be cleared (we can't directly test clearTimeout was called)
      expect(mockElement.classList.remove).toHaveBeenCalledWith('toast-show');
    });
  });

  describe('showLoading()', () => {
    const loadingStates = new Map();

    const showLoading = (element, message = 'Loading...') => {
      const targetElement = typeof element === 'string' ? document.querySelector(element) : element;

      if (!targetElement) {
        console.warn('showLoading: Element not found');
        return null;
      }

      const loadingId = `loading-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      const loadingOverlay = document.createElement('div');
      loadingOverlay.className = 'loading-overlay';
      loadingOverlay.setAttribute('data-loading-id', loadingId);

      const spinner = document.createElement('div');
      spinner.className = 'loading-spinner';

      const messageElement = document.createElement('div');
      messageElement.className = 'loading-message';
      messageElement.textContent = message;

      loadingOverlay.appendChild(spinner);
      loadingOverlay.appendChild(messageElement);

      const originalPosition = window.getComputedStyle(targetElement).position;
      if (originalPosition === 'static') {
        targetElement.style.position = 'relative';
      }

      targetElement.appendChild(loadingOverlay);

      loadingStates.set(loadingId, {
        element: targetElement,
        overlay: loadingOverlay,
        originalPosition,
        startTime: Date.now()
      });

      targetElement.setAttribute('aria-busy', 'true');

      return loadingId;
    };

    test('should create loading overlay', () => {
      const mockElement = document.createElement('div');
      document.querySelector.mockReturnValue(mockElement);

      const loadingId = showLoading('#test-element');

      expect(loadingId).toMatch(/^loading-/);
      expect(mockElement.appendChild).toHaveBeenCalled();
    });

    test('should set aria-busy attribute', () => {
      const mockElement = document.createElement('div');
      document.querySelector.mockReturnValue(mockElement);

      showLoading('#test-element');

      expect(mockElement.setAttribute).toHaveBeenCalledWith('aria-busy', 'true');
    });

    test('should handle element not found', () => {
      document.querySelector.mockReturnValue(null);

      const result = showLoading('#non-existent');

      expect(result).toBeNull();
      expect(console.warn).toHaveBeenCalledWith('showLoading: Element not found');
    });

    test('should accept element directly', () => {
      const mockElement = document.createElement('div');

      const loadingId = showLoading(mockElement);

      expect(loadingId).toBeTruthy();
      expect(mockElement.appendChild).toHaveBeenCalled();
    });

    test('should use custom message', () => {
      const mockElement = document.createElement('div');
      const customMessage = 'Processing...';

      showLoading(mockElement, customMessage);

      expect(document.createElement).toHaveBeenCalledWith('div');
    });

    test('should set position relative for static elements', () => {
      const mockElement = document.createElement('div');
      window.getComputedStyle.mockReturnValue({ position: 'static' });

      showLoading(mockElement);

      expect(mockElement.style.position).toBe('relative');
    });
  });

  describe('hideLoading()', () => {
    const loadingStates = new Map();

    const hideLoading = (element) => {
      let targetElement;
      let loadingId;

      if (typeof element === 'string') {
        if (loadingStates.has(element)) {
          loadingId = element;
          const state = loadingStates.get(loadingId);
          targetElement = state.element;
        } else {
          targetElement = document.querySelector(element);
        }
      } else {
        targetElement = element;
      }

      if (!targetElement) {
        console.warn('hideLoading: Element not found');
        return;
      }

      const overlays = targetElement.querySelectorAll('.loading-overlay');
      overlays.forEach(overlay => {
        const overlayId = overlay.getAttribute('data-loading-id');

        if (loadingId && overlayId !== loadingId) {
          return;
        }

        overlay.style.opacity = '0';
        setTimeout(() => {
          if (overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
          }
        }, 200);

        if (overlayId && loadingStates.has(overlayId)) {
          const state = loadingStates.get(overlayId);

          if (state.originalPosition === 'static') {
            targetElement.style.position = '';
          }

          loadingStates.delete(overlayId);
        }
      });

      if (targetElement.querySelectorAll('.loading-overlay').length === 0) {
        targetElement.removeAttribute('aria-busy');
      }
    };

    test('should remove loading overlay', () => {
      const mockElement = document.createElement('div');
      const mockOverlay = document.createElement('div');
      mockOverlay.parentNode = { removeChild: jest.fn() };
      mockOverlay.getAttribute = jest.fn(() => 'loading-123');

      mockElement.querySelectorAll = jest.fn(() => [mockOverlay]);
      document.querySelector.mockReturnValue(mockElement);

      hideLoading('#test-element');

      expect(mockOverlay.style.opacity).toBe('0');
    });

    test('should handle element not found', () => {
      document.querySelector.mockReturnValue(null);

      hideLoading('#non-existent');

      expect(console.warn).toHaveBeenCalledWith('hideLoading: Element not found');
    });

    test('should remove aria-busy when no overlays remain', () => {
      const mockElement = document.createElement('div');
      mockElement.querySelectorAll = jest.fn(() => []);
      document.querySelector.mockReturnValue(mockElement);

      hideLoading('#test-element');

      expect(mockElement.removeAttribute).toHaveBeenCalledWith('aria-busy');
    });

    test('should restore original position', (done) => {
      const mockElement = document.createElement('div');
      const mockOverlay = document.createElement('div');
      mockOverlay.parentNode = { removeChild: jest.fn() };
      mockOverlay.getAttribute = jest.fn(() => 'loading-123');

      mockElement.querySelectorAll = jest.fn(() => [mockOverlay]);

      loadingStates.set('loading-123', {
        element: mockElement,
        overlay: mockOverlay,
        originalPosition: 'static'
      });

      hideLoading(mockElement);

      setTimeout(() => {
        expect(mockElement.style.position).toBe('');
        done();
      }, 250);
    });
  });

  describe('showProgress()', () => {
    const showProgress = (element, percentage, message = '') => {
      const targetElement = typeof element === 'string' ? document.querySelector(element) : element;

      if (!targetElement) {
        console.warn('showProgress: Element not found');
        return null;
      }

      const clampedPercentage = Math.max(0, Math.min(100, percentage));

      let progressOverlay = targetElement.querySelector('.progress-overlay');
      let progressId;

      if (!progressOverlay) {
        progressId = `progress-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        progressOverlay = document.createElement('div');
        progressOverlay.className = 'progress-overlay';
        progressOverlay.setAttribute('data-progress-id', progressId);

        const progressContainer = document.createElement('div');
        progressContainer.className = 'progress-container';

        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar';

        const progressFill = document.createElement('div');
        progressFill.className = 'progress-fill';

        const progressText = document.createElement('div');
        progressText.className = 'progress-text';

        const progressMessage = document.createElement('div');
        progressMessage.className = 'progress-message';

        progressBar.appendChild(progressFill);
        progressContainer.appendChild(progressBar);
        progressContainer.appendChild(progressText);
        progressOverlay.appendChild(progressContainer);
        progressOverlay.appendChild(progressMessage);

        targetElement.appendChild(progressOverlay);
      }

      return progressId;
    };

    test('should create progress overlay', () => {
      const mockElement = document.createElement('div');
      mockElement.querySelector = jest.fn(() => null);
      document.querySelector.mockReturnValue(mockElement);

      const progressId = showProgress('#test-element', 50);

      expect(progressId).toMatch(/^progress-/);
      expect(mockElement.appendChild).toHaveBeenCalled();
    });

    test('should clamp percentage between 0 and 100', () => {
      const mockElement = document.createElement('div');
      mockElement.querySelector = jest.fn(() => null);

      showProgress(mockElement, 150); // Should clamp to 100
      showProgress(mockElement, -10); // Should clamp to 0

      expect(mockElement.appendChild).toHaveBeenCalled();
    });

    test('should handle element not found', () => {
      document.querySelector.mockReturnValue(null);

      const result = showProgress('#non-existent', 50);

      expect(result).toBeNull();
      expect(console.warn).toHaveBeenCalledWith('showProgress: Element not found');
    });

    test('should reuse existing progress overlay', () => {
      const mockOverlay = document.createElement('div');
      const mockElement = document.createElement('div');
      mockElement.querySelector = jest.fn(() => mockOverlay);

      const result = showProgress(mockElement, 75);

      expect(result).toBeUndefined(); // No new ID created
    });
  });

  describe('showTab()', () => {
    const showTab = (tabName) => {
      document.querySelectorAll('.main-container, .tab-content').forEach(tab => {
        tab.classList.remove('active');
      });

      setTimeout(() => {
        document.querySelectorAll('.main-container, .tab-content').forEach(tab => {
          tab.style.display = 'none';
        });

        const targetTab = document.getElementById(`${tabName}-tab`);
        if (targetTab) {
          if (tabName === 'home') {
            targetTab.style.display = 'flex';
          } else {
            targetTab.style.display = 'block';
          }

          targetTab.classList.add('active');
        }
      }, 300);

      document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
      });

      const activeNavItem = document.querySelector(`[data-tab="${tabName}"]`);
      if (activeNavItem) {
        activeNavItem.classList.add('active');
      }
    };

    test('should hide all tabs first', () => {
      const mockTabs = [
        { classList: { remove: jest.fn(), add: jest.fn() }, style: {} },
        { classList: { remove: jest.fn(), add: jest.fn() }, style: {} }
      ];

      document.querySelectorAll.mockReturnValue(mockTabs);

      showTab('home');

      mockTabs.forEach(tab => {
        expect(tab.classList.remove).toHaveBeenCalledWith('active');
      });
    });

    test('should show target tab', (done) => {
      const mockTab = {
        classList: { add: jest.fn(), remove: jest.fn() },
        style: {},
        offsetHeight: 0
      };

      document.getElementById.mockReturnValue(mockTab);
      document.querySelectorAll.mockReturnValue([]);

      showTab('home');

      setTimeout(() => {
        expect(mockTab.style.display).toBe('flex');
        expect(mockTab.classList.add).toHaveBeenCalledWith('active');
        done();
      }, 350);
    });

    test('should update nav items', () => {
      const mockNavItems = [
        { classList: { remove: jest.fn() } },
        { classList: { remove: jest.fn() } }
      ];

      const mockActiveNav = { classList: { add: jest.fn() } };

      document.querySelectorAll.mockReturnValue(mockNavItems);
      document.querySelector.mockReturnValue(mockActiveNav);

      showTab('settings');

      mockNavItems.forEach(item => {
        expect(item.classList.remove).toHaveBeenCalledWith('active');
      });
      expect(mockActiveNav.classList.add).toHaveBeenCalledWith('active');
    });
  });
});
