import os
import platform
import re
import sys

from django.contrib.messages import constants as messages
import django.forms

from nautobot import __version__
from nautobot.core.settings_funcs import is_truthy, parse_redis_connection  # noqa: F401

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

# Set the default AutoField for 3rd party apps
# N.B. Ideally this would be a `UUIDField`, but due to Django restrictions
#      we can’t do that yet
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


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

# Base directory wherein all created files (jobs, git repositories, file uploads, static files) will be stored)
NAUTOBOT_ROOT = os.getenv("NAUTOBOT_ROOT", os.path.expanduser("~/.nautobot"))

# By default, Nautobot will permit users to create duplicate prefixes and IP addresses in the global
# table (that is, those which are not assigned to any VRF). This behavior can be disabled by setting
# ENFORCE_GLOBAL_UNIQUE to True.
ENFORCE_GLOBAL_UNIQUE = is_truthy(os.getenv("NAUTOBOT_ENFORCE_GLOBAL_UNIQUE", "False"))

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

# Log Nautobot deprecation warnings. Note that this setting is ignored (deprecation logs always enabled) if DEBUG = True
LOG_DEPRECATION_WARNINGS = is_truthy(os.getenv("NAUTOBOT_LOG_DEPRECATION_WARNINGS", "False"))

MAINTENANCE_MODE = is_truthy(os.getenv("NAUTOBOT_MAINTENANCE_MODE", "False"))
# Metrics
METRICS_ENABLED = is_truthy(os.getenv("NAUTOBOT_METRICS_ENABLED", "False"))

# Napalm
NAPALM_ARGS = {}
NAPALM_PASSWORD = os.getenv("NAUTOBOT_NAPALM_PASSWORD", "")
NAPALM_TIMEOUT = int(os.getenv("NAUTOBOT_NAPALM_TIMEOUT", "30"))
NAPALM_USERNAME = os.getenv("NAUTOBOT_NAPALM_USERNAME", "")

# Plugins
PLUGINS = []
PLUGINS_CONFIG = {}

# Global 3rd-party authentication settings
EXTERNAL_AUTH_DEFAULT_GROUPS = []
EXTERNAL_AUTH_DEFAULT_PERMISSIONS = {}

# Remote auth backend settings
REMOTE_AUTH_AUTO_CREATE_USER = False
REMOTE_AUTH_HEADER = "HTTP_REMOTE_USER"

# SSO backend settings https://python-social-auth.readthedocs.io/en/latest/configuration/settings.html
SOCIAL_AUTH_POSTGRES_JSONFIELD = False
# Nautobot related - May be overridden if using custom social auth backend
SOCIAL_AUTH_BACKEND_PREFIX = "social_core.backends"

# Job log entry sanitization and similar
SANITIZER_PATTERNS = [
    # General removal of username-like and password-like tokens
    (re.compile(r"(https?://)?\S+\s*@", re.IGNORECASE), r"\1{replacement}@"),
    (re.compile(r"(username|password|passwd|pwd)(\s*i?s?\s*:?\s*)?\S+", re.IGNORECASE), r"\1\2{replacement}"),
]

# Storage
STORAGE_BACKEND = None
STORAGE_CONFIG = {}

# Test runner that is aware of our use of "integration" tags and only runs
# integration tests if explicitly passed in with `nautobot-server test --tag integration`.
TEST_RUNNER = "nautobot.core.tests.runner.NautobotTestRunner"
# Disable test data factories by default so as not to cause issues for plugins.
# The nautobot_config.py that Nautobot core uses for its own tests will override this to True.
TEST_USE_FACTORIES = is_truthy(os.getenv("NAUTOBOT_TEST_USE_FACTORIES", "False"))
# Pseudo-random number generator seed, for reproducibility of test results.
TEST_FACTORY_SEED = os.getenv("NAUTOBOT_TEST_FACTORY_SEED", None)

#
# django-slowtests
#

# Performance test uses `NautobotPerformanceTestRunner` to run, which is only available once you have `django-slowtests` installed in your dev environment.
# `invoke performance-test` and adding `--performance-report` or `--performance-snapshot` at the end of the `invoke` command
# will automatically opt to NautobotPerformanceTestRunner to run the tests.

