/**
 * Script to fix ESLint errors automatically
 * Run with: node scripts/fix-eslint-errors.js
 */

const fs = require('fs');
const path = require('path');

// Fix api.js
const apiPath = path.join(__dirname, '../js/api.js');
let apiContent = fs.readFileSync(apiPath, 'utf8');

// Fix duplicate clearCache method (remove second occurrence around line 188)
apiContent = apiContent.replace(
  /clearCache\(\) \{\s+this\.cache\.clear\(\);\s+\}\s+\/\*\*\s+\* Clear all cached data\s+\*\/\s+clearCache\(\) \{\s+this\.cache\.clear\(\);\s+\}/,
  'clearCache() {\n    this.cache.clear();\n  }'
);

// Fix no-return-await errors - remove await before return statements
apiContent = apiContent.replace(/return await response\.json\(\);/g, 'return response.json();');

// Save fixed api.js
fs.writeFileSync(apiPath, apiContent, 'utf8');
console.log('✓ Fixed api.js');

// Fix line endings in test files (CRLF to LF)
const testFiles = [
  '../js/api.test.js',
  '../js/validation.test.js',
  '../js/security.test.js',
  '../js/ui.test.js',
  '../js/storage.test.js'
];

testFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  if (fs.existsSync(filePath)) {
    let content = fs.readFileSync(filePath, 'utf8');
    // Convert CRLF to LF
    content = content.replace(/\r\n/g, '\n');
    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`✓ Fixed line endings in ${path.basename(file)}`);
  }
});

console.log('\n✅ All ESLint errors fixed!');
console.log('Run "npm run lint" to verify.');
