/**
 * SVG Illustration Animations Module
 * Provides animated illustrations for empty states, success/error graphics, and onboarding
 */

class SVGIllustrations {
  constructor() {
    this.illustrations = new Map();
    this.init();
  }

  init() {
    this.setupEmptyStateIllustrations();
    this.setupSuccessIllustrations();
    this.setupErrorIllustrations();
  }

  /**
   * Setup empty state illustrations
   */
  setupEmptyStateIllustrations() {
    const emptyStates = document.querySelectorAll('[data-illustration="empty-state"]');
    emptyStates.forEach(container => {
      this.renderEmptyState(container);
    });
  }

  /**
   * Render empty state illustration
   */
  renderEmptyState(container) {
    const svg = this.createEmptyStateSVG();
    container.innerHTML = '';
    container.appendChild(svg);
    this.animateEmptyState(svg);
  }

  /**
   * Create empty state SVG
   */
  createEmptyStateSVG() {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 200 200');
    svg.setAttribute('width', '200');
    svg.setAttribute('height', '200');
    svg.classList.add('illustration-empty-state');

    // Document icon
    const docGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    docGroup.classList.add('doc-group');
    
    const docRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    docRect.setAttribute('x', '60');
    docRect.setAttribute('y', '40');
    docRect.setAttribute('width', '80');
    docRect.setAttribute('height', '100');
    docRect.setAttribute('rx', '4');
    docRect.setAttribute('fill', 'none');
    docRect.setAttribute('stroke', 'currentColor');
    docRect.setAttribute('stroke-width', '2');
    
    const line1 = this.createLine(70, 60, 110, 60);
    const line2 = this.createLine(70, 75, 130, 75);
    const line3 = this.createLine(70, 90, 120, 90);
    const line4 = this.createLine(70, 105, 125, 105);
    
    docGroup.appendChild(docRect);
    docGroup.appendChild(line1);
    docGroup.appendChild(line2);
    docGroup.appendChild(line3);
    docGroup.appendChild(line4);
    
    // Magnifying glass
    const glassGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    glassGroup.classList.add('glass-group');
    
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', '120');
    circle.setAttribute('cy', '120');
    circle.setAttribute('r', '20');
    circle.setAttribute('fill', 'none');
    circle.setAttribute('stroke', 'currentColor');
    circle.setAttribute('stroke-width', '2');
    
    const handle = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    handle.setAttribute('x1', '135');
    handle.setAttribute('y1', '135');
    handle.setAttribute('x2', '150');
    handle.setAttribute('y2', '150');
    handle.setAttribute('stroke', 'currentColor');
    handle.setAttribute('stroke-width', '2');
    handle.setAttribute('stroke-linecap', 'round');
    
    glassGroup.appendChild(circle);
    glassGroup.appendChild(handle);
    
    svg.appendChild(docGroup);
    svg.appendChild(glassGroup);
    
    return svg;
  }

  /**
   * Animate empty state illustration
   */
  animateEmptyState(svg) {
    const docGroup = svg.querySelector('.doc-group');
    const glassGroup = svg.querySelector('.glass-group');
    
    // Fade in document
    docGroup.style.opacity = '0';
    docGroup.style.animation = 'fadeInUp 0.6s ease-out forwards';
    
    // Animate magnifying glass with delay
    glassGroup.style.opacity = '0';
    glassGroup.style.animation = 'fadeInScale 0.6s ease-out 0.3s forwards';
  }

  /**
   * Setup success illustrations
   */
  setupSuccessIllustrations() {
    const successStates = document.querySelectorAll('[data-illustration="success"]');
    successStates.forEach(container => {
      this.renderSuccessIllustration(container);
    });
  }

  /**
   * Render success illustration
   */
  renderSuccessIllustration(container) {
    const svg = this.createSuccessSVG();
    container.innerHTML = '';
    container.appendChild(svg);
    this.animateSuccess(svg);
  }

  /**
   * Create success SVG illustration
   */
  createSuccessSVG() {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 200 200');
    svg.setAttribute('width', '200');
    svg.setAttribute('height', '200');
    svg.classList.add('illustration-success');

    // Circle background
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', '100');
    circle.setAttribute('cy', '100');
    circle.setAttribute('r', '80');
    circle.setAttribute('fill', 'none');
    circle.setAttribute('stroke', 'currentColor');
    circle.setAttribute('stroke-width', '3');
    circle.classList.add('success-circle');
    
    // Checkmark
    const checkmark = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    checkmark.setAttribute('points', '60,100 85,125 140,70');
    checkmark.setAttribute('fill', 'none');
    checkmark.setAttribute('stroke', 'currentColor');
    checkmark.setAttribute('stroke-width', '4');
    checkmark.setAttribute('stroke-linecap', 'round');
    checkmark.setAttribute('stroke-linejoin', 'round');
    checkmark.classList.add('success-checkmark');
    
    svg.appendChild(circle);
    svg.appendChild(checkmark);
    
    return svg;
  }

