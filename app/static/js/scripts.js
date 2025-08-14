// Journal functionality shared across new_journal and entry_detail pages

// Global variables
let editor;
let selectedTags = new Set();
let availableTags = [];
let currentSuggestionIndex = -1;
let originalContent;
let isEditMode = false;

// Utility function to check if we're on a journal page
function isJournalPage() {
    return document.body.classList.contains('journal-page') || 
           document.getElementById('editorjs') !== null;
}

// Initialize journal functionality if on a journal page
document.addEventListener('DOMContentLoaded', function() {
    if (isJournalPage()) {
        // Check if this is edit mode based on window.isEditMode flag
        if (window.isEditMode) {
            isEditMode = true;
        }
        
        // Initialize with existing content if available (for edit mode)
        const initialContent = window.entryContent || null;
        initializeJournalPage(initialContent);
    }
});

function initializeJournalPage(existingContent = null) {
    console.log('Initializing journal page...', existingContent ? 'with existing content' : 'for new entry');
    
    // Wait for EditorJS to load
    if (typeof EditorJS === 'undefined') {
        console.log('EditorJS not ready, retrying...');
        setTimeout(() => initializeJournalPage(existingContent), 100);
        return;
    }
    
    initializeEditor(existingContent);
    initializeTagSystem();
    initializeFormValidation();
    initializeEventListeners();
    loadAvailableTags();
    
    // For detail page, also initialize content rendering
    if (document.getElementById('rendered-content')) {
        renderContent();
    }
}

function initializeEditor(existingContent = null) {
    console.log('Initializing EditorJS...');
    
    const holder = document.getElementById('editorjs');
    if (!holder) {
        console.error('EditorJS holder element not found');
        return;
    }

    // Basic tools that should always work
    const tools = {
        header: Header,
        list: List,
        checklist: Checklist,
        quote: Quote,
        delimiter: Delimiter,
        marker: Marker
    };

    // Get initial data - either from parameter or window global
    let initialData = { blocks: [] };
    if (existingContent && existingContent.blocks) {
        initialData = existingContent;
        console.log('Using provided existing content for editor');
    } else if (window.entryContent && window.entryContent.blocks) {
        initialData = window.entryContent;
        console.log('Using window.entryContent for editor');
    }

    try {
        editor = new EditorJS({
            holder: 'editorjs',
            placeholder: 'Start writing your journal entry here... Use "/" to see formatting options.',
            tools: tools,
            minHeight: 200,
            data: initialData,
            onReady: () => {
                console.log('Editor.js is ready to work!');
                
                // Fix styling and positioning
                const editorElement = document.querySelector('#editorjs .codex-editor__redactor');
                if (editorElement) {
                    editorElement.style.paddingLeft = '0';
                    editorElement.style.paddingRight = '0';
                }
                
                // Fix toolbar positioning
                setTimeout(() => {
                    const toolbar = document.querySelector('#editorjs .ce-toolbar');
                    if (toolbar) {
                        toolbar.style.marginLeft = '-30px';
                        toolbar.style.left = '0';
                    }
                    
                    const plusButton = document.querySelector('#editorjs .ce-toolbar__plus');
                    if (plusButton) {
                        plusButton.style.left = '0';
                        plusButton.style.marginLeft = '0';
                    }
                }, 100);
            },
            onChange: () => {
                console.log('Content changed');
            }
        });
    } catch (error) {
        console.error('Failed to initialize EditorJS:', error);
    }
}

function initializeTagSystem() {
    const tagInput = document.getElementById('tag-input');
    const tagSuggestions = document.getElementById('tag-suggestions');

    if (tagInput) {
        tagInput.addEventListener('input', handleTagInput);
        tagInput.addEventListener('keydown', handleTagKeydown);
        tagInput.addEventListener('blur', hideSuggestions);
    }
}

function initializeFormValidation() {
    const titleInput = document.getElementById('title');
    const titleCounter = document.getElementById('title-counter');

    if (titleInput && titleCounter) {
        titleInput.addEventListener('input', function() {
            const length = this.value.length;
            titleCounter.textContent = length;
            
            if (length > 255) {
                titleCounter.classList.add('text-danger');
                this.classList.add('is-invalid');
            } else {
                titleCounter.classList.remove('text-danger');
                this.classList.remove('is-invalid');
            }
        });
    }
}

function initializeEventListeners() {
    // Form submission
    const form = document.getElementById('journal-form') || document.getElementById('edit-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
}

function initializeDetailPageEvents() {
    // Edit button
    const editBtn = document.getElementById('edit-btn');
    if (editBtn) {
        editBtn.addEventListener('click', enterEditMode);
    }
    
    // Cancel edit button
    const cancelBtn = document.getElementById('cancel-edit-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', exitEditMode);
    }
    
    // Escape key to exit edit mode
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && isEditMode) {
            exitEditMode();
        }
    });
}

