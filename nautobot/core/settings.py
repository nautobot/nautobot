import os
import platform

from django.contrib.messages import constants as messages

from nautobot import __version__
from nautobot.core.settings_funcs import is_truthy, parse_redis_connection

#
# Environment setup
#

# This is used for display in the UI.
VERSION = __version__

# Hostname of the system. This is displayed in the web UI footers along with the
# version.
HOSTNAME = platform.node()

# Set the base directory two levels up (i.e. the base nautobot/ directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Set the swapable User model to the Nautobot custom User model
AUTH_USER_MODEL = "users.User"


###############################################################
# NAUTOBOT - Settings for Nautobot internals/plugins/defaults #
###############################################################

#
# Nautobot optional settings/defaults
#
ALLOWED_URL_SCHEMES = (
    "file",
    "ftp",
    "ftps",
    "http",
    "https",
    "irc",
    "mailto",
    "sftp",
    "ssh",
    "tel",
    "telnet",
    "tftp",
    "vnc",
    "xmpp",
)
BANNER_BOTTOM = ""
BANNER_LOGIN = ""
BANNER_TOP = ""

# Base directory wherein all created files (jobs, git repositories, file uploads, static files) will be stored)
NAUTOBOT_ROOT = os.getenv("NAUTOBOT_ROOT", os.path.expanduser("~/.nautobot"))

CHANGELOG_RETENTION = 90
DOCS_ROOT = os.path.join(BASE_DIR, "docs")
HIDE_RESTRICTED_UI = False

# By default, Nautobot will permit users to create duplicate prefixes and IP addresses in the global
# table (that is, those which are not assigned to any VRF). This behavior can be disabled by setting
# ENFORCE_GLOBAL_UNIQUE to True.
ENFORCE_GLOBAL_UNIQUE = False

# Exclude potentially sensitive models from wildcard view exemption. These may still be exempted
# by specifying the model individually in the EXEMPT_VIEW_PERMISSIONS configuration parameter.
EXEMPT_EXCLUDE_MODELS = (
    ("auth", "group"),
    ("users", "user"),
    ("users", "objectpermission"),
)

EXEMPT_VIEW_PERMISSIONS = []
GIT_ROOT = os.getenv("NAUTOBOT_GIT_ROOT", os.path.join(NAUTOBOT_ROOT, "git").rstrip("/"))
HTTP_PROXIES = None
JOBS_ROOT = os.getenv("NAUTOBOT_JOBS_ROOT", os.path.join(NAUTOBOT_ROOT, "jobs").rstrip("/"))
MAINTENANCE_MODE = False
MAX_PAGE_SIZE = 1000

# Metrics
METRICS_ENABLED = False

# Napalm
NAPALM_ARGS = {}
NAPALM_PASSWORD = ""
NAPALM_TIMEOUT = 30
NAPALM_USERNAME = ""

# Pagination
PAGINATE_COUNT = 50
PER_PAGE_DEFAULTS = [25, 50, 100, 250, 500, 1000]

# Plugins
PLUGINS = []
PLUGINS_CONFIG = {}

# IPv4?
PREFER_IPV4 = False

# Racks
RACK_ELEVATION_DEFAULT_UNIT_HEIGHT = 22
RACK_ELEVATION_DEFAULT_UNIT_WIDTH = 220

# Global 3rd-party authentication settings
EXTERNAL_AUTH_DEFAULT_GROUPS = []
EXTERNAL_AUTH_DEFAULT_PERMISSIONS = {}

# Remote auth backend settings
REMOTE_AUTH_AUTO_CREATE_USER = False
REMOTE_AUTH_HEADER = "HTTP_REMOTE_USER"

# Releases
RELEASE_CHECK_URL = None
RELEASE_CHECK_TIMEOUT = 24 * 3600

# SSO backend settings https://python-social-auth.readthedocs.io/en/latest/configuration/settings.html
SOCIAL_AUTH_POSTGRES_JSONFIELD = False

# Storage
STORAGE_BACKEND = None
STORAGE_CONFIG = {}

# Test runner that is aware of our use of "integration" tags and only runs
# integration tests if explicitly passed in with `nautobot-server test --tag integration`.
TEST_RUNNER = "nautobot.core.tests.runner.NautobotTestRunner"

