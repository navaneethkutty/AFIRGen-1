/**
 * Loading Animations Module
 * Provides functions for custom spinners, skeleton screens, progress bars, and success/error animations
 */

/**
 * Spinner types available
 */
const SpinnerType = {
  DEFAULT: 'default',
  DUAL_RING: 'dual-ring',
  DOTS: 'dots',
  PULSE: 'pulse',
  RIPPLE: 'ripple',
  BARS: 'bars',
  CIRCULAR: 'circular'
};

/**
 * Create a custom spinner element
 * @param {string} type - Spinner type from SpinnerType enum
 * @param {string} size - Size class: 'sm', 'md', 'lg', 'xl'
 * @returns {HTMLElement} Spinner element
 */
function createSpinner(type = SpinnerType.DEFAULT, size = 'md') {
  const spinner = document.createElement('div');
  spinner.className = `spinner-${type} loading-${size}`;

  switch (type) {
  case SpinnerType.DOTS:
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'dot';
      spinner.appendChild(dot);
    }
    break;

  case SpinnerType.RIPPLE:
    for (let i = 0; i < 2; i++) {
      const ripple = document.createElement('div');
      ripple.className = 'ripple';
      spinner.appendChild(ripple);
    }
    break;

  case SpinnerType.BARS:
    for (let i = 0; i < 4; i++) {
      const bar = document.createElement('div');
      bar.className = 'bar';
      spinner.appendChild(bar);
    }
    break;

  case SpinnerType.CIRCULAR:
    spinner.innerHTML = `
        <svg viewBox="0 0 50 50">
          <circle cx="25" cy="25" r="20"></circle>
        </svg>
      `;
    break;

  default:
    // Default and dual-ring don't need children
    break;
  }

  return spinner;
}

/**
 * Show a custom loading spinner
 * @param {HTMLElement|string} element - Element or selector to show loading on
 * @param {Object} options - Loading options
 * @returns {string} Loading ID for tracking
 */
