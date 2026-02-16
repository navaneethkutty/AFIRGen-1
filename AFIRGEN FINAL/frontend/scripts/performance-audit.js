/**
 * Performance Audit Script
 * Checks bundle sizes, asset optimization, and performance metrics
 */

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

console.log('='.repeat(60));
console.log('PERFORMANCE AUDIT REPORT');
console.log('='.repeat(60));
console.log();

// Helper function to get file size
function getFileSize(filePath) {
  try {
    const stats = fs.statSync(filePath);
    return stats.size;
  } catch (error) {
    return 0;
  }
}

// Helper function to get gzipped size
function getGzippedSize(filePath) {
  try {
    const content = fs.readFileSync(filePath);
    const gzipped = zlib.gzipSync(content);
    return gzipped.length;
  } catch (error) {
    return 0;
  }
}

// Helper function to format bytes
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Check bundle sizes
console.log('📦 BUNDLE SIZE ANALYSIS:');
console.log('─'.repeat(60));

const files = {
  'CSS': [
    'css/main.css',
    'css/themes.css',
    'css/glassmorphism.css'
  ],
  'JavaScript': [
    'js/app.js',
    'js/api.js',
    'js/validation.js',
    'js/security.js',
    'js/ui.js',
    'js/storage.js'
  ],
  'HTML': [
    'index.html'
  ]
};

const sizes = {
  css: { raw: 0, gzipped: 0 },
  js: { raw: 0, gzipped: 0 },
  html: { raw: 0, gzipped: 0 },
  total: { raw: 0, gzipped: 0 }
};

// Calculate CSS sizes
console.log('\n📄 CSS Files:');
files.CSS.forEach(file => {
  const filePath = path.join(__dirname, '..', file);
  const raw = getFileSize(filePath);
  const gzipped = getGzippedSize(filePath);
  
  if (raw > 0) {
    sizes.css.raw += raw;
    sizes.css.gzipped += gzipped;
    console.log(`  ${file}: ${formatBytes(raw)} (${formatBytes(gzipped)} gzipped)`);
  }
});

// Calculate JS sizes
console.log('\n📄 JavaScript Files:');
files.JavaScript.forEach(file => {
  const filePath = path.join(__dirname, '..', file);
  const raw = getFileSize(filePath);
  const gzipped = getGzippedSize(filePath);
  
  if (raw > 0) {
    sizes.js.raw += raw;
    sizes.js.gzipped += gzipped;
    console.log(`  ${file}: ${formatBytes(raw)} (${formatBytes(gzipped)} gzipped)`);
  }
});

// Calculate HTML sizes
console.log('\n📄 HTML Files:');
files.HTML.forEach(file => {
  const filePath = path.join(__dirname, '..', file);
  const raw = getFileSize(filePath);
  const gzipped = getGzippedSize(filePath);
  
  if (raw > 0) {
    sizes.html.raw += raw;
    sizes.html.gzipped += gzipped;
    console.log(`  ${file}: ${formatBytes(raw)} (${formatBytes(gzipped)} gzipped)`);
  }
});

// Calculate totals
sizes.total.raw = sizes.css.raw + sizes.js.raw + sizes.html.raw;
sizes.total.gzipped = sizes.css.gzipped + sizes.js.gzipped + sizes.html.gzipped;

console.log('\n📊 TOTALS:');
console.log('─'.repeat(60));
console.log(`CSS:        ${formatBytes(sizes.css.raw)} (${formatBytes(sizes.css.gzipped)} gzipped)`);
console.log(`JavaScript: ${formatBytes(sizes.js.raw)} (${formatBytes(sizes.js.gzipped)} gzipped)`);
console.log(`HTML:       ${formatBytes(sizes.html.raw)} (${formatBytes(sizes.html.gzipped)} gzipped)`);
console.log(`TOTAL:      ${formatBytes(sizes.total.raw)} (${formatBytes(sizes.total.gzipped)} gzipped)`);

// Check against requirements
console.log('\n✅ REQUIREMENTS CHECK:');
console.log('─'.repeat(60));

const requirements = {
  cssMax: 50 * 1024, // 50KB
  jsMax: 100 * 1024, // 100KB
  totalMax: 500 * 1024 // 500KB
};

const cssPasses = sizes.css.raw <= requirements.cssMax;
const jsPasses = sizes.js.raw <= requirements.jsMax;
const totalPasses = sizes.total.gzipped <= requirements.totalMax;

