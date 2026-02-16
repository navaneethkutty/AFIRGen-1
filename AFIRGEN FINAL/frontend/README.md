# AFIRGen Frontend

AI-powered FIR (First Information Report) Management System - Frontend Application

## Overview

AFIRGen is a modern, accessible, and performant web application that streamlines the FIR filing process using artificial intelligence. The frontend is built with vanilla JavaScript, modern CSS, and follows web standards for accessibility (WCAG 2.1 AA) and performance.

## Features

- **AI-Powered FIR Generation**: Upload documents or audio files to automatically generate FIRs
- **FIR History Management**: Search, filter, and manage historical FIR records
- **Dark Mode**: System-aware theme with manual toggle
- **Offline Support**: Service Worker enables offline functionality
- **PDF Export**: Generate and download FIRs as PDF documents
- **Drag & Drop**: Intuitive file upload with drag-and-drop support
- **Real-time Validation**: Instant feedback on form inputs
- **Accessibility**: Full keyboard navigation and screen reader support
- **Progressive Web App**: Installable on desktop and mobile devices

## Technology Stack

### Core Technologies
- **HTML5**: Semantic markup with ARIA attributes
- **CSS3**: Modern styling with custom properties and animations
- **JavaScript (ES6+)**: Modular architecture with native modules

### Libraries & Tools
- **DOMPurify**: XSS protection and input sanitization
- **jsPDF**: PDF generation
- **Jest**: Unit testing framework
- **Fast-Check**: Property-based testing
- **Playwright**: End-to-end testing
- **ESLint**: Code quality and linting
- **Prettier**: Code formatting

### Build Tools
- **Terser**: JavaScript minification
- **cssnano**: CSS minification
- **html-minifier**: HTML minification

## Project Structure

```
frontend/
├── css/                    # Stylesheets
│   ├── main.css           # Main styles
│   ├── themes.css         # Dark mode theme
│   ├── glassmorphism.css  # Visual effects
│   └── ...                # Additional style modules
├── js/                     # JavaScript modules
│   ├── app.js             # Main application entry
│   ├── api.js             # API client with retry logic
│   ├── validation.js      # Input validation
│   ├── security.js        # Security utilities
│   ├── ui.js              # UI components
│   ├── storage.js         # LocalStorage & IndexedDB
│   └── ...                # Additional modules
├── lib/                    # Third-party libraries
│   ├── dompurify.min.js   # XSS protection
│   └── jspdf.min.js       # PDF generation
├── tests/                  # Test files
│   └── critical-flows.spec.js  # E2E tests
├── scripts/                # Utility scripts
│   ├── accessibility-audit.js  # Accessibility checker
│   └── performance-audit.js    # Performance analyzer
├── dist/                   # Production build output
├── index.html             # Main HTML file
├── sw.js                  # Service Worker
├── manifest.json          # PWA manifest
└── package.json           # Dependencies and scripts
```

## Setup Instructions

### Prerequisites
- Node.js 16+ and npm 8+
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd AFIRGEN\ FINAL/frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm start
```

The application will be available at `http://localhost:8080`

## Build Instructions

### Development Build
```bash
npm run build:dev
```

### Production Build
```bash
npm run build
```

This will:
- Minify JavaScript files with Terser
- Minify CSS files with cssnano
- Minify HTML files with html-minifier
- Generate source maps
- Output to `dist/` directory

### Build Verification
```bash
# Check bundle sizes
npm run audit:performance

# Check accessibility
npm run audit:accessibility
```

## Testing

### Unit Tests
```bash
# Run all unit tests
npm test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

### Property-Based Tests
Property-based tests are included in the unit test suite and use Fast-Check to verify universal properties across many inputs.

### End-to-End Tests
```bash
# Run E2E tests (headless)
npm run test:e2e

# Run with browser UI
npm run test:e2e:headed

# Debug mode
npm run test:e2e:debug

# View test report
npm run test:e2e:report
```

### Linting
```bash
# Run ESLint
npm run lint

# Auto-fix issues
npm run lint:fix

# Format code with Prettier
npm run format
```

## Deployment Instructions

### Docker Deployment

1. Build Docker image:
```bash
docker build -t afirgen-frontend .
```

2. Run container:
```bash
docker run -p 80:80 afirgen-frontend
```

### Manual Deployment

1. Build production bundle:
```bash
npm run build
```

2. Deploy `dist/` directory to web server (nginx, Apache, etc.)

3. Configure server:
   - Enable gzip compression
   - Set cache headers for static assets
   - Configure HTTPS
   - Set up Content Security Policy headers

### Environment Configuration

Create a `.env` file for environment-specific settings:
```
API_BASE_URL=https://api.afirgen.com
ENVIRONMENT=production
```

## Performance

### Metrics
- **Bundle Size**: <500KB gzipped
- **First Contentful Paint (FCP)**: <1s
- **Time to Interactive (TTI)**: <3s
- **Lighthouse Score**: >90

### Optimizations
- Code splitting and lazy loading
- Service Worker caching
- Resource hints (preconnect, dns-prefetch)
- Deferred script loading
- Image optimization
- CSS and JS minification

## Accessibility

### WCAG 2.1 AA Compliance
- Semantic HTML structure
- ARIA labels and roles
- Keyboard navigation support
- Focus management
- Screen reader announcements
- Color contrast ratios >4.5:1
- Skip links for navigation

### Testing Tools
- axe DevTools
- NVDA screen reader
- VoiceOver screen reader
- Keyboard-only navigation

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Security

### Implemented Measures
- Content Security Policy (CSP)
- XSS protection with DOMPurify
- Input validation and sanitization
- HTTPS enforcement
- Secure cookie handling
- File type validation with magic numbers

## Contributing

1. Follow the existing code style
2. Run linting before committing: `npm run lint`
3. Write tests for new features
4. Ensure all tests pass: `npm test`
5. Update documentation as needed

## Troubleshooting

### Common Issues

**Service Worker not updating:**
- Clear browser cache
- Unregister service worker in DevTools
- Hard refresh (Ctrl+Shift+R)

**Tests failing:**
- Clear Jest cache: `npm run test:clear`
- Reinstall dependencies: `rm -rf node_modules && npm install`

**Build errors:**
- Check Node.js version: `node --version`
- Update dependencies: `npm update`

## License

[Your License Here]

## Contact

For questions or support, contact [Your Contact Info]
