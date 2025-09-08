/**
 * Dashboard Editor - EditorJS Integration for Journal Entries
 * Handles initialization and management of EditorJS instances for journal entries
 */

// Store entry data and editor instances
let editorInstances = {};
let currentActiveEntry = null;

/**
 * Initialize the dashboard editor system
 * @param {Object} entryData - Object containing entry data keyed by entry ID
 * @param {string} activeEntryId - ID of the currently active entry
 */
function initializeDashboardEditor(entryData, activeEntryId) {
    window.entryData = entryData;
    currentActiveEntry = activeEntryId;
    
    // Initialize editor for the currently active entry
    if (currentActiveEntry) {
        initializeEditor(currentActiveEntry);
    }

    // Add click handlers for journal links
    document.querySelectorAll('.journal-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const entryId = this.getAttribute('data-id');
            
            // Update active state
            document.querySelectorAll('.journal-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            switchToEntry(entryId);
        });
    });
}

/**
 * Initialize EditorJS for a specific entry
 * @param {string} entryId - The ID of the entry to initialize
 */
async function initializeEditor(entryId) {
    const editorElement = document.getElementById(`editorjs-${entryId}`);
    if (!editorElement || editorInstances[entryId]) {
        return;
    }

    try {
        // Wait for EditorJS to be available
        await waitForEditorJS();

        const editor = new EditorJS({
            holder: `editorjs-${entryId}`,
            data: window.entryData[entryId] || {},
            tools: getEditorTools(),
            placeholder: 'Start writing your journal entry...',
            minHeight: 500,
            autofocus: true,
            defaultBlock: 'paragraph',
            sanitizer: {
                p: true,
                b: true,
                i: true,
                u: true,
                strong: true,
                em: true,
                mark: true,
                a: {
                    href: true,
                    target: '_blank',
                }
            },
            onChange: (api, event) => {
                // Auto-save functionality can be added here
                console.log('Content changed for entry', entryId);
            },
            onReady: () => {
                console.log(`Editor ready for entry ${entryId}`);
                // Remove any loading states
                const container = document.getElementById(`editorjs-${entryId}`);
                if (container) {
                    container.classList.remove('editor-loading');
                }
            }
        });

        editorInstances[entryId] = editor;
    } catch (error) {
        console.error(`Failed to initialize editor for entry ${entryId}:`, error);
    }
}

/**
 * Get the configuration for EditorJS tools
 * @returns {Object} Tools configuration object
 */
function getEditorTools() {
    return {
        header: {
            class: Header,
            config: {
                placeholder: 'Enter a header',
                levels: [1, 2, 3, 4, 5, 6],
                defaultLevel: 3
            }
        },
        list: {
            class: List,
            inlineToolbar: true,
            config: {
                defaultStyle: 'unordered'
            }
        },
        checklist: {
            class: Checklist,
            inlineToolbar: true
        },
        quote: {
            class: Quote,
            inlineToolbar: true,
            shortcut: 'CMD+SHIFT+O',
            config: {
                quotePlaceholder: 'Enter a quote',
                captionPlaceholder: 'Quote author'
            }
        },
        delimiter: Delimiter,
        table: {
            class: Table,
            inlineToolbar: true,
            config: {
                rows: 2,
                cols: 3
            },
            shortcut: 'CMD+ALT+T',
        },
        linkTool: {
            class: LinkTool,
            config: {
                endpoint: '/api/fetch-url'
            }
        },
        raw: {
            class: RawTool,
            config: {
                placeholder: 'Enter raw HTML'
            }
        },
        code: {
            class: CodeBlock,
            config: {
                placeholder: 'Enter your code here...'
            },
            shortcut: 'CMD+SHIFT+C',
        },
        warning: {
            class: Warning,
            inlineToolbar: true,
            shortcut: 'CMD+SHIFT+W',
            config: {
                titlePlaceholder: 'Title',
                messagePlaceholder: 'Message'
            }
        },
        marker: {
            class: Marker,
            shortcut: 'CMD+SHIFT+M'
        },
        underline: Underline
    };
}

/**
 * Wait for EditorJS and plugins to load
 * @returns {Promise} Promise that resolves when EditorJS is ready
 */
async function waitForEditorJS() {
    const maxAttempts = 50;
    let attempts = 0;

    while (attempts < maxAttempts) {
        if (typeof EditorJS !== 'undefined' && 
            typeof Header !== 'undefined' && 
            typeof List !== 'undefined' &&
            typeof CodeBlock !== 'undefined') {
            return;
        }
        attempts++;
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error('EditorJS failed to load');
}

/**
 * Switch between entries
 * @param {string} entryId - The ID of the entry to switch to
 */
function switchToEntry(entryId) {
    // Ensure entryId is a string
    entryId = String(entryId);
    
    // Hide all entries
    document.querySelectorAll('.journal-entry').forEach(entry => {
        entry.classList.add('d-none');
    });

    // Show selected entry
    const entryElement = document.getElementById(`journal-${entryId}`);
    if (entryElement) {
        entryElement.classList.remove('d-none');
        
        // Update title in header
        const titleElement = document.getElementById('currentEntryTitle');
        const entryLink = document.querySelector(`[data-id="${entryId}"]`);
        if (titleElement && entryLink) {
            titleElement.textContent = entryLink.textContent;
        }

        // Initialize editor if not already done
        if (!editorInstances[entryId]) {
            initializeEditor(entryId);
        }

        currentActiveEntry = entryId;
    }
}

/**
 * Get the current editor instance
 * @param {string} entryId - The ID of the entry (optional, uses current active if not provided)
 * @returns {Object|null} The EditorJS instance or null if not found
 */
function getCurrentEditor(entryId = null) {
    const targetEntryId = entryId || currentActiveEntry;
    return editorInstances[targetEntryId] || null;
}

/**
 * Save the current editor content
 * @param {string} entryId - The ID of the entry to save (optional, uses current active if not provided)
 * @returns {Promise} Promise that resolves with the saved data
 */
async function saveEditorContent(entryId = null) {
    const editor = getCurrentEditor(entryId);
    if (editor) {
        try {
            const outputData = await editor.save();
            console.log('Article data: ', outputData);
            return outputData;
        } catch (error) {
            console.log('Saving failed: ', error);
            throw error;
        }
    }
    throw new Error('No editor instance found');
}

/**
 * Destroy an editor instance
 * @param {string} entryId - The ID of the entry whose editor should be destroyed
 */
function destroyEditor(entryId) {
    if (editorInstances[entryId]) {
        editorInstances[entryId].destroy();
        delete editorInstances[entryId];
    }
}

/**
 * Destroy all editor instances
 */
function destroyAllEditors() {
    Object.keys(editorInstances).forEach(entryId => {
        destroyEditor(entryId);
    });
}

// Export functions for global access if needed
window.DashboardEditor = {
    initialize: initializeDashboardEditor,
    initializeEditor,
    switchToEntry,
    getCurrentEditor,
    saveEditorContent,
    destroyEditor,
    destroyAllEditors
};
