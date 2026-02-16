# AFIRGen Frontend API Documentation

Complete reference for all JavaScript modules and their public APIs.

## Table of Contents

- [API Client](#api-client)
- [Validation](#validation)
- [Security](#security)
- [UI Components](#ui-components)
- [Storage](#storage)
- [FIR History](#fir-history)
- [PDF Export](#pdf-export)
- [Theme Management](#theme-management)

---

## API Client

**Module**: `js/api.js`

Centralized API communication with automatic retry logic, caching, and error handling.

### APIClient Class

#### Constructor

```javascript
new APIClient(baseURL, apiKey)
```

**Parameters:**
- `baseURL` (string): Base URL for API endpoints (default: from config)
- `apiKey` (string): API authentication key (default: from config)

**Example:**
```javascript
const client = new APIClient('https://api.afirgen.com', 'your-api-key');
```

#### Methods

##### request(endpoint, options)

Make a generic HTTP request with timeout support.

**Parameters:**
- `endpoint` (string): API endpoint path
- `options` (Object): Fetch options
  - `method` (string): HTTP method
  - `headers` (Object): Request headers
  - `body` (any): Request body
  - `timeout` (number): Request timeout in ms (default: 30000)

**Returns:** `Promise<Response>`

**Example:**
```javascript
const response = await client.request('/fir/generate', {
  method: 'POST',
  body: formData
});
```

##### get(endpoint, params, options)

Make a GET request with optional caching.

**Parameters:**
- `endpoint` (string): API endpoint path
- `params` (Object): Query parameters
- `options` (Object): Additional options
  - `useCache` (boolean): Enable caching (default: true)
  - `cacheTTL` (number): Cache time-to-live in ms (default: 300000)

**Returns:** `Promise<any>` - Parsed JSON response

**Example:**
```javascript
const firList = await client.get('/fir/list', { 
  status: 'pending',
  limit: 10 
});
```

##### post(endpoint, body, isFormData, options)

Make a POST request.

**Parameters:**
- `endpoint` (string): API endpoint path
- `body` (any): Request body (Object or FormData)
- `isFormData` (boolean): Whether body is FormData (default: false)
- `options` (Object): Additional options

**Returns:** `Promise<any>` - Parsed JSON response

**Example:**
```javascript
const result = await client.post('/fir/generate', {
  complainant: 'John Doe',
  incident: 'Theft'
});
```

##### retryRequest(fn, maxRetries, backoff)

Retry a request with exponential backoff.

**Parameters:**
- `fn` (Function): Async function to retry
- `maxRetries` (number): Maximum retry attempts (default: 3)
- `backoff` (number): Initial backoff delay in ms (default: 1000)

**Returns:** `Promise<any>` - Function result

##### getCached(key)

Get cached response.

**Parameters:**
- `key` (string): Cache key

**Returns:** `any | null` - Cached data or null

##### setCached(key, data, ttl)

Set cached response.

**Parameters:**
- `key` (string): Cache key
- `data` (any): Data to cache
- `ttl` (number): Time-to-live in ms (default: 300000)

##### clearCache()

Clear all cached responses.

---

## Validation

**Module**: `js/validation.js`

File and input validation with security checks.

### Functions

#### validateFile(file, options)

Comprehensive file validation.

**Parameters:**
- `file` (File): File to validate
- `options` (Object):
  - `maxSize` (number): Maximum file size in bytes (default: 10485760 = 10MB)
  - `allowedTypes` (Array): Allowed file extensions (default: ['.jpg', '.jpeg', '.png', '.pdf', '.wav', '.mp3'])
  - `checkMagicNumber` (boolean): Verify MIME type with magic numbers (default: true)

**Returns:** `Promise<Object>` - Validation result
```javascript
{
  success: boolean,
  error?: string,
  warnings?: string[]
}
```

**Example:**
```javascript
const result = await validateFile(file, {
  maxSize: 5 * 1024 * 1024, // 5MB
  allowedTypes: ['.pdf', '.jpg']
});

if (!result.success) {
  showToast(result.error, 'error');
}
```

#### validateFileType(file, allowedTypes)

Validate file extension.

**Parameters:**
- `file` (File): File to validate
- `allowedTypes` (Array): Allowed extensions

**Returns:** `Object` - Validation result

#### validateFileSize(file, maxSize)

Validate file size.

**Parameters:**
- `file` (File): File to validate
- `maxSize` (number): Maximum size in bytes

**Returns:** `Object` - Validation result

#### validateMimeType(file)

Validate MIME type using magic number check.

**Parameters:**
- `file` (File): File to validate

**Returns:** `Promise<Object>` - Validation result with detected MIME type

#### validateText(text, options)

Validate text input.

**Parameters:**
- `text` (string): Text to validate
- `options` (Object):
  - `minLength` (number): Minimum length
  - `maxLength` (number): Maximum length
  - `required` (boolean): Whether field is required
  - `pattern` (RegExp): Validation pattern

**Returns:** `Object` - Validation result

**Example:**
```javascript
const result = validateText(input.value, {
  minLength: 10,
  maxLength: 500,
  required: true
});
```

#### sanitizeInput(input)

Sanitize user input.

**Parameters:**
- `input` (string): Input to sanitize

**Returns:** `string` - Sanitized input

#### validateForm(formData)

Validate entire form.

**Parameters:**
- `formData` (Object): Form data to validate

**Returns:** `Object` - Validation result with field-specific errors

---

## Security

**Module**: `js/security.js`

XSS protection and input sanitization using DOMPurify.

### Functions

#### sanitizeHTML(html, options)

Sanitize HTML content to prevent XSS attacks.

**Parameters:**
- `html` (string): HTML to sanitize
- `options` (Object): DOMPurify options

**Returns:** `string` - Sanitized HTML

**Example:**
```javascript
const safeHTML = sanitizeHTML(userInput);
element.innerHTML = safeHTML;
```

#### sanitizeText(text)

Sanitize plain text by removing HTML tags.

**Parameters:**
- `text` (string): Text to sanitize

**Returns:** `string` - Plain text

#### escapeHTML(str)

Escape HTML entities.

**Parameters:**
- `str` (string): String to escape

**Returns:** `string` - Escaped string

**Example:**
```javascript
const escaped = escapeHTML('<script>alert("XSS")</script>');
// Returns: &lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;
```

---

## UI Components

**Module**: `js/ui.js`

UI components and interactions.

### Toast Notifications

#### showToast(message, type, duration)

Display a toast notification.

**Parameters:**
- `message` (string): Message to display
- `type` (string): Toast type - 'success', 'error', 'warning', 'info'
- `duration` (number): Duration in ms (0 = no auto-hide, default: 5000)

**Returns:** `string` - Toast ID

**Example:**
```javascript
showToast('FIR generated successfully!', 'success', 3000);
showToast('File upload failed', 'error');
```

#### hideToast(toastId)

Hide a specific toast.

**Parameters:**
- `toastId` (string): Toast ID returned by showToast()

### Loading States

#### showLoading(element, message)

Show loading indicator on element.

**Parameters:**
- `element` (HTMLElement): Element to show loading on
- `message` (string): Loading message (optional)

**Example:**
```javascript
showLoading(document.getElementById('generate-btn'), 'Generating FIR...');
```

#### hideLoading(element)

Hide loading indicator.

**Parameters:**
- `element` (HTMLElement): Element to hide loading from

#### showProgress(element, percentage)

Show progress bar.

**Parameters:**
- `element` (HTMLElement): Element to show progress on
- `percentage` (number): Progress percentage (0-100)

**Example:**
```javascript
showProgress(uploadContainer, 75);
```

### Modal

#### showModal(title, content, options)

Display a modal dialog.

**Parameters:**
- `title` (string): Modal title
- `content` (string | HTMLElement): Modal content
- `options` (Object):
  - `type` (string): Modal type - 'success', 'error', 'info'
  - `actions` (Array): Action buttons
  - `closable` (boolean): Whether modal can be closed (default: true)

**Example:**
```javascript
showModal('FIR Generated', firContent, {
  type: 'success',
  actions: [
    { label: 'Export PDF', onClick: exportPDF },
    { label: 'Close', onClick: closeModal }
  ]
});
```

#### hideModal()

Hide the current modal.

---

## Storage

**Module**: `js/storage.js`

LocalStorage and IndexedDB operations.

### LocalStorage

#### setLocal(key, value, ttl)

Store data in LocalStorage with optional TTL.

**Parameters:**
- `key` (string): Storage key
- `value` (any): Value to store (will be JSON stringified)
- `ttl` (number): Time-to-live in ms (optional)

**Example:**
```javascript
setLocal('user-preferences', { theme: 'dark' }, 86400000); // 24 hours
```

#### getLocal(key)

Retrieve data from LocalStorage.

**Parameters:**
- `key` (string): Storage key

**Returns:** `any | null` - Stored value or null if expired/not found

#### removeLocal(key)

Remove data from LocalStorage.

**Parameters:**
- `key` (string): Storage key

### IndexedDB

#### setDB(store, key, value)

Store data in IndexedDB.

**Parameters:**
- `store` (string): Object store name
- `key` (string): Record key
- `value` (any): Value to store

**Returns:** `Promise<void>`

**Example:**
```javascript
await setDB('fir-history', 'FIR-2024-001', firData);
```

#### getDB(store, key)

Retrieve data from IndexedDB.

**Parameters:**
- `store` (string): Object store name
- `key` (string): Record key

**Returns:** `Promise<any>` - Stored value

#### getAllDB(store)

Get all records from an object store.

**Parameters:**
- `store` (string): Object store name

**Returns:** `Promise<Array>` - All records

**Example:**
```javascript
const allFIRs = await getAllDB('fir-history');
```

#### deleteDB(store, key)

Delete a record from IndexedDB.

**Parameters:**
- `store` (string): Object store name
- `key` (string): Record key

**Returns:** `Promise<void>`

---

## FIR History

**Module**: `js/fir-history.js`

FIR history management with search and filtering.

### Functions

#### loadFIRHistory()

Load and display FIR history.

**Returns:** `Promise<void>`

#### searchFIRHistory(query)

Search FIR history.

**Parameters:**
- `query` (string): Search query

**Returns:** `Array` - Filtered FIR records

#### filterFIRHistory(status)

Filter FIR history by status.

**Parameters:**
- `status` (string): Status filter - 'all', 'pending', 'investigating', 'closed'

**Returns:** `Array` - Filtered FIR records

#### sortFIRHistory(sortBy)

Sort FIR history.

**Parameters:**
- `sortBy` (string): Sort criteria - 'date-desc', 'date-asc', 'status'

**Returns:** `Array` - Sorted FIR records

---

## PDF Export

**Module**: `js/pdf.js`

PDF generation and export using jsPDF.

### Functions

#### generatePDF(firData, options)

Generate PDF from FIR data.

**Parameters:**
- `firData` (Object): FIR data to include in PDF
- `options` (Object):
  - `format` (string): Page format (default: 'a4')
  - `orientation` (string): Page orientation (default: 'portrait')
  - `includeHeader` (boolean): Include header (default: true)
  - `includeFooter` (boolean): Include footer (default: true)

**Returns:** `jsPDF` - PDF document object

**Example:**
```javascript
const pdf = generatePDF(firData, {
  format: 'a4',
  orientation: 'portrait'
});
```

#### downloadPDF(pdf, filename)

Download PDF to user's device.

**Parameters:**
- `pdf` (jsPDF): PDF document
- `filename` (string): Download filename

**Example:**
```javascript
downloadPDF(pdf, 'FIR-2024-001.pdf');
```

#### printPDF(pdf)

Open print dialog for PDF.

**Parameters:**
- `pdf` (jsPDF): PDF document

---

## Theme Management

**Module**: `js/theme.js`

Dark mode and theme management.

### Functions

#### toggleDarkMode()

Toggle between light and dark mode.

**Example:**
```javascript
document.getElementById('theme-toggle').addEventListener('click', toggleDarkMode);
```

#### setTheme(theme)

Set specific theme.

**Parameters:**
- `theme` (string): Theme name - 'light' or 'dark'

**Example:**
```javascript
setTheme('dark');
```

#### getTheme()

Get current theme.

**Returns:** `string` - Current theme name

#### initTheme()

Initialize theme from user preference or system setting.

---

## Error Handling

All API functions follow a consistent error handling pattern:

```javascript
try {
  const result = await apiFunction();
  // Handle success
} catch (error) {
  if (error.name === 'TimeoutError') {
    showToast('Request timed out. Please try again.', 'error');
  } else if (error.name === 'NetworkError') {
    showToast('Network error. Check your connection.', 'error');
  } else {
    showToast(error.message, 'error');
  }
}
```

## Events

Custom events dispatched by the application:

- `fir:generated` - Fired when FIR is successfully generated
- `fir:saved` - Fired when FIR is saved to history
- `theme:changed` - Fired when theme is changed
- `file:uploaded` - Fired when file is uploaded
- `cache:cleared` - Fired when cache is cleared

**Example:**
```javascript
document.addEventListener('fir:generated', (event) => {
  console.log('FIR generated:', event.detail);
});
```

## Best Practices

1. **Always validate user input** before sending to API
2. **Use sanitizeHTML()** when displaying user-generated content
3. **Handle errors gracefully** with user-friendly messages
4. **Show loading states** for async operations
5. **Cache API responses** when appropriate
6. **Use toast notifications** instead of alert()
7. **Implement proper focus management** for accessibility
8. **Test with screen readers** and keyboard navigation

## TypeScript Definitions

For TypeScript projects, type definitions are available in `types/index.d.ts`.

## Support

For questions or issues with the API, please refer to the main README or contact the development team.
