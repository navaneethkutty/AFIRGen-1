/**
 * Comprehensive ESLint fix script
 */

const fs = require('fs');
const path = require('path');

function fixFile(filePath) {
    if (!fs.existsSync(filePath)) {
        console.log(`⚠ File not found: ${filePath}`);
        return;
    }

    let content = fs.readFileSync(filePath, 'utf8');
    const originalContent = content;

    // Fix line endings (CRLF to LF)
    content = content.replace(/\r\n/g, '\n');

    // Remove trailing spaces
    content = content.replace(/ +\n/g, '\n');
    content = content.replace(/ +$/gm, '');

    // Fix no-return-await
    content = content.replace(/return await response\.json\(\);/g, 'return response.json();');

    // Save if changed
    if (content !== originalContent) {
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`✓ Fixed ${path.basename(filePath)}`);
        return true;
    }

    console.log(`- No changes needed for ${path.basename(filePath)}`);
    return false;
}

// Files to fix
const files = [
    '../js/api.js',
    '../js/api.test.js',
    '../js/api.pbt.test.js',
    '../js/validation.test.js',
    '../js/security.test.js',
    '../js/ui.test.js',
    '../js/storage.test.js',
    '../js/dark-mode-contrast.test.js',
    '../js/pdf-export-completeness.test.js'
];

console.log('Fixing ESLint errors...\n');

let fixedCount = 0;
files.forEach(file => {
    const filePath = path.join(__dirname, file);
    if (fixFile(filePath)) {
        fixedCount++;
    }
});

console.log(`\n✅ Fixed ${fixedCount} file(s)`);
console.log('Run "npm run lint" to verify.');
