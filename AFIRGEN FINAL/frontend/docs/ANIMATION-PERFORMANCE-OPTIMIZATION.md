# Animation Performance Optimization Guide

## Overview

This document describes the performance optimizations applied to animations in the AFIRGen frontend application as part of Task 24.3.

**Requirements:** 5.2.8 - Smooth animations and transitions  
**Task:** 24.3 - Optimize animations for performance

## Optimization Strategies

### 1. Use CSS Transforms Instead of Position Properties

**Why:** CSS transforms are GPU-accelerated and don't trigger layout recalculations.

**Before:**
```css
.element:hover {
    top: -4px; /* Triggers layout */
    left: 10px; /* Triggers layout */
}
```

**After:**
```css
.element:hover {
    transform: translateY(-4px) translateX(10px); /* GPU-accelerated */
}
```

**Applied to:**
- All button hover effects
- Card lift animations
- Modal entrance animations
- Toast slide-in animations
- Input focus effects

### 2. Use will-change for Animated Elements

**Why:** The `will-change` property hints to the browser which properties will animate, allowing it to optimize ahead of time.

**Implementation:**
```css
.animated-element {
    will-change: transform;
}

.animated-element-multi {
    will-change: transform, opacity;
}
```

**Applied to:**
- `.generate-btn`, `.btn-primary`, `.toast-button` - `will-change: transform`
- `.btn-secondary`, `.copy-btn`, `.pagination-btn` - `will-change: transform`
- `.nav-item` - `will-change: transform`
- `.file-upload-item` - `will-change: transform`
- `.search-input`, `.fir-search-input`, `.fir-filter-select` - `will-change: transform`
- `.fir-item` - `will-change: transform`
- `.step-item` - `will-change: transform`
- `.resource-category` - `will-change: transform`
- `.team-member` - `will-change: transform`
- `.spinner`, `.loading-spinner` - `will-change: transform`
- `.modal-close` - `will-change: transform`
- `.drop-zone` - `will-change: transform`
- `.toast` - `will-change: transform, opacity`
- `.modal-content` - `will-change: transform, opacity`
- `.main-container` - `will-change: transform, opacity`
- `.progress-fill` - `will-change: width`

**Important Notes:**
- `will-change` should only be used on elements that will actually animate
- Don't overuse `will-change` as it consumes memory
- The browser automatically removes `will-change` optimization after animation completes

### 3. Specify Exact Transition Properties

**Why:** Using `transition: all` forces the browser to watch all properties for changes, which is inefficient.

**Before:**
```css
.element {
    transition: all 0.3s ease;
}
```

**After:**
```css
.element {
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
```

**Applied to:**
- All buttons (primary, secondary, toast)
- All inputs (search, filter)
- All cards (FIR items, step items, resource categories, team members)
- All interactive elements

### 4. Respect prefers-reduced-motion

**Why:** Users with vestibular disorders or motion sensitivity need reduced motion for accessibility.

**Implementation:**
```css
@media (prefers-reduced-motion: reduce) {
    /* Disable all animations and transitions */
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
    
    /* Remove transforms on hover/active states */
    .element:hover {
        transform: none !important;
    }
    
    /* Disable will-change to save resources */
    .element {
        will-change: auto !important;
    }
    
    /* Keep essential visual feedback (shadows, colors) */
    .element:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
}
```

**Features:**
- Disables all animations and transitions
- Removes transform effects on hover/active
- Disables `will-change` to save resources
- Keeps essential visual feedback (shadows, colors)
- Disables loading animations but keeps spinner visible
- Disables toast bounce but keeps fade
- Disables modal scale but keeps fade

## Performance Metrics

### Target Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Frame Rate | 60 FPS | Smooth animations (16.67ms per frame) |
| Animation Duration | <0.6s | Quick, responsive animations |
| Layout Shifts | 0 | No layout recalculations during animations |
| Paint Time | <16ms | Fast paint operations |

### Optimized Properties

**GPU-Accelerated (Fast):**
- `transform` (translate, scale, rotate)
- `opacity`
- `filter` (blur, brightness, etc.)

**CPU-Bound (Slow - Avoid):**
- `width`, `height`
- `top`, `left`, `right`, `bottom`
- `margin`, `padding`
- `border-width`

## Testing

### 1. Chrome DevTools Performance Profiling

