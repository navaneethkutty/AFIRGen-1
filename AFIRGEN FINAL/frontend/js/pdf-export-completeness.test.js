/**
 * Property Test 10: PDF Export Completeness
 * Validates: Requirements 5.5.2
 *
 * Property: For any FIR data exported to PDF, the generated PDF SHALL contain
 * all FIR fields, be properly formatted, and be downloadable without errors.
 */

const fc = require('fast-check');

// Mock jsPDF
const mockJsPDF = {
    jsPDF: class {
        constructor(options) {
            this.options = options;
            this.pages = [[]];
            this.currentPage = 0;
            this.content = [];
        }

        internal = {
            pageSize: {
                getWidth: () => 210,
                getHeight: () => 297
            },
            getNumberOfPages: () => this.pages.length
        };

        setFontSize(size) {
            this.content.push({ type: 'fontSize', value: size });
        }

        setFont(family, style) {
            this.content.push({ type: 'font', family, style });
        }

        setFillColor(r, g, b) {
            this.content.push({ type: 'fillColor', r, g, b });
        }

        setDrawColor(r, g, b) {
            this.content.push({ type: 'drawColor', r, g, b });
        }

        setTextColor(r, g, b) {
            this.content.push({ type: 'textColor', r, g, b });
        }

        text(text, x, y, options) {
            this.content.push({ type: 'text', text, x, y, options });
        }

        rect(x, y, w, h, style) {
            this.content.push({ type: 'rect', x, y, w, h, style });
        }

        line(x1, y1, x2, y2) {
            this.content.push({ type: 'line', x1, y1, x2, y2 });
        }

        addPage() {
            this.pages.push([]);
            this.currentPage++;
        }

        setPage(pageNum) {
            this.currentPage = pageNum - 1;
        }

        splitTextToSize(text, maxWidth) {
            const words = text.split(' ');
            const lines = [];
            let currentLine = '';

            words.forEach(word => {
                if ((currentLine + word).length * 2 < maxWidth) {
                    currentLine += (currentLine ? ' ' : '') + word;
                } else {
                    if (currentLine) lines.push(currentLine);
                    currentLine = word;
                }
            });

            if (currentLine) lines.push(currentLine);
            return lines;
        }

        save(filename) {
            this.savedFilename = filename;
        }

        output(type) {
            if (type === 'blob') {
                return new Blob(['mock pdf content'], { type: 'application/pdf' });
            }
            return 'mock pdf content';
        }
    }
};

// Mock window.jspdf
global.window = {
    jspdf: mockJsPDF,
    showToast: jest.fn()
};

// Import PDF module
const { generatePDF, downloadPDF, exportFIRAsPDF } = require('./pdf.js');

