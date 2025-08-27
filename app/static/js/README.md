# EditorJS Service Documentation

## Overview

The `EditorJSService` is a centralized, reusable service for managing EditorJS instances across the Daylog application. It provides a clean, maintainable interface for initializing, configuring, and interacting with EditorJS editors.

## Features

- **Centralized Management**: Single service handles all EditorJS instances
- **Reusable Configuration**: Consistent editor setup across all pages
- **Codeblock Support**: Added codeblock tool for code formatting
- **Tab Key Trigger**: Press Tab instead of "/" to open formatting menu
- **Dynamic Toolbar Positioning**: Toolbar appears on right at line start, left at line end
- **Clean Styling**: Dedicated CSS file for maintainable styles
- **Error Handling**: Robust error handling and user feedback
- **Bootstrap Integration**: Seamless integration with Bootstrap components

## Usage

### Basic Initialization

```javascript
// Initialize EditorJS with default configuration
await window.editorJSService.initialize('editorjs', {
    initialData: { blocks: [] },
    minHeight: 400,
    placeholder: 'Start writing... Press Tab to see formatting options.',
    onChange: handleContentChange,
    onReady: () => {
        console.log('Editor ready');
    }
});
```

### Configuration Options

- `initialData`: Initial content for the editor (default: `{ blocks: [] }`)
- `minHeight`: Minimum height of the editor (default: 300)
- `placeholder`: Placeholder text (default: 'Start writing...')
- `onChange`: Callback function for content changes
- `onReady`: Callback function when editor is ready

### Available Methods

#### `initialize(holderId, options)`
Initializes a new EditorJS instance.

#### `getContent()`
Returns the current editor content as a promise.

#### `setContent(data)`
Sets the editor content from the provided data.

#### `isReady()`
Returns true if the editor is initialized and ready.

#### `destroy()`
Destroys the current editor instance.

## Available Tools

The service includes the following EditorJS tools:

- **Header**: H1-H6 headings
- **Paragraph**: Standard text paragraphs
- **List**: Ordered and unordered lists
- **Checklist**: Interactive checklists
- **Quote**: Blockquotes with captions
- **Delimiter**: Visual separators
- **Marker**: Text highlighting
- **Code**: Inline code and code blocks
- **Codeblock**: Dedicated code block tool
- **Table**: Data tables
- **Link**: Hyperlinks
- **Raw**: Raw HTML content
- **Warning**: Warning/callout blocks

## Codeblock Feature

The codeblock tool allows users to insert formatted code blocks:

1. Press **Tab** in the editor to open the formatting menu
2. Select "Code" or "Codeblock" from the options
3. Enter your code in the provided text area
4. The code will be displayed with proper formatting and syntax highlighting

## Dynamic Toolbar Positioning

The EditorJS toolbar now positions itself dynamically based on cursor location:

- **At line start**: Toolbar appears on the right side
- **At line end**: Toolbar appears on the left side
- **Auto-hide**: Toolbar disappears after 5 seconds of inactivity

This provides better usability and prevents the toolbar from obstructing content.

## Styling

All EditorJS styling is contained in `static/css/editorjs.css`, which includes:

- Container styles for the editor
- Block-specific styling for each tool
- Responsive design considerations
- Bootstrap integration

## Integration Examples

### Dashboard Page
```javascript
await window.editorJSService.initialize('editorjs', {
    initialData: window.entryContent,
    minHeight: 400,
    placeholder: 'Start writing your journal entry...',
    onChange: handleContentChange,
    onReady: () => {
        console.log('Dashboard editor ready');
    }
});
```

### Edit/Create Pages
```javascript
await window.editorJSService.initialize('editorjs', {
    initialData: window.entryContent || { blocks: [] },
    minHeight: 400,
    placeholder: 'Start writing your journal entry...',
    onChange: handleContentChange,
    onReady: () => {
        console.log('Editor ready');
    }
});
```

## Error Handling

The service includes comprehensive error handling:

- Initialization errors are caught and logged
- User-friendly error messages are displayed
- Graceful degradation when editor fails to load

## Best Practices

1. **Always await initialization**: Use `await` when calling `initialize()`
2. **Check readiness**: Use `isReady()` before performing operations
3. **Handle errors**: Implement proper error handling in your callbacks
4. **Clean up**: Call `destroy()` when removing editors
5. **Consistent configuration**: Use similar configurations across pages for consistency

## Migration from Old Implementation

If migrating from the old EditorJS implementation:

1. Replace direct EditorJS instantiation with service calls
2. Update CSS references to use the new `editorjs.css`
3. Remove redundant JavaScript code
4. Update event handlers to use service methods

## Troubleshooting

### Editor not loading
- Check that all EditorJS scripts are loaded
- Ensure the holder element exists in the DOM
- Verify that the service script is included

### Content not saving
- Check that `isReady()` returns true before saving
- Ensure proper error handling in save callbacks
- Verify that the content structure is valid

### Styling issues
- Confirm that `editorjs.css` is loaded
- Check for CSS conflicts with other stylesheets
- Ensure proper container structure

## Future Enhancements

- Custom tool development
- Theme support
- Advanced configuration options
- Plugin management system</content>
<parameter name="filePath">c:\projects\python\daylog\app\static\js\README.md
