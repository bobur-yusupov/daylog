// Dashboard Sidebar Functionality
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.querySelector('.sidebar');
    const closeBtn = document.getElementById('closeSidebar');
    const openBtn = document.getElementById('openSidebar');
    const mainContent = document.querySelector('main');

    if (closeBtn && openBtn && sidebar && mainContent) {
        // Close sidebar
        closeBtn.addEventListener('click', function() {
            sidebar.classList.add('collapsed');
            mainContent.classList.remove('main-normal');
            mainContent.classList.add('main-expanded');
        });

        // Open sidebar
        openBtn.addEventListener('click', function() {
            sidebar.classList.remove('collapsed');
            mainContent.classList.remove('main-expanded');
            mainContent.classList.add('main-normal');
        });
    }
});