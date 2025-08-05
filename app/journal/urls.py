from django.urls import path
from .views import (
    DashboardView, NewJournalView, EditJournalView, JournalListView, 
    JournalDetailView, TagAutocompleteView
)

app_name = 'journal'

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("new/", NewJournalView.as_view(), name="new_entry"),
    path("list/", JournalListView.as_view(), name="entry_list"),
    path("entry/<uuid:entry_id>/", JournalDetailView.as_view(), name="entry_detail"),
    path("entry/<uuid:entry_id>/edit/", EditJournalView.as_view(), name="edit_entry"),
    path("api/tags/autocomplete/", TagAutocompleteView.as_view(), name="tag_autocomplete"),
]