# The baseline file that the performance test is running against
# TODO we need to replace the baselines in this file with more consistent results at least for CI
TEST_PERFORMANCE_BASELINE_FILE = os.getenv(
    "NAUTOBOT_TEST_PERFORMANCE_BASELINE_FILE", "nautobot/core/tests/performance_baselines.yml"
)

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

STRICT_FILTERING = is_truthy(os.getenv("NAUTOBOT_STRICT_FILTERING", "True"))

#
# Django REST framework (API)
#

REST_FRAMEWORK_VERSION = VERSION.rsplit(".", 1)[0]  # Use major.minor as API version
current_major, current_minor = REST_FRAMEWORK_VERSION.split(".")
# We support all major.minor API versions from 1.2 to the present latest version.
# This will need to be elaborated upon when we move to version 2.0
# Similar logic exists in tasks.py, please keep them in sync!
assert current_major == "1", f"REST_FRAMEWORK_ALLOWED_VERSIONS needs to be updated to handle version {current_major}"
REST_FRAMEWORK_ALLOWED_VERSIONS = [f"{current_major}.{minor}" for minor in range(2, int(current_minor) + 1)]

REST_FRAMEWORK = {
    "ALLOWED_VERSIONS": REST_FRAMEWORK_ALLOWED_VERSIONS,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "nautobot.core.api.authentication.TokenAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ("nautobot.core.api.filter_backends.NautobotFilterBackend",),
    "DEFAULT_METADATA_CLASS": "nautobot.core.api.metadata.BulkOperationMetadata",
    "DEFAULT_PAGINATION_CLASS": "nautobot.core.api.pagination.OptionalLimitOffsetPagination",
    "DEFAULT_PERMISSION_CLASSES": ("nautobot.core.api.authentication.TokenPermissions",),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "nautobot.core.api.renderers.FormlessBrowsableAPIRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": ("rest_framework.parsers.JSONParser",),
    "DEFAULT_SCHEMA_CLASS": "nautobot.core.api.schema.NautobotAutoSchema",
    # Version to use if the client doesn't request otherwise.
    # This should only change (if at all) with Nautobot major (breaking) releases.
    "DEFAULT_VERSION": "1.2",
    "DEFAULT_VERSIONING_CLASS": "nautobot.core.api.versioning.NautobotAPIVersioning",
    "PAGE_SIZE": None,
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
# drf_spectacular (OpenAPI/Swagger)
#

SPECTACULAR_SETTINGS = {
    "TITLE": "API Documentation",
    "DESCRIPTION": "Source of truth and network automation platform",
    "LICENSE": {"name": "Apache v2 License"},
    "VERSION": VERSION,
    # For a semblance of backwards-compatibility with drf-yasg / OpenAPI 2.0, where "/api" was a common "basePath"
    # in the schema.
    # OpenAPI 3.0 removes "basePath" in favor of "servers", so we now declare "/api" as the server relative URL and
    # trim it from all of the individual paths correspondingly.
    # See also https://github.com/nautobot/nautobot-ansible/pull/135 for an example of why this is desirable.
    "SERVERS": [{"url": "/api"}],
    "SCHEMA_PATH_PREFIX": "/api",
    "SCHEMA_PATH_PREFIX_TRIM": True,
    # use sidecar - locally packaged UI files, not CDN
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "ENUM_NAME_OVERRIDES": {
        # These choice enums need to be overridden because they get assigned to the `type` field and
        # result in this error:
        #    enum naming encountered a non-optimally resolvable collision for fields named "type".
        "CableTypeChoices": "nautobot.dcim.choices.CableTypeChoices",
        "ConsolePortTypeChoices": "nautobot.dcim.choices.ConsolePortTypeChoices",
        "CustomFieldTypeChoices": "nautobot.extras.choices.CustomFieldTypeChoices",
        "InterfaceTypeChoices": "nautobot.dcim.choices.InterfaceTypeChoices",
        "PortTypeChoices": "nautobot.dcim.choices.PortTypeChoices",
        "PowerFeedTypeChoices": "nautobot.dcim.choices.PowerFeedTypeChoices",
        "PowerOutletTypeChoices": "nautobot.dcim.choices.PowerOutletTypeChoices",
        "PowerPortTypeChoices": "nautobot.dcim.choices.PowerPortTypeChoices",
        "RackTypeChoices": "nautobot.dcim.choices.RackTypeChoices",
        "RelationshipTypeChoices": "nautobot.extras.choices.RelationshipTypeChoices",
        # Each of these StatusModels has bulk and non-bulk serializers, with the same status options,
        # which confounds drf-spectacular's automatic naming of enums, resulting in the below warning:
        #   enum naming encountered a non-optimally resolvable collision for fields named "status"
        # By explicitly naming the enums ourselves we avoid this warning.
        "CableStatusChoices": "nautobot.dcim.api.serializers.CableSerializer.status_choices",
        "CircuitStatusChoices": "nautobot.circuits.api.serializers.CircuitSerializer.status_choices",
        "DeviceStatusChoices": "nautobot.dcim.api.serializers.DeviceWithConfigContextSerializer.status_choices",
        "InterfaceStatusChoices": "nautobot.dcim.api.serializers.InterfaceSerializer.status_choices",
        "IPAddressStatusChoices": "nautobot.ipam.api.serializers.IPAddressSerializer.status_choices",
        "LocationStatusChoices": "nautobot.dcim.api.serializers.LocationSerializer.status_choices",
        "PowerFeedStatusChoices": "nautobot.dcim.api.serializers.PowerFeedSerializer.status_choices",
        "PrefixStatusChoices": "nautobot.ipam.api.serializers.PrefixSerializer.status_choices",
        "RackStatusChoices": "nautobot.dcim.api.serializers.RackSerializer.status_choices",
        "VirtualMachineStatusChoices": "nautobot.virtualization.api.serializers.VirtualMachineWithConfigContextSerializer.status_choices",
        "VLANStatusChoices": "nautobot.ipam.api.serializers.VLANSerializer.status_choices",
        # These choice enums need to be overridden because they get assigned to different names with the same choice set and
        # result in this error:
        #   encountered multiple names for the same choice set
        "JobExecutionTypeIntervalChoices": "nautobot.extras.choices.JobExecutionType",
    },
    # Create separate schema components for PATCH requests (fields generally are not `required` on PATCH)
    "COMPONENT_SPLIT_PATCH": True,
    # Create separate schema components for request vs response where appropriate
    "COMPONENT_SPLIT_REQUEST": True,
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
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),
        "USER": os.getenv("NAUTOBOT_DB_USER", ""),
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),
        "PORT": os.getenv("NAUTOBOT_DB_PORT", ""),
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", "300")),
        "ENGINE": os.getenv("NAUTOBOT_DB_ENGINE", "django.db.backends.postgresql"),
    }
}

