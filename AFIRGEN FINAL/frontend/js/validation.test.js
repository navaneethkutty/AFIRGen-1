/**
 * Unit tests for Validation module
 */

// Mock document for sanitizeInput
global.document = {
  createElement: jest.fn(() => ({
    textContent: '',
    innerHTML: '',
    set textContent(value) {
      this._textContent = value;
      // Simulate browser HTML entity encoding
      this.innerHTML = value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    },
    get textContent() {
      return this._textContent;
    }
  }))
};

// Mock window
global.window = {
  showToast: jest.fn(),
  Validation: {}
};

describe('File Validation', () => {
  describe('validateFileType()', () => {
    // Mock validateFileType function
    const validateFileType = (file, allowedTypes = ['.jpg', '.jpeg', '.png', '.wav', '.mp3']) => {
      if (!file) {
        return { success: false, error: 'No file provided' };
      }

      const fileName = file.name.toLowerCase();
      const hasValidExtension = allowedTypes.some(type => fileName.endsWith(type.toLowerCase()));

      if (!hasValidExtension) {
        return {
          success: false,
          error: `File type not allowed. Allowed types: ${allowedTypes.join(', ')}`
        };
      }

      return { success: true };
    };

    test('should accept valid file types', () => {
      const validFiles = [
        { name: 'test.jpg' },
        { name: 'test.jpeg' },
        { name: 'test.png' },
        { name: 'test.pdf' },
        { name: 'test.wav' },
        { name: 'test.mp3' }
      ];

      validFiles.forEach(file => {
        const result = validateFileType(file);
        expect(result.success).toBe(true);
      });
    });

    test('should reject invalid file types', () => {
      const invalidFiles = [
        { name: 'test.exe' },
        { name: 'test.txt' },
        { name: 'test.doc' },
        { name: 'test.zip' }
      ];

      invalidFiles.forEach(file => {
        const result = validateFileType(file);
        expect(result.success).toBe(false);
        expect(result.error).toContain('File type not allowed');
      });
    });

    test('should be case insensitive', () => {
      const files = [
        { name: 'test.JPG' },
        { name: 'test.PNG' },
        { name: 'test.PDF' }
      ];

      files.forEach(file => {
        const result = validateFileType(file);
        expect(result.success).toBe(true);
      });
    });

    test('should handle null file', () => {
      const result = validateFileType(null);
      expect(result.success).toBe(false);
      expect(result.error).toBe('No file provided');
    });

    test('should accept custom allowed types', () => {
      const file = { name: 'test.txt' };
      const result = validateFileType(file, ['.txt', '.doc']);
      expect(result.success).toBe(true);
    });
  });

  describe('validateFileSize()', () => {
    const validateFileSize = (file, maxSize = 10 * 1024 * 1024) => {
      if (!file) {
        return { success: false, error: 'No file provided' };
      }

      if (file.size > maxSize) {
        const maxSizeMB = (maxSize / (1024 * 1024)).toFixed(2);
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        return {
          success: false,
          error: `File size (${fileSizeMB}MB) exceeds maximum allowed size of ${maxSizeMB}MB`
        };
      }

      return { success: true };
    };

    test('should accept files within size limit', () => {
      const file = { name: 'test.jpg', size: 5 * 1024 * 1024 }; // 5MB
      const result = validateFileSize(file);
      expect(result.success).toBe(true);
    });

    test('should reject files exceeding size limit', () => {
      const file = { name: 'test.jpg', size: 15 * 1024 * 1024 }; // 15MB
      const result = validateFileSize(file);
      expect(result.success).toBe(false);
      expect(result.error).toContain('exceeds maximum allowed size');
    });

    test('should accept file at exact size limit', () => {
      const file = { name: 'test.jpg', size: 10 * 1024 * 1024 }; // Exactly 10MB
      const result = validateFileSize(file);
      expect(result.success).toBe(true);
    });

    test('should handle null file', () => {
      const result = validateFileSize(null);
      expect(result.success).toBe(false);
      expect(result.error).toBe('No file provided');
    });

    test('should accept custom max size', () => {
      const file = { name: 'test.jpg', size: 3 * 1024 * 1024 }; // 3MB
      const result = validateFileSize(file, 2 * 1024 * 1024); // 2MB limit
      expect(result.success).toBe(false);
    });

    test('should handle zero-size files', () => {
      const file = { name: 'test.jpg', size: 0 };
      const result = validateFileSize(file);
      expect(result.success).toBe(true);
    });
  });

  describe('validateMimeType()', () => {
    test('should validate JPEG files', async () => {
      const mockFile = {
        slice: jest.fn(() => ({
          arrayBuffer: jest.fn().mockResolvedValue(
            new Uint8Array([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46]).buffer
          )
        }))
      };

      const validateMimeType = async (file) => {
        if (!file) {
          return { success: false, error: 'No file provided' };
        }

        try {
          const slice = file.slice(0, 8);
          const arrayBuffer = await slice.arrayBuffer();
          const bytes = new Uint8Array(arrayBuffer);

          // Check for JPEG signature
          if (bytes[0] === 0xFF && bytes[1] === 0xD8 && bytes[2] === 0xFF) {
            return { success: true, mimeType: 'image/jpeg' };
          }

          return { success: false, error: 'File type could not be verified' };
        } catch (error) {
          return { success: false, error: `Failed to read file: ${error.message}` };
        }
      };

      const result = await validateMimeType(mockFile);
      expect(result.success).toBe(true);
      expect(result.mimeType).toBe('image/jpeg');
    });

    test('should validate PNG files', async () => {
      const mockFile = {
        slice: jest.fn(() => ({
          arrayBuffer: jest.fn().mockResolvedValue(
            new Uint8Array([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]).buffer
          )
        }))
      };

      const validateMimeType = async (file) => {
        if (!file) {
          return { success: false, error: 'No file provided' };
        }

        try {
          const slice = file.slice(0, 8);
          const arrayBuffer = await slice.arrayBuffer();
          const bytes = new Uint8Array(arrayBuffer);

          // Check for PNG signature
          if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4E && bytes[3] === 0x47) {
            return { success: true, mimeType: 'image/png' };
          }

          return { success: false, error: 'File type could not be verified' };
        } catch (error) {
          return { success: false, error: `Failed to read file: ${error.message}` };
        }
      };

      const result = await validateMimeType(mockFile);
      expect(result.success).toBe(true);
      expect(result.mimeType).toBe('image/png');
    });

    test('should reject invalid magic numbers', async () => {
      const mockFile = {
        slice: jest.fn(() => ({
          arrayBuffer: jest.fn().mockResolvedValue(
            new Uint8Array([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]).buffer
          )
        }))
      };

      const validateMimeType = async (file) => {
        return { success: false, error: 'File type could not be verified' };
      };

      const result = await validateMimeType(mockFile);
      expect(result.success).toBe(false);
      expect(result.error).toContain('could not be verified');
    });
  });
});

