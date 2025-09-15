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
    
    // Initialize editor for the currently active entry
    if (currentActiveEntry) {
        initializeEditor(currentActiveEntry);
    }

    // Add click handlers for journal links
    document.querySelectorAll('.journal-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const entryId = this.getAttribute('data-id');
            
            // Add loading state
            this.classList.add('loading');
            
            // Update active state with animation
            document.querySelectorAll('.journal-link').forEach(l => {
                l.classList.remove('active');
                l.classList.remove('loading');
            });
            
            // Small delay to show loading state
            setTimeout(() => {
                this.classList.remove('loading');
                this.classList.add('active');
                switchToEntry(entryId);
            }, 200);
        });

        // Add keyboard navigation
        link.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                const nextLink = this.parentElement.nextElementSibling?.querySelector('.journal-link');
                if (nextLink) nextLink.focus();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                const prevLink = this.parentElement.previousElementSibling?.querySelector('.journal-link');
                if (prevLink) prevLink.focus();
            }
        });

        // Add hover effects
        link.addEventListener('mouseenter', function() {
            if (!this.classList.contains('active')) {
                this.style.transform = 'translateX(2px)';
            }
        });

        link.addEventListener('mouseleave', function() {
            if (!this.classList.contains('active')) {
                this.style.transform = 'translateX(0)';
            }
        });

        // Make links focusable
        link.setAttribute('tabindex', '0');
    });

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
            onChange: (api, event) => {
                // Mark as having unsaved changes
                markAsUnsaved();
                
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
    
    // Check for unsaved changes before switching
    // if (hasUnsavedChanges && currentActiveEntry !== entryId) {
    //     if (!confirm('You have unsaved changes. Do you want to continue without saving?')) {
    //         return;
    //     }
    // }
    
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
        // if (titleElement && entryLink) {
        //     titleElement.textContent = entryLink.textContent;
        // }

        // Update last updated time
        updateLastUpdatedTime(entryId);

        // Initialize editor if not already done
        if (!editorInstances[entryId]) {
            initializeEditor(entryId);
        }

        currentActiveEntry = entryId;
        
        // Reset save state for new entry
        markAsSaved();
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
    updateLastUpdatedTimeAfterSave
};
