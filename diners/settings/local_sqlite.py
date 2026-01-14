from .base import *
from diners.utils.mock_graphql import MockGraphqlService

# Local SQLite DB for quick testing
DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Use a local/mock GraphQL service to avoid external calls
GRAPHQL_SERVICE = MockGraphqlService()

# Safer defaults for local dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
}

# Ensure session security doesn't make running locally awkward
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Note: set DJANGO_SETTINGS_MODULE=diners.settings.local_sqlite to use this config
