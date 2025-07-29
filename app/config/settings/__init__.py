import os

# Get the environment from environment variable, default to 'dev'
environment = os.getenv('DJANGO_ENVIRONMENT', 'dev')

if environment == 'production':
    from .production import *
else:
    # For 'dev' or any other environment, use dev settings.
    from .dev import *