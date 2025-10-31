/**
 * Dashboard Editor - EditorJS Integration for Journal Entries
 * Handles initialization and management of EditorJS instances for journal entries
 */

// Store entry data and editor instances
let editorInstances = {};
let currentActiveEntry = null;
let autoSaveEnabled = true;
let autoSaveTimeout = null;
let hasUnsavedChanges = false;
let entryMetadata = {};
let autoTitleGenerated = {}; // Track which entries have auto-generated titles
let autoTitleTimeout = null; // Debounce timer for auto-title generation

/**
 * Initialize the dashboard editor system
 * @param {Object} entryData - Object containing entry data keyed by entry ID
 * @param {string} activeEntryId - ID of the currently active entry
 * @param {Object} metadata - Object containing entry metadata keyed by entry ID
 */
function initializeDashboardEditor(entryData, activeEntryId, metadata = {}) {
    window.entryData = entryData;
    entryMetadata = metadata;
    currentActiveEntry = activeEntryId;
    
    // Check if the active entry has a default title
    if (currentActiveEntry) {
        const titleElement = document.getElementById('currentEntryTitle');
        if (titleElement) {
            const currentTitle = titleElement.value || titleElement.textContent || '';
            if (currentTitle.startsWith('New Entry - ')) {
                autoTitleGenerated[currentActiveEntry] = true; // Enable auto-generation
            }
        }
    }
    
    // Initialize editor for the currently active entry
    if (currentActiveEntry) {
        initializeEditor(currentActiveEntry);
    }

    // NOTE: Journal link click handlers are now managed by scripts.js
    // to avoid conflicts. The switchToEntry function is still available
    // for external calls.

    // Initialize save functionality
    initializeSaveFunctionality();
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
            onChange: async (api, event) => {
                // Mark as having unsaved changes
                markAsUnsaved();
                
                // Debounce auto-title generation to avoid excessive calls
                clearTimeout(autoTitleTimeout);
                autoTitleTimeout = setTimeout(() => {
                    autoGenerateTitleFromContent(entryId, api);
                }, 500); // Wait 500ms after user stops typing
                
                // Auto-save functionality
                if (autoSaveEnabled) {
                    clearTimeout(autoSaveTimeout);
                    autoSaveTimeout = setTimeout(() => {
                        saveCurrentEntry();
                    }, 3000); // Auto-save after 3 seconds of inactivity
                }
                
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
 * Auto-generate title from first three words of content
 * Only updates if the title is still in the default "New Entry - {date}" format
 * @param {string} entryId - The ID of the entry
 * @param {Object} api - EditorJS API instance
 */
async function autoGenerateTitleFromContent(entryId, api) {
    try {
        const titleElement = document.getElementById('currentEntryTitle');
        if (!titleElement) return;
        
        const currentTitle = titleElement.value || titleElement.textContent || '';
        
        // Check if title is still in default format "New Entry - {date}"
        const isDefaultTitle = currentTitle.startsWith('New Entry - ');
        
        // Only auto-generate if it's still the default title OR we've already auto-generated for this entry
        if (!isDefaultTitle && !autoTitleGenerated[entryId]) {
            return;
        }
        
        // Get a lightweight copy of content by saving
        const data = await api.saver.save();
        
        // Extract text from blocks
        let allText = '';
        if (data.blocks && Array.isArray(data.blocks)) {
            // Only process first few blocks to optimize performance
            const maxBlocks = Math.min(data.blocks.length, 5);
            
            for (let i = 0; i < maxBlocks; i++) {
                const block = data.blocks[i];
                
                // Extract text based on block type
                if (block.data) {
                    if (block.data.text) {
                        // Paragraph, header, quote, etc.
                        allText += block.data.text + ' ';
                    } else if (block.data.items && Array.isArray(block.data.items)) {
                        // List or checklist
                        for (const item of block.data.items) {
                            if (typeof item === 'string') {
                                allText += item + ' ';
                            } else if (item.content) {
                                allText += item.content + ' ';
                            } else if (item.text) {
                                allText += item.text + ' ';
                            }
                        }
                    } else if (block.data.caption) {
                        // Some blocks have caption field
                        allText += block.data.caption + ' ';
                    }
                }
                
                // Stop early if we have enough words
                const currentWords = allText.trim().split(/\s+/).filter(w => w.length > 0);
                if (currentWords.length >= 3) {
                    break;
                }
            }
        }
        
        // Remove HTML tags and extra whitespace
        allText = allText.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
        
        if (allText.length === 0) return;
        
        // Get first three words
        const words = allText.split(/\s+/).filter(w => w.length > 0);
        if (words.length === 0) return;
        
        const firstThreeWords = words.slice(0, 3).join(' ');
        
        if (firstThreeWords.length === 0) return;
        
        // Only update if the title has actually changed
        if (currentTitle === firstThreeWords) return;
        
        // Update the title
        titleElement.value = firstThreeWords;
        if (titleElement.textContent !== undefined) {
            titleElement.textContent = firstThreeWords;
        }
        
        // Mark that this entry has an auto-generated title
        autoTitleGenerated[entryId] = true;
        
        console.log(`Auto-generated title for entry ${entryId}: "${firstThreeWords}"`);
        
    } catch (error) {
        console.error('Error auto-generating title:', error);
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
    
    console.log('DashboardEditor switchToEntry called for:', entryId);
    
    // Hide all entries
    document.querySelectorAll('.journal-entry').forEach(entry => {
        entry.classList.add('d-none');
    });

    // Show selected entry
    const entryElement = document.getElementById(`journal-${entryId}`);
    if (entryElement) {
        entryElement.classList.remove('d-none');
        console.log('Made entry visible:', entryId);
        
        // Update title in header if needed
        const titleElement = document.getElementById('currentEntryTitle');
        const entryLink = document.querySelector(`[data-id="${entryId}"]`);
        if (titleElement && entryLink) {
            const linkTitle = entryLink.getAttribute('title') || entryLink.textContent.trim();
            if (linkTitle && titleElement.textContent !== linkTitle) {
                titleElement.textContent = linkTitle;
                console.log('Updated title to:', linkTitle);
            }
        }
    } else {
        console.warn('Entry element not found for:', entryId);
    }

    // Update last updated time
    updateLastUpdatedTime(entryId);

    // Initialize editor if not already done
    if (!editorInstances[entryId]) {
        console.log('Initializing new editor for:', entryId);
        initializeEditor(entryId);
    } else {
        console.log('Editor already exists for:', entryId);
    }

    // Update current active entry
    currentActiveEntry = entryId;
    
    // Check if this entry has a default title format and mark it for auto-generation
    const titleElement = document.getElementById('currentEntryTitle');
    if (titleElement) {
        const currentTitle = titleElement.value || titleElement.textContent || '';
        if (currentTitle.startsWith('New Entry - ')) {
            autoTitleGenerated[entryId] = true; // Allow auto-generation
        }
    }
    
    // Reset save state for new entry
    markAsSaved();
    
    console.log('switchToEntry completed for:', entryId);
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

/**
 * Initialize save functionality
 */
function initializeSaveFunctionality() {
    const saveButton = document.getElementById('saveButton');
    const autoSaveToggle = document.getElementById('autoSaveToggle');
    const titleElement = document.getElementById('currentEntryTitle');

    // Save button click handler
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            saveCurrentEntry();
        });
    }

    // Auto-save toggle handler
    if (autoSaveToggle) {
        updateAutoSaveToggle();
        autoSaveToggle.addEventListener('click', function() {
            autoSaveEnabled = !autoSaveEnabled;
            updateAutoSaveToggle();
            
            if (autoSaveEnabled) {
                showNotification('Auto-save enabled', 'success');
            } else {
                showNotification('Auto-save disabled', 'info');
                clearTimeout(autoSaveTimeout);
            }
        });
    }

    // Title change handler
    if (titleElement) {
        titleElement.addEventListener('blur', function() {
            if (currentActiveEntry) {
                markAsUnsaved();
                if (autoSaveEnabled) {
                    clearTimeout(autoSaveTimeout);
                    autoSaveTimeout = setTimeout(() => {
                        saveCurrentEntry();
                    }, 1000);
                }
            }
        });

        // Prevent enter key from creating new lines in title
        titleElement.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.blur();
            }
        });
    }

    // Keyboard shortcut for save (Ctrl+S)
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            saveCurrentEntry();
        }
    });
}