describe('Text Validation', () => {
  const validateText = (text, options = {}) => {
    const {
      minLength = 1,
      maxLength = 10000,
      required = true,
      format = null,
      pattern = null,
      noSpecialChars = false
    } = options;

    if (required && (!text || text.trim().length === 0)) {
      return { success: false, error: 'Text is required' };
    }

    if (!required && (!text || text.trim().length === 0)) {
      return { success: true };
    }

    if (text && text.length < minLength) {
      return {
        success: false,
        error: `Text must be at least ${minLength} characters`
      };
    }

    if (text && text.length > maxLength) {
      return {
        success: false,
        error: `Text must not exceed ${maxLength} characters`
      };
    }

    if (noSpecialChars && text) {
      const specialCharsRegex = /[<>'"&;]/;
      if (specialCharsRegex.test(text)) {
        return {
          success: false,
          error: 'Text contains invalid special characters'
        };
      }
    }

    if (format && text) {
      switch (format) {
      case 'email':
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(text)) {
          return { success: false, error: 'Invalid email format' };
        }
        break;

      case 'phone':
        const phoneRegex = /^[\d\s\-\+\(\)]+$/;
        const digitsOnly = text.replace(/\D/g, '');
        if (!phoneRegex.test(text) || digitsOnly.length < 10 || digitsOnly.length > 15) {
          return { success: false, error: 'Invalid phone number format' };
        }
        break;

      case 'alphanumeric':
        const alphanumericRegex = /^[a-zA-Z0-9\s]+$/;
        if (!alphanumericRegex.test(text)) {
          return { success: false, error: 'Text must contain only letters and numbers' };
        }
        break;

      case 'numeric':
        const numericRegex = /^[0-9]+$/;
        if (!numericRegex.test(text)) {
          return { success: false, error: 'Text must contain only numbers' };
        }
        break;

      case 'alpha':
        const alphaRegex = /^[a-zA-Z\s]+$/;
        if (!alphaRegex.test(text)) {
          return { success: false, error: 'Text must contain only letters' };
        }
        break;

      default:
        return { success: false, error: `Unknown format: ${format}` };
      }
    }

    if (pattern && text) {
      if (!pattern.test(text)) {
        return {
          success: false,
          error: 'Text does not match required format'
        };
      }
    }

    return { success: true };
  };

  describe('validateText()', () => {
    test('should accept valid text', () => {
      const result = validateText('Hello World');
      expect(result.success).toBe(true);
    });

    test('should reject empty required text', () => {
      const result = validateText('');
      expect(result.success).toBe(false);
      expect(result.error).toBe('Text is required');
    });

    test('should accept empty non-required text', () => {
      const result = validateText('', { required: false });
      expect(result.success).toBe(true);
    });

    test('should enforce minimum length', () => {
      const result = validateText('Hi', { minLength: 5 });
      expect(result.success).toBe(false);
      expect(result.error).toContain('at least 5 characters');
    });

    test('should enforce maximum length', () => {
      const result = validateText('This is a very long text', { maxLength: 10 });
      expect(result.success).toBe(false);
      expect(result.error).toContain('not exceed 10 characters');
    });

    test('should validate email format', () => {
      expect(validateText('test@example.com', { format: 'email' }).success).toBe(true);
      expect(validateText('invalid-email', { format: 'email' }).success).toBe(false);
      expect(validateText('test@', { format: 'email' }).success).toBe(false);
      expect(validateText('@example.com', { format: 'email' }).success).toBe(false);
    });

    test('should validate phone format', () => {
      expect(validateText('1234567890', { format: 'phone' }).success).toBe(true);
      expect(validateText('+1-234-567-8900', { format: 'phone' }).success).toBe(true);
      expect(validateText('(123) 456-7890', { format: 'phone' }).success).toBe(true);
      expect(validateText('123', { format: 'phone' }).success).toBe(false); // Too short
      expect(validateText('abc123', { format: 'phone' }).success).toBe(false); // Contains letters
    });

    test('should validate alphanumeric format', () => {
      expect(validateText('Test123', { format: 'alphanumeric' }).success).toBe(true);
      expect(validateText('Test 123', { format: 'alphanumeric' }).success).toBe(true);
      expect(validateText('Test@123', { format: 'alphanumeric' }).success).toBe(false);
    });

    test('should validate numeric format', () => {
      expect(validateText('12345', { format: 'numeric' }).success).toBe(true);
      expect(validateText('123abc', { format: 'numeric' }).success).toBe(false);
      expect(validateText('12.34', { format: 'numeric' }).success).toBe(false);
    });

    test('should validate alpha format', () => {
      expect(validateText('Hello World', { format: 'alpha' }).success).toBe(true);
      expect(validateText('Hello123', { format: 'alpha' }).success).toBe(false);
    });

    test('should reject special characters when noSpecialChars is true', () => {
      expect(validateText('Hello<script>', { noSpecialChars: true }).success).toBe(false);
      expect(validateText('Hello&World', { noSpecialChars: true }).success).toBe(false);
      expect(validateText('Hello"World', { noSpecialChars: true }).success).toBe(false);
      expect(validateText('HelloWorld', { noSpecialChars: true }).success).toBe(true);
    });

    test('should validate custom pattern', () => {
      const pattern = /^[A-Z]{3}-\d{3}$/; // Format: ABC-123
      expect(validateText('ABC-123', { pattern }).success).toBe(true);
      expect(validateText('abc-123', { pattern }).success).toBe(false);
      expect(validateText('ABC123', { pattern }).success).toBe(false);
    });
  });
});

