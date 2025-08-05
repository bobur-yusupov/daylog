from django.urls import path
from .views import dashboard, NewJournalView

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("new/", NewJournalView.as_view(), name="new_entry"),
]
