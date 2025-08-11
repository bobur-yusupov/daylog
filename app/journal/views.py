# Import all views from the views module for backward compatibility
# This allows the URLs to continue working while maintaining a cleaner structure
from .views import (
    DashboardView,
    JournalListView, 
    JournalDetailView,
    NewJournalView,
    EditJournalView,
    TagAutocompleteView,
)