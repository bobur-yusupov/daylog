# Import all views to maintain backward compatibility
from .dashboard_views import DashboardView
from .entry_views import (
    JournalListView,
    JournalDetailView,
    SharedJournalView,
    GenerateShareTokenView,
    RevokeShareTokenView,
)
from .create_views import NewJournalView
from .edit_views import EditJournalView
from .tag_views import TagAutocompleteView, TagListView, TagUpdateView, TagDeleteView

__all__ = [
    "DashboardView",
    "JournalListView",
    "JournalDetailView",
    "SharedJournalView",
    "GenerateShareTokenView",
    "RevokeShareTokenView",
    "NewJournalView",
    "EditJournalView",
    "TagAutocompleteView",
    "TagListView",
    "TagUpdateView",
    "TagDeleteView",
]
