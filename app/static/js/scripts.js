$(document).ready(function() {
    const $sidebar = $('.sidebar');
    const $closeBtn = $('#closeSidebar');
    const $openBtn = $('#openSidebar');
    const $mainContent = $('main');

    if ($sidebar.length && $closeBtn.length && $openBtn.length && $mainContent.length) {
        $closeBtn.on('click', function() {
            $sidebar.addClass('collapsed');
            $mainContent.removeClass('main-normal').addClass('main-expanded');
        });

        $openBtn.on('click', function() {
            $sidebar.removeClass('collapsed');
            $mainContent.removeClass('main-expanded').addClass('main-normal');
        });
    };

    $('#recentEntries').on('click', '.journal-link', function(e) {
        e.preventDefault();
        const journalId = $(this).data('id');

        // Hide all, show clicked journal
        $('.journal-entry').addClass('d-none');
        $('#journal-' + journalId).removeClass('d-none');

        // Highlight active sidebar link
        $('#recentEntries .journal-link').removeClass('active');
        $(this).addClass('active');
    });
});