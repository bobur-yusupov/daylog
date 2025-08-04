from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from dotenv import load_dotenv
import os

load_dotenv()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("authentication.urls")),
    path("api/", include("api.urls")),
    path("", include("journal.urls")),
]

# Debug toolbar URLs - check both settings.DEBUG and environment variable
if settings.DEBUG or (hasattr(settings, 'DEBUG') and settings.DEBUG) or os.getenv("DEBUG") == "True":
    try:
        import debug_toolbar
        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        # Debug toolbar not installed, skip
        pass