#
# Django cryptography
#

# CRYPTOGRAPHY_BACKEND = cryptography.hazmat.backends.default_backend()
# CRYPTOGRAPHY_DIGEST = cryptography.hazmat.primitives.hashes.SHA256
CRYPTOGRAPHY_KEY = None  # Defaults to SECRET_KEY if unset
CRYPTOGRAPHY_SALT = "nautobot-cryptography"


#
# Django Prometheus
#

PROMETHEUS_EXPORT_MIGRATIONS = False


#
# Django filters
#

FILTERS_NULL_CHOICE_LABEL = "None"
FILTERS_NULL_CHOICE_VALUE = "null"


#
# Django REST framework (API)
#

REST_FRAMEWORK_VERSION = VERSION.rsplit(".", 1)[0]  # Use major.minor as API version
REST_FRAMEWORK = {
    "ALLOWED_VERSIONS": [REST_FRAMEWORK_VERSION],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "nautobot.core.api.authentication.TokenAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_METADATA_CLASS": "nautobot.core.api.metadata.BulkOperationMetadata",
    "DEFAULT_PAGINATION_CLASS": "nautobot.core.api.pagination.OptionalLimitOffsetPagination",
    "DEFAULT_PERMISSION_CLASSES": ("nautobot.core.api.authentication.TokenPermissions",),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "nautobot.core.api.renderers.FormlessBrowsableAPIRenderer",
    ),
    "DEFAULT_VERSION": REST_FRAMEWORK_VERSION,
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",
    "PAGE_SIZE": PAGINATE_COUNT,
    "SCHEMA_COERCE_METHOD_NAMES": {
        # Default mappings
        "retrieve": "read",
        "destroy": "delete",
        # Custom operations
        "bulk_destroy": "bulk_delete",
    },
    "VIEW_NAME_FUNCTION": "nautobot.utilities.api.get_view_name",
}


#
# drf_yasg (OpenAPI/Swagger)
#

SWAGGER_SETTINGS = {
    "DEFAULT_AUTO_SCHEMA_CLASS": "nautobot.utilities.custom_inspectors.NautobotSwaggerAutoSchema",
    "DEFAULT_FIELD_INSPECTORS": [
        "nautobot.utilities.custom_inspectors.StatusFieldInspector",
        "nautobot.utilities.custom_inspectors.CustomFieldsDataFieldInspector",
        "nautobot.utilities.custom_inspectors.JSONFieldInspector",
        "nautobot.utilities.custom_inspectors.NullableBooleanFieldInspector",
        "nautobot.utilities.custom_inspectors.ChoiceFieldInspector",
        "nautobot.utilities.custom_inspectors.SerializedPKRelatedFieldInspector",
        "drf_yasg.inspectors.CamelCaseJSONFilter",
        "drf_yasg.inspectors.ReferencingSerializerInspector",
        "drf_yasg.inspectors.RelatedFieldInspector",
        "drf_yasg.inspectors.ChoiceFieldInspector",
        "drf_yasg.inspectors.FileFieldInspector",
        "drf_yasg.inspectors.DictFieldInspector",
        "drf_yasg.inspectors.SerializerMethodFieldInspector",
        "drf_yasg.inspectors.SimpleFieldInspector",
        "drf_yasg.inspectors.StringDefaultFieldInspector",
    ],
    "DEFAULT_FILTER_INSPECTORS": [
        "drf_yasg.inspectors.CoreAPICompatInspector",
    ],
    "DEFAULT_INFO": "nautobot.core.urls.openapi_info",
    "DEFAULT_MODEL_DEPTH": 1,
    "DEFAULT_PAGINATOR_INSPECTORS": [
        "nautobot.utilities.custom_inspectors.NullablePaginatorInspector",
        "drf_yasg.inspectors.DjangoRestResponsePagination",
        "drf_yasg.inspectors.CoreAPICompatInspector",
    ],
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
        }
    },
    "VALIDATOR_URL": None,
}


##############################################
# DJANGO - Core settings required for Django #
##############################################

#
# Databases
#