/**
 * Save the current entry
 */
async function saveCurrentEntry() {
    if (!currentActiveEntry) {
        showNotification('No entry selected', 'warning');
        return;
    }

    const editor = getCurrentEditor();
    if (!editor) {
        showNotification('Editor not found', 'error');
        return;
    }

    try {
        showSavingStatus();
        
        // Get editor content
        const editorData = await editor.save();
        
        // Get title
        const titleElement = document.getElementById('currentEntryTitle');
        const title = titleElement ? titleElement.textContent.trim() : '';
        
        if (!title) {
            showNotification('Title is required', 'error');
            hideSavingStatus();
            return;
        }

        // Prepare data for API
        const data = {
            title: title,
            content: editorData,
        };

        // Send to API
        const response = await fetch(`/api/entries/${currentActiveEntry}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            const result = await response.json();
            markAsSaved();
            showNotification('Entry saved successfully', 'success');
            
            // Update the entry link text if title changed
            updateEntryLinkTitle(currentActiveEntry, title);
            
            // Update the last updated time with current time
            updateLastUpdatedTimeAfterSave(currentActiveEntry);
            
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save entry');
        }

    } catch (error) {
        console.error('Save error:', error);
        showNotification(`Save failed: ${error.message}`, 'error');
    } finally {
        hideSavingStatus();
    }
}

/**
 * Mark entry as having unsaved changes
 */
function markAsUnsaved() {
    hasUnsavedChanges = true;
    const saveButton = document.getElementById('saveButton');
    if (saveButton) {
        saveButton.classList.remove('btn-outline-secondary');
        saveButton.classList.add('btn-primary');
    }
    hideSaveStatus();
}

/**
 * Mark entry as saved
 */
function markAsSaved() {
    hasUnsavedChanges = false;
    const saveButton = document.getElementById('saveButton');
    if (saveButton) {
        saveButton.classList.remove('btn-primary');
        saveButton.classList.add('btn-outline-secondary');
    }
    showSaveStatus();
}

/**
 * Show saving status
 */
function showSavingStatus() {
    const savingStatus = document.getElementById('savingStatus');
    const saveStatus = document.getElementById('saveStatus');
    
    if (savingStatus) savingStatus.classList.remove('d-none');
    if (saveStatus) saveStatus.classList.add('d-none');
}

/**
 * Hide saving status
 */
function hideSavingStatus() {
    const savingStatus = document.getElementById('savingStatus');
    if (savingStatus) savingStatus.classList.add('d-none');
}

/**
 * Show save status
 */
function showSaveStatus() {
    const saveStatus = document.getElementById('saveStatus');
    const savingStatus = document.getElementById('savingStatus');
    
    if (saveStatus) saveStatus.classList.remove('d-none');
    if (savingStatus) savingStatus.classList.add('d-none');
    
    // Hide after 3 seconds
    setTimeout(() => {
        if (saveStatus) saveStatus.classList.add('d-none');
    }, 7000);
}

/**
 * Hide save status
 */
function hideSaveStatus() {
    const saveStatus = document.getElementById('saveStatus');
    if (saveStatus) saveStatus.classList.add('d-none');
}

/**
 * Update auto-save toggle appearance
 */
function updateAutoSaveToggle() {
    const autoSaveToggle = document.getElementById('autoSaveToggle');
    if (autoSaveToggle) {
        if (autoSaveEnabled) {
            autoSaveToggle.classList.remove('btn-outline-secondary');
            autoSaveToggle.classList.add('btn-outline-success');
            autoSaveToggle.title = 'Auto-save enabled - Click to disable';
        } else {
            autoSaveToggle.classList.remove('btn-outline-success');
            autoSaveToggle.classList.add('btn-outline-secondary');
            autoSaveToggle.title = 'Auto-save disabled - Click to enable';
        }
    }
}

/**
 * Truncate text to match Django's truncatechars behavior
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length (default 20 to match template)
 * @returns {string} Truncated text
 */
function truncateText(text, maxLength = 20) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 1) + '...';
}

/**
 * Update entry link title in sidebar
 */
function updateEntryLinkTitle(entryId, newTitle) {
    const entryLink = document.querySelector(`[data-id="${entryId}"]`);
    if (entryLink) {
        const titleElement = entryLink.querySelector('.journal-title');
        if (titleElement) {
            // Use consistent truncation function
            titleElement.textContent = truncateText(newTitle, 20);
            entryLink.setAttribute('title', newTitle); // Update tooltip with full title
        } else {
            // Fallback for old structure
            entryLink.textContent = truncateText(newTitle, 20);
            entryLink.setAttribute('title', newTitle);
        }
    }
}

/**
 * Get CSRF token from cookies
 */
function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    return '';
}

/**
 * Update the last updated time for an entry
 * @param {string} entryId - The ID of the entry
 */
function updateLastUpdatedTime(entryId) {
    const lastUpdatedElement = document.getElementById('lastUpdated');
    if (lastUpdatedElement && entryMetadata[entryId]) {
        lastUpdatedElement.textContent = `Last updated: ${entryMetadata[entryId].updated_at}`;
    }
}

/**
 * Update the last updated time after saving (sets to current time)
 * @param {string} entryId - The ID of the entry that was saved
 */
function updateLastUpdatedTimeAfterSave(entryId) {
    const lastUpdatedElement = document.getElementById('lastUpdated');
    if (lastUpdatedElement) {
        const now = new Date();
        const formattedTime = formatDateTime(now);
        lastUpdatedElement.textContent = `Last updated: ${formattedTime}`;
        
        // Update the metadata cache
        if (entryMetadata[entryId]) {
            entryMetadata[entryId].updated_at = formattedTime;
            entryMetadata[entryId].updated_at_iso = now.toISOString();
        }
    }
}

/**
 * Format a date to match Django's "M d, Y H:i" format
 * @param {Date} date - The date to format
 * @returns {string} Formatted date string
 */
function formatDateTime(date) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    const month = months[date.getMonth()];
    const day = date.getDate();
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    
    return `${month} ${day}, ${year} ${hours}:${minutes}`;
}

/**
 * Show notification to user
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'bottom: 20px; right: 20px; z-index: 1050; min-width: 300px;';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Export functions for global access if needed
window.DashboardEditor = {
    initialize: initializeDashboardEditor,
    initializeEditor,
    switchToEntry,
    getCurrentEditor,
    saveEditorContent,
    saveCurrentEntry,
    destroyEditor,
    destroyAllEditors,
    markAsUnsaved,
    markAsSaved,
    updateLastUpdatedTime,
    updateLastUpdatedTimeAfterSave,
    disableAutoTitle: function(entryId) {
        // Disable auto-title generation for this entry
        if (entryId) {
            autoTitleGenerated[entryId] = false;
        }
    }
};
