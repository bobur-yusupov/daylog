# Import all views to maintain backward compatibility
from .dashboard_views import DashboardView
from .entry_views import JournalListView, JournalDetailView
from .create_views import NewJournalView
from .edit_views import EditJournalView
from .tag_views import TagAutocompleteView

__all__ = [
    "DashboardView",
    "JournalListView",
    "JournalDetailView",
    "NewJournalView",
    "EditJournalView",
    "TagAutocompleteView",
]