# Ensure proper Unicode handling for MySQL
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"]["OPTIONS"] = {"charset": "utf8mb4"}

# The secret key is used to encrypt session keys and salt passwords.
SECRET_KEY = os.getenv("NAUTOBOT_SECRET_KEY")

# Default overrides
ALLOWED_HOSTS = os.getenv("NAUTOBOT_ALLOWED_HOSTS", "").split(" ")
CSRF_TRUSTED_ORIGINS = []
CSRF_FAILURE_VIEW = "nautobot.core.views.csrf_failure"
DATE_FORMAT = os.getenv("NAUTOBOT_DATE_FORMAT", "N j, Y")
DATETIME_FORMAT = os.getenv("NAUTOBOT_DATETIME_FORMAT", "N j, Y g:i a")
DEBUG = is_truthy(os.getenv("NAUTOBOT_DEBUG", "False"))
INTERNAL_IPS = ("127.0.0.1", "::1")
FORCE_SCRIPT_NAME = None

TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

if TESTING:
    # keep log quiet by default when running unit/integration tests
    LOGGING = {}
else:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "normal": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s :\n  %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "verbose": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s() :\n  %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "normal_console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "normal",
            },
            "verbose_console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "loggers": {
            "django": {"handlers": ["normal_console"], "level": "INFO"},
            "nautobot": {
                "handlers": ["verbose_console" if DEBUG else "normal_console"],
                "level": LOG_LEVEL,
            },
        },
    }

