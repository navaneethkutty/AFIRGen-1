# Cursor Effects Implementation Guide

## Overview

The Cursor Effects module provides an interactive and visually engaging cursor experience for desktop users of the AFIRGen frontend application. The system includes three main effects: cursor trail, ripple effects on clicks, and a subtle glow following the cursor.

## Features

### 1. Cursor Trail
- **Description**: Smooth trail of fading particles that follow the cursor
- **Behavior**: 
  - Maximum of 20 trail particles at once
  - Particles fade out gradually (5% opacity decay per frame)
  - Particles shrink as they fade (95% size per frame)
  - Automatic cleanup when particles become invisible
- **Visual**: Radial gradient particles with theme-aware colors

### 2. Ripple Effect
- **Description**: Expanding ring effect triggered on mouse clicks
- **Behavior**:
  - Maximum of 5 simultaneous ripples
  - Expands from 0 to 80px radius
  - Fades out as it expands (2% opacity decay per frame)
  - Speed: 3px per frame
- **Visual**: Ring with inner glow gradient

### 3. Glow Effect
- **Description**: Subtle ambient glow that follows the cursor
- **Behavior**:
  - 40px radius glow
  - Updates position on every mouse move
  - Smooth radial gradient
- **Visual**: Soft glow with theme-aware colors

## Architecture

### Class Structure

```javascript
class CursorEffects {
  constructor()
  init()
  detectMobile()
  resize()
  handleMouseMove(e)
  handleClick(e)
  addTrail(x, y)
  addRipple(x, y)
  getTrailColor()
  getRippleColor()
  updateTrails()
  updateRipples()
  drawTrails()
  drawRipples()
  drawGlow()
  update()
  draw()
  animate()
  stop()
  clear()
  destroy()
}
```

### Canvas Rendering