async function loadAvailableTags() {
    try {
        // This would need to be replaced with actual API endpoint
        // For now using dummy data
        availableTags = ['work', 'personal', 'health', 'travel', 'ideas', 'goals', 'reflection'];
    } catch (error) {
        console.error('Failed to load available tags:', error);
    }
}

function handleTagInput(e) {
    const query = e.target.value.trim();
    
    if (query.length === 0) {
        hideSuggestions();
        return;
    }

    // Handle comma or enter to add tag
    if (query.endsWith(',') || query.endsWith('\n')) {
        const tagName = query.slice(0, -1).trim();
        if (tagName) {
            addTag(tagName);
            e.target.value = '';
        }
        hideSuggestions();
        return;
    }

    showTagSuggestions(query);
}

function handleTagKeydown(e) {
    const suggestions = document.querySelectorAll('.tag-suggestion');
    
    switch(e.key) {
        case 'Enter':
            e.preventDefault();
            if (currentSuggestionIndex >= 0 && suggestions[currentSuggestionIndex]) {
                const tagName = suggestions[currentSuggestionIndex].textContent;
                addTag(tagName);
                e.target.value = '';
                hideSuggestions();
            } else {
                const tagName = e.target.value.trim();
                if (tagName) {
                    addTag(tagName);
                    e.target.value = '';
                    hideSuggestions();
                }
            }
            break;
        case 'ArrowDown':
            e.preventDefault();
            currentSuggestionIndex = Math.min(currentSuggestionIndex + 1, suggestions.length - 1);
            updateSuggestionSelection();
            break;
        case 'ArrowUp':
            e.preventDefault();
            currentSuggestionIndex = Math.max(currentSuggestionIndex - 1, -1);
            updateSuggestionSelection();
            break;
        case 'Escape':
            hideSuggestions();
            break;
        case ',':
            e.preventDefault();
            const tagName = e.target.value.trim();
            if (tagName) {
                addTag(tagName);
                e.target.value = '';
            }
            hideSuggestions();
            break;
    }
}

function addTag(tagName) {
    tagName = tagName.toLowerCase().trim();
    
    if (tagName && !selectedTags.has(tagName)) {
        selectedTags.add(tagName);
        renderSelectedTags();
    }
}

function removeTag(tagName) {
    selectedTags.delete(tagName);
    renderSelectedTags();
}

function renderSelectedTags() {
    const container = document.getElementById('selected-tags');
    if (!container) return;
    
    container.innerHTML = Array.from(selectedTags).map(tag => `
        <span class="tag-badge">
            ${tag}
            <button type="button" class="tag-remove" onclick="removeTag('${tag}')" title="Remove tag">
                ×
            </button>
        </span>
    `).join('');
}

function showTagSuggestions(query) {
    const suggestionsContainer = document.getElementById('tag-suggestions');
    if (!suggestionsContainer) return;
    
    const filteredTags = availableTags
        .filter(tag => 
            tag.toLowerCase().includes(query.toLowerCase()) &&
            !selectedTags.has(tag.toLowerCase())
        )
        .slice(0, 10);
    
    if (filteredTags.length > 0) {
        suggestionsContainer.innerHTML = filteredTags.map(tag => `
            <div class="tag-suggestion" onclick="selectTagSuggestion('${tag}')">
                ${tag}
            </div>
        `).join('');
        suggestionsContainer.style.display = 'block';
    } else {
        hideSuggestions();
    }
}

function hideSuggestions() {
    const suggestionsContainer = document.getElementById('tag-suggestions');
    if (suggestionsContainer) {
        suggestionsContainer.style.display = 'none';
    }
    currentSuggestionIndex = -1;
}

function selectTagSuggestion(tag) {
    addTag(tag);
    const tagInput = document.getElementById('tag-input');
    if (tagInput) {
        tagInput.value = '';
    }
    hideSuggestions();
}

function updateSuggestionSelection() {
    const suggestions = document.querySelectorAll('.tag-suggestion');
    suggestions.forEach((suggestion, index) => {
        if (index === currentSuggestionIndex) {
            suggestion.classList.add('active');
        } else {
            suggestion.classList.remove('active');
        }
    });
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    if (!editor) {
        console.error('Editor not initialized');
        alert('Editor is not ready. Please wait and try again.');
        return;
    }

    const saveBtn = document.getElementById('save-btn');
    
    try {
        // Show saving state
        if (saveBtn) {
            saveBtn.disabled = true;
            const originalContent = saveBtn.innerHTML;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';
        }

        // Get editor content
        const outputData = await editor.save();
        
        // Set content in hidden field
        const contentField = document.getElementById('content');
        if (contentField) {
            contentField.value = JSON.stringify(outputData);
        }

        // Create tag inputs
        createTagInputs();
        
        // Submit form
        e.target.submit();
        
    } catch (error) {
        console.error('Save failed:', error);
        alert('Failed to save journal entry. Please check your content and try again.');
        
        // Reset button state
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Save';
        }
    }
}

