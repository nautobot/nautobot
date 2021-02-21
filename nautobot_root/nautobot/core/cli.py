"""
Utilities and primitives for the `nautobot-server` CLI command.
"""

import os
import warnings

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management.utils import get_random_secret_key
from django.core.validators import URLValidator
from jinja2 import Template

from nautobot.extras.plugins.utils import load_plugins, get_sso_backend_name
from .runner import run_app


# Default file location for the generated config emitted by `init`
DEFAULT_CONFIG_PATH = "~/.nautobot/nautobot_config.py"

# Default settings to use when building the config
DEFAULT_SETTINGS = "nautobot.core.settings"

# Name of the environment variable used to specify path of config
SETTINGS_ENVVAR = "NAUTOBOT_CONFIG"

# Base directory for this module
BASE_DIR = os.path.dirname(__file__)

# File path of template used to generate config emitted by `init`
CONFIG_TEMPLATE = os.path.join(BASE_DIR, "templates/nautobot_config.py.j2")


def main():
    """
    The main server CLI command that replaces `manage.py` and allows a
    configuration file to be passed in.

    How this works:

    - Process CLI args
    - Load default settings
    - Read config file from path
    - Overlay config settings on top of default settings
    - Overlay special/conditional settings (see `_configure_settings`)
    """
    run_app(
        project='nautobot',
        default_config_path=DEFAULT_CONFIG_PATH,
        default_settings=DEFAULT_SETTINGS,
        settings_initializer=generate_settings,
        settings_envvar=SETTINGS_ENVVAR,
        initializer=_configure_settings,  # Called after defaults
    )


def generate_settings(config_template=CONFIG_TEMPLATE, **kwargs):
    """
    This command is ran when `default_config_path` doesn't exist, or `init` is
    ran and returns a string representing the default data to put into the
    settings file.
    """
    secret_key = get_random_secret_key()

    with open(config_template) as fh:
        config = Template(fh.read())

    return config.render(secret_key=secret_key)


