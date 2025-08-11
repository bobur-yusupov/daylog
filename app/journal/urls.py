from django.urls import path
from .views import (
    DashboardView, NewJournalView, EditJournalView, JournalListView, 
    JournalDetailView, TagAutocompleteView
)

app_name = 'journal'

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("entry/new/", NewJournalView.as_view(), name="new_entry"),
    path("entry/list/", JournalListView.as_view(), name="entry_list"),
    path("entry/j/<uuid:entry_id>/", JournalDetailView.as_view(), name="entry_detail"),
    path("entry/e/<uuid:entry_id>/", EditJournalView.as_view(), name="edit_entry"),
    path("api/tags/autocomplete/", TagAutocompleteView.as_view(), name="tag_autocomplete"),
]
