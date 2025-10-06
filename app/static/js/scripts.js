// Dashboard JavaScript - Simple and Reliable
(function() {
    'use strict';
    
    // Global state
    let dashboardData = null;
    let currentEntryId = null;
    let titleSaveTimeout = null;
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeApp);
    } else {
        initializeApp();
    }
    
    function initializeApp() {
        // Load dashboard data
        loadDashboardData();
        
        // Setup components
        setupSidebarToggle();
        setupJournalSwitching();
        setupSearchFunctionality();
        setupNewEntryButton();
        setupProfileDropdown();
        setupTitleEditing();
        setupGlobalKeyboardShortcuts();
        setupTagManagement();
    }
    
    function setupGlobalKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // F2 to edit title
            if (e.key === 'F2' && !e.ctrlKey && !e.altKey && !e.shiftKey) {
                e.preventDefault();
                const titleEditBtn = document.getElementById('titleEditBtn');
                if (titleEditBtn && !titleEditBtn.classList.contains('d-none')) {
                    titleEditBtn.click();
                }
            }
            
            // Ctrl+S to save (if in title editing mode)
            if (e.key === 's' && e.ctrlKey && !e.altKey && !e.shiftKey) {
                const titleSaveBtn = document.getElementById('titleSaveBtn');
                if (titleSaveBtn && !titleSaveBtn.classList.contains('d-none')) {
                    e.preventDefault();
                    titleSaveBtn.click();
                }
            }
        });
    }
    
    function loadDashboardData() {
        try {
            const metadataElement = document.getElementById('entry-metadata');
            if (metadataElement) {
                dashboardData = JSON.parse(metadataElement.textContent);
                
                if (dashboardData.active_entry) {
                    currentEntryId = dashboardData.active_entry.id;
                    loadActiveEntryContent();
                }
            }
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }
    
    function loadActiveEntryContent() {
        if (!currentEntryId) return;
        
        try {
            // Get content from the separate script tag
            const contentElement = document.getElementById('active-entry-content');
            let entryContent = null;
            
            if (contentElement) {
                entryContent = JSON.parse(contentElement.textContent);
            } else {
                entryContent = {
                    time: Date.now(),
                    blocks: [],
                    version: "2.28.2"
                };
            }
            
            // Initialize editor if DashboardEditor is available
            if (window.DashboardEditor) {
                const entryData = {};
                entryData[currentEntryId] = entryContent;
                
                const metadata = dashboardData.active_entry ? {
                    [currentEntryId]: dashboardData.active_entry
                } : {};
                
                setTimeout(() => {
                    // Make title input compatible with dashboard editor
                    makeInputCompatibleWithDashboardEditor();
                    
                    window.DashboardEditor.initialize(entryData, currentEntryId, metadata);
                }, 100);
            }
            
        } catch (error) {
            console.error('Error loading entry content:', error);
        }
    }
    
    function makeInputCompatibleWithDashboardEditor() {
        const titleInput = document.getElementById('currentEntryTitle');
        if (titleInput && titleInput.tagName === 'INPUT') {
            // Override textContent getter/setter to work with input value
            Object.defineProperty(titleInput, 'textContent', {
                get: function() {
                    return this.value;
                },
                set: function(value) {
                    this.value = value;
                }
            });
        }
    }
    
    function setupTitleEditing() {
        const titleInput = document.getElementById('currentEntryTitle');
        const titleWrapper = document.querySelector('.title-input-wrapper');
        const titleEditBtn = document.getElementById('titleEditBtn');
        const titleSaveBtn = document.getElementById('titleSaveBtn');
        const titleCancelBtn = document.getElementById('titleCancelBtn');
        
        if (!titleInput || !currentEntryId || !titleWrapper) return;
        
        let originalTitle = titleInput.value;
        let isEditing = false;
        
        // Add character counter
        const charCounter = document.createElement('div');
        charCounter.className = 'title-char-counter';
        titleWrapper.appendChild(charCounter);
        
        // Add save indicator
        const saveIndicator = document.createElement('div');
        saveIndicator.className = 'title-save-indicator';
        saveIndicator.innerHTML = '<i class="bi bi-check-circle me-1"></i>Saved';
        titleWrapper.appendChild(saveIndicator);
        
        function updateCharCounter() {
            const length = titleInput.value.length;
            const maxLength = titleInput.getAttribute('maxlength') || 200;
            charCounter.textContent = `${length}/${maxLength}`;
            
            charCounter.classList.remove('warning', 'danger');
            if (length > maxLength * 0.8) {
                charCounter.classList.add(length > maxLength * 0.9 ? 'danger' : 'warning');
            }
        }
        
        function enterEditMode() {
            isEditing = true;
            originalTitle = titleInput.value;
            titleWrapper.classList.add('editing');
            titleEditBtn.classList.add('d-none');
            titleSaveBtn.classList.remove('d-none');
            titleCancelBtn.classList.remove('d-none');
            titleInput.focus();
            titleInput.select();
            updateCharCounter();
        }
        
        function exitEditMode() {
            isEditing = false;
            titleWrapper.classList.remove('editing');
            titleEditBtn.classList.remove('d-none');
            titleSaveBtn.classList.add('d-none');
            titleCancelBtn.classList.add('d-none');
            charCounter.textContent = '';
        }
        
        function cancelEdit() {
            titleInput.value = originalTitle;
            exitEditMode();
        }
        
        function saveTitle() {
            const newTitle = titleInput.value.trim();
            if (newTitle && newTitle !== originalTitle) {
                saveTitleChange(newTitle);
                originalTitle = newTitle;
            }
            exitEditMode();
        }
        
        function showSaveIndicator(isError = false) {
            saveIndicator.classList.toggle('error', isError);
            saveIndicator.innerHTML = isError ? 
                '<i class="bi bi-exclamation-circle me-1"></i>Error' :
                '<i class="bi bi-check-circle me-1"></i>Saved';
            saveIndicator.classList.add('show');
            setTimeout(() => {
                saveIndicator.classList.remove('show');
            }, 2000);
        }
        
        // Event listeners
        titleEditBtn.addEventListener('click', enterEditMode);
        titleSaveBtn.addEventListener('click', saveTitle);
        titleCancelBtn.addEventListener('click', cancelEdit);
        
        // Input events
        titleInput.addEventListener('input', function() {
            if (isEditing) {
                updateCharCounter();
            }
        });
        
        titleInput.addEventListener('focus', function() {
            if (!isEditing) {
                enterEditMode();
            }
        });
        
        titleInput.addEventListener('blur', function() {
            // Small delay to allow button clicks to register
            setTimeout(() => {
                if (isEditing && !titleWrapper.contains(document.activeElement)) {
                    const newTitle = this.value.trim();
                    if (newTitle && newTitle !== originalTitle) {
                        saveTitle();
                    } else {
                        exitEditMode();
                    }
                }
            }, 150);
        });
        
        titleInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveTitle();
                
                // Try to focus the editor
                if (window.DashboardEditor) {
                    const editor = window.DashboardEditor.getCurrentEditor();
                    if (editor && editor.blocks && typeof editor.blocks.getBlockByIndex === 'function') {
                        const firstBlock = editor.blocks.getBlockByIndex(0);
                        if (firstBlock && typeof firstBlock.focus === 'function') {
                            firstBlock.focus();
                        }
                        
                    }
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelEdit();
            }
        });
        
        // Override the original saveTitleChange to show indicator
        const originalSaveTitleChange = window.saveTitleChange || saveTitleChange;
        window.saveTitleChange = async function(newTitle) {
            try {
                await originalSaveTitleChange(newTitle);
                showSaveIndicator(false);
            } catch (error) {
                showSaveIndicator(true);
                throw error;
            }
        };
    }
    
    async function saveTitleChange(newTitle) {
        if (!currentEntryId || !newTitle.trim()) return;
        
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            
            if (!csrfToken) {
                showNotification('Authentication error - please refresh the page', 'error');
                return;
            }
            
            // Show saving state
            const titleInput = document.getElementById('currentEntryTitle');
            if (titleInput) {
                titleInput.disabled = true;
            }
            
            // Get current editor content
            let currentContent = {
                time: Date.now(),
                blocks: [],
                version: "2.28.2"
            };
            
            if (window.DashboardEditor) {
                const editor = window.DashboardEditor.getCurrentEditor();
                if (editor) {
                    try {
                        currentContent = await editor.save();
                    } catch (err) {
                        // Use default content if editor save fails
                    }
                }
            }
            
            const response = await fetch(`/api/entries/${currentEntryId}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    title: newTitle.trim(),
                    content: currentContent
                })
            });
            
            if (response.ok) {
                const entryData = await response.json();
                updateLastUpdated(entryData.updated_at);
                
                // Update the title in the sidebar if it exists
                const sidebarEntry = document.querySelector(`[data-id="${currentEntryId}"] .journal-title`);
                if (sidebarEntry) {
                    sidebarEntry.textContent = newTitle.length > 20 ? newTitle.substring(0, 20) + '...' : newTitle;
                }
                
                showNotification('Title saved successfully', 'success');
            } else {
                const errorData = await response.json().catch(() => ({}));
                const errorMessage = errorData.detail || errorData.title || 'Failed to save title';
                showNotification(errorMessage, 'error');
                throw new Error(errorMessage);
            }
            
        } catch (error) {
            showNotification('Failed to save title - please try again', 'error');
            throw error;
        } finally {
            // Re-enable input
            const titleInput = document.getElementById('currentEntryTitle');
            if (titleInput) {
                titleInput.disabled = false;
            }
        }
    }
    
    function setupSidebarToggle() {
        const sidebar = document.querySelector('.sidebar');
        const openBtn = document.getElementById('openSidebar');
        const closeBtn = document.getElementById('closeSidebar');
        const main = document.querySelector('main');
        
        if (!sidebar || !openBtn || !closeBtn || !main) return;
        
        function hideSidebar() {
            sidebar.style.transform = 'translateX(-100%)';
            main.style.marginLeft = '0';
        }
        
        function showSidebar() {
            sidebar.style.transform = 'translateX(0)';
            main.style.marginLeft = '300px';
        }
        
        openBtn.addEventListener('click', showSidebar);
        closeBtn.addEventListener('click', hideSidebar);
    }
    
    function setupJournalSwitching() {
        const journalLinks = document.querySelectorAll('.journal-link');
        
        journalLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const entryId = this.dataset.id;
                if (entryId && entryId !== currentEntryId) {
                    // Simple redirect - most reliable approach
                    window.location.href = `/entry/${entryId}/`;
                }
            });
        });
    }
    
    function setupSearchFunctionality() {
        const searchInput = document.getElementById('searchInput');
        if (!searchInput) return;
        
        let searchTimeout;
        
        // Handle local filtering on input
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim().toLowerCase();
            
            searchTimeout = setTimeout(() => {
                filterEntries(query);
            }, 300);
        });
        
        // Handle Enter key to go to search page
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = this.value.trim();
                if (query) {
                    window.location.href = `/search/?q=${encodeURIComponent(query)}`;
                }
            }
        });
    }
    
    function filterEntries(query) {
        const journalLinks = document.querySelectorAll('.journal-link');
        
        journalLinks.forEach(link => {
            const titleElement = link.querySelector('.journal-title');
            if (titleElement) {
                const title = titleElement.textContent.toLowerCase();
                const matches = !query || title.includes(query);
                const navItem = link.closest('.nav-item');
                if (navItem) {
                    navItem.style.display = matches ? 'block' : 'none';
                }
            }
        });
        

    }
    
    function setupNewEntryButton() {
        const newEntryBtn = document.getElementById('newEntryBtn');
        if (!newEntryBtn) return;
        
        newEntryBtn.addEventListener('click', function(e) {
            e.preventDefault();
            // Simple redirect to create new entry
            window.location.href = '/entry/new/';
        });
    }
    
    function setupProfileDropdown() {
        const profileToggle = document.getElementById('profileToggle');
        const profileDropdown = document.getElementById('profileDropdown');
        
        if (!profileToggle || !profileDropdown) return;
        
        profileToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Toggle the dropdown
            const isVisible = profileDropdown.classList.contains('show');
            if (isVisible) {
                profileDropdown.classList.remove('show');
                profileToggle.classList.remove('active');
            } else {
                profileDropdown.classList.add('show');
                profileToggle.classList.add('active');
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!profileToggle.contains(e.target) && !profileDropdown.contains(e.target)) {
                profileDropdown.classList.remove('show');
                profileToggle.classList.remove('active');
            }
        });
    }
    
    function updateLastUpdated(dateTime) {
        const lastUpdatedElement = document.getElementById('lastUpdated');
        if (lastUpdatedElement) {
            const date = new Date(dateTime);
            lastUpdatedElement.textContent = `Last updated: ${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
        }
    }
    
    // =================
    // Tag Management
    // =================
    
    function setupTagManagement() {
        const addTagBtn = document.getElementById('addTagBtn');
        const tagInputContainer = document.getElementById('tagInputContainer');
        const tagInput = document.getElementById('tagInput');
        const saveTagBtn = document.getElementById('saveTagBtn');
        const cancelTagBtn = document.getElementById('cancelTagBtn');
        const tagsDisplay = document.getElementById('tagsDisplay');
        const tagSuggestions = document.getElementById('tagSuggestions');
        
        if (!addTagBtn || !currentEntryId) return;
        
        let suggestionTimeout = null;
        let selectedSuggestionIndex = -1;
        
        // Show tag input
        addTagBtn.addEventListener('click', function() {
            showTagInput();
        });
        
        // Hide tag input
        cancelTagBtn.addEventListener('click', function() {
            hideTagInput();
        });
        
        // Save tag
        saveTagBtn.addEventListener('click', function() {
            saveTag();
        });
        
        // Handle Enter and Escape keys in tag input
        tagInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (selectedSuggestionIndex >= 0) {
                    selectSuggestion(selectedSuggestionIndex);
                } else {
                    saveTag();
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideTagInput();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                navigateSuggestions(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                navigateSuggestions(-1);
            }
        });
        
        // Handle tag input changes for suggestions
        tagInput.addEventListener('input', function() {
            const value = this.value.trim();
            if (value.length >= 2) {
                clearTimeout(suggestionTimeout);
                suggestionTimeout = setTimeout(() => fetchTagSuggestions(value), 300);
            } else {
                hideSuggestions();
            }
        });
        
        // Handle tag removal
        tagsDisplay.addEventListener('click', function(e) {
            if (e.target.classList.contains('btn-close')) {
                const tagId = e.target.getAttribute('data-tag-id');
                removeTag(tagId);
            }
        });
        
        // Close suggestions when clicking outside
        document.addEventListener('click', function(e) {
            if (!tagInputContainer.contains(e.target)) {
                hideSuggestions();
            }
        });
        
        function showTagInput() {
            addTagBtn.classList.add('d-none');
            tagInputContainer.classList.remove('d-none');
            tagInput.focus();
            selectedSuggestionIndex = -1;
        }
        
        function hideTagInput() {
            addTagBtn.classList.remove('d-none');
            tagInputContainer.classList.add('d-none');
            tagInput.value = '';
            hideSuggestions();
            selectedSuggestionIndex = -1;
        }
        
        function saveTag() {
            const tagName = tagInput.value.trim();
            if (!tagName) {
                hideTagInput();
                return;
            }
            
            // Check for duplicate tags
            const existingTags = Array.from(tagsDisplay.querySelectorAll('.tag-item'))
                .map(tag => tag.textContent.replace('×', '').trim().toLowerCase());
            
            if (existingTags.includes(tagName.toLowerCase())) {
                showNotification('Tag already exists', 'warning');
                hideTagInput();
                return;
            }
            
            // Show loading state
            const loadingTag = createLoadingTag();
            addTagBtn.before(loadingTag);
            hideTagInput();
            
            // Save tag via API
            fetch(`/api/entries/${currentEntryId}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    tag_names: [...existingTags, tagName]
                })
            })
            .then(response => response.json())
            .then(data => {
                loadingTag.remove();
                if (data.id) {
                    // Find the new tag in the response
                    const newTag = data.tags.find(tag => 
                        tag.name.toLowerCase() === tagName.toLowerCase()
                    );
                    if (newTag) {
                        addTagToDisplay(newTag);
                        showNotification('Tag added successfully', 'success');
                    }
                } else {
                    showNotification('Failed to add tag', 'error');
                }
            })
            .catch(error => {
                console.error('Error saving tag:', error);
                loadingTag.remove();
                showNotification('Failed to add tag', 'error');
            });
        }
        
        function removeTag(tagId) {
            const tagElement = document.querySelector(`[data-tag-id="${tagId}"]`);
            if (!tagElement) return;
            
            // Get current tags except the one being removed
            const remainingTags = Array.from(tagsDisplay.querySelectorAll('.tag-item'))
                .filter(tag => tag.getAttribute('data-tag-id') !== tagId)
                .map(tag => tag.textContent.replace('×', '').trim());
            
            // Show loading state
            tagElement.style.opacity = '0.5';
            tagElement.style.pointerEvents = 'none';
            
            // Remove tag via API
            fetch(`/api/entries/${currentEntryId}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    tag_names: remainingTags
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.id) {
                    tagElement.remove();
                    showNotification('Tag removed successfully', 'success');
                } else {
                    tagElement.style.opacity = '';
                    tagElement.style.pointerEvents = '';
                    showNotification('Failed to remove tag', 'error');
                }
            })
            .catch(error => {
                console.error('Error removing tag:', error);
                tagElement.style.opacity = '';
                tagElement.style.pointerEvents = '';
                showNotification('Failed to remove tag', 'error');
            });
        }
        
        function fetchTagSuggestions(query) {
            fetch(`/api/tags/search/?q=${encodeURIComponent(query)}`, {
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.results && data.results.length > 0) {
                    showSuggestions(data.results);
                } else {
                    hideSuggestions();
                }
            })
            .catch(error => {
                console.error('Error fetching tag suggestions:', error);
                hideSuggestions();
            });
        }
        
        function showSuggestions(suggestions) {
            tagSuggestions.innerHTML = '';
            suggestions.forEach((tag, index) => {
                const item = document.createElement('div');
                item.className = 'tag-suggestion-item';
                item.innerHTML = `
                    <span class="tag-name">${escapeHtml(tag.name)}</span>
                    <span class="tag-count">${tag.entry_count} entries</span>
                `;
                item.addEventListener('click', () => selectSuggestion(index));
                tagSuggestions.appendChild(item);
            });
            tagSuggestions.classList.add('show');
            selectedSuggestionIndex = -1;
        }
        
        function hideSuggestions() {
            tagSuggestions.classList.remove('show');
            selectedSuggestionIndex = -1;
        }
        
        function navigateSuggestions(direction) {
            const items = tagSuggestions.querySelectorAll('.tag-suggestion-item');
            if (items.length === 0) return;
            
            // Remove previous highlight
            if (selectedSuggestionIndex >= 0) {
                items[selectedSuggestionIndex].classList.remove('highlighted');
            }
            
            // Calculate new index
            selectedSuggestionIndex += direction;
            if (selectedSuggestionIndex < 0) {
                selectedSuggestionIndex = items.length - 1;
            } else if (selectedSuggestionIndex >= items.length) {
                selectedSuggestionIndex = 0;
            }
            
            // Highlight new item
            items[selectedSuggestionIndex].classList.add('highlighted');
            items[selectedSuggestionIndex].scrollIntoView({ block: 'nearest' });
        }
        
        function selectSuggestion(index) {
            const items = tagSuggestions.querySelectorAll('.tag-suggestion-item');
            if (items[index]) {
                const tagName = items[index].querySelector('.tag-name').textContent;
                tagInput.value = tagName;
                hideSuggestions();
                saveTag();
            }
        }
        
        function createLoadingTag() {
            const loadingTag = document.createElement('span');
            loadingTag.className = 'tag-loading';
            loadingTag.innerHTML = `
                <div class="spinner-border" role="status" aria-hidden="true"></div>
                Adding...
            `;
            return loadingTag;
        }
        
        function addTagToDisplay(tag) {
            const tagElement = document.createElement('span');
            tagElement.className = 'badge bg-primary tag-item';
            tagElement.setAttribute('data-tag-id', tag.id);
            tagElement.innerHTML = `
                <i class="bi bi-tag-fill me-1"></i>${escapeHtml(tag.name)}
                <button type="button" class="btn-close btn-close-white ms-1" 
                        data-tag-id="${tag.id}" 
                        title="Remove tag" 
                        aria-label="Remove ${escapeHtml(tag.name)} tag"></button>
            `;
            addTagBtn.before(tagElement);
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function getCsrfToken() {
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                   document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';
        }
    }
    
    // =================
    // Notification System
    // =================
    
    function showNotification(message, type = 'info') {
        // Remove existing notifications
        const existing = document.querySelectorAll('.notification');
        existing.forEach(n => n.remove());
        
        // Create new notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : 'success'} notification`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 250px;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }
        }, 3000);
    }
    
    // Add CSS for notifications
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        .notification {
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
    `;
    document.head.appendChild(style);
    
})();