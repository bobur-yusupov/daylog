from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views.journal_views import TagViewSet, JournalEntryViewSet

app_name = "api"

# Create router for ViewSets
router = DefaultRouter()
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'entries', JournalEntryViewSet, basename='journalentry')

# Authentication API endpoints using class-based views
auth_patterns = [
    path("register/", views.RegisterAPIView.as_view(), name="register"),
    path("login/", views.LoginAPIView.as_view(), name="login"),
    path("logout/", views.LogoutAPIView.as_view(), name="logout"),
]

urlpatterns = [
    path("auth/", include(auth_patterns)),
    path("", include(router.urls)),
]
