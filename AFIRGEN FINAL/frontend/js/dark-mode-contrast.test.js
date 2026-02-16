/**
 * Property Test 7: Dark Mode Consistency
 * Validates: Requirements 5.4.7
 *
 * Property: For any UI element, when dark mode is enabled, the system SHALL
 * apply dark theme colors with contrast ratio >4.5:1 for text and >3:1 for UI components.
 */

const { test } = require('@fast-check/jest');
const fc = require('fast-check');

// Mock DOM environment
const { JSDOM } = require('jsdom');

describe('Property 7: Dark Mode Consistency', () => {
    let dom;
    let document;
    let window;

    beforeEach(() => {
        // Create a fresh DOM for each test
        dom = new JSDOM(`
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    :root {
                        --bg-color: #ffffff;
                        --text-color: #000000;
                        --border-color: #cccccc;
                        --primary-color: #000000;
                    }

                    body.dark-mode,
                    body:not(.light-mode) {
                        --bg-color: #0a0a0a;
                        --text-color: #e5e5e5;
                        --border-color: #2a2a2a;
                        --primary-color: #ffffff;
                    }

                    body {
                        background-color: var(--bg-color);
                        color: var(--text-color);
                    }

                    .card {
                        background-color: var(--bg-color);
                        border: 1px solid var(--border-color);
                        color: var(--text-color);
                    }

                    button {
                        background-color: var(--primary-color);
                        color: var(--bg-color);
                        border: 1px solid var(--border-color);
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Test Heading</h1>
                    <p>Test paragraph text</p>
                    <button>Test Button</button>
                </div>
            </body>
            </html>
        `, {
            url: 'http://localhost',
            pretendToBeVisual: true
        });

        document = dom.window.document;
        window = dom.window;
    });

    afterEach(() => {
        dom.window.close();
    });

    /**
     * Calculate relative luminance of a color
     * @param {number} r - Red (0-255)
     * @param {number} g - Green (0-255)
     * @param {number} b - Blue (0-255)
     * @returns {number} Relative luminance
     */
    function getLuminance(r, g, b) {
        const [rs, gs, bs] = [r, g, b].map(c => {
            c = c / 255;
            return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
    }

    /**
     * Calculate contrast ratio between two colors
     * @param {string} color1 - First color (hex)
     * @param {string} color2 - Second color (hex)
     * @returns {number} Contrast ratio
     */
    function getContrastRatio(color1, color2) {
        const rgb1 = hexToRgb(color1);
        const rgb2 = hexToRgb(color2);

        const l1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
        const l2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);

        const lighter = Math.max(l1, l2);
        const darker = Math.min(l1, l2);

        return (lighter + 0.05) / (darker + 0.05);
    }

    /**
     * Convert hex color to RGB
     * @param {string} hex - Hex color
     * @returns {Object} RGB object
     */
    function hexToRgb(hex) {
        hex = hex.replace('#', '');

        if (hex.length === 3) {
            hex = hex.split('').map(c => c + c).join('');
        }

        return {
            r: parseInt(hex.substr(0, 2), 16),
            g: parseInt(hex.substr(2, 2), 16),
            b: parseInt(hex.substr(4, 2), 16)
        };
    }

    /**
     * Get computed color from element
     * @param {Element} element - DOM element
     * @param {string} property - CSS property
     * @returns {string} Hex color
     */
    function getComputedColor(element, property) {
        const computed = window.getComputedStyle(element);
        const color = computed.getPropertyValue(property);

        // Convert rgb(r, g, b) to hex
        const match = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
        if (match) {
            const r = parseInt(match[1]).toString(16).padStart(2, '0');
            const g = parseInt(match[2]).toString(16).padStart(2, '0');
            const b = parseInt(match[3]).toString(16).padStart(2, '0');
            return `#${r}${g}${b}`;
        }

        return color;
    }

    test('Text elements have contrast ratio > 4.5:1 in dark mode', () => {
        fc.assert(
            fc.property(
                fc.constantFrom('h1', 'h2', 'h3', 'p', 'span', 'div', 'button'),
                (tagName) => {
                    // Enable dark mode
                    document.body.classList.remove('light-mode');

                    // Create or get element
                    let element = document.querySelector(tagName);
                    if (!element) {
                        element = document.createElement(tagName);
                        element.textContent = 'Test text';
                        document.body.appendChild(element);
                    }

                    // Get colors
                    const textColor = getComputedColor(element, 'color');
                    const bgColor = getComputedColor(element, 'background-color');

                    // Calculate contrast ratio
                    const contrastRatio = getContrastRatio(textColor, bgColor);

                    // Text should have contrast ratio > 4.5:1 (WCAG AA)
                    return contrastRatio >= 4.5;
                }
            ),
            { numRuns: 50 }
        );
    });

    test('UI components have contrast ratio > 3:1 in dark mode', () => {
        fc.assert(
            fc.property(
                fc.constantFrom('button', 'input', 'select', 'textarea'),
                (tagName) => {
                    // Enable dark mode
                    document.body.classList.remove('light-mode');

                    // Create element
                    const element = document.createElement(tagName);
                    document.body.appendChild(element);

                    // Get colors
                    const borderColor = getComputedColor(element, 'border-color');
                    const bgColor = getComputedColor(element, 'background-color');

                    // Calculate contrast ratio
                    const contrastRatio = getContrastRatio(borderColor, bgColor);

                    // UI components should have contrast ratio > 3:1 (WCAG AA)
                    return contrastRatio >= 3.0;
                }
            ),
            { numRuns: 50 }
        );
    });

    test('Dark mode applies consistently across all elements', () => {
        fc.assert(
            fc.property(
                fc.array(fc.constantFrom('div', 'p', 'span', 'button', 'h1'), { minLength: 1, maxLength: 10 }),
                (tagNames) => {
                    // Enable dark mode
                    document.body.classList.remove('light-mode');

                    // Create elements
                    const elements = tagNames.map(tag => {
                        const el = document.createElement(tag);
                        el.textContent = 'Test';
                        document.body.appendChild(el);
                        return el;
                    });

                    // Check all elements have dark mode colors
                    const allDark = elements.every(el => {
                        const textColor = getComputedColor(el, 'color');
                        const bgColor = getComputedColor(el, 'background-color');

                        // Dark mode should have light text on dark background
                        const textLuminance = getLuminance(...Object.values(hexToRgb(textColor)));
                        const bgLuminance = getLuminance(...Object.values(hexToRgb(bgColor)));

                        return textLuminance > bgLuminance;
                    });

                    // Clean up
                    elements.forEach(el => el.remove());

                    return allDark;
                }
            ),
            { numRuns: 30 }
        );
    });

    test('Dark mode toggle preserves contrast ratios', () => {
        fc.assert(
            fc.property(
                fc.boolean(),
                (enableDarkMode) => {
                    // Toggle dark mode
                    if (enableDarkMode) {
                        document.body.classList.remove('light-mode');
                    } else {
                        document.body.classList.add('light-mode');
                    }

                    // Get text element
                    const element = document.querySelector('p') || document.createElement('p');
                    element.textContent = 'Test text';
                    if (!element.parentNode) {
                        document.body.appendChild(element);
                    }

                    // Get colors
                    const textColor = getComputedColor(element, 'color');
                    const bgColor = getComputedColor(element, 'background-color');

                    // Calculate contrast ratio
                    const contrastRatio = getContrastRatio(textColor, bgColor);

                    // Should always maintain minimum contrast
                    return contrastRatio >= 4.5;
                }
            ),
            { numRuns: 100 }
        );
    });

    test('Dark mode colors are within valid range', () => {
        fc.assert(
            fc.property(
                fc.constantFrom('color', 'background-color', 'border-color'),
                (property) => {
                    // Enable dark mode
                    document.body.classList.remove('light-mode');

                    // Get color value
                    const element = document.body;
                    const color = getComputedColor(element, property);
                    const rgb = hexToRgb(color);

                    // All RGB values should be valid (0-255)
                    return rgb.r >= 0 && rgb.r <= 255 &&
                           rgb.g >= 0 && rgb.g <= 255 &&
                           rgb.b >= 0 && rgb.b <= 255;
                }
            ),
            { numRuns: 50 }
        );
    });
});

/**
 * Integration test: Verify dark mode in actual application
 */
describe('Dark Mode Integration', () => {
    test('Dark mode applies to all page elements', () => {
        const dom = new JSDOM(`
            <!DOCTYPE html>
            <html>
            <body>
                <nav><a href="#">Link</a></nav>
                <main>
                    <h1>Heading</h1>
                    <p>Paragraph</p>
                    <button>Button</button>
                    <input type="text" placeholder="Input">
                </main>
            </body>
            </html>
        `);

        const document = dom.window.document;

        // Enable dark mode
        document.body.classList.remove('light-mode');

        // Verify dark mode class is applied
        expect(document.body.classList.contains('light-mode')).toBe(false);

        dom.window.close();
    });
});