function createTagInputs() {
    // Remove existing tag inputs
    document.querySelectorAll('input[name="tags"]').forEach(input => input.remove());
    
    // Create multiple hidden inputs for tags
    const form = document.getElementById('journal-form') || document.getElementById('edit-form');
    selectedTags.forEach(tag => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'tags';
        input.value = tag;
        form.appendChild(input);
    });
}

// Detail page specific functions
function enterEditMode() {
    isEditMode = true;
    document.body.classList.add('editing');
    
    // Store original content
    if (window.entryContent) {
        originalContent = JSON.stringify(window.entryContent);
    }
    
    // Re-initialize editor with content
    if (editor) {
        editor.destroy();
    }
    initializeEditor();
}

function exitEditMode() {
    isEditMode = false;
    document.body.classList.remove('editing');
    
    // Destroy editor
    if (editor) {
        editor.destroy();
        editor = null;
    }
    
    // Reset title field
    const titleField = document.getElementById('title-edit');
    if (titleField && window.originalTitle) {
        titleField.value = window.originalTitle;
    }
}

function renderContent() {
    const container = document.getElementById('rendered-content');
    
    if (!window.entryContent || !window.entryContent.blocks) {
        container.innerHTML = '<p class="text-muted">No content available.</p>';
        return;
    }

    const renderedHtml = window.entryContent.blocks.map(block => {
        switch(block.type) {
            case 'paragraph':
                return `<p>${block.data.text || ''}</p>`;
            case 'header':
                const level = block.data.level || 2;
                return `<h${level}>${block.data.text || ''}</h${level}>`;
            case 'list':
                const listItems = (block.data.items || []).map(item => {
                    if (typeof item === 'string') {
                        return `<li>${item}</li>`;
                    } else if (item.content) {
                        return `<li>${item.content}</li>`;
                    }
                    return '<li></li>';
                }).join('');
                const listType = block.data.style === 'ordered' ? 'ol' : 'ul';
                return `<${listType}>${listItems}</${listType}>`;
            case 'checklist':
                const checkItems = (block.data.items || []).map(item => {
                    const checked = item.checked ? 'checked' : '';
                    return `<div class="form-check">
                        <input class="form-check-input" type="checkbox" ${checked} disabled>
                        <label class="form-check-label">${item.text}</label>
                    </div>`;
                }).join('');
                return `<div class="checklist mb-3">${checkItems}</div>`;
            case 'quote':
                return `<blockquote class="blockquote">
                    <p>${block.data.text || ''}</p>
                    ${block.data.caption ? `<footer class="blockquote-footer">${block.data.caption}</footer>` : ''}
                </blockquote>`;
            case 'warning':
                return `<div class="alert alert-warning" role="alert">
                    ${block.data.title ? `<h6 class="alert-heading">${block.data.title}</h6>` : ''}
                    <p class="mb-0">${block.data.message || ''}</p>
                </div>`;
            case 'delimiter':
                return '<hr>';
            case 'code':
                return `<pre><code>${block.data.code || ''}</code></pre>`;
            case 'raw':
                return block.data.html || '';
            case 'table':
                if (!block.data.content || !Array.isArray(block.data.content)) return '';
                const tableRows = block.data.content.map((row, index) => {
                    const cellTag = index === 0 && block.data.withHeadings ? 'th' : 'td';
                    const cells = row.map(cell => `<${cellTag}>${cell}</${cellTag}>`).join('');
                    return `<tr>${cells}</tr>`;
                }).join('');
                return `<table class="table table-bordered">${tableRows}</table>`;
            case 'linkTool':
                return `<div class="card mb-3">
                    <div class="card-body">
                        <h6 class="card-title">
                            <a href="${block.data.link}" target="_blank" rel="noopener">
                                ${block.data.meta?.title || block.data.link}
                            </a>
                        </h6>
                        ${block.data.meta?.description ? `<p class="card-text">${block.data.meta.description}</p>` : ''}
                    </div>
                </div>`;
            default:
                console.warn('Unsupported block type:', block.type);
                return `<div class="alert alert-warning">Unsupported content type: ${block.type}</div>`;
        }
    }).join('');

    container.innerHTML = renderedHtml;
}