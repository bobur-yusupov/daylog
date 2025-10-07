from .base import *  # noqa: F403,F401
import socket
import os

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]  # Allow all hosts in development

INSTALLED_APPS += [  # noqa: F405
    "drf_spectacular",
    "debug_toolbar",
]

MIDDLEWARE += [  # noqa: F405
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
        docker_gateway_ips = [ip[:-1] + "1" for ip in ips if "." in ip]

        for ip in docker_gateway_ips:
            if ip not in INTERNAL_IPS:
                INTERNAL_IPS.append(ip)

        if "host.docker.internal" not in INTERNAL_IPS:
            INTERNAL_IPS.append("host.docker.internal")

    except Exception:
        pass

# Debug toolbar configuration for Docker
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    "SHOW_COLLAPSED": False,
}

# Show all SQL queries in debug mode
if DEBUG:
    DEBUG_TOOLBAR_PANELS = [
        "debug_toolbar.panels.versions.VersionsPanel",
        "debug_toolbar.panels.timer.TimerPanel",
        "debug_toolbar.panels.settings.SettingsPanel",
        "debug_toolbar.panels.headers.HeadersPanel",
        "debug_toolbar.panels.request.RequestPanel",
        "debug_toolbar.panels.sql.SQLPanel",
        "debug_toolbar.panels.staticfiles.StaticFilesPanel",
        "debug_toolbar.panels.templates.TemplatesPanel",
        "debug_toolbar.panels.cache.CachePanel",
        "debug_toolbar.panels.signals.SignalsPanel",
        "debug_toolbar.panels.logging.LoggingPanel",
        "debug_toolbar.panels.redirects.RedirectsPanel",
        "debug_toolbar.panels.profiling.ProfilingPanel",
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
