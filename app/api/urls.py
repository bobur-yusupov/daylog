from django.urls import path, include
from . import views

app_name = 'api'

# Authentication API endpoints using class-based views
auth_patterns = [
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
]

urlpatterns = [
    path('auth/', include(auth_patterns)),
    # Future API endpoints will be added here
    # path('entries/', include('api.entries_urls')),
    # path('tags/', include('api.tags_urls')),
]