# Only PostgresSQL is supported, so database driver is hard-coded. This can
# still be overloaded in custom settings.
# https://docs.djangoproject.com/en/stable/ref/settings/#databases
DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DATABASE", "nautobot"),
        "USER": os.getenv("NAUTOBOT_USER", ""),
        "PASSWORD": os.getenv("NAUTOBOT_PASSWORD", ""),
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),
        "PORT": os.getenv("NAUTOBOT_DB_PORT", ""),
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", 300)),
        "ENGINE": os.getenv("NAUTOBOT_DB_ENGINE", "django.db.backends.postgresql"),
    }
}

# The secret key is used to encrypt session keys and salt passwords.
SECRET_KEY = os.getenv("SECRET_KEY")

# Default overrides
ALLOWED_HOSTS = []
CSRF_TRUSTED_ORIGINS = []
DATETIME_FORMAT = "N j, Y g:i a"
INTERNAL_IPS = ("127.0.0.1", "::1")
FORCE_SCRIPT_NAME = None
LOGGING = {}
MEDIA_ROOT = os.path.join(NAUTOBOT_ROOT, "media").rstrip("/")
SESSION_FILE_PATH = None
SHORT_DATE_FORMAT = "Y-m-d"
SHORT_DATETIME_FORMAT = "Y-m-d H:i"
TIME_FORMAT = "g:i a"
TIME_ZONE = "UTC"

# Installed apps and Django plugins. Nautobot plugins will be appended here later.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "cacheops",
    "corsheaders",
    "django_filters",
    "django_jinja",
    "django_tables2",
    "django_prometheus",
    "mptt",
    "rest_framework",
    "social_django",
    "taggit",
    "timezone_field",
    "nautobot.core",
    "nautobot.circuits",
    "nautobot.dcim",
    "nautobot.ipam",
    "nautobot.extras",
    "nautobot.tenancy",
    "nautobot.users",
    "nautobot.utilities",
    "nautobot.virtualization",
    "django_rq",  # Must come after nautobot.extras to allow overriding management commands
    "drf_yasg",
    "graphene_django",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.storage",
]

# Middleware
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "nautobot.core.middleware.ExceptionHandlingMiddleware",
    "nautobot.core.middleware.RemoteUserMiddleware",
    "nautobot.core.middleware.ExternalAuthMiddleware",
    "nautobot.core.middleware.APIVersionMiddleware",
    "nautobot.core.middleware.ObjectChangeMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "nautobot.core.urls"

TEMPLATES = [
    {
        "NAME": "django",
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.media",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
                "nautobot.core.context_processors.settings_and_registry",
                "nautobot.core.context_processors.sso_auth",
            ],
        },
    },
    {
        "NAME": "jinja",
        "BACKEND": "django_jinja.backend.Jinja2",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.media",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
                "nautobot.core.context_processors.settings_and_registry",
                "nautobot.core.context_processors.sso_auth",
            ],
        },
    },
]

# Set up authentication backends
AUTHENTICATION_BACKENDS = [
    # Always check object permissions
    "nautobot.core.authentication.ObjectPermissionBackend",
]

# Internationalization
LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_TZ = True

# WSGI
WSGI_APPLICATION = "nautobot.core.wsgi.application"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
X_FRAME_OPTIONS = "SAMEORIGIN"

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(NAUTOBOT_ROOT, "static")
STATIC_URL = "static/"
STATICFILES_DIRS = (os.path.join(BASE_DIR, "project-static"),)

# Media
MEDIA_URL = "media/"

# Disable default limit of 1000 fields per request. Needed for bulk deletion of objects. (Added in Django 1.10.)
DATA_UPLOAD_MAX_NUMBER_FIELDS = None

# Messages
MESSAGE_TAGS = {
    messages.ERROR: "danger",
}

# Authentication URLs
# This is the URL route name for the login view.
LOGIN_URL = "login"

# This is the URL route name for the home page (index) view.
LOGIN_REDIRECT_URL = "home"

#
# From django-cors-headers
#

# If True, all origins will be allowed. Other settings restricting allowed origins will be ignored.
# Defaults to False. Setting this to True can be dangerous, as it allows any website to make
# cross-origin requests to yours. Generally you'll want to restrict the list of allowed origins with
# CORS_ALLOWED_ORIGINS or CORS_ALLOWED_ORIGIN_REGEXES.
CORS_ALLOW_ALL_ORIGINS = False