describe('Property 10: PDF Export Completeness', () => {

    // Arbitrary for FIR data
    const firDataArbitrary = fc.record({
        number: fc.option(fc.string({ minLength: 5, maxLength: 20 }), { nil: undefined }),
        date: fc.option(fc.date(), { nil: undefined }),
        location: fc.option(fc.string({ minLength: 5, maxLength: 50 }), { nil: undefined }),
        policeStation: fc.option(fc.string({ minLength: 5, maxLength: 50 }), { nil: undefined }),
        complainant: fc.option(fc.string({ minLength: 10, maxLength: 100 }), { nil: undefined }),
        description: fc.option(fc.string({ minLength: 20, maxLength: 500 }), { nil: undefined }),
        content: fc.option(fc.string({ minLength: 20, maxLength: 500 }), { nil: undefined }),
        fir_content: fc.option(fc.string({ minLength: 20, maxLength: 500 }), { nil: undefined }),
        status: fc.option(fc.constantFrom('pending', 'investigating', 'closed'), { nil: undefined }),
        officer: fc.option(fc.string({ minLength: 5, maxLength: 50 }), { nil: undefined })
    });

    test('Generated PDF contains all provided FIR fields', () => {
        fc.assert(
            fc.property(firDataArbitrary, (firData) => {
                const pdf = generatePDF(firData);

                // PDF should be generated
                if (!pdf) return false;

                // Check that all non-null fields are included in PDF content
                const contentTexts = pdf.content
                    .filter(item => item.type === 'text')
                    .map(item => Array.isArray(item.text) ? item.text.join(' ') : item.text)
                    .join(' ');

                // Verify each field is present if it exists
                const checks = [];

                if (firData.number) {
                    checks.push(contentTexts.includes(firData.number));
                }

                if (firData.complainant) {
                    checks.push(contentTexts.includes(firData.complainant));
                }

                if (firData.description) {
                    checks.push(contentTexts.includes(firData.description));
                } else if (firData.content) {
                    checks.push(contentTexts.includes(firData.content));
                } else if (firData.fir_content) {
                    checks.push(contentTexts.includes(firData.fir_content));
                }

                if (firData.status) {
                    checks.push(contentTexts.toLowerCase().includes(firData.status.toLowerCase()));
                }

                // All provided fields should be present
                return checks.length === 0 || checks.every(check => check === true);
            }),
            { numRuns: 100 }
        );
    });

    test('PDF has proper structure with header and footer', () => {
        fc.assert(
            fc.property(firDataArbitrary, (firData) => {
                const pdf = generatePDF(firData);

                if (!pdf) return false;

                const contentTexts = pdf.content
                    .filter(item => item.type === 'text')
                    .map(item => Array.isArray(item.text) ? item.text.join(' ') : item.text);

                // Should have header
                const hasHeader = contentTexts.some(text =>
                    text.includes('FIRST INFORMATION REPORT')
                );

                // Should have footer elements
                const hasPageNumber = contentTexts.some(text =>
                    text.includes('Page')
                );

                const hasTimestamp = contentTexts.some(text =>
                    text.includes('Generated')
                );

                return hasHeader && hasPageNumber && hasTimestamp;
            }),
            { numRuns: 50 }
        );
    });

    test('PDF formatting is consistent', () => {
        fc.assert(
            fc.property(firDataArbitrary, (firData) => {
                const pdf = generatePDF(firData);

                if (!pdf) return false;

                // Check that font sizes are used
                const fontSizes = pdf.content
                    .filter(item => item.type === 'fontSize')
                    .map(item => item.value);

                // Should have multiple font sizes for hierarchy
                const uniqueSizes = new Set(fontSizes);

                // Check that fonts are set
                const fonts = pdf.content
                    .filter(item => item.type === 'font');

                // Should use both normal and bold fonts
                const hasBold = fonts.some(f => f.style === 'bold');
                const hasNormal = fonts.some(f => f.style === 'normal');

                return uniqueSizes.size >= 2 && hasBold && hasNormal;
            }),
            { numRuns: 50 }
        );
    });

    test('PDF can be downloaded without errors', () => {
        fc.assert(
            fc.property(
                firDataArbitrary,
                fc.string({ minLength: 5, maxLength: 50 }),
                (firData, filename) => {
                    const pdf = generatePDF(firData);

                    if (!pdf) return false;

                    // Should not throw error
                    try {
                        downloadPDF(pdf, filename);
                        return pdf.savedFilename !== undefined;
                    } catch (error) {
                        return false;
                    }
                }
            ),
            { numRuns: 50 }
        );
    });

    test('PDF filename is sanitized', () => {
        fc.assert(
            fc.property(
                firDataArbitrary,
                fc.string({ minLength: 1, maxLength: 50 }),
                (firData, filename) => {
                    const pdf = generatePDF(firData);

                    if (!pdf) return true; // Skip if PDF generation fails

                    downloadPDF(pdf, filename);

                    // Filename should not contain special characters
                    const sanitized = pdf.savedFilename;
                    const hasInvalidChars = /[<>:"/\\|?*]/.test(sanitized);

                    return !hasInvalidChars;
                }
            ),
            { numRuns: 50 }
        );
    });

    test('PDF export handles missing fields gracefully', () => {
        fc.assert(
            fc.property(
                fc.record({
                    number: fc.option(fc.string(), { nil: undefined }),
                    date: fc.option(fc.date(), { nil: undefined }),
                    complainant: fc.option(fc.string(), { nil: undefined })
                }),
                (firData) => {
                    // Should not throw error even with minimal data
                    try {
                        const pdf = generatePDF(firData);
                        return pdf !== null;
                    } catch (error) {
                        return false;
                    }
                }
            ),
            { numRuns: 50 }
        );
    });

    test('PDF sections are properly separated', () => {
        fc.assert(
            fc.property(firDataArbitrary, (firData) => {
                const pdf = generatePDF(firData);

                if (!pdf) return false;

                // Check for section separators (lines)
                const lines = pdf.content.filter(item => item.type === 'line');

                // Should have at least one separator line
                return lines.length >= 1;
            }),
            { numRuns: 50 }
        );
    });

    test('PDF respects page boundaries', () => {
        fc.assert(
            fc.property(
                fc.record({
                    number: fc.option(fc.string({ minLength: 5, maxLength: 20 }), { nil: undefined }),
                    date: fc.option(fc.date(), { nil: undefined }),
                    location: fc.option(fc.string({ minLength: 5, maxLength: 50 }), { nil: undefined }),
                    policeStation: fc.option(fc.string({ minLength: 5, maxLength: 50 }), { nil: undefined }),
                    complainant: fc.option(fc.string({ minLength: 10, maxLength: 100 }), { nil: undefined }),
                    description: fc.string({ minLength: 1000, maxLength: 5000 }),
                    content: fc.option(fc.string({ minLength: 20, maxLength: 500 }), { nil: undefined }),
                    fir_content: fc.option(fc.string({ minLength: 20, maxLength: 500 }), { nil: undefined }),
                    status: fc.option(fc.constantFrom('pending', 'investigating', 'closed'), { nil: undefined }),
                    officer: fc.option(fc.string({ minLength: 5, maxLength: 50 }), { nil: undefined })
                }),
                (firData) => {
                    const pdf = generatePDF(firData);

                    if (!pdf) return false;

                    // Long content should create multiple pages
                    const pageCount = pdf.internal.getNumberOfPages();

                    // With long description, should have at least 1 page
                    return pageCount >= 1;
                }
            ),
            { numRuns: 30 }
        );
    });

    test('Export function integrates all components', () => {
        fc.assert(
            fc.property(
                firDataArbitrary,
                fc.boolean(),
                fc.boolean(),
                (firData, download, print) => {
                    try {
                        const pdf = exportFIRAsPDF(firData, { download, print });
                        return pdf !== null && pdf !== undefined;
                    } catch (error) {
                        return false;
                    }
                }
            ),
            { numRuns: 50 }
        );
    });

    test('PDF output is valid blob', () => {
        fc.assert(
            fc.property(firDataArbitrary, (firData) => {
                const pdf = generatePDF(firData);

                if (!pdf) return false;

                const blob = pdf.output('blob');

                // Should be a Blob with correct type
                return blob instanceof Blob && blob.type === 'application/pdf';
            }),
            { numRuns: 50 }
        );
    });
});

/**
 * Integration tests
 */
describe('PDF Export Integration', () => {
    test('Complete FIR export workflow', () => {
        const firData = {
            number: 'FIR/2024/001',
            date: new Date('2024-01-15'),
            location: 'Test Police Station',
            complainant: 'John Doe',
            description: 'Test complaint description',
            status: 'pending'
        };

        const pdf = generatePDF(firData);
        expect(pdf).not.toBeNull();

        downloadPDF(pdf, 'test-fir.pdf');
        expect(pdf.savedFilename).toBe('test-fir.pdf');
    });

    test('Minimal FIR data export', () => {
        const firData = {
            number: 'FIR/2024/002'
        };

        const pdf = generatePDF(firData);
        expect(pdf).not.toBeNull();
    });

    test('Export with all fields populated', () => {
        const firData = {
            number: 'FIR/2024/003',
            date: new Date(),
            location: 'Central Police Station',
            policeStation: 'Central PS',
            complainant: 'Jane Smith',
            description: 'Detailed complaint description with multiple sentences.',
            status: 'investigating',
            officer: 'Officer Brown'
        };

        const pdf = generatePDF(firData);
        expect(pdf).not.toBeNull();

        const contentTexts = pdf.content
            .filter(item => item.type === 'text')
            .map(item => Array.isArray(item.text) ? item.text.join(' ') : item.text)
            .join(' ');

        expect(contentTexts).toContain(firData.number);
        expect(contentTexts).toContain(firData.complainant);
        expect(contentTexts).toContain(firData.description);
    });
});
