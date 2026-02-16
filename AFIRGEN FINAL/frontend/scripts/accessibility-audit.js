/**
 * Accessibility Audit Script
 * Runs automated accessibility checks and generates a report
 */

const fs = require('fs');
const path = require('path');

console.log('='.repeat(60));
console.log('ACCESSIBILITY AUDIT REPORT');
console.log('='.repeat(60));
console.log();

// Check for index.html
const indexPath = path.join(__dirname, '..', 'index.html');
if (!fs.existsSync(indexPath)) {
  console.error('❌ index.html not found');
  process.exit(1);
}

console.log('✅ index.html found');

// Read and analyze HTML
const html = fs.readFileSync(indexPath, 'utf-8');

// Accessibility checks
const checks = {
  hasLang: /<html[^>]*\slang=["'][^"']+["']/.test(html),
  hasTitle: /<title>/.test(html),
  hasMetaViewport: /<meta[^>]*name=["']viewport["']/.test(html),
  hasSkipLink: /skip.*content|skip.*main/i.test(html),
  hasAriaLabels: /aria-label/i.test(html),
  hasAriaLive: /aria-live/i.test(html),
  hasSemanticHTML: /<(nav|main|header|footer|aside|section|article)/.test(html),
  hasButtonElements: /<button/.test(html),
  hasAltText: /alt=["']/i.test(html),
  hasFormLabels: /<label/.test(html)
};

console.log('\n📋 HTML Structure Checks:');
console.log('─'.repeat(60));
console.log(`${checks.hasLang ? '✅' : '❌'} HTML lang attribute`);
console.log(`${checks.hasTitle ? '✅' : '❌'} Page title`);
console.log(`${checks.hasMetaViewport ? '✅' : '❌'} Viewport meta tag`);
console.log(`${checks.hasSkipLink ? '✅' : '❌'} Skip to content link`);
console.log(`${checks.hasSemanticHTML ? '✅' : '❌'} Semantic HTML elements`);
console.log(`${checks.hasButtonElements ? '✅' : '❌'} Button elements (not divs)`);

console.log('\n🎯 ARIA Attributes:');
console.log('─'.repeat(60));
console.log(`${checks.hasAriaLabels ? '✅' : '❌'} ARIA labels present`);
console.log(`${checks.hasAriaLive ? '✅' : '❌'} ARIA live regions`);

console.log('\n🖼️  Content Accessibility:');
console.log('─'.repeat(60));
console.log(`${checks.hasAltText ? '✅' : '❌'} Image alt attributes`);
console.log(`${checks.hasFormLabels ? '✅' : '❌'} Form labels`);

// Check CSS files for focus indicators
const cssPath = path.join(__dirname, '..', 'css', 'main.css');
let hasFocusStyles = false;

if (fs.existsSync(cssPath)) {
  const css = fs.readFileSync(cssPath, 'utf-8');
  hasFocusStyles = /:focus/.test(css);
}

console.log('\n🎨 Visual Accessibility:');
console.log('─'.repeat(60));
console.log(`${hasFocusStyles ? '✅' : '❌'} Focus indicators in CSS`);

// Check JavaScript files for keyboard navigation
const jsFiles = ['app.js', 'keyboard-navigation.js', 'ui.js'];
let hasKeyboardHandlers = false;

for (const file of jsFiles) {
  const jsPath = path.join(__dirname, '..', 'js', file);
  if (fs.existsSync(jsPath)) {
    const js = fs.readFileSync(jsPath, 'utf-8');
    if (/addEventListener.*['"]key/i.test(js) || /onkey/i.test(js)) {
      hasKeyboardHandlers = true;
      break;
    }
  }
}

console.log(`${hasKeyboardHandlers ? '✅' : '❌'} Keyboard event handlers`);

// Calculate score
const totalChecks = Object.keys(checks).length + 2; // +2 for CSS and JS checks
const passedChecks = Object.values(checks).filter(Boolean).length + 
                     (hasFocusStyles ? 1 : 0) + 
                     (hasKeyboardHandlers ? 1 : 0);
const score = Math.round((passedChecks / totalChecks) * 100);

console.log('\n📊 ACCESSIBILITY SCORE:');
console.log('='.repeat(60));
console.log(`Score: ${score}% (${passedChecks}/${totalChecks} checks passed)`);

if (score >= 90) {
  console.log('✅ EXCELLENT - Meets accessibility requirements');
} else if (score >= 70) {
  console.log('⚠️  GOOD - Some improvements needed');
} else {
  console.log('❌ NEEDS WORK - Significant accessibility issues');
}

console.log('\n📝 RECOMMENDATIONS:');
console.log('─'.repeat(60));

if (!checks.hasLang) {
  console.log('• Add lang attribute to <html> tag');
}
if (!checks.hasSkipLink) {
  console.log('• Add "Skip to main content" link');
}
if (!checks.hasAriaLabels) {
  console.log('• Add ARIA labels to interactive elements');
}
if (!checks.hasAriaLive) {
  console.log('• Add ARIA live regions for dynamic content');
}
if (!hasFocusStyles) {
  console.log('• Add visible focus indicators in CSS');
}
if (!hasKeyboardHandlers) {
  console.log('• Implement keyboard navigation handlers');
}

console.log('\n💡 NEXT STEPS:');
console.log('─'.repeat(60));
console.log('1. Run Lighthouse audit in Chrome DevTools');
console.log('2. Test with screen readers (NVDA, VoiceOver)');
console.log('3. Test keyboard navigation (Tab, Enter, Escape)');
console.log('4. Use axe DevTools for detailed analysis');
console.log('5. Test with users who rely on assistive technology');

console.log('\n' + '='.repeat(60));
console.log('Audit complete!');
console.log('='.repeat(60));

// Exit with appropriate code
process.exit(score >= 90 ? 0 : 1);