MEDIA_ROOT = os.path.join(NAUTOBOT_ROOT, "media").rstrip("/")
SESSION_COOKIE_AGE = int(os.getenv("NAUTOBOT_SESSION_COOKIE_AGE", "1209600"))  # 2 weeks, in seconds
SESSION_FILE_PATH = os.getenv("NAUTOBOT_SESSION_FILE_PATH", None)
SHORT_DATE_FORMAT = os.getenv("NAUTOBOT_SHORT_DATE_FORMAT", "Y-m-d")
SHORT_DATETIME_FORMAT = os.getenv("NAUTOBOT_SHORT_DATETIME_FORMAT", "Y-m-d H:i")
SHORT_TIME_FORMAT = os.getenv("NAUTOBOT_SHORT_TIME_FORMAT", "H:i:s")
TIME_FORMAT = os.getenv("NAUTOBOT_TIME_FORMAT", "g:i a")
TIME_ZONE = os.getenv("NAUTOBOT_TIME_ZONE", "UTC")

# Disable importing the WSGI module before starting the server application. This is required for
# uWSGI postfork callbacks to execute as is currently required in `nautobot.core.wsgi`.
WEBSERVER_WARMUP = False

# Installed apps and Django plugins. Nautobot plugins will be appended here later.
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "cacheops",  # v2 TODO(jathan); Remove cacheops.
    "corsheaders",
    "django_filters",
    "django_jinja",
    "django_tables2",
    "django_prometheus",
    "mptt",
    "social_django",
    "taggit",
    "timezone_field",
    "nautobot.core.apps.NautobotConstanceConfig",  # overridden form of "constance" AppConfig
    "nautobot.core",
    "django.contrib.admin",  # Must be after `nautobot.core` for template overrides
    "django_celery_beat",  # Must be after `nautobot.core` for template overrides
    "rest_framework",  # Must be after `nautobot.core` for template overrides
    "db_file_storage",
    "nautobot.circuits",
    "nautobot.dcim",
    "nautobot.ipam",
    "nautobot.extras",
    "nautobot.tenancy",
    "nautobot.users",
    "nautobot.utilities",
    "nautobot.virtualization",
    "django_rq",  # Must come after nautobot.extras to allow overriding management commands
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "graphene_django",
    "health_check",
    "health_check.storage",
    "django_extensions",
    "constance.backends.database",
    "django_ajax_tables",
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
                "nautobot.core.context_processors.settings",
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
                "nautobot.core.context_processors.settings",
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
X_FRAME_OPTIONS = "DENY"

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
# django-constance
#

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"
CONSTANCE_DATABASE_PREFIX = "constance:nautobot:"
CONSTANCE_IGNORE_ADMIN_VERSION_CHECK = True  # avoid potential errors in a multi-node deployment

CONSTANCE_ADDITIONAL_FIELDS = {
    "per_page_defaults_field": [
        "nautobot.utilities.forms.fields.JSONArrayFormField",
        {
            "widget": "django.forms.TextInput",
            "base_field": django.forms.IntegerField(min_value=1),
        },
    ],
    "release_check_timeout_field": [
        "django.forms.IntegerField",
        {
            "min_value": 3600,
        },
    ],
    "release_check_url_field": [
        "django.forms.URLField",
        {
            "required": False,
        },
    ],
}

