import os
import socket

from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured

try:
    import configuration
except ImportError:
    raise ImproperlyConfigured("Configuration file is not present. Please define netbox/netbox/configuration.py per "
                               "the documentation.")


# Import local configuration
for setting in ['ALLOWED_HOSTS', 'DATABASE', 'SECRET_KEY']:
    try:
        globals()[setting] = getattr(configuration, setting)
    except AttributeError:
        raise ImproperlyConfigured("Mandatory setting {} is missing from configuration.py. Please define it per the "
                                   "documentation.".format(setting))

# Default configurations
ADMINS = getattr(configuration, 'ADMINS', [])
CSRF_TRUSTED_ORIGINS = getattr(configuration, 'CSRF_TRUSTED_ORIGINS', [])
DEBUG = getattr(configuration, 'DEBUG', False)
EMAIL = getattr(configuration, 'EMAIL', {})
LOGIN_REQUIRED = getattr(configuration, 'LOGIN_REQUIRED', False)
MAINTENANCE_MODE = getattr(configuration, 'MAINTENANCE_MODE', False)
PAGINATE_COUNT = getattr(configuration, 'PAGINATE_COUNT', 50)
NETBOX_USERNAME = getattr(configuration, 'NETBOX_USERNAME', '')
NETBOX_PASSWORD = getattr(configuration, 'NETBOX_PASSWORD', '')
TIME_ZONE = getattr(configuration, 'TIME_ZONE', 'UTC')


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database
configuration.DATABASE.update({'ENGINE': 'django.db.backends.postgresql'})
DATABASES = {
    'default': configuration.DATABASE,
}

# Email
EMAIL_HOST = EMAIL.get('SERVER')
EMAIL_PORT = EMAIL.get('PORT', 25)
EMAIL_HOST_USER = EMAIL.get('USERNAME')
EMAIL_HOST_PASSWORD = EMAIL.get('PASSWORD')
EMAIL_TIMEOUT = EMAIL.get('TIMEOUT', 10)
SERVER_EMAIL = EMAIL.get('FROM_EMAIL')
EMAIL_SUBJECT_PREFIX = '[NetBox] '

# Installed applications
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'debug_toolbar',
    'django_extensions',
    'django_tables2',
    'rest_framework',
    'rest_framework_swagger',
    'circuits',
    'dcim',
    'ipam',
    'extras',
    'secrets',
    'users',
    'utilities',
)

# Middleware
MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'utilities.middleware.LoginRequiredMiddleware',
)

ROOT_URLCONF = 'netbox.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR + '/templates/'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'utilities.context_processors.settings',
                'django.core.context_processors.request',
            ],
        },
    },
]

# WSGI
WSGI_APPLICATION = 'netbox.wsgi.application'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/
STATIC_ROOT = BASE_DIR + '/static/'
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "project-static"),
)

# Messages
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}

# Authentication URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_URL = '/logout/'

# Default time formats
DATE_FORMAT = 'N j, Y'
SHORT_DATE_FORMAT = 'Y-m-d'
TIME_FORMAT = 'g:i:s a'
SHORT_TIME_FORMAT = 'H:i:s'
DATETIME_FORMAT = 'N j, Y \a\t g:i a'
SHORT_DATETIME_FORMAT = 'Y-m-d H:i'

# Secrets
SECRETS_MIN_PUBKEY_SIZE = 2048

# Django REST framework
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',)
}

try:
    HOSTNAME = socket.gethostname()
except:
    HOSTNAME = 'localhost'
