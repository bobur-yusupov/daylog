import os

# Get the environment from environment variable, default to 'dev'
environment = os.getenv('DJANGO_ENVIRONMENT', 'dev')

if environment == 'production':
    from .production import *
elif environment == 'dev':
    from .dev import *
else:
    # Default to dev settings
    from .dev import *