console.log(`${cssPasses ? '✅' : '❌'} CSS < 50KB: ${formatBytes(sizes.css.raw)} / 50KB`);
console.log(`${jsPasses ? '✅' : '❌'} JS < 100KB: ${formatBytes(sizes.js.raw)} / 100KB`);
console.log(`${totalPasses ? '✅' : '❌'} Total (gzipped) < 500KB: ${formatBytes(sizes.total.gzipped)} / 500KB`);

// Check for optimization features
console.log('\n🔧 OPTIMIZATION FEATURES:');
console.log('─'.repeat(60));

const indexPath = path.join(__dirname, '..', 'index.html');
const indexContent = fs.existsSync(indexPath) ? fs.readFileSync(indexPath, 'utf-8') : '';

const optimizations = {
  hasServiceWorker: /service.*worker|sw\.js/i.test(indexContent),
  hasPreconnect: /<link[^>]*rel=["']preconnect["']/i.test(indexContent),
  hasDnsPrefetch: /<link[^>]*rel=["']dns-prefetch["']/i.test(indexContent),
  hasLazyLoading: /loading=["']lazy["']/i.test(indexContent),
  hasAsyncScripts: /<script[^>]*async/i.test(indexContent),
  hasDeferScripts: /<script[^>]*defer/i.test(indexContent)
};

console.log(`${optimizations.hasServiceWorker ? '✅' : '❌'} Service Worker for offline support`);
console.log(`${optimizations.hasPreconnect ? '✅' : '❌'} Preconnect resource hints`);
console.log(`${optimizations.hasDnsPrefetch ? '✅' : '❌'} DNS prefetch`);
console.log(`${optimizations.hasLazyLoading ? '✅' : '❌'} Lazy loading images`);
console.log(`${optimizations.hasAsyncScripts ? '✅' : '❌'} Async script loading`);
console.log(`${optimizations.hasDeferScripts ? '✅' : '❌'} Deferred script loading`);

// Check for minified files in dist
console.log('\n📦 BUILD OUTPUT (dist/):');
console.log('─'.repeat(60));

const distPath = path.join(__dirname, '..', 'dist');
if (fs.existsSync(distPath)) {
  const distFiles = fs.readdirSync(distPath, { recursive: true });
  const minifiedFiles = distFiles.filter(f => f.endsWith('.min.js') || f.endsWith('.min.css'));
  
  console.log(`✅ Found ${minifiedFiles.length} minified files in dist/`);
  
  let distTotal = 0;
  minifiedFiles.forEach(file => {
    const filePath = path.join(distPath, file);
    const size = getFileSize(filePath);
    distTotal += size;
  });
  
  console.log(`   Total minified size: ${formatBytes(distTotal)}`);
} else {
  console.log('⚠️  dist/ directory not found - run npm run build');
}

// Calculate performance score
const checks = [
  cssPasses,
  jsPasses,
  totalPasses,
  ...Object.values(optimizations)
];

const passedChecks = checks.filter(Boolean).length;
const totalChecks = checks.length;
const score = Math.round((passedChecks / totalChecks) * 100);

console.log('\n📊 PERFORMANCE SCORE:');
console.log('='.repeat(60));
console.log(`Score: ${score}% (${passedChecks}/${totalChecks} checks passed)`);

if (score >= 90) {
  console.log('✅ EXCELLENT - Meets performance requirements');
} else if (score >= 70) {
  console.log('⚠️  GOOD - Some optimizations needed');
} else {
  console.log('❌ NEEDS WORK - Significant performance issues');
}

console.log('\n📝 RECOMMENDATIONS:');
console.log('─'.repeat(60));

if (!cssPasses) {
  console.log('• Reduce CSS bundle size (currently over 50KB)');
}
if (!jsPasses) {
  console.log('• Reduce JavaScript bundle size (currently over 100KB)');
}
if (!totalPasses) {
  console.log('• Reduce total bundle size (currently over 500KB gzipped)');
}
if (!optimizations.hasServiceWorker) {
  console.log('• Implement Service Worker for offline support');
}
if (!optimizations.hasPreconnect) {
  console.log('• Add preconnect hints for external resources');
}
if (!optimizations.hasLazyLoading) {
  console.log('• Add lazy loading to images');
}

console.log('\n💡 NEXT STEPS:');
console.log('─'.repeat(60));
console.log('1. Run npm run build to create minified bundles');
console.log('2. Run Lighthouse audit in Chrome DevTools');
console.log('3. Test on 3G network (Chrome DevTools throttling)');
console.log('4. Measure FCP (First Contentful Paint) < 1s');
console.log('5. Measure TTI (Time to Interactive) < 3s');

console.log('\n' + '='.repeat(60));
console.log('Audit complete!');
console.log('='.repeat(60));

// Exit with appropriate code
process.exit(score >= 90 ? 0 : 1);
