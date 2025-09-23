from .base import *  # noqa: F403,F401
import os

DEBUG = False

# Allow environment variable to specify multiple hosts
ALLOWED_HOSTS = [
    "*",
]

MIDDLEWARE += [  # noqa: F405
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

# Use the newer STORAGES setting for Django 4.2+
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
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
