from datetime import timedelta, time
from pathlib import Path

from decouple import config
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from diners.utils.graphql import GraphqlService

BASE_DIR = Path(__file__).resolve().parent.parent.parent

VENV_PATH = BASE_DIR.parent

STATICFILES_DIRS = [BASE_DIR / 'static']

STATIC_ROOT = VENV_PATH / 'static_root'
MEDIA_ROOT = VENV_PATH / 'media'

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

SECRET_KEY = config('SECRET_KEY')

SITE_ID = 1

INSTALLED_APPS = [
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_filters',

    'import_export',
    'widget_tweaks',

    'session_security',
    'preventconcurrentlogins',
    'django_extensions',
    'axes',
    'safety_mix',

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
    'session_security.middleware.SessionSecurityMiddleware',
    'preventconcurrentlogins.middleware.PreventConcurrentLoginsMiddleware',
    'axes.middleware.AxesMiddleware',
    'safety_mix.middleware.ExtLogMiddleware'
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend'
]

ROOT_URLCONF = 'diners.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'diners.wsgi.application'

LOCALE_PATHS = (
    (BASE_DIR / 'locale'),
    (BASE_DIR / 'locale/admin/locale'),
    (BASE_DIR / 'locale/axes/locale'),
    (BASE_DIR / 'locale/session_security/locale'),
)

LANGUAGES = [
    ('es', _('Spanish')),
    ('en', _('English')),
]

LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/Havana'

USE_I18N = True

USE_L10N = True

USE_TZ = False

LOGIN_URL = reverse_lazy('admin:login')

LOGIN_REDIRECT_URL = '/admin/'

LOGOUT_REDIRECT_URL = reverse_lazy('admin:login')

MIN_NUMBER_TYPE_DISHES = 1

MAX_NUMBER_TYPE_DISHES = 11

MIN_NUMBER_ID_PERSON = 1

MAX_NUMBER_ID_PERSON = 10000

IMPORT_EXPORT_USE_TRANSACTIONS = True

# safety_mix stuff
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SESSION_SECURITY_WARN_AFTER = 540

SESSION_SECURITY_EXPIRE_AFTER = 600

# AXES_ONLY_USER_FAILURES = True

AXES_COOLOFF_TIME = timedelta(minutes=5)

AXES_LOCKOUT_TEMPLATE = 'safety_mix/lockout.html'

AUTH_USER_MODEL = 'people.User'

TIME_INPUT_FORMATS = [
    '%I:%M %p',  # 6:22 PM
    '%I %p',  # 6 PM
    '%H:%M:%S',  # '14:30:59'
    '%H:%M:%S.%f',  # '14:30:59.000200'
    '%H:%M',  # '14:30'
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LIST_POSITIONS_PAY_WEEKEND = []

GRAPHQL_SERVICE = GraphqlService()

CANT_TUPLE_TO_SHOW = 20
