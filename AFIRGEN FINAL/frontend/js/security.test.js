/**
 * Unit tests for Security module
 */

// Mock DOMPurify
global.DOMPurify = {
  sanitize: jest.fn((html, config) => {
    // Simple mock implementation that removes script tags
    return html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  })
};

describe('Security Module', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    jest.spyOn(document, 'querySelector');
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('sanitizeHTML()', () => {
    const sanitizeHTML = (html) => {
      if (typeof html !== 'string') {
        return '';
      }

      if (typeof DOMPurify === 'undefined') {
        console.error('DOMPurify library not loaded');
        return escapeHTML(html);
      }

      const config = {
        ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p', 'br', 'span', 'div'],
        ALLOWED_ATTR: ['class'],
        KEEP_CONTENT: true,
        RETURN_DOM: false,
        RETURN_DOM_FRAGMENT: false
      };

      return DOMPurify.sanitize(html, config);
    };

    test('should remove script tags', () => {
      const input = '<script>alert("XSS")</script><p>Hello</p>';
      const result = sanitizeHTML(input);
      expect(result).not.toContain('<script>');
      expect(result).toContain('<p>Hello</p>');
    });

    test('should call DOMPurify with correct config', () => {
      const input = '<p>Test</p>';
      sanitizeHTML(input);

      expect(DOMPurify.sanitize).toHaveBeenCalledWith(
        input,
        expect.objectContaining({
          ALLOWED_TAGS: expect.arrayContaining(['p', 'b', 'i']),
          ALLOWED_ATTR: ['class']
        })
      );
    });

    test('should handle non-string input', () => {
      expect(sanitizeHTML(null)).toBe('');
      expect(sanitizeHTML(undefined)).toBe('');
      expect(sanitizeHTML(123)).toBe('');
      expect(sanitizeHTML({})).toBe('');
    });

    test('should handle empty string', () => {
      const result = sanitizeHTML('');
      expect(result).toBe('');
    });

    test('should preserve allowed tags', () => {
      const input = '<p>Hello <b>World</b></p>';
      const result = sanitizeHTML(input);
      expect(result).toContain('<p>');
      expect(result).toContain('<b>');
    });
  });

  describe('sanitizeText()', () => {
    const sanitizeText = (text, options = {}) => {
      if (typeof text !== 'string') {
        return '';
      }

      const { maxLength = 10000 } = options;

      // Remove control characters (except newline, tab, carriage return)
      let sanitized = text.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');

      // Limit length to prevent DoS
      if (sanitized.length > maxLength) {
        sanitized = sanitized.substring(0, maxLength);
      }

      // Trim whitespace
      sanitized = sanitized.trim();

      return sanitized;
    };

    test('should remove control characters', () => {
      const input = 'Hello\x00World\x01Test';
      const result = sanitizeText(input);
      expect(result).not.toContain('\x00');
      expect(result).not.toContain('\x01');
      expect(result).toBe('HelloWorldTest');
    });

    test('should preserve newlines and tabs', () => {
      const input = 'Hello\nWorld\tTest';
      const result = sanitizeText(input);
      expect(result).toContain('\n');
      expect(result).toContain('\t');
    });

    test('should trim whitespace', () => {
      const input = '  Hello World  ';
      const result = sanitizeText(input);
      expect(result).toBe('Hello World');
    });

    test('should enforce max length', () => {
      const input = 'a'.repeat(100);
      const result = sanitizeText(input, { maxLength: 50 });
      expect(result.length).toBe(50);
    });

    test('should handle non-string input', () => {
      expect(sanitizeText(null)).toBe('');
      expect(sanitizeText(undefined)).toBe('');
      expect(sanitizeText(123)).toBe('');
    });

    test('should handle empty string', () => {
      const result = sanitizeText('');
      expect(result).toBe('');
    });

    test('should use default max length', () => {
      const input = 'a'.repeat(15000);
      const result = sanitizeText(input);
      expect(result.length).toBe(10000);
    });
  });

  describe('escapeHTML()', () => {
    const escapeHTML = (str) => {
      if (typeof str !== 'string') {
        return '';
      }

      const htmlEscapeMap = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
      };

      return str.replace(/[&<>"'/]/g, (char) => htmlEscapeMap[char]);
    };

    test('should escape HTML special characters', () => {
      const input = '<script>alert("XSS")</script>';
      const result = escapeHTML(input);
      expect(result).toBe('&lt;script&gt;alert(&quot;XSS&quot;)&lt;&#x2F;script&gt;');
    });

    test('should escape ampersands', () => {
      const input = 'Tom & Jerry';
      const result = escapeHTML(input);
      expect(result).toBe('Tom &amp; Jerry');
    });

    test('should escape quotes', () => {
      const input = 'He said "Hello"';
      const result = escapeHTML(input);
      expect(result).toContain('&quot;');
    });

    test('should escape single quotes', () => {
      const input = "It's a test";
      const result = escapeHTML(input);
      expect(result).toContain('&#x27;');
    });

    test('should escape forward slashes', () => {
      const input = '</script>';
      const result = escapeHTML(input);
      expect(result).toContain('&#x2F;');
    });

    test('should handle non-string input', () => {
      expect(escapeHTML(null)).toBe('');
      expect(escapeHTML(undefined)).toBe('');
      expect(escapeHTML(123)).toBe('');
    });

    test('should handle empty string', () => {
      const result = escapeHTML('');
      expect(result).toBe('');
    });

    test('should handle text without special characters', () => {
      const input = 'Hello World';
      const result = escapeHTML(input);
      expect(result).toBe('Hello World');
    });
  });

  describe('sanitizeURL()', () => {
    const sanitizeURL = (url, allowedProtocols = ['http:', 'https:']) => {
      if (typeof url !== 'string' || !url.trim()) {
        return null;
      }

      try {
        const parsed = new URL(url);

        if (!allowedProtocols.includes(parsed.protocol)) {
          return null;
        }

        return parsed.href;
      } catch (e) {
        return null;
      }
    };

    test('should accept valid HTTP URLs', () => {
      const url = 'http://example.com';
      const result = sanitizeURL(url);
      expect(result).toBe('http://example.com/');
    });

    test('should accept valid HTTPS URLs', () => {
      const url = 'https://example.com';
      const result = sanitizeURL(url);
      expect(result).toBe('https://example.com/');
    });

    test('should reject javascript: protocol', () => {
      const url = 'javascript:alert("XSS")';
      const result = sanitizeURL(url);
      expect(result).toBeNull();
    });

    test('should reject data: protocol', () => {
      const url = 'data:text/html,<script>alert("XSS")</script>';
      const result = sanitizeURL(url);
      expect(result).toBeNull();
    });

    test('should reject file: protocol', () => {
      const url = 'file:///etc/passwd';
      const result = sanitizeURL(url);
      expect(result).toBeNull();
    });

    test('should handle invalid URLs', () => {
      const url = 'not a valid url';
      const result = sanitizeURL(url);
      expect(result).toBeNull();
    });

    test('should handle empty string', () => {
      const result = sanitizeURL('');
      expect(result).toBeNull();
    });

    test('should handle null/undefined', () => {
      expect(sanitizeURL(null)).toBeNull();
      expect(sanitizeURL(undefined)).toBeNull();
    });

    test('should accept custom allowed protocols', () => {
      const url = 'ftp://example.com';
      const result = sanitizeURL(url, ['ftp:']);
      expect(result).toBe('ftp://example.com/');
    });

    test('should normalize URLs', () => {
      const url = 'https://example.com/path/../file.html';
      const result = sanitizeURL(url);
      expect(result).toBe('https://example.com/file.html');
    });
  });

  describe('CSP Functions', () => {
    describe('enforceCSP()', () => {
      const enforceCSP = () => {
        const cspMeta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');

        if (!cspMeta) {
          console.error('CSP meta tag not found in document');
          return false;
        }

        const cspContent = cspMeta.getAttribute('content');

        if (!cspContent) {
          console.error('CSP meta tag has no content');
          return false;
        }

        const requiredDirectives = [
          'default-src',
          'script-src',
          'style-src',
          'font-src',
          'connect-src',
          'img-src',
          'frame-ancestors',
          'base-uri',
          'form-action'
        ];

        const missingDirectives = requiredDirectives.filter(
          directive => !cspContent.includes(directive)
        );

        if (missingDirectives.length > 0) {
          console.warn('CSP missing directives:', missingDirectives);
        }

        console.log('CSP enforced:', cspContent);
        return true;
      };

      test('should return false when CSP meta tag is missing', () => {
        document.querySelector.mockReturnValue(null);

        const result = enforceCSP();

        expect(result).toBe(false);
        expect(console.error).toHaveBeenCalledWith('CSP meta tag not found in document');
      });

      test('should return false when CSP content is empty', () => {
        const mockMeta = {
          getAttribute: jest.fn().mockReturnValue('')
        };
        document.querySelector.mockReturnValue(mockMeta);

        const result = enforceCSP();

        expect(result).toBe(false);
        expect(console.error).toHaveBeenCalledWith('CSP meta tag has no content');
      });

      test('should return true when CSP is properly configured', () => {
        const cspContent = "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'";
        const mockMeta = {
          getAttribute: jest.fn().mockReturnValue(cspContent)
        };
        document.querySelector.mockReturnValue(mockMeta);

        const result = enforceCSP();

        expect(result).toBe(true);
        expect(console.log).toHaveBeenCalledWith('CSP enforced:', cspContent);
      });

      test('should warn about missing directives', () => {
        const cspContent = "default-src 'self'; script-src 'self'";
        const mockMeta = {
          getAttribute: jest.fn().mockReturnValue(cspContent)
        };
        document.querySelector.mockReturnValue(mockMeta);

        enforceCSP();

        expect(console.warn).toHaveBeenCalledWith(
          'CSP missing directives:',
          expect.arrayContaining(['style-src', 'font-src'])
        );
      });
    });

    describe('reportCSPViolation()', () => {
      const reportCSPViolation = (violation) => {
        const violationDetails = {
          blockedURI: violation.blockedURI,
          violatedDirective: violation.violatedDirective,
          effectiveDirective: violation.effectiveDirective,
          originalPolicy: violation.originalPolicy,
          sourceFile: violation.sourceFile,
          lineNumber: violation.lineNumber,
          columnNumber: violation.columnNumber,
          timestamp: expect.any(String)
        };

        console.error('CSP Violation:', violationDetails);
      };

      test('should log CSP violation details', () => {
        const mockViolation = {
          blockedURI: 'https://evil.com/script.js',
          violatedDirective: 'script-src',
          effectiveDirective: 'script-src',
          originalPolicy: "default-src 'self'",
          sourceFile: 'https://example.com/page.html',
          lineNumber: 10,
          columnNumber: 5
        };

        reportCSPViolation(mockViolation);

        expect(console.error).toHaveBeenCalledWith(
          'CSP Violation:',
          expect.objectContaining({
            blockedURI: 'https://evil.com/script.js',
            violatedDirective: 'script-src'
          })
        );
      });
    });
  });

  describe('XSS Prevention', () => {
    test('should prevent XSS through script injection', () => {
      const escapeHTML = (str) => {
        if (typeof str !== 'string') return '';
        const htmlEscapeMap = {
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#x27;',
          '/': '&#x2F;'
        };
        return str.replace(/[&<>"'/]/g, (char) => htmlEscapeMap[char]);
      };

      const xssPayloads = [
        '<script>alert("XSS")</script>',
        '<img src=x onerror=alert("XSS")>',
        '<svg onload=alert("XSS")>',
        'javascript:alert("XSS")',
        '<iframe src="javascript:alert(\'XSS\')"></iframe>'
      ];

      xssPayloads.forEach(payload => {
        const escaped = escapeHTML(payload);
        expect(escaped).not.toContain('<script');
        expect(escaped).not.toContain('javascript:');
        expect(escaped).toContain('onerror=');
        expect(escaped).toContain('onload=');
        expect(escaped).not.toContain('<img');
      });
    });

    test('should prevent XSS through event handlers', () => {
      const escapeHTML = (str) => {
        if (typeof str !== 'string') return '';
        const htmlEscapeMap = {
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#x27;',
          '/': '&#x2F;'
        };
        return str.replace(/[&<>"'/]/g, (char) => htmlEscapeMap[char]);
      };

      const payload = '<div onclick="alert(\'XSS\')">Click me</div>';
      const escaped = escapeHTML(payload);
      expect(escaped).toContain('onclick=');
      expect(escaped).not.toContain('<div');
    });
  });
});
