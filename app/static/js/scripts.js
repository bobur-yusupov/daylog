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
        if (!titleInput || !currentEntryId) return;
        
        // Save title on blur (lose focus)
        titleInput.addEventListener('blur', function() {
            const newTitle = this.value.trim();
            if (newTitle) {
                saveTitleChange(newTitle);
            }
        });
        
        // Save on Enter key
        titleInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const newTitle = this.value.trim();
                if (newTitle) {
                    saveTitleChange(newTitle);
                }
                
                // Try to focus the editor
                if (window.DashboardEditor) {
                    const editor = window.DashboardEditor.getCurrentEditor();
                    if (editor) {
                        try {
                            editor.focus();
                        } catch (err) {
                            // Editor focus failed, continue normally
                        }
                    }
                }
            }
        });
    }
    
    async function saveTitleChange(newTitle) {
        if (!currentEntryId) return;
        
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            
            if (!csrfToken) {
                showNotification('Authentication error', 'error');
                return;
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
                    title: newTitle,
                    content: currentContent
                })
            });
            
            if (response.ok) {
                const entryData = await response.json();
                updateLastUpdated(entryData.updated_at);
                showNotification('Title saved', 'success');
            } else {
                showNotification('Failed to save title', 'error');
            }
            
        } catch (error) {
            showNotification('Failed to save title', 'error');
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
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim().toLowerCase();
            
            searchTimeout = setTimeout(() => {
                filterEntries(query);
            }, 300);
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
        const profileBtn = document.getElementById('profileDropdown');
        const dropdownMenu = document.querySelector('.dropdown-menu');
        
        if (!profileBtn || !dropdownMenu) return;
        
        profileBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const isVisible = dropdownMenu.style.display === 'block';
            dropdownMenu.style.display = isVisible ? 'none' : 'block';
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function() {
            if (dropdownMenu) {
                dropdownMenu.style.display = 'none';
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