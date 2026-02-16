/**
 * Text Reveal Animations Module
 * 
 * Implements various text reveal animations:
 * - Fade-in text on scroll using Intersection Observer
 * - Typewriter effect for hero text
 * - Staggered letter animations
 * 
 * Performance optimized using Intersection Observer API
 */

class TextRevealAnimations {
  constructor() {
    this.observerOptions = {
      root: null,
      rootMargin: '0px',
      threshold: 0.1
    };
    
    this.observer = null;
    this.typewriterQueue = [];
    this.isTypewriting = false;
  }

  /**
   * Initialize all text reveal animations
   */
  init() {
    // All animations disabled - text displays immediately
    // No fade-in, no typewriter, no staggered letters
  }

  /**
   * Set up Intersection Observer for performance-optimized scroll animations
   */
  setupIntersectionObserver() {
    if (!('IntersectionObserver' in window)) {
      console.warn('IntersectionObserver not supported, animations will be disabled');
      return;
    }

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const target = entry.target;
          
          // Trigger appropriate animation based on data attribute
          if (target.hasAttribute('data-fade-in')) {
            this.animateFadeIn(target);
          }
          
          if (target.hasAttribute('data-stagger-letters')) {
            this.animateStaggeredLetters(target);
          }
          
          // Unobserve after animation to improve performance
          this.observer.unobserve(target);
        }
      });
    }, this.observerOptions);
  }

  /**
   * Set up fade-in elements for scroll-triggered animations
   */
  setupFadeInElements() {
    // Add fade-in animation to step items
    const stepItems = document.querySelectorAll('.step-item');
    stepItems.forEach((item, index) => {
      item.setAttribute('data-fade-in', '');
      item.setAttribute('data-fade-delay', index * 100);
      item.classList.add('text-reveal-hidden');
      
      if (this.observer) {
        this.observer.observe(item);
      }
    });

    // Add fade-in to page sections
    const pageSections = document.querySelectorAll('.page-section');
    pageSections.forEach(section => {
      const title = section.querySelector('.page-title');
      const subtitle = section.querySelector('.page-subtitle');
      
      if (title) {
        title.setAttribute('data-fade-in', '');
        title.classList.add('text-reveal-hidden');
        if (this.observer) {
          this.observer.observe(title);
        }
      }
      
      if (subtitle) {
        subtitle.setAttribute('data-fade-in', '');
        subtitle.setAttribute('data-fade-delay', '100');
        subtitle.classList.add('text-reveal-hidden');
        if (this.observer) {
          this.observer.observe(subtitle);
        }
      }
    });

    // Add fade-in to team members and resource items
    const teamMembers = document.querySelectorAll('.team-member');
    teamMembers.forEach((member, index) => {
      member.setAttribute('data-fade-in', '');
      member.setAttribute('data-fade-delay', index * 150);
      member.classList.add('text-reveal-hidden');
      
      if (this.observer) {
        this.observer.observe(member);
      }
    });

    const resourceCategories = document.querySelectorAll('.resource-category');
    resourceCategories.forEach((category, index) => {
      category.setAttribute('data-fade-in', '');
      category.setAttribute('data-fade-delay', index * 100);
      category.classList.add('text-reveal-hidden');
      
      if (this.observer) {
        this.observer.observe(category);
      }
    });
  }

  /**
   * Animate fade-in effect for an element
   * @param {HTMLElement} element - Element to animate
   */
  animateFadeIn(element) {
    const delay = parseInt(element.getAttribute('data-fade-delay') || '0', 10);
    
    setTimeout(() => {
      element.classList.remove('text-reveal-hidden');
      element.classList.add('text-reveal-fade-in');
    }, delay);
  }

  /**
   * Set up typewriter effect for hero title
   */
  setupTypewriterEffect() {
    // Typewriter effect disabled - keeping title static
    const heroTitle = document.querySelector('.hero-title');
    
    if (!heroTitle) {
      return;
    }

    // Just ensure the title is visible without animation
    heroTitle.classList.remove('typewriter-cursor');
  }

  /**
   * Typewriter effect animation
   * @param {HTMLElement} element - Element to apply effect to
   * @param {string} text - Text to type out
   * @param {number} speed - Speed in milliseconds per character
   */
  typewriterEffect(element, text, speed = 100) {
    let index = 0;
    
    // Clear element before typing
    element.textContent = '';
    
    const type = () => {
      if (index < text.length) {
        element.textContent += text.charAt(index);
        index++;
        setTimeout(type, speed);
      } else {
        // Remove cursor after typing is complete
        setTimeout(() => {
          element.classList.remove('typewriter-cursor');
        }, 500);
      }
    };
    
    type();
  }

  /**
   * Set up staggered letter animations
   */
  setupStaggeredLetters() {
    // Staggered letter animations disabled - text displays immediately
    // No letter-by-letter reveal animations
  }

  /**
   * Animate staggered letters effect
   * @param {HTMLElement} element - Element to animate
   */
  animateStaggeredLetters(element) {
    // Staggered letter animation disabled - just show the text
    element.classList.remove('text-reveal-hidden');
  }

  /**
   * Clean up and disconnect observer
   */
  destroy() {
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  /**
   * Manually trigger animations for elements (useful for dynamic content)
   * @param {HTMLElement} element - Element to animate
   * @param {string} animationType - Type of animation ('fade-in', 'stagger-letters', 'typewriter')
   */
  triggerAnimation(element, animationType) {
    switch (animationType) {
      case 'fade-in':
        this.animateFadeIn(element);
        break;
      case 'stagger-letters':
        this.animateStaggeredLetters(element);
        break;
      case 'typewriter':
        const text = element.textContent;
        element.textContent = '';
        this.typewriterEffect(element, text);
        break;
      default:
        console.warn(`Unknown animation type: ${animationType}`);
    }
  }
}

// ALL TEXT REVEAL ANIMATIONS DISABLED
// Initialize text reveal animations when DOM is ready
let textRevealInstance = null;

function initTextReveal() {
  // ALL ANIMATIONS DISABLED - DO NOTHING
  console.log('[TextReveal] All animations disabled - text displays immediately');
}

// Auto-initialize on DOM ready - DISABLED
// if (document.readyState === 'loading') {
//   document.addEventListener('DOMContentLoaded', initTextReveal);
// } else {
//   initTextReveal();
// }

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { TextRevealAnimations, initTextReveal };
}