CONSTANCE_CONFIG = {
    "BANNER_BOTTOM": [
        "",
        "Custom HTML to display in a banner at the bottom of all pages.",
    ],
    "BANNER_LOGIN": [
        "",
        "Custom HTML to display in a banner at the top of the login page.",
    ],
    "BANNER_TOP": [
        "",
        "Custom HTML to display in a banner at the top of all pages.",
    ],
    "CHANGELOG_RETENTION": [
        90,
        "Number of days to retain object changelog history.\nSet this to 0 to retain changes indefinitely.",
    ],
    "DISABLE_PREFIX_LIST_HIERARCHY": [
        False,
        "Disable rendering parent/child relationships in the IPAM Prefix list view and instead show a flat list.",
    ],
    "HIDE_RESTRICTED_UI": [
        False,
        "If set to True, users with limited permissions will not be shown menu items and home-page elements that "
        "they do not have permission to access.",
    ],
    "MAX_PAGE_SIZE": [
        1000,
        "Maximum number of objects that a user can list in one UI page or one API call.\n"
        "If set to 0, a user can retrieve an unlimited number of objects.",
    ],
    "PAGINATE_COUNT": [
        50,
        "Default number of objects to display per page when listing objects in the UI and/or REST API.",
    ],
    "PER_PAGE_DEFAULTS": [
        [25, 50, 100, 250, 500, 1000],
        "Pagination options to present to the user to choose amongst.\n"
        "For proper user experience, this list should include the PAGINATE_COUNT and MAX_PAGE_SIZE values as options.",
        # Use custom field type defined above
        "per_page_defaults_field",
    ],
    "PREFER_IPV4": [
        False,
        "Whether to prefer IPv4 primary addresses over IPv6 primary addresses for devices.",
    ],
    "RACK_ELEVATION_DEFAULT_UNIT_HEIGHT": [
        22,
        "Default height (in pixels) of a rack unit in a rack elevation diagram",
    ],
    "RACK_ELEVATION_DEFAULT_UNIT_WIDTH": [
        230,
        "Default width (in pixels) of a rack unit in a rack elevation diagram",
    ],
    "RELEASE_CHECK_TIMEOUT": [
        24 * 3600,
        "Number of seconds (must be at least 3600, or one hour) to cache the result of a release check "
        "before checking again for a new release.",
        # Use custom field type defined above
        "release_check_timeout_field",
    ],
    "RELEASE_CHECK_URL": [
        "",
        "URL of GitHub repository REST API endpoint to poll periodically for availability of new Nautobot releases.\n"
        'This can be set to the official repository "https://api.github.com/repos/nautobot/nautobot/releases" or '
        "a custom fork.\nSet this to an empty string to disable automatic update checks.",
        # Use custom field type defined above
        "release_check_url_field",
    ],
}

CONSTANCE_CONFIG_FIELDSETS = {
    "Banners": ["BANNER_LOGIN", "BANNER_TOP", "BANNER_BOTTOM"],
    "Change Logging": ["CHANGELOG_RETENTION"],
    "Device Connectivity": ["PREFER_IPV4"],
    "Pagination": ["PAGINATE_COUNT", "MAX_PAGE_SIZE", "PER_PAGE_DEFAULTS"],
    "Rack Elevation Rendering": ["RACK_ELEVATION_DEFAULT_UNIT_HEIGHT", "RACK_ELEVATION_DEFAULT_UNIT_WIDTH"],
    "Release Checking": ["RELEASE_CHECK_URL", "RELEASE_CHECK_TIMEOUT"],
    "User Interface": ["DISABLE_PREFIX_LIST_HIERARCHY", "HIDE_RESTRICTED_UI"],
}

#
# From django-cors-headers
#

# If True, all origins will be allowed. Other settings restricting allowed origins will be ignored.
# Defaults to False. Setting this to True can be dangerous, as it allows any website to make
# cross-origin requests to yours. Generally you'll want to restrict the list of allowed origins with
# CORS_ALLOWED_ORIGINS or CORS_ALLOWED_ORIGIN_REGEXES.
CORS_ALLOW_ALL_ORIGINS = is_truthy(os.getenv("NAUTOBOT_CORS_ALLOW_ALL_ORIGINS", "False"))

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

# v2 TODO(jathan): Remove all cacheops settings.
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
CACHEOPS_ENABLED = is_truthy(os.getenv("NAUTOBOT_CACHEOPS_ENABLED", "False"))
CACHEOPS_REDIS = os.getenv("NAUTOBOT_CACHEOPS_REDIS", parse_redis_connection(redis_database=1))
CACHEOPS_DEFAULTS = {"timeout": int(os.getenv("NAUTOBOT_CACHEOPS_TIMEOUT", "900"))}

# The django-redis cache is used to establish concurrent locks using Redis. The
# django-rq settings will use the same instance/database by default.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": parse_redis_connection(redis_database=0),
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