  /**
   * Animate success illustration
   */
  animateSuccess(svg) {
    const circle = svg.querySelector('.success-circle');
    const checkmark = svg.querySelector('.success-checkmark');
    
    // Animate circle
    const circleLength = circle.getTotalLength();
    circle.style.strokeDasharray = circleLength;
    circle.style.strokeDashoffset = circleLength;
    circle.style.animation = 'drawCircle 0.6s ease-out forwards';
    
    // Animate checkmark with delay
    const checkmarkLength = checkmark.getTotalLength();
    checkmark.style.strokeDasharray = checkmarkLength;
    checkmark.style.strokeDashoffset = checkmarkLength;
    checkmark.style.animation = 'drawCheckmark 0.4s ease-out 0.4s forwards';
  }

  /**
   * Setup error illustrations
   */
  setupErrorIllustrations() {
    const errorStates = document.querySelectorAll('[data-illustration="error"]');
    errorStates.forEach(container => {
      this.renderErrorIllustration(container);
    });
  }

  /**
   * Render error illustration
   */
  renderErrorIllustration(container) {
    const svg = this.createErrorSVG();
    container.innerHTML = '';
    container.appendChild(svg);
    this.animateError(svg);
  }

  /**
   * Create error SVG illustration
   */
  createErrorSVG() {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 200 200');
    svg.setAttribute('width', '200');
    svg.setAttribute('height', '200');
    svg.classList.add('illustration-error');

    // Circle background
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', '100');
    circle.setAttribute('cy', '100');
    circle.setAttribute('r', '80');
    circle.setAttribute('fill', 'none');
    circle.setAttribute('stroke', 'currentColor');
    circle.setAttribute('stroke-width', '3');
    circle.classList.add('error-circle');
    
    // X mark
    const line1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line1.setAttribute('x1', '70');
    line1.setAttribute('y1', '70');
    line1.setAttribute('x2', '130');
    line1.setAttribute('y2', '130');
    line1.setAttribute('stroke', 'currentColor');
    line1.setAttribute('stroke-width', '4');
    line1.setAttribute('stroke-linecap', 'round');
    line1.classList.add('error-line-1');
    
    const line2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line2.setAttribute('x1', '130');
    line2.setAttribute('y1', '70');
    line2.setAttribute('x2', '70');
    line2.setAttribute('y2', '130');
    line2.setAttribute('stroke', 'currentColor');
    line2.setAttribute('stroke-width', '4');
    line2.setAttribute('stroke-linecap', 'round');
    line2.classList.add('error-line-2');
    
    svg.appendChild(circle);
    svg.appendChild(line1);
    svg.appendChild(line2);
    
    return svg;
  }

  /**
   * Animate error illustration
   */
  animateError(svg) {
    const circle = svg.querySelector('.error-circle');
    const line1 = svg.querySelector('.error-line-1');
    const line2 = svg.querySelector('.error-line-2');
    
    // Animate circle
    const circleLength = circle.getTotalLength();
    circle.style.strokeDasharray = circleLength;
    circle.style.strokeDashoffset = circleLength;
    circle.style.animation = 'drawCircle 0.6s ease-out forwards';
    
    // Animate X lines with delay
    const line1Length = line1.getTotalLength();
    line1.style.strokeDasharray = line1Length;
    line1.style.strokeDashoffset = line1Length;
    line1.style.animation = 'drawLine 0.3s ease-out 0.4s forwards';
    
    const line2Length = line2.getTotalLength();
    line2.style.strokeDasharray = line2Length;
    line2.style.strokeDashoffset = line2Length;
    line2.style.animation = 'drawLine 0.3s ease-out 0.6s forwards';
    
    // Add shake effect
    svg.style.animation = 'shake 0.5s ease-in-out 0.8s';
  }

  /**
   * Helper to create line element
   */
  createLine(x1, y1, x2, y2) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', x1);
    line.setAttribute('y1', y1);
    line.setAttribute('x2', x2);
    line.setAttribute('y2', y2);
    line.setAttribute('stroke', 'currentColor');
    line.setAttribute('stroke-width', '2');
    line.setAttribute('stroke-linecap', 'round');
    line.setAttribute('opacity', '0.6');
    return line;
  }

  /**
   * Trigger illustration animation
   */
  triggerIllustration(container, type) {
    switch (type) {
      case 'empty-state':
        this.renderEmptyState(container);
        break;
      case 'success':
        this.renderSuccessIllustration(container);
        break;
      case 'error':
        this.renderErrorIllustration(container);
        break;
      default:
        console.warn(`Unknown illustration type: ${type}`);
    }
  }
}

// Initialize on DOM ready
if (typeof window !== 'undefined') {
  window.SVGIllustrations = SVGIllustrations;
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.svgIllustrations = new SVGIllustrations();
    });
  } else {
    window.svgIllustrations = new SVGIllustrations();
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SVGIllustrations;
}
