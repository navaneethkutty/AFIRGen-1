/**
 * Unit tests for loading-animations.js
 */

const {
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
} = require('./loading-animations');

// Mock DOM
document.body.innerHTML = '<div id="test-container"></div>';

describe('Loading Animations Module', () => {
  let testContainer;

  beforeEach(() => {
    testContainer = document.getElementById('test-container');
    testContainer.innerHTML = '';
  });

  afterEach(() => {
    testContainer.innerHTML = '';
  });

  describe('createSpinner', () => {
    test('should create default spinner', () => {
      const spinner = createSpinner(SpinnerType.DEFAULT);
      expect(spinner).toBeTruthy();
      expect(spinner.className).toContain('spinner-default');
      expect(spinner.className).toContain('loading-md');
    });

    test('should create dots spinner with 3 dots', () => {
      const spinner = createSpinner(SpinnerType.DOTS);
      expect(spinner.className).toContain('spinner-dots');
      expect(spinner.querySelectorAll('.dot').length).toBe(3);
    });

    test('should create ripple spinner with 2 ripples', () => {
      const spinner = createSpinner(SpinnerType.RIPPLE);
      expect(spinner.className).toContain('spinner-ripple');
      expect(spinner.querySelectorAll('.ripple').length).toBe(2);
    });

    test('should create bars spinner with 4 bars', () => {
      const spinner = createSpinner(SpinnerType.BARS);
      expect(spinner.className).toContain('spinner-bars');
      expect(spinner.querySelectorAll('.bar').length).toBe(4);
    });

    test('should create circular spinner with SVG', () => {
      const spinner = createSpinner(SpinnerType.CIRCULAR);
      expect(spinner.className).toContain('spinner-circular');
      expect(spinner.querySelector('svg')).toBeTruthy();
      expect(spinner.querySelector('circle')).toBeTruthy();
    });

    test('should apply size classes', () => {
      const spinnerSm = createSpinner(SpinnerType.DEFAULT, 'sm');
      expect(spinnerSm.className).toContain('loading-sm');

      const spinnerLg = createSpinner(SpinnerType.DEFAULT, 'lg');
      expect(spinnerLg.className).toContain('loading-lg');
    });
  });

  describe('showCustomLoading', () => {
    test('should show loading with default spinner', () => {
      const loadingId = showCustomLoading(testContainer);
      expect(loadingId).toBeTruthy();
      expect(testContainer.querySelector('.loading-overlay')).toBeTruthy();
      expect(testContainer.querySelector('.spinner-default')).toBeTruthy();
      expect(testContainer.getAttribute('aria-busy')).toBe('true');
    });

    test('should show loading with custom spinner type', () => {
      showCustomLoading(testContainer, { type: SpinnerType.DOTS });
      expect(testContainer.querySelector('.spinner-dots')).toBeTruthy();
    });

    test('should show loading with custom message', () => {
      const message = 'Processing...';
      showCustomLoading(testContainer, { message });
      const messageElement = testContainer.querySelector('.loading-message');
      expect(messageElement).toBeTruthy();
      expect(messageElement.textContent).toBe(message);
    });

    test('should show loading without overlay', () => {
      showCustomLoading(testContainer, { overlay: false });
      expect(testContainer.querySelector('.loading-overlay')).toBeFalsy();
      expect(testContainer.querySelector('.loading-container')).toBeTruthy();
    });

    test('should return null for invalid element', () => {
      const loadingId = showCustomLoading('#non-existent');
      expect(loadingId).toBeNull();
    });
  });

  describe('createSkeleton', () => {
    test('should create text skeleton', () => {
      const skeleton = createSkeleton('text');
      expect(skeleton.className).toContain('skeleton');
      expect(skeleton.className).toContain('skeleton-text');
    });

    test('should create title skeleton', () => {
      const skeleton = createSkeleton('title');
      expect(skeleton.className).toContain('skeleton-title');
    });

    test('should create avatar skeleton', () => {
      const skeleton = createSkeleton('avatar');
      expect(skeleton.className).toContain('skeleton-avatar');
    });

    test('should apply size classes', () => {
      const skeleton = createSkeleton('text', { size: 'lg' });
      expect(skeleton.className).toContain('skeleton-text-lg');
    });

    test('should apply custom width and height', () => {
      const skeleton = createSkeleton('text', { width: '200px', height: '50px' });
      expect(skeleton.style.width).toBe('200px');
      expect(skeleton.style.height).toBe('50px');
    });

    test('should handle numeric width and height', () => {
      const skeleton = createSkeleton('text', { width: 200, height: 50 });
      expect(skeleton.style.width).toBe('200px');
      expect(skeleton.style.height).toBe('50px');
    });
  });

  describe('createSkeletonCard', () => {
    test('should create skeleton card with avatar', () => {
      const card = createSkeletonCard({ showAvatar: true });
      expect(card.className).toContain('skeleton-card');
      expect(card.querySelector('.skeleton-card-header')).toBeTruthy();
      expect(card.querySelector('.skeleton-avatar')).toBeTruthy();
    });

    test('should create skeleton card without avatar', () => {
      const card = createSkeletonCard({ showAvatar: false });
      expect(card.querySelector('.skeleton-card-header')).toBeFalsy();
    });

    test('should create skeleton card with custom number of lines', () => {
      const lines = 5;
      const card = createSkeletonCard({ lines });
      const textLines = card.querySelectorAll('.skeleton-card-body .skeleton-text');
      expect(textLines.length).toBe(lines);
    });
  });

  describe('createSkeletonFIRList', () => {
    test('should create FIR list with default count', () => {
      const list = createSkeletonFIRList();
      expect(list.className).toContain('skeleton-fir-list');
      expect(list.querySelectorAll('.skeleton-fir-item').length).toBe(3);
    });

    test('should create FIR list with custom count', () => {
      const count = 5;
      const list = createSkeletonFIRList(count);
      expect(list.querySelectorAll('.skeleton-fir-item').length).toBe(count);
    });

    test('should have proper structure for each item', () => {
      const list = createSkeletonFIRList(1);
      const item = list.querySelector('.skeleton-fir-item');
      expect(item.querySelector('.skeleton-fir-item-header')).toBeTruthy();
      expect(item.querySelector('.skeleton-fir-number')).toBeTruthy();
      expect(item.querySelector('.skeleton-fir-status')).toBeTruthy();
      expect(item.querySelector('.skeleton-fir-details')).toBeTruthy();
    });
  });

  describe('showSkeleton', () => {
    test('should show skeleton in container', () => {
      const skeletonId = showSkeleton(testContainer);
      expect(skeletonId).toBeTruthy();
      expect(testContainer.querySelector('.skeleton-container')).toBeTruthy();
      expect(testContainer.getAttribute('aria-busy')).toBe('true');
    });

    test('should show card skeleton', () => {
      showSkeleton(testContainer, { type: 'card' });
      expect(testContainer.querySelector('.skeleton-card')).toBeTruthy();
    });

    test('should show FIR list skeleton', () => {
      showSkeleton(testContainer, { type: 'fir-list', count: 3 });
      expect(testContainer.querySelector('.skeleton-fir-list')).toBeTruthy();
      expect(testContainer.querySelectorAll('.skeleton-fir-item').length).toBe(3);
    });

    test('should show multiple skeletons', () => {
      showSkeleton(testContainer, { type: 'card', count: 3 });
      expect(testContainer.querySelectorAll('.skeleton-card').length).toBe(3);
    });

    test('should return null for invalid element', () => {
      const skeletonId = showSkeleton('#non-existent');
      expect(skeletonId).toBeNull();
    });
  });

  describe('hideSkeleton', () => {
    test('should hide skeleton by element', (done) => {
      showSkeleton(testContainer);
      hideSkeleton(testContainer);
      
      // Wait for fade out animation
      setTimeout(() => {
        expect(testContainer.querySelector('.skeleton-container')).toBeFalsy();
        done();
      }, 400);
    });

    test('should hide skeleton by ID', (done) => {
      const skeletonId = showSkeleton(testContainer);
      hideSkeleton(skeletonId);
      
      setTimeout(() => {
        expect(testContainer.querySelector('.skeleton-container')).toBeFalsy();
        done();
      }, 400);
    });
  });

  describe('createProgressBar', () => {
    test('should create animated progress bar', () => {
      const progressBar = createProgressBar({ type: 'animated', percentage: 50 });
      expect(progressBar.className).toContain('progress-bar-animated');
      expect(progressBar.querySelector('.progress-fill-animated')).toBeTruthy();
      expect(progressBar.querySelector('.progress-fill-animated').style.width).toBe('50%');
    });

    test('should create striped progress bar', () => {
      const progressBar = createProgressBar({ type: 'striped', percentage: 75 });
      expect(progressBar.className).toContain('progress-bar-striped');
      expect(progressBar.querySelector('.progress-fill-striped')).toBeTruthy();
    });

    test('should create indeterminate progress bar', () => {
      const progressBar = createProgressBar({ type: 'indeterminate' });
      expect(progressBar.className).toContain('progress-bar-indeterminate');
      expect(progressBar.querySelector('.progress-fill-indeterminate')).toBeFalsy();
    });

    test('should show progress text', () => {
      const progressBar = createProgressBar({ percentage: 60, showText: true });
      const text = progressBar.querySelector('.progress-text');
      expect(text).toBeTruthy();
      expect(text.textContent).toBe('60%');
    });

    test('should hide progress text', () => {
      const progressBar = createProgressBar({ percentage: 60, showText: false });
      expect(progressBar.querySelector('.progress-text')).toBeFalsy();
    });

    test('should clamp percentage to 0-100 range', () => {
      const progressBar1 = createProgressBar({ percentage: -10 });
      expect(progressBar1.querySelector('.progress-fill-animated').style.width).toBe('0%');

      const progressBar2 = createProgressBar({ percentage: 150 });
      expect(progressBar2.querySelector('.progress-fill-animated').style.width).toBe('100%');
    });
  });

  describe('updateProgressBar', () => {
    test('should update progress bar percentage', () => {
      const progressBar = createProgressBar({ percentage: 0 });
      updateProgressBar(progressBar, 75);
      
      const fill = progressBar.querySelector('.progress-fill-animated');
      expect(fill.style.width).toBe('75%');
    });

    test('should update progress text', () => {
      const progressBar = createProgressBar({ percentage: 0, showText: true });
      updateProgressBar(progressBar, 85);
      
      const text = progressBar.querySelector('.progress-text');
      expect(text.textContent).toBe('85%');
    });

    test('should clamp percentage to 0-100 range', () => {
      const progressBar = createProgressBar({ percentage: 50 });
      
      updateProgressBar(progressBar, -10);
      expect(progressBar.querySelector('.progress-fill-animated').style.width).toBe('0%');

      updateProgressBar(progressBar, 150);
      expect(progressBar.querySelector('.progress-fill-animated').style.width).toBe('100%');
    });
  });

  describe('showSuccessAnimation', () => {
    test('should show success animation', async () => {
      const promise = showSuccessAnimation(testContainer, { duration: 100 });
      
      expect(testContainer.querySelector('.success-animation')).toBeTruthy();
      expect(testContainer.querySelector('.success-checkmark')).toBeTruthy();
      
      await promise;
      
      // Animation should be removed after promise resolves
      expect(testContainer.querySelector('.success-animation')).toBeFalsy();
    });

    test('should show custom message', () => {
      const message = 'Upload successful!';
      showSuccessAnimation(testContainer, { message, duration: 100 });
      
      const messageElement = testContainer.querySelector('.loading-text');
      expect(messageElement.textContent).toBe(message);
    });

    test('should reject for invalid element', async () => {
      await expect(showSuccessAnimation('#non-existent')).rejects.toThrow('Element not found');
    });
  });

  describe('showErrorAnimation', () => {
    test('should show error animation', async () => {
      const promise = showErrorAnimation(testContainer, { duration: 100 });
      
      expect(testContainer.querySelector('.error-animation')).toBeTruthy();
      expect(testContainer.querySelector('.error-x')).toBeTruthy();
      
      await promise;
    });

    test('should show custom message', () => {
      const message = 'Upload failed!';
      showErrorAnimation(testContainer, { message, duration: 100 });
      
      const messageElement = testContainer.querySelector('.loading-text');
      expect(messageElement.textContent).toBe(message);
    });
  });

  describe('showWarningAnimation', () => {
    test('should show warning animation', async () => {
      const promise = showWarningAnimation(testContainer, { duration: 100 });
      
      expect(testContainer.querySelector('.warning-animation')).toBeTruthy();
      expect(testContainer.querySelector('.warning-icon')).toBeTruthy();
      
      await promise;
    });
  });

  describe('showInfoAnimation', () => {
    test('should show info animation', async () => {
      const promise = showInfoAnimation(testContainer, { duration: 100 });
      
      expect(testContainer.querySelector('.info-animation')).toBeTruthy();
      expect(testContainer.querySelector('.info-icon')).toBeTruthy();
      
      await promise;
    });
  });

  describe('SpinnerType enum', () => {
    test('should have all spinner types', () => {
      expect(SpinnerType.DEFAULT).toBe('default');
      expect(SpinnerType.DUAL_RING).toBe('dual-ring');
      expect(SpinnerType.DOTS).toBe('dots');
      expect(SpinnerType.PULSE).toBe('pulse');
      expect(SpinnerType.RIPPLE).toBe('ripple');
      expect(SpinnerType.BARS).toBe('bars');
      expect(SpinnerType.CIRCULAR).toBe('circular');
    });
  });
});
