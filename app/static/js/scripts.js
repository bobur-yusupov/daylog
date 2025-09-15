// Dashboard JavaScript functionality - Completely rewritten for reliability
(function() {
    'use strict';
    
    // Global state
    let sidebarVisible = true;
    let dashboardData = null;
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeApp);
    } else {
        initializeApp();
    }
    
    function initializeApp() {
        console.log('Initializing dashboard app...');
        
        // Initialize all components
        setupSidebarToggle();
        loadDashboardData();
        setupJournalSwitching();
        setupSearchFunctionality();
        setupProfileDropdown();
        
        console.log('Dashboard app initialized successfully');
    }
    
    function setupSidebarToggle() {
        const sidebar = document.querySelector('.sidebar');
        const openBtn = document.getElementById('openSidebar');
        const closeBtn = document.getElementById('closeSidebar');
        const main = document.querySelector('main');
        
        if (!sidebar || !openBtn || !closeBtn || !main) {
            console.error('Sidebar elements missing:', {
                sidebar: !!sidebar,
                openBtn: !!openBtn,
                closeBtn: !!closeBtn,
                main: !!main
            });
            return;
        }
        
        // Create CSS class for hidden sidebar
        if (!document.getElementById('sidebar-toggle-styles')) {
            const style = document.createElement('style');
            style.id = 'sidebar-toggle-styles';
            style.textContent = `
                .sidebar-hidden {
                    display: none !important;
                }
                .main-full-width {
                    width: 100% !important;
                    margin-left: 0 !important;
                }
                .open-sidebar-btn {
                    display: inline-block !important;
                }
                .open-sidebar-btn.hidden {
                    display: none !important;
                }
            `;
            document.head.appendChild(style);
        }
        
        function hideSidebar() {
            console.log('Hiding sidebar');
            sidebar.classList.add('sidebar-hidden');
            main.classList.add('main-full-width');
            openBtn.classList.remove('hidden');
            sidebarVisible = false;
        }
        
        function showSidebar() {
            console.log('Showing sidebar');
            sidebar.classList.remove('sidebar-hidden');
            main.classList.remove('main-full-width');
            openBtn.classList.add('hidden');
            sidebarVisible = true;
        }
        
        // Event listeners
        closeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Close button clicked');
            hideSidebar();
        });
        
        openBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Open button clicked');
            showSidebar();
        });
        
        // Initialize state
        showSidebar(); // Start with sidebar visible
        
        console.log('Sidebar toggle setup complete');
    }
    
    function loadDashboardData() {
        try {
            const entryDataEl = document.getElementById('entry-data');
            const entryMetadataEl = document.getElementById('entry-metadata');
            const activeEntryIdEl = document.getElementById('active-entry-id');
            
            if (!entryDataEl || !entryMetadataEl || !activeEntryIdEl) {
                console.warn('Dashboard data elements not found');
                return;
            }
            
            const entryData = JSON.parse(entryDataEl.textContent);
            const entryMetadata = JSON.parse(entryMetadataEl.textContent);
            const activeEntryId = activeEntryIdEl.textContent.trim();
            
            dashboardData = {
                entryData,
                entryMetadata,
                activeEntryId
            };
            
            // Initialize editor if available
            if (window.DashboardEditor && typeof window.DashboardEditor.initialize === 'function') {
                window.DashboardEditor.initialize(entryData, activeEntryId, entryMetadata);
            }
            
            console.log('Dashboard data loaded:', dashboardData);
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }
    
    function setupJournalSwitching() {
        const journalLinks = document.querySelectorAll('.journal-link');
        
        if (journalLinks.length === 0) {
            console.warn('No journal links found');
            return;
        }
        
        journalLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                if (!dashboardData) {
                    console.error('Dashboard data not available');
                    return;
                }
                
                const newId = this.getAttribute('data-id');
                const currentId = dashboardData.activeEntryId;
                
                if (newId === currentId) {
                    console.log('Same entry clicked, ignoring');
                    return;
                }
                
                console.log('Switching from entry', currentId, 'to', newId);
                
                // Update active state in sidebar
                const currentActive = document.querySelector('.journal-link.active');
                if (currentActive) {
                    currentActive.classList.remove('active');
                }
                this.classList.add('active');
                
                // Show/hide journal content
                const oldJournal = document.getElementById('journal-' + currentId);
                const newJournal = document.getElementById('journal-' + newId);
                
                if (oldJournal) {
                    oldJournal.classList.add('d-none');
                }
                if (newJournal) {
                    newJournal.classList.remove('d-none');
                }
                
                // Update header
                const titleEl = document.getElementById('currentEntryTitle');
                const lastUpdatedEl = document.getElementById('lastUpdated');
                
                if (titleEl && dashboardData.entryMetadata[newId]) {
                    titleEl.textContent = dashboardData.entryMetadata[newId].title;
                }
                
                if (lastUpdatedEl && dashboardData.entryMetadata[newId]) {
                    lastUpdatedEl.textContent = 'Last updated: ' + dashboardData.entryMetadata[newId].updated_at;
                }
                
                // Update active entry ID
                dashboardData.activeEntryId = newId;
                
                console.log('Entry switch complete');
            });
        });
        
        console.log('Journal switching setup complete for', journalLinks.length, 'links');
    }
    
    function setupSearchFunctionality() {
        const searchToggleBtn = document.getElementById('searchToggleBtn');
        const searchContainer = document.getElementById('searchContainer');
        const searchInput = document.getElementById('searchInput');
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        const entriesList = document.getElementById('recentEntries');
        const searchInfo = document.getElementById('searchInfo');
        const searchResultText = document.getElementById('searchResultText');
        
        if (!searchToggleBtn || !searchContainer || !searchInput || !clearSearchBtn) {
            console.warn('Search elements not found');
            return;
        }
        
        let searchVisible = false;
        let searchTimeout = null;
        
        // Toggle search input visibility
        function toggleSearch() {
            searchVisible = !searchVisible;
            
            if (searchVisible) {
                searchContainer.classList.remove('d-none');
                if (searchInfo) searchInfo.classList.remove('d-none');
                searchInput.focus();
                searchToggleBtn.innerHTML = '<i class="bi bi-x"></i>';
                searchToggleBtn.classList.add('active');
                searchToggleBtn.classList.remove('btn-outline-secondary');
                searchToggleBtn.classList.add('btn-secondary');
            } else {
                searchContainer.classList.add('d-none');
                if (searchInfo) searchInfo.classList.add('d-none');
                searchInput.value = '';
                searchToggleBtn.innerHTML = '<i class="bi bi-search"></i>';
                searchToggleBtn.classList.remove('active');
                searchToggleBtn.classList.add('btn-outline-secondary');
                searchToggleBtn.classList.remove('btn-secondary');
                // Reset to show all entries
                performSearch('');
            }
        }
        
        // Show loading state
        function showSearchLoading(show = true) {
            if (show) {
                searchInput.classList.add('search-loading');
                // Add a subtle indication that search is active without disabling
                searchInput.style.backgroundColor = '#f8f9fa';
                if (searchResultText) {
                    searchResultText.innerHTML = '<i class="bi bi-search me-1"></i>Searching...';
                }
            } else {
                searchInput.classList.remove('search-loading');
                // Restore normal background
                searchInput.style.backgroundColor = '';
            }
        }
        
        // Perform backend search
        function performSearch(query) {
            const url = new URL(window.location.href);
            url.searchParams.set('search', query);
            
            // Store comprehensive focus state
            const focusState = {
                wasSearchInputFocused: document.activeElement === searchInput,
                selectionStart: searchInput ? searchInput.selectionStart : 0,
                selectionEnd: searchInput ? searchInput.selectionEnd : 0,
                inputValue: searchInput ? searchInput.value : ''
            };
            
            // Show loading state (without disabling input)
            if (query.trim()) {
                showSearchLoading(true);
            }
            
            fetch(url.toString(), {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => response.json())
            .then(data => {
                updateEntriesList(data.entries, data.search_query);
                updateSearchInfo(data.entries.length, data.search_query);
                
                // Update URL without reloading page
                if (query.trim()) {
                    window.history.replaceState({}, '', url.toString());
                } else {
                    // Remove search parameter
                    url.searchParams.delete('search');
                    window.history.replaceState({}, '', url.toString());
                }
            })
            .catch(error => {
                console.error('Search error:', error);
                showSearchError();
            })
            .finally(() => {
                showSearchLoading(false);
                
                // Aggressive focus restoration
                if (focusState.wasSearchInputFocused && searchInput) {
                    // Multiple attempts to restore focus with different timing
                    const restoreFocus = () => {
                        if (document.activeElement !== searchInput) {
                            searchInput.focus();
                            // Restore selection if the value hasn't changed
                            if (searchInput.value === focusState.inputValue) {
                                searchInput.setSelectionRange(focusState.selectionStart, focusState.selectionEnd);
                            }
                        }
                    };
                    
                    // Immediate attempt
                    restoreFocus();
                    
                    // Backup attempts with different timing
                    setTimeout(restoreFocus, 0);
                    requestAnimationFrame(restoreFocus);
                    setTimeout(restoreFocus, 50);
                }
            });
        }
        
        // Update search info text
        function updateSearchInfo(count, query) {
            if (!searchResultText) return;
            
            if (query && query.trim()) {
                const resultText = count === 0 ? 'No results found' : 
                                 count === 1 ? '1 result found' : 
                                 `${count} results found`;
                searchResultText.innerHTML = `<i class="bi bi-info-circle me-1"></i>${resultText} for "${query}"`;
            } else {
                searchResultText.innerHTML = '<i class="bi bi-info-circle me-1"></i>Search in titles and content';
            }
        }
        
        // Update the entries list with search results
        function updateEntriesList(entries, searchQuery) {
            // Store focus state before DOM update
            const wasSearchInputFocused = document.activeElement === searchInput;
            const currentSelection = searchInput ? {
                start: searchInput.selectionStart,
                end: searchInput.selectionEnd,
                value: searchInput.value
            } : null;
            
            if (!entries || entries.length === 0) {
                entriesList.innerHTML = `
                    <li class="nav-item">
                        <div class="empty-state">
                            <i class="bi bi-search text-muted"></i>
                            <p class="text-muted mb-0">No entries found</p>
                            <small class="text-muted">${searchQuery ? `for "${searchQuery}"` : 'Try a different search term'}</small>
                        </div>
                    </li>
                `;
            } else {
                const entriesHTML = entries.map(entry => `
                    <li class="nav-item">
                        <a class="nav-link journal-link ${entry.is_active ? 'active' : ''}"
                           href="#"
                           data-id="${entry.id}"
                           title="${entry.title}">
                            <div class="journal-link-content">
                                <i class="bi bi-journal-text journal-icon"></i>
                                <span class="journal-title">${highlightSearchTerm(truncateText(entry.title, 20), searchQuery)}</span>
                            </div>
                        </a>
                    </li>
                `).join('');
                
                entriesList.innerHTML = entriesHTML;
                
                // Reinitialize journal switching for new elements
                if (window.setupJournalSwitching) {
                    window.setupJournalSwitching();
                }
            }
            
            // Restore focus and selection immediately after DOM update
            if (wasSearchInputFocused && searchInput && currentSelection) {
                // Use requestAnimationFrame to ensure DOM is fully updated
                requestAnimationFrame(() => {
                    searchInput.focus();
                    // Restore cursor position and selection
                    if (searchInput.value === currentSelection.value) {
                        searchInput.setSelectionRange(currentSelection.start, currentSelection.end);
                    }
                });
            }
        }
        
        // Highlight search terms in text
        function highlightSearchTerm(text, searchTerm) {
            if (!searchTerm || !searchTerm.trim()) return text;
            
            const regex = new RegExp(`(${escapeRegExp(searchTerm)})`, 'gi');
            return text.replace(regex, '<span class="search-highlight">$1</span>');
        }
        
        // Escape special regex characters
        function escapeRegExp(string) {
            return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }
        
        // Show search error
        function showSearchError() {
            entriesList.innerHTML = `
                <li class="nav-item">
                    <div class="empty-state">
                        <i class="bi bi-exclamation-triangle text-warning"></i>
                        <p class="text-muted mb-0">Search failed</p>
                        <small class="text-muted">Please try again</small>
                    </div>
                </li>
            `;
            
            if (searchResultText) {
                searchResultText.innerHTML = '<i class="bi bi-exclamation-triangle me-1"></i>Search failed';
            }
        }
        
        // Truncate text helper function
        function truncateText(text, maxLength) {
            if (text.length <= maxLength) return text;
            return text.substring(0, maxLength - 3) + '...';
        }
        
        // Debounced search function
        function debouncedSearch(query) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300); // 300ms delay
        }
        
        // Event listeners
        searchToggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleSearch();
        });
        
        clearSearchBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            searchInput.value = '';
            performSearch('');
            searchInput.focus();
        });
        
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim();
            debouncedSearch(query);
        });
        
        // Close search when clicking outside
        document.addEventListener('click', function(e) {
            if (searchVisible && !searchContainer.contains(e.target) && !searchToggleBtn.contains(e.target)) {
                toggleSearch();
            }
        });
        
        // Handle escape key
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                toggleSearch();
            }
        });
        
        // Check if page loaded with search query
        const urlParams = new URLSearchParams(window.location.search);
        const initialSearch = urlParams.get('search');
        if (initialSearch) {
            searchInput.value = initialSearch;
            toggleSearch();
        }
        
        console.log('Enhanced search functionality setup complete');
    }
    
    // Make setupJournalSwitching available globally so it can be called after search updates
    window.setupJournalSwitching = setupJournalSwitching;
    
    function setupProfileDropdown() {
        const profileToggle = document.getElementById('profileToggle');
        const profileDropdown = document.getElementById('profileDropdown');
        
        if (!profileToggle || !profileDropdown) {
            console.warn('Profile dropdown elements not found');
            return;
        }
        
        let isDropdownOpen = false;
        
        // Toggle dropdown when clicking the profile toggle
        profileToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (isDropdownOpen) {
                closeProfileDropdown();
            } else {
                openProfileDropdown();
            }
        });
        
        // Prevent dropdown from closing when clicking inside it
        profileDropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!profileToggle.contains(e.target)) {
                closeProfileDropdown();
            }
        });
        
        // Handle escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && isDropdownOpen) {
                closeProfileDropdown();
                profileToggle.focus();
            }
        });
        
        function openProfileDropdown() {
            isDropdownOpen = true;
            profileToggle.classList.add('active');
            profileDropdown.classList.add('show');
            console.log('Profile dropdown opened');
        }
        
        function closeProfileDropdown() {
            isDropdownOpen = false;
            profileToggle.classList.remove('active');
            profileDropdown.classList.remove('show');
            console.log('Profile dropdown closed');
        }
        
        console.log('Profile dropdown setup complete');
    }
    
})();