# Default celery queue name that will be used by workers and tasks if no queue is specified
CELERY_TASK_DEFAULT_QUEUE = os.getenv("NAUTOBOT_CELERY_TASK_DEFAULT_QUEUE", "default")

# Global task time limits (seconds)
# Exceeding the soft limit will result in a SoftTimeLimitExceeded exception,
# while exceeding the hard limit will result in a SIGKILL.
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("NAUTOBOT_CELERY_TASK_SOFT_TIME_LIMIT", str(5 * 60)))
CELERY_TASK_TIME_LIMIT = int(os.getenv("NAUTOBOT_CELERY_TASK_TIME_LIMIT", str(10 * 60)))

# These settings define the custom nautobot serialization encoding as an accepted data encoding format
# and register that format for task input and result serialization
CELERY_ACCEPT_CONTENT = ["nautobot_json"]
CELERY_RESULT_ACCEPT_CONTENT = ["nautobot_json"]
CELERY_TASK_SERIALIZER = "nautobot_json"
CELERY_RESULT_SERIALIZER = "nautobot_json"

CELERY_BEAT_SCHEDULER = "nautobot.core.celery.schedulers:NautobotDatabaseScheduler"

# Sets an age out timer of redis lock. This is NOT implicitly applied to locks, must be added
# to a lock creation as `timeout=settings.REDIS_LOCK_TIMEOUT`
REDIS_LOCK_TIMEOUT = int(os.getenv("NAUTOBOT_REDIS_LOCK_TIMEOUT", "600"))

#
# Custom branding (logo and title)
#

# Branding logo locations. The logo takes the place of the Nautobot logo in the top right of the nav bar.
# The filepath should be relative to the `MEDIA_ROOT`.
BRANDING_FILEPATHS = {
    "logo": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_LOGO", None),  # Navbar logo
    "favicon": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_FAVICON", None),  # Browser favicon
    "icon_16": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_ICON_16", None),  # 16x16px icon
    "icon_32": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_ICON_32", None),  # 32x32px icon
    "icon_180": os.getenv(
        "NAUTOBOT_BRANDING_FILEPATHS_ICON_180", None
    ),  # 180x180px icon - used for the apple-touch-icon header
    "icon_192": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_ICON_192", None),  # 192x192px icon
    "icon_mask": os.getenv(
        "NAUTOBOT_BRANDING_FILEPATHS_ICON_MASK", None
    ),  # mono-chrome icon used for the mask-icon header
}

# Title to use in place of "Nautobot"
BRANDING_TITLE = os.getenv("NAUTOBOT_BRANDING_TITLE", "Nautobot")

# Prepended to CSV, YAML and export template filenames (i.e. `nautobot_device.yml`)
BRANDING_PREPENDED_FILENAME = os.getenv("NAUTOBOT_BRANDING_PREPENDED_FILENAME", "nautobot_")

# Branding URLs (links in the bottom right of the footer)
BRANDING_URLS = {
    "code": os.getenv("NAUTOBOT_BRANDING_URLS_CODE", "https://github.com/nautobot/nautobot"),
    "docs": os.getenv("NAUTOBOT_BRANDING_URLS_DOCS", None),
    "help": os.getenv("NAUTOBOT_BRANDING_URLS_HELP", "https://github.com/nautobot/nautobot/wiki"),
}

# Undocumented link in the bottom right of the footer which is meant to persist any custom branding changes.
BRANDING_POWERED_BY_URL = "https://docs.nautobot.com/"

#
# Django extensions settings
#

# Dont load the 'taggit' app, since we have our own custom `Tag` and `TaggedItem` models
SHELL_PLUS_DONT_LOAD = ["taggit"]

#
# UI settings
#


# UI_RACK_VIEW_TRUNCATE_FUNCTION
def UI_RACK_VIEW_TRUNCATE_FUNCTION(device_display_name):
    """Given device display name, truncate to fit the rack elevation view.

    :param device_display_name: Full display name of the device attempting to be rendered in the rack elevation.
    :type device_display_name: str

    :return: Truncated device name
    :type: str
    """
    return str(device_display_name).split(".")[0]
