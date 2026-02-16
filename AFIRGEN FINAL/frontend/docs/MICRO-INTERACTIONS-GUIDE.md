# Micro-Interactions Quick Reference Guide

## For Developers

This guide provides quick reference for using and extending the micro-interactions system.

## Quick Start

### 1. Using Existing Animations

Simply apply the appropriate CSS class to your element:

```html
<!-- Button with hover effects -->
<button class="generate-btn">Click Me</button>

<!-- Input with focus effects -->
<input type="text" class="search-input" placeholder="Search...">

<!-- Card with hover effects -->
<div class="fir-item">Card content</div>

<!-- Loading spinner -->
<div class="loading-spinner"></div>
```

### 2. Animation Classes

| Class | Effect | Use Case |
|-------|--------|----------|
| `.generate-btn` | Lift, shadow, ripple | Primary actions |
| `.btn-secondary` | Subtle lift, shadow | Secondary actions |
| `.search-input` | Glow, lift, icon pulse | Search fields |
| `.fir-item` | Lift, scale, gradient | List items |
| `.step-item` | Lift, scale, glow | Feature cards |
| `.loading-spinner` | Rotation | Loading states |
| `.toast` | Bounce entrance | Notifications |
| `.drop-zone` | Pulse, glow | Drag & drop areas |

### 3. Custom Animations

To add custom animations, follow this pattern:

```css
/* Define the element */
.my-element {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Add hover effect */
.my-element:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* Add active effect */
.my-element:active {
    transform: translateY(0) scale(0.98);
}
```

### 4. Keyframe Animations

Available keyframe animations:

```css
/* Spinner rotation */
animation: spin 0.8s linear infinite;

/* Icon pulse */
animation: iconPulse 0.6s ease;

/* Loading pulse */
animation: loadingPulse 2s ease-in-out infinite;

/* Shimmer effect */
animation: shimmer 1.5s infinite;

/* Toast bounce */
animation: toastBounceIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);

/* Modal scale */
animation: modalScaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
```

## Best Practices

### 1. Performance

✅ **DO:**
- Use `transform` and `opacity` for animations
- Keep animations under 0.6s
- Use `cubic-bezier` for natural motion
- Test on low-end devices

❌ **DON'T:**
- Animate `width`, `height`, `top`, `left`
- Create animations longer than 1s
- Use `linear` easing for UI elements
- Forget to test performance

### 2. Accessibility

✅ **DO:**
- Respect `prefers-reduced-motion`
- Maintain focus indicators
- Provide alternative feedback
- Test with keyboard navigation

❌ **DON'T:**
- Remove focus outlines
- Create seizure-inducing effects
- Rely solely on animation for feedback
- Ignore screen reader users

### 3. User Experience

✅ **DO:**
- Provide immediate feedback (<100ms)
- Use consistent timing
- Match animation to action
- Keep it subtle

❌ **DON'T:**
- Delay user actions
- Use random timing
- Over-animate everything
- Distract from content

## Common Patterns

### 1. Button Click Feedback

```css
.my-button {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.my-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
}

.my-button:active {
    transform: translateY(0) scale(0.98);
}
```

### 2. Input Focus Glow

```css
.my-input {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.my-input:focus {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4), 
                0 0 0 3px rgba(96, 165, 250, 0.2);
}
```

### 3. Card Hover Lift

```css
.my-card {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.my-card:hover {
    transform: translateY(-4px) scale(1.02);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
}
```

### 4. Loading Spinner

```css
.my-spinner {
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

### 5. Toast Notification

```css
.my-toast {
    animation: toastBounceIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes toastBounceIn {
    0% {
        opacity: 0;
        transform: translateX(400px) scale(0.8);
    }
    60% {
        opacity: 1;
        transform: translateX(-10px) scale(1.05);
    }
    100% {
        transform: translateX(0) scale(1);
    }
}
```

## Timing Functions

### Cubic Bezier Values

```css
/* Natural motion (recommended) */
cubic-bezier(0.4, 0, 0.2, 1)

/* Bounce effect */
cubic-bezier(0.34, 1.56, 0.64, 1)

/* Ease out */
cubic-bezier(0, 0, 0.2, 1)

/* Ease in */
cubic-bezier(0.4, 0, 1, 1)
```

### Duration Guidelines

| Duration | Use Case |
|----------|----------|
| 0.1s - 0.2s | Instant feedback (hover) |
| 0.2s - 0.3s | Standard transitions |
| 0.3s - 0.5s | Complex animations |
| 0.5s - 1.0s | Entrance/exit animations |
| 1.0s+ | Ambient animations only |

## Debugging

### 1. Chrome DevTools

```javascript
// Slow down animations for debugging
document.documentElement.style.setProperty('--animation-speed', '0.1');
```

### 2. Animation Inspector

1. Open Chrome DevTools
2. Go to "More tools" → "Animations"
3. Trigger animation
4. Inspect timing and easing

### 3. Performance Profiling

1. Open Chrome DevTools
2. Go to "Performance" tab
3. Record interaction
4. Check for 60fps (16.67ms per frame)

## Troubleshooting

### Animation Not Working

1. Check CSS specificity
2. Verify class is applied
3. Check for conflicting styles
4. Test in different browser

### Animation Too Slow/Fast

1. Adjust `transition-duration`
2. Check `animation-duration`
3. Verify timing function
4. Test on different devices

### Animation Janky

1. Use `transform` instead of position
2. Avoid animating `width`/`height`
3. Check for layout thrashing
4. Profile with DevTools

### Accessibility Issues

1. Add `prefers-reduced-motion` support
2. Maintain focus indicators
3. Test with keyboard only
4. Test with screen reader

## Examples

### Complete Button Component

```html
<button class="custom-button">
    <svg class="button-icon">...</svg>
    <span>Click Me</span>
</button>
```

```css
.custom-button {
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.custom-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
}

.custom-button:hover .button-icon {
    transform: scale(1.1);
    transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.custom-button:active {
    transform: translateY(0) scale(0.98);
}

/* Ripple effect */
.custom-button::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.3);
    transform: translate(-50%, -50%);
    transition: width 0.6s, height 0.6s;
}

.custom-button:active::after {
    width: 300px;
    height: 300px;
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
    .custom-button,
    .custom-button:hover,
    .custom-button:active {
        transform: none;
        transition-duration: 0.01ms;
    }
}
```

## Resources

- [MDN: CSS Animations](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations)
- [MDN: CSS Transitions](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Transitions)
- [Cubic Bezier Generator](https://cubic-bezier.com/)
- [Animation Timing Functions](https://easings.net/)
- [Web Animations API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API)

## Support

For questions or issues:
1. Check `MICRO-INTERACTIONS-IMPLEMENTATION.md` for detailed documentation
2. Test with `test-micro-interactions.html`
3. Review browser console for errors
4. Check browser compatibility

---

**Last Updated:** 2024  
**Version:** 1.0  
**Task:** 24.2 - Add micro-interactions  
**Requirement:** 5.2.8 - Smooth animations and transitions