def _configure_settings(config):
    """
    Callback for processing conditional or special purpose settings.

    Any specially prepared settings will be handled here, such as loading
    plugins, enabling social auth, etc.

    This is intended to be called by `run_app` and should not be invoked
    directly.

    :param config:
        A dictionary of `config_path`, `project`, `settings`

    Example::

        {
            'project': 'nautobot',
            'config_path': '/path/to/nautobot_config.py',
            'settings': <LazySettings "nautobot_config">
        }
    """

    settings = config['settings']

    # Include the config path to the settings to align with builtin
    # `settings.SETTINGS_MODULE`. Useful for debugging correct config path.
    settings.SETTINGS_PATH = config['config_path']

    #
    # Databases
    #

    # If metrics are enabled and postgres is the backend, set the driver to the
    # one provided by django-prometheous.
    if settings.METRICS_ENABLED and 'postgres' in settings.DATABASES['default']['ENGINE']:
        settings.DATABASES['default']['ENGINE'] = 'django_prometheus.db.backends.postgresql'

    #
    # Pagination
    #

    if settings.PAGINATE_COUNT not in settings.PER_PAGE_DEFAULTS:
        settings.PER_PAGE_DEFAULTS.append(settings.PAGINATE_COUNT)
        settings.PER_PAGE_DEFAULTS = sorted(settings.PER_PAGE_DEFAULTS)

    #
    # Email
    #

    # FIXME(jathan): Consider ripping this out entirely. Each of these are Django
    # core settings that are being wrapped in this custom `EMAIL` setting. For now,
    # if `EMAIL` is set, then this will be processed, otherwise these EMAIL_*
    # variables will just pass through from settings untouched (per Django
    # settings)
    if settings.EMAIL:
        settings.EMAIL_HOST = settings.EMAIL.get('SERVER')
        settings.EMAIL_HOST_USER = settings.EMAIL.get('USERNAME')
        settings.EMAIL_HOST_PASSWORD = settings.EMAIL.get('PASSWORD')
        settings.EMAIL_PORT = settings.EMAIL.get('PORT', 25)
        settings.EMAIL_SSL_CERTFILE = settings.EMAIL.get('SSL_CERTFILE')
        settings.EMAIL_SSL_KEYFILE = settings.EMAIL.get('SSL_KEYFILE')
        settings.EMAIL_SUBJECT_PREFIX = '[Nautobot] '
        settings.EMAIL_USE_SSL = settings.EMAIL.get('USE_SSL', False)
        settings.EMAIL_USE_TLS = settings.EMAIL.get('USE_TLS', False)
        settings.EMAIL_TIMEOUT = settings.EMAIL.get('TIMEOUT', 10)
        settings.SERVER_EMAIL = settings.EMAIL.get('FROM_EMAIL')

    #
    # Authentication
    #

    # FIXME(jathan): This is just here as an interim validation check, to be
    # replaced in a future update when all other validations hard-coded here in
    # settings are moved to use the Django system check framework.
    if 'nautobot.core.authentication.ObjectPermissionBackend' not in settings.AUTHENTICATION_BACKENDS:
        raise ImproperlyConfigured(
            "nautobot.core.authentication.ObjectPermissionBackend must be defined in "
            "'AUTHENTICATION_BACKENDS'"
        )

    #
    # Releases
    #

    # Validate update repo URL and timeout
    if settings.RELEASE_CHECK_URL:
        try:
            URLValidator(settings.RELEASE_CHECK_URL)
        except ValidationError:
            raise ImproperlyConfigured(
                "RELEASE_CHECK_URL must be a valid API URL. Example: "
                "https://api.github.com/repos/nautobot/nautobot"
            )

    # FIXME(jathan): Why is this enforced here? This would be better enforced in the core.
    # Enforce a minimum cache timeout for update checks
    if settings.RELEASE_CHECK_TIMEOUT < 3600:
        raise ImproperlyConfigured("RELEASE_CHECK_TIMEOUT has to be at least 3600 seconds (1 hour)")

    #
    # Media storage
    #

    if settings.STORAGE_BACKEND is not None:
        settings.DEFAULT_FILE_STORAGE = settings.STORAGE_BACKEND

        # django-storages
        if settings.STORAGE_BACKEND.startswith('storages.'):

            try:
                import storages.utils
            except ModuleNotFoundError as e:
                if getattr(e, 'name') == 'storages':
                    raise ImproperlyConfigured(
                        f"STORAGE_BACKEND is set to {STORAGE_BACKEND} but django-storages is not present. It can be "
                        f"installed by running 'pip install django-storages'."
                    )
                raise e

            # Monkey-patch django-storages to fetch settings from STORAGE_CONFIG
            def _setting(name, default=None):
                if name in settings.STORAGE_CONFIG:
                    return settings.STORAGE_CONFIG[name]
                return globals().get(name, default)
            storages.utils.setting = _setting

    if settings.STORAGE_CONFIG and settings.STORAGE_BACKEND is None:
        warnings.warn(
            "STORAGE_CONFIG has been set in settings but STORAGE_BACKEND is not defined. STORAGE_CONFIG will be "
            "ignored."
        )

    #
    # Redis
    #

    # Background task queuing
    if 'tasks' not in settings.REDIS:
        raise ImproperlyConfigured(
            "REDIS section in settings is missing the 'tasks' subsection."
        )
    settings.TASKS_REDIS = settings.REDIS['tasks']
    settings.TASKS_REDIS_HOST = settings.TASKS_REDIS.get('HOST', 'localhost')
    settings.TASKS_REDIS_PORT = settings.TASKS_REDIS.get('PORT', 6379)
    settings.TASKS_REDIS_SENTINELS = settings.TASKS_REDIS.get('SENTINELS', [])
    settings.TASKS_REDIS_USING_SENTINEL = all([
        isinstance(settings.TASKS_REDIS_SENTINELS, (list, tuple)),
        len(settings.TASKS_REDIS_SENTINELS) > 0
    ])
    settings.TASKS_REDIS_SENTINEL_SERVICE = settings.TASKS_REDIS.get('SENTINEL_SERVICE', 'default')
    settings.TASKS_REDIS_SENTINEL_TIMEOUT = settings.TASKS_REDIS.get('SENTINEL_TIMEOUT', 10)
    settings.TASKS_REDIS_PASSWORD = settings.TASKS_REDIS.get('PASSWORD', '')
    settings.TASKS_REDIS_DATABASE = settings.TASKS_REDIS.get('DATABASE', 0)
    settings.TASKS_REDIS_SSL = settings.TASKS_REDIS.get('SSL', False)

    # Caching
    if 'caching' not in settings.REDIS:
        raise ImproperlyConfigured(
            "REDIS section in settings is missing caching subsection."
        )
    settings.CACHING_REDIS = settings.REDIS['caching']
    settings.CACHING_REDIS_HOST = settings.CACHING_REDIS.get('HOST', 'localhost')
    settings.CACHING_REDIS_PORT = settings.CACHING_REDIS.get('PORT', 6379)
    settings.CACHING_REDIS_SENTINELS = settings.CACHING_REDIS.get('SENTINELS', [])
    settings.CACHING_REDIS_USING_SENTINEL = all([
        isinstance(settings.CACHING_REDIS_SENTINELS, (list, tuple)),
        len(settings.CACHING_REDIS_SENTINELS) > 0
    ])
    settings.CACHING_REDIS_SENTINEL_SERVICE = settings.CACHING_REDIS.get('SENTINEL_SERVICE', 'default')
    settings.CACHING_REDIS_PASSWORD = settings.CACHING_REDIS.get('PASSWORD', '')
    settings.CACHING_REDIS_DATABASE = settings.CACHING_REDIS.get('DATABASE', 0)
    settings.CACHING_REDIS_SSL = settings.CACHING_REDIS.get('SSL', False)

    #
    # Sessions
    #

    if settings.LOGIN_TIMEOUT is not None:
        # Django default is 1209600 seconds (14 days)
        settings.SESSION_COOKIE_AGE = settings.LOGIN_TIMEOUT
    if settings.SESSION_FILE_PATH is not None:
        settings.SESSION_ENGINE = 'django.contrib.sessions.backends.file'

    #
    # Caching
    #
    if settings.CACHING_REDIS_USING_SENTINEL:
        settings.CACHEOPS_SENTINEL = {
            'locations': settings.CACHING_REDIS_SENTINELS,
            'service_name': settings.CACHING_REDIS_SENTINEL_SERVICE,
            'db': settings.CACHING_REDIS_DATABASE,
        }
    else:
        if settings.CACHING_REDIS_SSL:
            settings.REDIS_CACHE_CON_STRING = 'rediss://'
        else:
            settings.REDIS_CACHE_CON_STRING = 'redis://'

        if settings.CACHING_REDIS_PASSWORD:
            settings.REDIS_CACHE_CON_STRING = '{}:{}@'.format(
                settings.REDIS_CACHE_CON_STRING,
                settings.CACHING_REDIS_PASSWORD
            )

        settings.REDIS_CACHE_CON_STRING = '{}{}:{}/{}'.format(
            settings.REDIS_CACHE_CON_STRING,
            settings.CACHING_REDIS_HOST,
            settings.CACHING_REDIS_PORT,
            settings.CACHING_REDIS_DATABASE
        )
        settings.CACHEOPS_REDIS = settings.REDIS_CACHE_CON_STRING

    if not settings.CACHE_TIMEOUT:
        settings.CACHEOPS_ENABLED = False
    else:
        settings.CACHEOPS_ENABLED = True

    settings.CACHEOPS_DEFAULTS = {
        'timeout': settings.CACHE_TIMEOUT
    }

    #
    # Django RQ (Webhooks backend)
    #
    if settings.TASKS_REDIS_USING_SENTINEL:
        settings.RQ_PARAMS = {
            'SENTINELS': settings.TASKS_REDIS_SENTINELS,
            'MASTER_NAME': settings.TASKS_REDIS_SENTINEL_SERVICE,
            'DB': settings.TASKS_REDIS_DATABASE,
            'PASSWORD': settings.TASKS_REDIS_PASSWORD,
            'SOCKET_TIMEOUT': None,
            'CONNECTION_KWARGS': {
                'socket_connect_timeout': settings.TASKS_REDIS_SENTINEL_TIMEOUT
            },
        }
    else:
        settings.RQ_PARAMS = {
            'HOST': settings.TASKS_REDIS_HOST,
            'PORT': settings.TASKS_REDIS_PORT,
            'DB': settings.TASKS_REDIS_DATABASE,
            'PASSWORD': settings.TASKS_REDIS_PASSWORD,
            'SSL': settings.TASKS_REDIS_SSL,
            'DEFAULT_TIMEOUT': settings.RQ_DEFAULT_TIMEOUT,
        }

    settings.RQ_QUEUES = {
        'default': settings.RQ_PARAMS,  # Webhooks
        'check_releases': settings.RQ_PARAMS,
    }

    #
    # SSO
    #

    # If social auth is toggled, inject the appropriate settings
    if settings.SOCIAL_AUTH_ENABLED:
        settings.INSTALLED_APPS.append("social_django")
        settings.AUTHENTICATION_BACKENDS.insert(0, settings.SOCIAL_AUTH_MODULE)
        backend_name = get_sso_backend_name(settings.SOCIAL_AUTH_MODULE)
        settings.LOGIN_URL = '/{}login/{}/'.format(settings.BASE_PATH, backend_name)

    #
    # Plugins
    #

    # Process the plugins and manipulate the specified config settings that are
    # passed in.
    load_plugins(
        settings.PLUGINS,
        settings.INSTALLED_APPS,
        settings.PLUGINS_CONFIG,
        settings.VERSION,
        settings.MIDDLEWARE,
        settings.CACHEOPS
    )