# A list of strings representing regexes that match Origins that are authorized to make cross-site
# HTTP requests. Defaults to [].
CORS_ALLOWED_ORIGIN_REGEXES = []

# A list of origins that are authorized to make cross-site HTTP requests. Defaults to [].
CORS_ALLOWED_ORIGINS = []

#
# GraphQL
#

GRAPHENE = {
    "SCHEMA": "nautobot.core.graphql.schema_init.schema",
    "DJANGO_CHOICE_FIELD_ENUM_V3_NAMING": True,  # any field with a name of type will break in Graphene otherwise.
}
GRAPHQL_CUSTOM_FIELD_PREFIX = "cf"
GRAPHQL_RELATIONSHIP_PREFIX = "rel"
GRAPHQL_COMPUTED_FIELD_PREFIX = "cpf"


#
# Caching
#

# The django-cacheops plugin is used to cache querysets. The built-in Django
# caching is not used.
CACHEOPS = {
    "auth.user": {"ops": "get", "timeout": 60 * 15},
    "auth.*": {"ops": ("fetch", "get")},
    "auth.permission": {"ops": "all"},
    "circuits.*": {"ops": "all"},
    "dcim.inventoryitem": None,  # MPTT models are exempt due to raw SQL
    "dcim.region": None,  # MPTT models are exempt due to raw SQL
    "dcim.rackgroup": None,  # MPTT models are exempt due to raw SQL
    "dcim.*": {"ops": "all"},
    "ipam.*": {"ops": "all"},
    "extras.*": {"ops": "all"},
    "users.*": {"ops": "all"},
    "tenancy.tenantgroup": None,  # MPTT models are exempt due to raw SQL
    "tenancy.*": {"ops": "all"},
    "virtualization.*": {"ops": "all"},
}
CACHEOPS_DEGRADE_ON_FAILURE = True
CACHEOPS_ENABLED = True
CACHEOPS_REDIS = "redis://localhost:6379/1"
CACHEOPS_DEFAULTS = {"timeout": 900}

# The django-redis cache is used to establish concurrent locks using Redis. The
# django-rq settings will use the same instance/database by default.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/0",
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": "",
        },
    }
}

#
# Django RQ (used for legacy background processesing)
#

# These defaults utilize the Django caches setting defined for django-redis.
# See: https://github.com/rq/django-rq#support-for-django-redis-and-django-redis-cache
RQ_QUEUES = {
    "default": {
        "USE_REDIS_CACHE": "default",
    },
    "check_releases": {
        "USE_REDIS_CACHE": "default",
    },
    "custom_fields": {
        "USE_REDIS_CACHE": "default",
    },
    "webhooks": {
        "USE_REDIS_CACHE": "default",
    },
}

#
# Celery (used for background processing)
#

# Celery broker URL used to tell workers where queues are located
CELERY_BROKER_URL = os.getenv("NAUTOBOT_CELERY_BROKER_URL", parse_redis_connection(redis_database=0))

# Celery results backend URL to tell workers where to publish task results
CELERY_RESULT_BACKEND = os.getenv("NAUTOBOT_CELERY_RESULT_BACKEND", parse_redis_connection(redis_database=0))

# Instruct celery to report the started status of a job, instead of just `pending`, `finished`, or `failed`
CELERY_TASK_TRACK_STARTED = True

# Global task time limits (seconds)
# Exceeding the soft limit will result in a SoftTimeLimitExceeded exception,
# while exceeding the hard limit will result in a SIGKILL.
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("NAUTOBOT_CELERY_TASK_SOFT_TIME_LIMIT", 5 * 60))
CELERY_TASK_TIME_LIMIT = int(os.getenv("NAUTOBOT_CELERY_TASK_TIME_LIMIT", 10 * 60))

# These settings define the custom nautobot serialization encoding as an accepted data encoding format
# and register that format for task input and result serialization
CELERY_ACCEPT_CONTENT = ["nautobot_json"]
CELERY_RESULT_ACCEPT_CONTENT = ["nautobot_json"]
CELERY_TASK_SERIALIZER = "nautobot_json"
CELERY_RESULT_SERIALIZER = "nautobot_json"