```javascript
// Record animation performance
1. Open Chrome DevTools
2. Go to "Performance" tab
3. Click "Record"
4. Trigger animation (hover, click, etc.)
5. Stop recording
6. Check for 60fps (green line should be at top)
7. Look for layout/paint warnings (red/yellow)
```

### 2. Animation Inspector

```javascript
// Inspect animation timing
1. Open Chrome DevTools
2. Go to "More tools" → "Animations"
3. Trigger animation
4. Inspect timing, easing, and duration
5. Verify smooth cubic-bezier curves
```

### 3. Reduced Motion Testing

```javascript
// Test prefers-reduced-motion
1. Open Chrome DevTools
2. Press Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows)
3. Type "Emulate CSS prefers-reduced-motion"
4. Select "prefers-reduced-motion: reduce"
5. Verify animations are disabled
6. Verify visual feedback still works
```

### 4. Performance Checklist

- [ ] All animations run at 60fps
- [ ] No layout shifts during animations
- [ ] No paint warnings in DevTools
- [ ] Animations complete in <0.6s
- [ ] `will-change` is used appropriately
- [ ] `prefers-reduced-motion` is respected
- [ ] Only `transform` and `opacity` are animated
- [ ] Specific transition properties are defined

## Browser Compatibility

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome 90+ | ✅ Full | All features supported |
| Firefox 88+ | ✅ Full | All features supported |
| Safari 14+ | ✅ Full | All features supported |
| Edge 90+ | ✅ Full | All features supported |
| IE 11 | ⚠️ Partial | `will-change` not supported |

## Common Issues and Solutions

### Issue 1: Janky Animations

**Symptoms:** Animation stutters or drops frames

**Solutions:**
1. Check if animating layout properties (width, height, top, left)
2. Use `transform` instead
3. Verify `will-change` is applied
4. Check for JavaScript blocking main thread
5. Profile with Chrome DevTools

### Issue 2: Animations Too Slow

**Symptoms:** Animations feel sluggish

**Solutions:**
1. Reduce `transition-duration` (target <0.3s)
2. Use faster easing function (e.g., `cubic-bezier(0.4, 0, 0.2, 1)`)
3. Remove unnecessary animations
4. Simplify animation (fewer properties)

### Issue 3: Memory Issues

**Symptoms:** Browser becomes slow or crashes

**Solutions:**
1. Remove `will-change` from non-animated elements
2. Limit number of animated elements on page
3. Use `will-change` only during animation
4. Check for memory leaks in DevTools

### Issue 4: Accessibility Issues

**Symptoms:** Users report motion sickness or discomfort

**Solutions:**
1. Verify `prefers-reduced-motion` is implemented
2. Test with reduced motion enabled
3. Reduce animation intensity
4. Provide option to disable animations

## Best Practices

### DO:
✅ Use `transform` and `opacity` for animations  
✅ Apply `will-change` to animated elements  
✅ Specify exact transition properties  
✅ Respect `prefers-reduced-motion`  
✅ Keep animations under 0.6s  
✅ Use cubic-bezier for natural motion  
✅ Test on low-end devices  
✅ Profile with Chrome DevTools  

### DON'T:
❌ Animate layout properties (width, height, top, left)  
❌ Use `transition: all`  
❌ Overuse `will-change`  
❌ Create animations longer than 1s  
❌ Ignore `prefers-reduced-motion`  
❌ Animate too many elements at once  
❌ Use `linear` easing for UI elements  
❌ Forget to test performance  

## Resources

- [MDN: CSS Transforms](https://developer.mozilla.org/en-US/docs/Web/CSS/transform)
- [MDN: will-change](https://developer.mozilla.org/en-US/docs/Web/CSS/will-change)
- [MDN: prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
- [Google: Rendering Performance](https://developers.google.com/web/fundamentals/performance/rendering)
- [CSS Triggers](https://csstriggers.com/) - See which properties trigger layout/paint

## Changelog

### Version 1.0 (2024)
- Initial implementation of animation performance optimizations
- Added `will-change` to all animated elements
- Replaced `transition: all` with specific properties
- Enhanced `prefers-reduced-motion` support
- Documented all optimizations

---

**Task:** 24.3 - Optimize animations for performance  
**Requirement:** 5.2.8 - Smooth animations and transitions  
**Last Updated:** 2024
