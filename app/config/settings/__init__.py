import os

# Get the environment from environment variable, default to 'dev'
environment = os.getenv("DJANGO_ENVIRONMENT", "dev")

if environment == "production":
    from .production import *  # noqa: F403,F401
else:
    # For 'dev' or any other environment, use dev settings.
    from .dev import *  # noqa: F403,F401
