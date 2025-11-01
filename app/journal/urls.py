from django.urls import path
from .views import (
    DashboardView,
    NewJournalView,
    JournalDetailView,
    JournalListView,
    EditJournalView,
    TagAutocompleteView,
    TagListView,
    TagUpdateView,
    TagDeleteView,
    GenerateShareTokenView,
    RevokeShareTokenView,
)

app_name = "journal"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("new/", NewJournalView.as_view(), name="new_entry"),
    path("entries/", JournalListView.as_view(), name="entry_list"),
    path("entry/<uuid:entry_id>/", JournalDetailView.as_view(), name="entry_detail"),
    path("entry/<uuid:entry_id>/dashboard/", DashboardView.as_view(), name="dashboard_with_entry"),
    path("entry/<uuid:entry_id>/edit/", EditJournalView.as_view(), name="edit_entry"),
    path(
        "entry/<uuid:entry_id>/share/generate/",
        GenerateShareTokenView.as_view(),
        name="generate_share_token",
    ),
    path(
        "entry/<uuid:entry_id>/share/revoke/",
        RevokeShareTokenView.as_view(),
        name="revoke_share_token",
    ),
    path("tags/", TagListView.as_view(), name="tag_list"),
    path("tags/autocomplete/", TagAutocompleteView.as_view(), name="tag_autocomplete"),
    path("tags/<uuid:tag_id>/edit/", TagUpdateView.as_view(), name="tag_edit"),
    path("tags/<uuid:tag_id>/delete/", TagDeleteView.as_view(), name="tag_delete"),
]