The module uses a single fixed-position canvas overlay:
- **Position**: Fixed, full viewport coverage
- **Z-index**: 9999 (top layer)
- **Pointer events**: None (doesn't interfere with interactions)
- **ARIA**: Hidden from screen readers

### Animation Loop

Uses `requestAnimationFrame` for smooth 60fps animations:
1. Update particle positions and properties
2. Remove dead particles
3. Clear canvas
4. Draw glow effect
5. Draw trail particles
6. Draw ripple effects
7. Request next frame

## Mobile Detection

The system automatically detects and disables on mobile devices using multiple checks:

```javascript
detectMobile() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
         window.matchMedia('(max-width: 768px)').matches ||
         ('ontouchstart' in window);
}
```

**Detection Methods**:
1. User agent string matching
2. Screen width check (≤768px)
3. Touch capability detection

## Theme Integration

Colors adapt automatically to light/dark mode:

### Light Mode
- Trail: `rgba(100, 100, 255, opacity)`
- Ripple: `rgba(100, 150, 255, opacity)`
- Glow: `rgba(100, 150, 255, 0.3)`

### Dark Mode
- Trail: `rgba(100, 200, 255, opacity)`
- Ripple: `rgba(150, 220, 255, opacity)`
- Glow: `rgba(150, 220, 255, 0.3)`

## Performance Optimizations

### 1. Particle Limits
- **Trail particles**: Maximum 20
- **Ripples**: Maximum 5
- Oldest particles removed when limit reached

### 2. Efficient Culling
- Particles removed when opacity ≤ 0
- Particles removed when size < 1px
- Ripples removed when radius ≥ maxRadius

### 3. GPU Acceleration
```css
#cursor-effects-canvas {
  will-change: transform;
  backface-visibility: hidden;
  perspective: 1000px;
  transform: translateZ(0);
}
```

### 4. Conditional Rendering
- Disabled on mobile devices
- Disabled when `prefers-reduced-motion` is set
- Disabled in high contrast mode
- Hidden in print mode

## Accessibility

### Reduced Motion Support
```javascript
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (prefersReducedMotion) {
  console.log('Cursor effects disabled due to prefers-reduced-motion');
  return;
}
```

### Screen Reader Compatibility
- Canvas marked with `aria-hidden="true"`
- No interference with keyboard navigation
- Pointer events disabled on canvas

### High Contrast Mode
Effects automatically disabled in high contrast mode:
```css
@media (prefers-contrast: high) {
  #cursor-effects-canvas {
    display: none !important;
  }
}
```

## Integration

### HTML
Add script reference before closing `</body>` tag:
```html
<script src="js/cursor-effects.js"></script>
```

### CSS
Add stylesheet in `<head>`:
```html
<link rel="stylesheet" href="css/cursor-effects.css">
```

### Automatic Initialization
The module initializes automatically on page load:
```javascript
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCursorEffects);
} else {
  initCursorEffects();
}
```

## API Reference

### Global Functions

#### `initCursorEffects()`
Initialize the cursor effects system.
```javascript
window.initCursorEffects();
```

#### `stopCursorEffects()`
Stop the animation loop (particles remain visible).
```javascript
window.stopCursorEffects();
```

#### `clearCursorEffects()`
Remove all active particles.
```javascript
window.clearCursorEffects();
```

### Global Instance

Access the cursor effects instance:
```javascript
const effects = window.cursorEffects;
console.log(effects.trails.length); // Number of trail particles
console.log(effects.ripples.length); // Number of active ripples
```

## Testing

### Test Page
Open `test-cursor-effects.html` to:
- See all effects in action
- Monitor performance metrics (FPS, particle counts)
- Test controls (clear, stop, restart)
- Trigger multiple ripples
- Verify mobile detection

### Manual Testing Checklist

- [ ] Cursor trail follows mouse smoothly
- [ ] Trail particles fade out gradually
- [ ] Ripples expand on click
- [ ] Multiple ripples can be active
- [ ] Glow follows cursor
- [ ] Effects disabled on mobile
- [ ] Effects disabled with reduced motion
- [ ] Colors adapt to theme
- [ ] 60fps performance maintained
- [ ] No interference with page interactions

### Performance Metrics

Expected performance on modern devices:

| Metric | Target | Typical |
|--------|--------|---------|
| FPS | 60fps | 60fps |
| Trail Particles | 0-20 | 10-15 |
| Active Ripples | 0-5 | 1-2 |
| CPU Usage | <3% | <2% |
| Memory | <5MB | <3MB |

## Browser Compatibility

### Supported Browsers
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Required Features
- Canvas 2D context
- RequestAnimationFrame
- CSS transforms
- Media queries

## Troubleshooting

### Effects Not Visible

**Check 1**: Mobile device?
```javascript
console.log(window.cursorEffects.isMobile);
```

**Check 2**: Reduced motion enabled?
```javascript
console.log(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
```

**Check 3**: Canvas created?
```javascript
console.log(document.getElementById('cursor-effects-canvas'));
```

### Poor Performance

**Solution 1**: Reduce particle limits
```javascript
window.cursorEffects.maxTrails = 10; // Default: 20
window.cursorEffects.maxRipples = 3; // Default: 5
```

**Solution 2**: Increase decay rates
```javascript
// Modify in cursor-effects.js
trail.decay = 0.1; // Default: 0.05 (faster fade)
ripple.decay = 0.04; // Default: 0.02 (faster fade)
```

### Colors Not Matching Theme

**Check**: Theme class on body
```javascript
console.log(document.body.classList.contains('dark-mode'));
```

**Solution**: Ensure theme toggle updates body class

## Customization

### Adjust Trail Length
```javascript
// In cursor-effects.js, constructor
this.maxTrails = 30; // Default: 20
```

### Adjust Ripple Size
```javascript
// In addRipple method
maxRadius: 120, // Default: 80
```

### Change Colors
```javascript
// In getTrailColor method
return 'rgba(255, 100, 100, '; // Red trail
```

### Adjust Glow Size
```javascript
// In drawGlow method
const glowSize = 60; // Default: 40
```

## Performance Considerations

### Best Practices
1. Keep particle limits reasonable (20 trails, 5 ripples)
2. Use efficient decay rates for quick cleanup
3. Avoid creating effects in tight loops
4. Monitor FPS in production

### Memory Management
- Particles automatically removed when dead
- Canvas cleared every frame
- Event listeners properly cleaned up on destroy

### CPU Usage
- Canvas rendering is GPU-accelerated
- RequestAnimationFrame syncs with display refresh
- Minimal JavaScript computation per frame

## Future Enhancements

### Potential Features
1. **Customizable colors**: User-selectable trail/ripple colors
2. **Effect intensity**: Slider to control particle density
3. **Custom shapes**: Stars, hearts, or other particle shapes
4. **Magnetic effect**: Particles attracted to interactive elements
5. **Sound effects**: Optional audio feedback on clicks
6. **Particle physics**: More realistic motion with velocity/acceleration
7. **Multi-touch support**: Tablet support with multiple cursors

### Performance Improvements
1. **WebGL rendering**: For more particles with better performance
2. **Offscreen canvas**: Render in worker thread
3. **Adaptive quality**: Reduce effects on low-end devices
4. **Lazy initialization**: Only start when cursor moves

## Code Examples

### Trigger Ripple Programmatically
```javascript
// Trigger ripple at specific position
if (window.cursorEffects) {
  window.cursorEffects.addRipple(x, y);
}
```

### Create Multiple Ripples
```javascript
// Create ripple pattern
const centerX = window.innerWidth / 2;
const centerY = window.innerHeight / 2;

for (let i = 0; i < 8; i++) {
  const angle = (Math.PI * 2 * i) / 8;
  const radius = 100;
  const x = centerX + Math.cos(angle) * radius;
  const y = centerY + Math.sin(angle) * radius;
  
  setTimeout(() => {
    window.cursorEffects.addRipple(x, y);
  }, i * 100);
}
```

### Monitor Performance
```javascript
// Track FPS
let lastTime = performance.now();
let frameCount = 0;

function checkFPS() {
  const now = performance.now();
  frameCount++;
  
  if (now - lastTime >= 1000) {
    const fps = Math.round((frameCount * 1000) / (now - lastTime));
    console.log('FPS:', fps);
    frameCount = 0;
    lastTime = now;
  }
  
  requestAnimationFrame(checkFPS);
}

checkFPS();
```

## Conclusion

The Cursor Effects module provides a polished, performant, and accessible enhancement to the AFIRGen frontend. With automatic mobile detection, theme integration, and respect for user preferences, it delivers a premium desktop experience without compromising usability or performance.

## Related Documentation

- [Particle Effects Implementation](PARTICLE-EFFECTS-IMPLEMENTATION.md)
- [Glassmorphism Implementation](GLASSMORPHISM-IMPLEMENTATION.md)
- [Parallax Scrolling Implementation](PARALLAX-SCROLLING-IMPLEMENTATION.md)
- [Animation Performance Optimization](ANIMATION-PERFORMANCE-OPTIMIZATION.md)
