from .base import *
from diners.utils.mock_graphql import MockGraphqlService

# Local SQLite DB for quick testing
DEBUG = False
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Use a local/mock GraphQL service to avoid external calls
GRAPHQL_SERVICE = MockGraphqlService()

# Limit installed apps and middleware for local/offline development to avoid 3rd party import errors
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'debug_toolbar',
    'diners',
    'diners.utils',
    'diners.apps.core',
    'diners.apps.people.apps.PeopleConfig',
    'diners.apps.reservation.apps.ReservationConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Debug toolbar config
INTERNAL_IPS = ['127.0.0.1', '::1']
DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': lambda request: True, 'IS_RUNNING_TESTS': False}

# Ensure tasks run locally (synchronously) so we can test Celery-backed flows without Redis
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES_EXCEPTIONS = True

# Safer defaults for local dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
}

# Ensure session security doesn't make running locally awkward
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Note: set DJANGO_SETTINGS_MODULE=diners.settings.local_sqlite to use this config