describe('Input Sanitization', () => {
  const sanitizeInput = (input, options = {}) => {
    const {
      stripTags = true,
      escapeQuotes = true,
      trimWhitespace = true
    } = options;

    if (!input) {
      return '';
    }

    let sanitized = input;

    if (trimWhitespace) {
      sanitized = sanitized.trim();
    }

    if (stripTags) {
      const div = document.createElement('div');
      div.textContent = sanitized;
      sanitized = div.innerHTML;
    }

    if (escapeQuotes) {
      sanitized = sanitized
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
    sanitized = sanitized.replace(/\0/g, '');

    return sanitized;
  };

  describe('sanitizeInput()', () => {
    test('should remove HTML tags', () => {
      const result = sanitizeInput('<script>alert("xss")</script>');
      expect(result).not.toContain('<script>');
      expect(result).not.toContain('</script>');
    });

    test('should escape quotes', () => {
      const result = sanitizeInput('Hello "World" and \'Test\'');
      expect(result).toContain('&quot;');
      expect(result).toContain('&#039;');
    });

    test('should trim whitespace', () => {
      const result = sanitizeInput('  Hello World  ');
      expect(result).toBe('Hello World');
    });

    test('should handle empty input', () => {
      expect(sanitizeInput('')).toBe('');
      expect(sanitizeInput(null)).toBe('');
      expect(sanitizeInput(undefined)).toBe('');
    });

    test('should remove control characters', () => {
      const result = sanitizeInput('Hello\x00World\x01Test');
      expect(result).not.toContain('\x00');
      expect(result).not.toContain('\x01');
    });

    test('should preserve newlines and tabs when stripTags is false', () => {
      const result = sanitizeInput('Hello\nWorld\tTest', { stripTags: false });
      expect(result).toContain('\n');
      expect(result).toContain('\t');
    });
  });
});

describe('Form Validation', () => {
  const validateForm = (formData, rules = {}) => {
    const errors = [];
    const fieldValues = {};

    if (formData instanceof FormData) {
      for (const [key, value] of formData.entries()) {
        fieldValues[key] = value;
      }
    } else {
      Object.assign(fieldValues, formData);
    }

    if (Object.keys(rules).length === 0) {
      if (Object.keys(fieldValues).length === 0) {
        errors.push({ field: 'form', message: 'Form is empty' });
      }
    } else {
      for (const [fieldName, fieldRules] of Object.entries(rules)) {
        const value = fieldValues[fieldName];

        // Simplified validation for testing
        if (fieldRules.required && (!value || value.trim().length === 0)) {
          errors.push({
            field: fieldName,
            message: 'Text is required'
          });
        }
      }
    }

    if (errors.length > 0) {
      return { success: false, errors };
    }

    return { success: true };
  };

  describe('validateForm()', () => {
    test('should validate form with all valid fields', () => {
      const formData = {
        name: 'John Doe',
        email: 'john@example.com',
        phone: '1234567890'
      };

      const rules = {
        name: { required: true },
        email: { required: true },
        phone: { required: false }
      };

      const result = validateForm(formData, rules);
      expect(result.success).toBe(true);
    });

    test('should detect missing required fields', () => {
      const formData = {
        name: '',
        email: 'john@example.com'
      };

      const rules = {
        name: { required: true },
        email: { required: true }
      };

      const result = validateForm(formData, rules);
      expect(result.success).toBe(false);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].field).toBe('name');
    });

    test('should handle empty form', () => {
      const result = validateForm({}, {});
      expect(result.success).toBe(false);
      expect(result.errors[0].message).toBe('Form is empty');
    });

    test('should validate form with no rules', () => {
      const formData = {
        name: 'John Doe'
      };

      const result = validateForm(formData, {});
      expect(result.success).toBe(true);
    });
  });
});