function showCustomLoading(element, options = {}) {
  const {
    type = SpinnerType.DEFAULT,
    size = 'md',
    message = 'Loading...',
    overlay = true
  } = options;

  const targetElement = typeof element === 'string' ? document.querySelector(element) : element;

  if (!targetElement) {
    console.warn('showCustomLoading: Element not found');
    return null;
  }

  // Generate unique loading ID
  const loadingId = `loading-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  // Create loading container
  const loadingContainer = document.createElement('div');
  loadingContainer.className = overlay ? 'loading-overlay' : 'loading-container';
  loadingContainer.setAttribute('data-loading-id', loadingId);

  // Create spinner
  const spinner = createSpinner(type, size);

  // Create message
  const messageElement = document.createElement('div');
  messageElement.className = 'loading-message';
  messageElement.textContent = message;

  // Assemble loading UI
  loadingContainer.appendChild(spinner);
  if (message) {
    loadingContainer.appendChild(messageElement);
  }

  // Store original position style if overlay
  if (overlay) {
    const originalPosition = window.getComputedStyle(targetElement).position;
    if (originalPosition === 'static') {
      targetElement.style.position = 'relative';
    }
  }

  // Add loading container to element
  targetElement.appendChild(loadingContainer);

  // Set aria-busy for accessibility
  targetElement.setAttribute('aria-busy', 'true');

  return loadingId;
}

/**
 * Create a skeleton element
 * @param {string} type - Skeleton type: 'text', 'title', 'avatar', 'button', 'input', 'card'
 * @param {Object} options - Skeleton options
 * @returns {HTMLElement} Skeleton element
 */
function createSkeleton(type = 'text', options = {}) {
  const { size = 'md', width, height } = options;

  const skeleton = document.createElement('div');
  skeleton.className = `skeleton skeleton-${type}`;

  if (size && size !== 'md') {
    skeleton.classList.add(`skeleton-${type}-${size}`);
  }

  if (width) {
    skeleton.style.width = typeof width === 'number' ? `${width}px` : width;
  }

  if (height) {
    skeleton.style.height = typeof height === 'number' ? `${height}px` : height;
  }

  return skeleton;
}

/**
 * Create a skeleton card
 * @param {Object} options - Card options
 * @returns {HTMLElement} Skeleton card element
 */
function createSkeletonCard(options = {}) {
  const { showAvatar = true, lines = 3 } = options;

  const card = document.createElement('div');
  card.className = 'skeleton-card';

  // Header with avatar
  if (showAvatar) {
    const header = document.createElement('div');
    header.className = 'skeleton-card-header';

    const avatar = createSkeleton('avatar');
    const title = createSkeleton('text', { width: '60%' });

    header.appendChild(avatar);
    header.appendChild(title);
    card.appendChild(header);
  }

  // Body with text lines
  const body = document.createElement('div');
  body.className = 'skeleton-card-body';

  for (let i = 0; i < lines; i++) {
    const line = createSkeleton('text');
    if (i === lines - 1) {
      line.style.width = '80%';
    }
    body.appendChild(line);
  }

  card.appendChild(body);

  return card;
}

/**
 * Create a skeleton FIR list
 * @param {number} count - Number of skeleton items
 * @returns {HTMLElement} Skeleton FIR list element
 */
function createSkeletonFIRList(count = 3) {
  const list = document.createElement('div');
  list.className = 'skeleton-fir-list';

  for (let i = 0; i < count; i++) {
    const item = document.createElement('div');
    item.className = 'skeleton-fir-item';

    // Header
    const header = document.createElement('div');
    header.className = 'skeleton-fir-item-header';

    const number = createSkeleton('text');
    number.className = 'skeleton skeleton-fir-number';

    const status = createSkeleton('text');
    status.className = 'skeleton skeleton-fir-status';

    header.appendChild(number);
    header.appendChild(status);

    // Details
    const details = document.createElement('div');
    details.className = 'skeleton-fir-details';

    for (let j = 0; j < 2; j++) {
      const line = createSkeleton('text', { size: 'sm' });
      details.appendChild(line);
    }

    item.appendChild(header);
    item.appendChild(details);
    list.appendChild(item);
  }

  return list;
}

/**
 * Show skeleton screen
 * @param {HTMLElement|string} element - Element or selector to show skeleton in
 * @param {Object} options - Skeleton options
 * @returns {string} Skeleton ID for tracking
 */
function showSkeleton(element, options = {}) {
  const {
    type = 'card',
    count = 1,
    ...skeletonOptions
  } = options;

  const targetElement = typeof element === 'string' ? document.querySelector(element) : element;

  if (!targetElement) {
    console.warn('showSkeleton: Element not found');
    return null;
  }

  // Generate unique skeleton ID
  const skeletonId = `skeleton-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  // Create skeleton container
  const container = document.createElement('div');
  container.className = 'skeleton-container';
  container.setAttribute('data-skeleton-id', skeletonId);

  // Create skeleton elements
  if (type === 'fir-list') {
    const list = createSkeletonFIRList(count);
    container.appendChild(list);
  } else if (type === 'card') {
    for (let i = 0; i < count; i++) {
      const card = createSkeletonCard(skeletonOptions);
      container.appendChild(card);
    }
  } else {
    for (let i = 0; i < count; i++) {
      const skeleton = createSkeleton(type, skeletonOptions);
      container.appendChild(skeleton);
    }
  }

  // Add to element
  targetElement.appendChild(container);

  // Set aria-busy for accessibility
  targetElement.setAttribute('aria-busy', 'true');

  return skeletonId;
}

/**
 * Hide skeleton screen
 * @param {HTMLElement|string} element - Element, selector, or skeleton ID
 */
function hideSkeleton(element) {
  let targetElement;
  let skeletonId;

  // Handle different input types
  if (typeof element === 'string') {
    // Check if it's a skeleton ID
    const skeletonContainer = document.querySelector(`[data-skeleton-id="${element}"]`);
    if (skeletonContainer) {
      skeletonId = element;
      targetElement = skeletonContainer.parentElement;
    } else {
      // It's a selector
      targetElement = document.querySelector(element);
    }
  } else {
    targetElement = element;
  }

  if (!targetElement) {
    console.warn('hideSkeleton: Element not found');
    return;
  }

  // Find and remove skeleton containers
  const containers = targetElement.querySelectorAll('.skeleton-container');
  containers.forEach(container => {
    const containerId = container.getAttribute('data-skeleton-id');

    // If we have a specific skeleton ID, only remove that one
    if (skeletonId && containerId !== skeletonId) {
      return;
    }

    // Fade out and remove
    container.style.opacity = '0';
    container.style.transition = 'opacity 0.3s ease';
    setTimeout(() => {
      if (container.parentNode) {
        container.parentNode.removeChild(container);
      }
    }, 300);
  });

  // Remove aria-busy if no more skeletons
  if (targetElement.querySelectorAll('.skeleton-container').length === 0) {
    targetElement.removeAttribute('aria-busy');
  }
}

