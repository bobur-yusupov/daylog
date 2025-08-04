from .base import *
import socket

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]  # Allow all hosts in development

INSTALLED_APPS += [
    "drf_spectacular",
    "debug_toolbar",
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# Docker-compatible INTERNAL_IPS configuration
INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

# Add Docker gateway IP for debug toolbar to work in containers
if DEBUG:
    try:
        # Get the current container's IP
        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
        INTERNAL_IPS += [ip[:-1] + "1" for ip in ips if "." in ip]
        
        # Add common Docker network gateway IPs
        INTERNAL_IPS += [
            "172.17.0.1",    # Default Docker bridge
            "172.18.0.1",    # Docker Compose networks
            "172.19.0.1",
            "172.20.0.1",
            "172.21.0.1",
            "172.22.0.1",
            "172.23.0.1",
            "172.24.0.1",
            "10.0.2.2",      # VirtualBox
            "192.168.1.1",   # Common home router
            "192.168.0.1",   # Common home router
        ]
        
        # Add host.docker.internal for Docker Desktop
        INTERNAL_IPS.append("host.docker.internal")
        
    except Exception as e:
        # Fallback if socket operations fail
        INTERNAL_IPS += ["172.17.0.1", "10.0.2.2"]

# Debug toolbar configuration for Docker
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    'SHOW_COLLAPSED': False,
}

# Show all SQL queries in debug mode
if DEBUG:
    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
    ]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Daylog API",
    "DESCRIPTION": "API documentation for Daylog application",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT"),
    }
}
