# CodeMirror Integration for Daylog

This document describes the CodeMirror integration implemented for the Daylog project's code blocks in EditorJS.

## Overview

The CodeMirror integration provides a powerful code editing experience within EditorJS with features like:

- Syntax highlighting for multiple programming languages
- Line numbers
- Bracket matching and auto-closing
- Code commenting/uncommenting (Ctrl+/ or Cmd+/)
- Language selection dropdown
- Responsive design
- Read-only mode support

## Supported Languages

The implementation supports the following programming languages:

- JavaScript
- Python
- HTML
- CSS
- JSON
- SQL
- Bash
- PHP
- Java
- C++
- C#
- Ruby
- Go
- Rust
- TypeScript
- Markdown
- XML
- YAML
- Plain Text

## Files Structure

### JavaScript Files

- `app/static/js/codeblock.js` - Main CodeBlock class implementation
- `app/static/js/dashboard-editor.js` - EditorJS integration

### CSS Files

- `app/static/css/editorjs-blocks.css` - Styling for code blocks

### Template Files

- `app/templates/journal/dashboard.html` - Main dashboard with CodeMirror includes

### Test Files

- `app/static/test-codeblock.html` - Standalone test page for CodeMirror functionality

## Features

### 1. Language Selection

Each code block includes a dropdown to select the programming language, which automatically updates the syntax highlighting.

### 2. Syntax Highlighting

GitHub-style syntax highlighting with appropriate colors for:

- Keywords
- Strings
- Comments
- Numbers
- Operators
- Variables
- Functions

### 3. Editor Features

- Line numbers with proper alignment
- Bracket matching with visual indicators
- Auto-closing brackets and quotes
- Active line highlighting
- Tabulation support (4 spaces)
- Code commenting/uncommenting shortcuts

### 4. Keyboard Shortcuts

- `Tab` - Indent selection or insert 4 spaces
- `Shift+Tab` - Unindent selection
- `Ctrl+/` or `Cmd+/` - Toggle line comment

### 5. Responsive Design

The code blocks are fully responsive and work well on mobile devices with adjusted font sizes and spacing.

## Usage

### Basic Usage in EditorJS

The CodeBlock is automatically available in EditorJS when properly configured:

```javascript
const editor = new EditorJS({
    tools: {
        code: {
            class: CodeBlock,
            config: {
                placeholder: 'Enter your code here...'
            },
            shortcut: 'CMD+SHIFT+C',
        }
    }
});
```

### Data Format

The CodeBlock saves data in the following format:

```json
{
    "code": "console.log('Hello, World!');",
    "language": "javascript"
}
```

### Programmatic Usage

```javascript
// Create a new code block
const codeBlock = new CodeBlock({
    data: {
        code: 'print("Hello, World!")',
        language: 'python'
    },
    config: {},
    api: {},
    readOnly: false
});

// Render the block
const element = codeBlock.render();
document.body.appendChild(element);

// Get saved data
const savedData = codeBlock.save();
```

## Testing

To test the CodeMirror implementation:

1. Open `app/static/test-codeblock.html` in a web browser
2. Try editing the code in different language modes
3. Test the language selector functionality
4. Verify keyboard shortcuts work correctly
5. Check responsive behavior on different screen sizes

## Customization

### Adding New Languages

To add support for a new programming language:

1. Add the language mode script to the dashboard template
2. Update the `languages` object in `codeblock.js`:

```javascript
this.languages = {
    // existing languages...
    'newlang': { mode: 'text/x-newlang', label: 'New Language' }
};
```

Optionally add comment syntax to the `toggleComment` method

### Styling Customization

Modify `app/static/css/editorjs-blocks.css` to customize:

- Color scheme
- Font family and sizes
- Border and spacing
- Responsive breakpoints

### Theme Support

The implementation uses a default theme but can be extended to support multiple themes by:

1. Adding theme selection to the header
2. Including additional CodeMirror theme CSS files
3. Updating the `initializeCodeMirror` method to set the theme option

## Dependencies

### Required CDN Resources

The implementation requires the following CDN resources to be loaded:

1. **CodeMirror Core**

   ```html
   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/6.65.7/codemirror.min.css" />
   <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/6.65.7/codemirror.min.js"></script>
   ```

2. **Language Modes** (as needed)

   ```html
   <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/6.65.7/mode/javascript/javascript.min.js"></script>
   <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/6.65.7/mode/python/python.min.js"></script>
   <!-- Additional language modes... -->
   ```

3. **Addons**

   ```html
   <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/6.65.7/addon/edit/matchbrackets.min.js"></script>
   <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/6.65.7/addon/edit/closebrackets.min.js"></script>
   <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/6.65.7/addon/selection/active-line.min.js"></script>
   ```

## Performance Considerations

- Language mode scripts are loaded on page load to ensure smooth operation
- CodeMirror instances are created lazily when code blocks are rendered
- Auto-refresh is implemented with a small delay to prevent layout issues
- The implementation uses efficient event handling to minimize performance impact

## Browser Support

The CodeMirror implementation supports all modern browsers:

- Chrome 60+
- Firefox 60+
- Safari 12+
- Edge 79+

## Troubleshooting

### Common Issues

1. **Syntax highlighting not working**
   - Ensure the appropriate language mode script is loaded
   - Check browser console for JavaScript errors
   - Verify the language is properly configured

2. **Editor not rendering**
   - Check that CodeMirror core script is loaded
   - Ensure the container element exists
   - Look for CSS conflicts

3. **Styling issues**
   - Verify `editorjs-blocks.css` is loaded
   - Check for CSS specificity conflicts
   - Test with browser developer tools

### Debug Mode

To enable debug logging, add this to your browser console:

```javascript
window.CODEBLOCK_DEBUG = true;
```

This will log additional information about CodeMirror initialization and language mode changes.