/**
 * Create an animated progress bar
 * @param {Object} options - Progress bar options
 * @returns {HTMLElement} Progress bar element
 */
function createProgressBar(options = {}) {
  const {
    type = 'animated', // 'animated', 'striped', 'indeterminate'
    percentage = 0,
    showText = true
  } = options;

  const container = document.createElement('div');
  container.className = `progress-bar-${type}`;

  if (type === 'indeterminate') {
    // Indeterminate progress bar doesn't need children
    return container;
  }

  const fill = document.createElement('div');
  fill.className = `progress-fill-${type}`;
  fill.style.width = `${Math.max(0, Math.min(100, percentage))}%`;

  container.appendChild(fill);

  if (showText && type !== 'indeterminate') {
    const text = document.createElement('div');
    text.className = 'progress-text';
    text.textContent = `${Math.round(percentage)}%`;
    container.appendChild(text);
  }

  return container;
}

/**
 * Update progress bar percentage
 * @param {HTMLElement} progressBar - Progress bar element
 * @param {number} percentage - New percentage (0-100)
 */
function updateProgressBar(progressBar, percentage) {
  const fill = progressBar.querySelector('[class*="progress-fill"]');
  const text = progressBar.querySelector('.progress-text');

  const clampedPercentage = Math.max(0, Math.min(100, percentage));

  if (fill) {
    fill.style.width = `${clampedPercentage}%`;
  }

  if (text) {
    text.textContent = `${Math.round(clampedPercentage)}%`;
  }
}

/**
 * Show a success animation
 * @param {HTMLElement|string} element - Element or selector to show animation in
 * @param {Object} options - Animation options
 * @returns {Promise} Resolves when animation completes
 */
function showSuccessAnimation(element, options = {}) {
  const { duration = 2000, message = 'Success!' } = options;

  const targetElement = typeof element === 'string' ? document.querySelector(element) : element;

  if (!targetElement) {
    console.warn('showSuccessAnimation: Element not found');
    return Promise.reject(new Error('Element not found'));
  }

  return new Promise((resolve) => {
    // Create animation container
    const container = document.createElement('div');
    container.className = 'loading-container';

    // Create success animation
    const animation = document.createElement('div');
    animation.className = 'success-animation';

    const checkmark = document.createElement('div');
    checkmark.className = 'success-checkmark';

    animation.appendChild(checkmark);

    // Create message
    const messageElement = document.createElement('div');
    messageElement.className = 'loading-text';
    messageElement.textContent = message;

    container.appendChild(animation);
    container.appendChild(messageElement);

    // Add to element
    targetElement.appendChild(container);

    // Remove after duration
    setTimeout(() => {
      container.style.opacity = '0';
      container.style.transition = 'opacity 0.3s ease';
      setTimeout(() => {
        if (container.parentNode) {
          container.parentNode.removeChild(container);
        }
        resolve();
      }, 300);
    }, duration);
  });
}

/**
 * Show an error animation
 * @param {HTMLElement|string} element - Element or selector to show animation in
 * @param {Object} options - Animation options
 * @returns {Promise} Resolves when animation completes
 */
function showErrorAnimation(element, options = {}) {
  const { duration = 2000, message = 'Error!' } = options;

  const targetElement = typeof element === 'string' ? document.querySelector(element) : element;

  if (!targetElement) {
    console.warn('showErrorAnimation: Element not found');
    return Promise.reject(new Error('Element not found'));
  }

  return new Promise((resolve) => {
    // Create animation container
    const container = document.createElement('div');
    container.className = 'loading-container';

    // Create error animation
    const animation = document.createElement('div');
    animation.className = 'error-animation';

    const errorX = document.createElement('div');
    errorX.className = 'error-x';

    animation.appendChild(errorX);

    // Create message
    const messageElement = document.createElement('div');
    messageElement.className = 'loading-text';
    messageElement.textContent = message;

    container.appendChild(animation);
    container.appendChild(messageElement);

    // Add to element
    targetElement.appendChild(container);

    // Remove after duration
    setTimeout(() => {
      container.style.opacity = '0';
      container.style.transition = 'opacity 0.3s ease';
      setTimeout(() => {
        if (container.parentNode) {
          container.parentNode.removeChild(container);
        }
        resolve();
      }, 300);
    }, duration);
  });
}

