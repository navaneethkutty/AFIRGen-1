# AFIRGen User Guide

Welcome to AFIRGen - the AI-powered FIR (First Information Report) Management System. This guide will help you get started and make the most of the application.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Generating a FIR](#generating-a-fir)
3. [Managing FIR History](#managing-fir-history)
4. [Exporting and Printing](#exporting-and-printing)
5. [Customization](#customization)
6. [Accessibility Features](#accessibility-features)
7. [Offline Mode](#offline-mode)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### System Requirements

- Modern web browser (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- Internet connection (for initial load and API calls)
- JavaScript enabled

### First Time Setup

1. **Open the Application**: Navigate to the AFIRGen URL in your web browser
2. **Allow Notifications** (optional): Click "Allow" when prompted to receive notifications
3. **Install as App** (optional): Click the install button in your browser's address bar to install AFIRGen as a Progressive Web App

### Interface Overview

The AFIRGen interface consists of three main areas:

- **Navigation Bar** (top): Switch between Home, About, and Resources pages
- **Sidebar** (left): View and search FIR history
- **Main Content** (center): Upload files and generate FIRs

---

## Generating a FIR

### Step 1: Upload Documents

You can upload documents in two ways:

#### Method 1: Click to Upload
1. Click on the "Upload Letter" button
2. Select a document file from your computer
   - Supported formats: PDF, DOC, DOCX, TXT, JPG, PNG
   - Maximum file size: 10MB

#### Method 2: Drag and Drop
1. Drag a document file from your computer
2. Drop it onto the "Upload Letter" area
3. The file will be validated automatically

**Tip**: The upload area will highlight when you drag a file over it.

### Step 2: Upload Audio (Optional)

If you have audio recordings of witness statements:

1. Click "Upload Audio" or drag and drop an audio file
   - Supported formats: MP3, WAV, M4A, OGG
   - Maximum file size: 10MB

### Step 3: Generate FIR

1. Once files are uploaded, the "Generate" button will become active
2. Click the arrow button to start FIR generation
3. Wait while the AI processes your files (typically 10-30 seconds)
4. A progress indicator will show the processing status

### Step 4: Review and Save

1. The generated FIR will appear in a modal window
2. Review the content carefully
3. Click "Copy" to copy the FIR text to clipboard
4. Click "Export PDF" to download as PDF
5. Click "Save to Records" to add to your FIR history

---

## Managing FIR History

### Viewing FIR History

The sidebar displays all your previously generated FIRs:

- **FIR Number**: Unique identifier for each FIR
- **Date**: When the FIR was generated
- **Status**: Current status (Pending, Investigating, Closed)
- **Complainant**: Name of the complainant

### Searching FIRs

1. Click the search box at the top of the sidebar
2. Type to search by:
   - FIR number
   - Complainant name
   - Date
3. Results update in real-time as you type

### Filtering FIRs

Use the status dropdown to filter FIRs:

- **All Status**: Show all FIRs
- **Pending**: Show only pending FIRs
- **Investigating**: Show FIRs under investigation
- **Closed**: Show closed FIRs

### Sorting FIRs

Use the sort dropdown to organize FIRs:

- **Newest First**: Most recent FIRs at the top
- **Oldest First**: Oldest FIRs at the top
- **By Status**: Group by status

### Viewing FIR Details

1. Click on any FIR in the sidebar
2. The full FIR content will open in a modal
3. From here you can:
   - Copy the content
   - Export as PDF
   - Print the FIR

---

## Exporting and Printing

### Export as PDF

1. Open a FIR (from history or after generation)
2. Click "Export PDF" button
3. The PDF will download automatically
4. PDF includes:
   - FIR number and date
   - All FIR content
   - Professional formatting
   - Page numbers

### Print FIR

1. Open a FIR
2. Click "Print" button (if available)
3. Your browser's print dialog will open
4. Select printer and options
5. Click "Print"

**Tip**: The print layout is optimized for A4 paper with proper margins and formatting.

---

## Customization

### Dark Mode

Toggle between light and dark themes:

1. Look for the theme toggle button in the navigation bar
2. Click to switch between light and dark mode
3. Your preference is saved automatically
4. The app respects your system's dark mode setting by default

**Benefits of Dark Mode:**
- Reduced eye strain in low-light conditions
- Better battery life on OLED screens
- Modern, sleek appearance

### Accessibility Settings

AFIRGen includes several accessibility features:

- **High Contrast**: Automatically adjusts for high contrast mode
- **Reduced Motion**: Respects your system's motion preferences
- **Font Size**: Scales with your browser's font size settings

---

## Accessibility Features

AFIRGen is designed to be accessible to all users.

### Keyboard Navigation

Navigate the entire application using only your keyboard:

- **Tab**: Move to next interactive element
- **Shift + Tab**: Move to previous element
- **Enter/Space**: Activate buttons and links
- **Escape**: Close modals and dialogs
- **Arrow Keys**: Navigate within lists and menus

### Screen Reader Support

AFIRGen works with popular screen readers:

- **NVDA** (Windows)
- **JAWS** (Windows)
- **VoiceOver** (macOS/iOS)
- **TalkBack** (Android)

**Features:**
- Descriptive labels for all controls
- Status announcements for actions
- Proper heading structure
- ARIA landmarks for navigation

### Skip Links

Press Tab when the page loads to reveal a "Skip to main content" link that jumps past navigation.

### Focus Indicators

All interactive elements show a clear focus indicator when navigated with keyboard.

---

## Offline Mode

AFIRGen works offline after your first visit.

### How It Works

1. **First Visit**: The app downloads and caches essential files
2. **Subsequent Visits**: The app loads from cache
3. **Offline**: You can view cached FIRs and use basic features
4. **Online**: New FIRs sync automatically when connection returns

### What Works Offline

- View previously loaded FIRs
- Search and filter cached FIRs
- Access the interface
- View documentation

### What Requires Internet

- Generating new FIRs (requires AI processing)
- Syncing FIR history
- Uploading files
- Downloading PDFs

### Checking Connection Status

The app will show a notification when:
- You go offline
- Connection is restored
- Operations are queued for sync

---

## Troubleshooting

### File Upload Issues

**Problem**: File won't upload

**Solutions:**
- Check file size (must be under 10MB)
- Verify file format is supported
- Try a different file
- Clear browser cache and reload

**Problem**: "File type not allowed" error

**Solutions:**
- Ensure file has correct extension (.pdf, .jpg, etc.)
- File may be corrupted - try opening it first
- Convert file to a supported format

### FIR Generation Issues

**Problem**: FIR generation takes too long

**Solutions:**
- Check your internet connection
- Large files take longer to process
- Try refreshing the page and uploading again
- Contact support if issue persists

**Problem**: Generated FIR is incomplete

**Solutions:**
- Ensure uploaded document is clear and readable
- Try uploading a higher quality scan
- Add more context in the document
- Use audio upload to supplement information

### Display Issues

**Problem**: Layout looks broken

**Solutions:**
- Clear browser cache (Ctrl+Shift+Delete)
- Update your browser to the latest version
- Try a different browser
- Disable browser extensions temporarily

**Problem**: Dark mode not working

**Solutions:**
- Click the theme toggle button
- Check browser's dark mode settings
- Clear LocalStorage and reload

### Performance Issues

**Problem**: App is slow or unresponsive

**Solutions:**
- Close unnecessary browser tabs
- Clear browser cache
- Disable browser extensions
- Check system resources (CPU, memory)
- Try a different browser

### PDF Export Issues

**Problem**: PDF won't download

**Solutions:**
- Check browser's download settings
- Allow pop-ups for this site
- Try right-click and "Save as"
- Check available disk space

**Problem**: PDF formatting is incorrect

**Solutions:**
- Try exporting again
- Use print function as alternative
- Report issue with screenshot

---

## Tips and Best Practices

### For Best Results

1. **Upload Clear Documents**: Use high-quality scans or photos
2. **Provide Complete Information**: Include all relevant details in documents
3. **Use Audio Supplements**: Add audio recordings for additional context
4. **Review Before Saving**: Always review generated FIRs for accuracy
5. **Save Regularly**: Save important FIRs to history immediately

### Security Tips

1. **Use Secure Connection**: Always access via HTTPS
2. **Don't Share Credentials**: Keep your login information private
3. **Log Out on Shared Devices**: Always log out when using public computers
4. **Regular Backups**: Export important FIRs as PDFs for backup
5. **Update Browser**: Keep your browser updated for security patches

### Efficiency Tips

1. **Use Keyboard Shortcuts**: Navigate faster with keyboard
2. **Organize with Filters**: Use status filters to organize FIRs
3. **Search Effectively**: Use specific terms for faster search
4. **Batch Processing**: Upload multiple files at once when possible
5. **Install as App**: Install as PWA for faster access

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Tab | Navigate forward |
| Shift + Tab | Navigate backward |
| Enter | Activate button/link |
| Space | Activate button/checkbox |
| Escape | Close modal/dialog |
| Ctrl/Cmd + F | Focus search box |
| Ctrl/Cmd + S | Save current FIR |
| Ctrl/Cmd + P | Print current FIR |

---

## Getting Help

### In-App Help

- Hover over elements for tooltips
- Look for info icons (ℹ️) for contextual help
- Check status messages for guidance

### Documentation

- **README.md**: Setup and installation
- **API.md**: Developer documentation
- **This Guide**: User instructions

### Support

If you encounter issues not covered in this guide:

1. Check the troubleshooting section
2. Review the FAQ (if available)
3. Contact your system administrator
4. Report bugs through the proper channels

---

## Frequently Asked Questions

**Q: Is my data secure?**
A: Yes, all data is encrypted in transit and at rest. We follow industry best practices for security.

**Q: Can I use AFIRGen on mobile?**
A: Yes, AFIRGen is fully responsive and works on mobile devices. Install it as a PWA for the best experience.

**Q: How long are FIRs stored?**
A: FIRs are stored indefinitely in your browser's local storage and on the server (if logged in).

**Q: Can I edit a generated FIR?**
A: Currently, you can copy the FIR text and edit it externally. In-app editing may be added in future updates.

**Q: What languages are supported?**
A: Currently, AFIRGen supports English. Additional languages may be added in future versions.

**Q: Can I delete FIRs?**
A: Yes, you can delete FIRs from your history. This action cannot be undone.

**Q: Does AFIRGen work offline?**
A: Yes, after your first visit, you can view cached FIRs offline. Generating new FIRs requires an internet connection.

---

## Updates and New Features

AFIRGen is regularly updated with new features and improvements. Check the About page or release notes for the latest updates.

### Recent Updates

- Enhanced dark mode with better contrast
- Improved PDF export formatting
- Faster FIR generation
- Better accessibility support
- Offline mode improvements

### Upcoming Features

- Multi-language support
- In-app FIR editing
- Advanced search filters
- Batch FIR generation
- Mobile app versions

---

## Feedback

We value your feedback! If you have suggestions for improvements or encounter any issues, please let us know through the appropriate channels.

Thank you for using AFIRGen!
