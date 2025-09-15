from django.urls import path
from .views import (
    DashboardView,
    NewJournalView,
    EditJournalView,
    JournalListView,
    JournalDetailView,
    TagAutocompleteView,
    TagListView,
    TagUpdateView,
    TagDeleteView,
)

app_name = "journal"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("entry/new/", NewJournalView.as_view(), name="new_entry"),
    path("entry/list/", JournalListView.as_view(), name="entry_list"),
    path("entry/<uuid:entry_id>/edit/", EditJournalView.as_view(), name="edit_entry"),
    path("entry/<uuid:entry_id>/", JournalDetailView.as_view(), name="entry_detail"),
    path("tags/autocomplete/", TagAutocompleteView.as_view(), name="tag_autocomplete"),
    path("tags/list/", TagListView.as_view(), name="tag_list"),
    path("tags/update/<str:pk>/", TagUpdateView.as_view(), name="tag_update"),
    path("tags/delete/<str:pk>/", TagDeleteView.as_view(), name="tag_delete"),
]