/**
 * Show a warning animation
 * @param {HTMLElement|string} element - Element or selector to show animation in
 * @param {Object} options - Animation options
 * @returns {Promise} Resolves when animation completes
 */
function showWarningAnimation(element, options = {}) {
  const { duration = 2000, message = 'Warning!' } = options;

  const targetElement = typeof element === 'string' ? document.querySelector(element) : element;

  if (!targetElement) {
    console.warn('showWarningAnimation: Element not found');
    return Promise.reject(new Error('Element not found'));
  }

  return new Promise((resolve) => {
    // Create animation container
    const container = document.createElement('div');
    container.className = 'loading-container';

    // Create warning animation
    const animation = document.createElement('div');
    animation.className = 'warning-animation';

    const warningIcon = document.createElement('div');
    warningIcon.className = 'warning-icon';

    animation.appendChild(warningIcon);

    // Create message
    const messageElement = document.createElement('div');
    messageElement.className = 'loading-text';
    messageElement.textContent = message;

    container.appendChild(animation);
    container.appendChild(messageElement);

    // Add to element
    targetElement.appendChild(container);

    // Remove after duration
    setTimeout(() => {
      container.style.opacity = '0';
      container.style.transition = 'opacity 0.3s ease';
      setTimeout(() => {
        if (container.parentNode) {
          container.parentNode.removeChild(container);
        }
        resolve();
      }, 300);
    }, duration);
  });
}

/**
 * Show an info animation
 * @param {HTMLElement|string} element - Element or selector to show animation in
 * @param {Object} options - Animation options
 * @returns {Promise} Resolves when animation completes
 */
function showInfoAnimation(element, options = {}) {
  const { duration = 2000, message = 'Info' } = options;

  const targetElement = typeof element === 'string' ? document.querySelector(element) : element;

  if (!targetElement) {
    console.warn('showInfoAnimation: Element not found');
    return Promise.reject(new Error('Element not found'));
  }

  return new Promise((resolve) => {
    // Create animation container
    const container = document.createElement('div');
    container.className = 'loading-container';

    // Create info animation
    const animation = document.createElement('div');
    animation.className = 'info-animation';

    const infoIcon = document.createElement('div');
    infoIcon.className = 'info-icon';

    animation.appendChild(infoIcon);

    // Create message
    const messageElement = document.createElement('div');
    messageElement.className = 'loading-text';
    messageElement.textContent = message;

    container.appendChild(animation);
    container.appendChild(messageElement);

    // Add to element
    targetElement.appendChild(container);

    // Remove after duration
    setTimeout(() => {
      container.style.opacity = '0';
      container.style.transition = 'opacity 0.3s ease';
      setTimeout(() => {
        if (container.parentNode) {
          container.parentNode.removeChild(container);
        }
        resolve();
      }, 300);
    }, duration);
  });
}

// Export functions
if (typeof window !== 'undefined') {
  window.LoadingAnimations = {
    SpinnerType,
    createSpinner,
    showCustomLoading,
    createSkeleton,
    createSkeletonCard,
    createSkeletonFIRList,
    showSkeleton,
    hideSkeleton,
    createProgressBar,
    updateProgressBar,
    showSuccessAnimation,
    showErrorAnimation,
    showWarningAnimation,
    showInfoAnimation
  };
}

// Also export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    SpinnerType,
    createSpinner,
    showCustomLoading,
    createSkeleton,
    createSkeletonCard,
    createSkeletonFIRList,
    showSkeleton,
    hideSkeleton,
    createProgressBar,
    updateProgressBar,
    showSuccessAnimation,
    showErrorAnimation,
    showWarningAnimation,
    showInfoAnimation
  };
}
