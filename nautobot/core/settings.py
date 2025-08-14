import datetime
import os
import os.path
import platform
import re
import sys
import tempfile

from django.contrib.messages import constants as messages
import django.forms
from django.utils.safestring import mark_safe

from nautobot import __version__
from nautobot.core.constants import (
    CONFIG_SETTING_SEPARATOR as _CONFIG_SETTING_SEPARATOR,
    MAX_PAGE_SIZE_DEFAULT as _MAX_PAGE_SIZE_DEFAULT,
    PAGINATE_COUNT_DEFAULT as _PAGINATE_COUNT_DEFAULT,
)
from nautobot.core.settings_funcs import ConstanceConfigItem, is_truthy, parse_redis_connection

#
# Environment setup
#

# This is used for display in the UI. There are also VERSION_MAJOR and VERSION_MINOR derived from this later.
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
#      we can't do that yet
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


###############################################################
# NAUTOBOT - Settings for Nautobot internals/plugins/defaults #
###############################################################

#
# Nautobot optional settings/defaults
#

# Base directory wherein all created files (jobs, git repositories, file uploads, static files) will be stored)
NAUTOBOT_ROOT = os.getenv("NAUTOBOT_ROOT", os.path.expanduser("~/.nautobot"))

# Allow users to enable request profiling via django-silk for admins to inspect.
if "NAUTOBOT_ALLOW_REQUEST_PROFILING" in os.environ and os.environ["NAUTOBOT_ALLOW_REQUEST_PROFILING"] != "":
    ALLOW_REQUEST_PROFILING = is_truthy(os.environ["NAUTOBOT_ALLOW_REQUEST_PROFILING"])

# URL schemes that are allowed within links in Nautobot
ALLOWED_URL_SCHEMES = [
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
]

# Banners to display to users. Markdown and limited HTML are allowed.
if "NAUTOBOT_BANNER_BOTTOM" in os.environ and os.environ["NAUTOBOT_BANNER_BOTTOM"] != "":
    BANNER_BOTTOM = os.environ["NAUTOBOT_BANNER_BOTTOM"]
if "NAUTOBOT_BANNER_LOGIN" in os.environ and os.environ["NAUTOBOT_BANNER_LOGIN"] != "":
    BANNER_LOGIN = os.environ["NAUTOBOT_BANNER_LOGIN"]
if "NAUTOBOT_BANNER_TOP" in os.environ and os.environ["NAUTOBOT_BANNER_TOP"] != "":
    BANNER_TOP = os.environ["NAUTOBOT_BANNER_TOP"]

# Number of days to retain changelog entries. Set to 0 to retain changes indefinitely. Defaults to 90 if not set here.
if "NAUTOBOT_CHANGELOG_RETENTION" in os.environ and os.environ["NAUTOBOT_CHANGELOG_RETENTION"] != "":
    CHANGELOG_RETENTION = int(os.environ["NAUTOBOT_CHANGELOG_RETENTION"])

# Disable linking of Config Context objects via Dynamic Groups by default. This could cause performance impacts
# when a large number of dynamic groups are present
CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED = is_truthy(os.getenv("NAUTOBOT_CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED", "False"))

# UUID uniquely but anonymously identifying this Nautobot deployment.
if "NAUTOBOT_DEPLOYMENT_ID" in os.environ and os.environ["NAUTOBOT_DEPLOYMENT_ID"] != "":
    DEPLOYMENT_ID = os.environ["NAUTOBOT_DEPLOYMENT_ID"]

# Device names are not guaranteed globally-unique by Nautobot but in practice they often are.
# Set this to True to use the device name alone as the natural key for Device objects.
# Set this to False to use the sequence (name, tenant, location) as the natural key instead.
#
if "NAUTOBOT_DEVICE_NAME_AS_NATURAL_KEY" in os.environ and os.environ["NAUTOBOT_DEVICE_NAME_AS_NATURAL_KEY"] != "":
    DEVICE_NAME_AS_NATURAL_KEY = is_truthy(os.environ["NAUTOBOT_DEVICE_NAME_AS_NATURAL_KEY"])

# Event Brokers
EVENT_BROKERS = {}

# Exclude potentially sensitive models from wildcard view exemption. These may still be exempted
# by specifying the model individually in the EXEMPT_VIEW_PERMISSIONS configuration parameter.
EXEMPT_EXCLUDE_MODELS = (
    ("auth", "group"),
    ("users", "user"),
    ("users", "objectpermission"),
)

# Models to exempt from the enforcement of view permissions
EXEMPT_VIEW_PERMISSIONS = []

# The file path to a directory where cloned Git repositories will be located
GIT_ROOT = os.getenv("NAUTOBOT_GIT_ROOT", os.path.join(NAUTOBOT_ROOT, "git").rstrip("/"))

# HTTP proxies to use for outbound requests originating from Nautobot (e.g. when sending webhook requests)
HTTP_PROXIES = None

# Send anonymized installation metrics when post_upgrade or send_installation_metrics management commands are run
INSTALLATION_METRICS_ENABLED = is_truthy(os.getenv("NAUTOBOT_INSTALLATION_METRICS_ENABLED", "True"))

# Maximum file size (in bytes) that as running Job can create in a call to `Job.create_file()`. Default is 10 << 20
if "NAUTOBOT_JOB_CREATE_FILE_MAX_SIZE" in os.environ and os.environ["NAUTOBOT_JOB_CREATE_FILE_MAX_SIZE"] != "":
    JOB_CREATE_FILE_MAX_SIZE = int(os.environ["NAUTOBOT_JOB_CREATE_FILE_MAX_SIZE"])

# The storage backend to use for Job input files and Job output files
JOB_FILE_IO_STORAGE = os.getenv("NAUTOBOT_JOB_FILE_IO_STORAGE", "db_file_storage.storage.DatabaseFileStorage")

# The file path to a directory where locally installed Jobs can be discovered
JOBS_ROOT = os.getenv("NAUTOBOT_JOBS_ROOT", os.path.join(NAUTOBOT_ROOT, "jobs").rstrip("/"))

# `Location` names are not guaranteed globally-unique by Nautobot but in practice they often are.
# Set this to `True` to use the location `name` alone as the natural key for `Location` objects.
# Set this to `False` to use the sequence `(name, parent__name, parent__parent__name, ...)` as the natural key instead.
if "NAUTOBOT_LOCATION_NAME_AS_NATURAL_KEY" in os.environ and os.environ["NAUTOBOT_LOCATION_NAME_AS_NATURAL_KEY"] != "":
    LOCATION_NAME_AS_NATURAL_KEY = is_truthy(os.environ["NAUTOBOT_LOCATION_NAME_AS_NATURAL_KEY"])


# Log Nautobot deprecation warnings. Note that this setting is ignored (deprecation logs always enabled) if DEBUG = True
LOG_DEPRECATION_WARNINGS = is_truthy(os.getenv("NAUTOBOT_LOG_DEPRECATION_WARNINGS", "False"))

# Setting this to True will display a "maintenance mode" banner at the top of every page.
MAINTENANCE_MODE = is_truthy(os.getenv("NAUTOBOT_MAINTENANCE_MODE", "False"))

# Maximum number of objects that the UI and API will retrieve in a single request. Default is 1000
if "NAUTOBOT_MAX_PAGE_SIZE" in os.environ and os.environ["NAUTOBOT_MAX_PAGE_SIZE"] != "":
    MAX_PAGE_SIZE = int(os.environ["NAUTOBOT_MAX_PAGE_SIZE"])

# Metrics
METRICS_ENABLED = is_truthy(os.getenv("NAUTOBOT_METRICS_ENABLED", "False"))
METRICS_AUTHENTICATED = is_truthy(os.getenv("NAUTOBOT_METRICS_AUTHENTICATED", "False"))
METRICS_DISABLED_APPS = []
if "NAUTOBOT_METRICS_DISABLED_APPS" in os.environ and os.environ["NAUTOBOT_METRICS_DISABLED_APPS"] != "":
    METRICS_DISABLED_APPS = os.getenv("NAUTOBOT_METRICS_DISABLED_APPS", "").split(_CONFIG_SETTING_SEPARATOR)

# Napalm
NAPALM_ARGS = {}
NAPALM_PASSWORD = os.getenv("NAUTOBOT_NAPALM_PASSWORD", "")
NAPALM_TIMEOUT = int(os.getenv("NAUTOBOT_NAPALM_TIMEOUT", "30"))
NAPALM_USERNAME = os.getenv("NAUTOBOT_NAPALM_USERNAME", "")

# Expiration date (YYYY-MM-DD) for an active Nautobot support contract with Network to Code.
# Displayed in the About page.
if (
    "NAUTOBOT_NTC_SUPPORT_CONTRACT_EXPIRATION_DATE" in os.environ
    and os.environ["NAUTOBOT_NTC_SUPPORT_CONTRACT_EXPIRATION_DATE"] != ""
):
    NTC_SUPPORT_CONTRACT_EXPIRATION_DATE = datetime.date.fromisoformat(
        os.environ["NAUTOBOT_NTC_SUPPORT_CONTRACT_EXPIRATION_DATE"]
    )

# Default number of objects to display per page of the UI and REST API. Default is 50
if "NAUTOBOT_PAGINATE_COUNT" in os.environ and os.environ["NAUTOBOT_PAGINATE_COUNT"] != "":
    PAGINATE_COUNT = int(os.environ["NAUTOBOT_PAGINATE_COUNT"])

# The options displayed in the web interface dropdown to limit the number of objects per page.
# Default is [25, 50, 100, 250, 500, 1000]
if "NAUTOBOT_PER_PAGE_DEFAULTS" in os.environ and os.environ["NAUTOBOT_PER_PAGE_DEFAULTS"] != "":
    PER_PAGE_DEFAULTS = [int(val) for val in os.environ["NAUTOBOT_PER_PAGE_DEFAULTS"].split(_CONFIG_SETTING_SEPARATOR)]

# Plugins
PLUGINS = []
PLUGINS_CONFIG = {}

# Prefer IPv6 addresses or IPv4 addresses in selecting a device's primary IP address? Default False
if "NAUTOBOT_PREFER_IPV4" in os.environ and os.environ["NAUTOBOT_PREFER_IPV4"] != "":
    PREFER_IPV4 = is_truthy(os.environ["NAUTOBOT_PREFER_IPV4"])

# Publish a simple "no-index" robots.txt for Nautobot?
PUBLISH_ROBOTS_TXT = is_truthy(os.getenv("NAUTOBOT_PUBLISH_ROBOTS_TXT", "True"))

# Default height and width in pixels of a single rack unit in rendered rack elevations. Defaults are 22 and 220
if (
    "NAUTOBOT_RACK_ELEVATION_DEFAULT_UNIT_HEIGHT" in os.environ
    and os.environ["NAUTOBOT_RACK_ELEVATION_DEFAULT_UNIT_HEIGHT"] != ""
):
    RACK_ELEVATION_DEFAULT_UNIT_HEIGHT = int(os.environ["NAUTOBOT_RACK_ELEVATION_DEFAULT_UNIT_HEIGHT"])
if (
    "NAUTOBOT_RACK_ELEVATION_DEFAULT_UNIT_WIDTH" in os.environ
    and os.environ["NAUTOBOT_RACK_ELEVATION_DEFAULT_UNIT_WIDTH"] != ""
):
    RACK_ELEVATION_DEFAULT_UNIT_WIDTH = int(os.environ["NAUTOBOT_RACK_ELEVATION_DEFAULT_UNIT_WIDTH"])

# Enable two-digit format for the rack unit numbering in rack elevations.
if (
    "NAUTOBOT_RACK_ELEVATION_UNIT_TWO_DIGIT_FORMAT" in os.environ
    and os.environ["NAUTOBOT_RACK_ELEVATION_UNIT_TWO_DIGIT_FORMAT"] != ""
):
    RACK_ELEVATION_UNIT_TWO_DIGIT_FORMAT = is_truthy(os.environ["NAUTOBOT_RACK_ELEVATION_UNIT_TWO_DIGIT_FORMAT"])

# How frequently to check for a new Nautobot release on GitHub, and the URL to check for this information.
# Defaults to disabled (no URL) and check every 24 hours when enabled
if "NAUTOBOT_RELEASE_CHECK_TIMEOUT" in os.environ and os.environ["NAUTOBOT_RELEASE_CHECK_TIMEOUT"] != "":
    RELEASE_CHECK_TIMEOUT = int(os.environ["NAUTOBOT_RELEASE_CHECK_TIMEOUT"])
if "NAUTOBOT_RELEASE_CHECK_URL" in os.environ and os.environ["NAUTOBOT_RELEASE_CHECK_URL"] != "":
    RELEASE_CHECK_URL = os.environ["NAUTOBOT_RELEASE_CHECK_URL"]

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

# Enables adding the OAuth2/OIDC group sync module to the authentication pipeline
SSO_ENABLE_GROUP_SYNC = is_truthy(os.getenv("NAUTOBOT_SSO_ENABLE_GROUP_SYNC", "false"))
if SSO_ENABLE_GROUP_SYNC:
    SOCIAL_AUTH_PIPELINE = (
        "social_core.pipeline.social_auth.social_details",
        "social_core.pipeline.social_auth.social_uid",
        "social_core.pipeline.social_auth.auth_allowed",
        "social_core.pipeline.social_auth.social_user",
        "social_core.pipeline.user.get_username",
        "social_core.pipeline.user.create_user",
        "social_core.pipeline.social_auth.associate_user",
        "social_core.pipeline.social_auth.load_extra_data",
        "social_core.pipeline.user.user_details",
        "nautobot.extras.group_sync.group_sync",
    )
# OAuth2/OIDC claim where the list of groups the authenticating user is a part of
SSO_CLAIMS_GROUP = os.getenv("NAUTOBOT_SSO_CLAIMS_GROUP", "groups")
# list of groups that an authenticating user can be a part of to get the Django staff permission
SSO_STAFF_GROUPS = [
    group for group in os.getenv("NAUTOBOT_SSO_STAFF_GROUPS", "").split(_CONFIG_SETTING_SEPARATOR) if group != ""
]
# list of groups that an authenticating user can be a part of to be a Django super user
SSO_SUPERUSER_GROUPS = [
    group for group in os.getenv("NAUTOBOT_SSO_SUPERUSER_GROUPS", "").split(_CONFIG_SETTING_SEPARATOR) if group != ""
]

# Job log entry sanitization and similar
SANITIZER_PATTERNS = [
    # General removal of username-like and password-like tokens
    (re.compile(r"(https?://)?\S+\s*@", re.IGNORECASE), r"\1{replacement}@"),
    (
        re.compile(r"(username|password|passwd|pwd|secret|secrets)([\"']?(?:\s+is.?|:)?\s+)\S+[\"']?", re.IGNORECASE),
        r"\1\2{replacement}",
    ),
]

# Storage
STORAGE_BACKEND = None
STORAGE_CONFIG = {}

# Custom message to display on 4xx and 5xx error pages. Markdown and HTML are supported.
# Default message directs the user to #nautobot on NTC's Slack community.
if "NAUTOBOT_SUPPORT_MESSAGE" in os.environ and os.environ["NAUTOBOT_SUPPORT_MESSAGE"] != "":
    SUPPORT_MESSAGE = os.environ["NAUTOBOT_SUPPORT_MESSAGE"]

# Test runner that is aware of our use of "integration" tags and only runs
# integration tests if explicitly passed in with `nautobot-server test --tag integration`.
TEST_RUNNER = "nautobot.core.tests.runner.NautobotTestRunner"
# Disable test data factories by default so as not to cause issues for plugins.
# The nautobot_config.py that Nautobot core uses for its own tests will override this to True.
TEST_USE_FACTORIES = is_truthy(os.getenv("NAUTOBOT_TEST_USE_FACTORIES", "False"))
# Pseudo-random number generator seed, for reproducibility of test results.
TEST_FACTORY_SEED = os.getenv("NAUTOBOT_TEST_FACTORY_SEED", None)

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
VERSION_MAJOR, VERSION_MINOR = [int(v) for v in REST_FRAMEWORK_VERSION.split(".")]
# We support all major.minor API versions from 2.0 to the present latest version.
# Similar logic exists in tasks.py, please keep them in sync!
if VERSION_MAJOR != 2:
    raise RuntimeError(f"REST_FRAMEWORK_ALLOWED_VERSIONS needs to be updated to handle version {VERSION_MAJOR}")
REST_FRAMEWORK_ALLOWED_VERSIONS = [f"{VERSION_MAJOR}.{minor}" for minor in range(0, VERSION_MINOR + 1)]

REST_FRAMEWORK = {
    "ALLOWED_VERSIONS": REST_FRAMEWORK_ALLOWED_VERSIONS,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "nautobot.core.api.authentication.TokenAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "nautobot.core.api.filter_backends.NautobotFilterBackend",
        "nautobot.core.api.filter_backends.NautobotOrderingFilter",
    ),
    "DEFAULT_METADATA_CLASS": "nautobot.core.api.metadata.NautobotMetadata",
    "DEFAULT_PAGINATION_CLASS": "nautobot.core.api.pagination.OptionalLimitOffsetPagination",
    "DEFAULT_PERMISSION_CLASSES": ("nautobot.core.api.authentication.TokenPermissions",),
    "DEFAULT_RENDERER_CLASSES": (
        "nautobot.core.api.renderers.NautobotJSONRenderer",
        "nautobot.core.api.renderers.FormlessBrowsableAPIRenderer",
        "nautobot.core.api.renderers.NautobotCSVRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "nautobot.core.api.parsers.NautobotCSVParser",
    ),
    "DEFAULT_SCHEMA_CLASS": "nautobot.core.api.schema.NautobotAutoSchema",
    # Version to use if the client doesn't request otherwise. Default to current (i.e. latest)
    "DEFAULT_VERSION": REST_FRAMEWORK_VERSION,
    "DEFAULT_VERSIONING_CLASS": "nautobot.core.api.versioning.NautobotAPIVersioning",
    "ORDERING_PARAM": "sort",  # This is not meant to be changed by users, but is used internally by the API
    "PAGE_SIZE": None,
    "SCHEMA_COERCE_METHOD_NAMES": {
        # Default mappings
        "retrieve": "read",
        "destroy": "delete",
        # Custom operations
        "bulk_destroy": "bulk_delete",
    },
    "VIEW_NAME_FUNCTION": "nautobot.core.api.utils.get_view_name",
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
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
    "SCHEMA_PATH_PREFIX": "/api",
    "SCHEMA_PATH_PREFIX_TRIM": True,
    # use sidecar - locally packaged UI files, not CDN
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "displayOperationId": True,
    },
    "REDOC_DIST": "SIDECAR",
    # Do not list all possible enum values in the description of filter fields and the like
    # In addition to being highly verbose, it's inaccurate for filter fields like *__ic and *__re
    "ENUM_GENERATE_CHOICE_DESCRIPTION": False,
    "ENUM_NAME_OVERRIDES": {
        # These choice enums need to be overridden because they get assigned to the `type` field and
        # result in this error:
        #    enum naming encountered a non-optimally resolvable collision for fields named "type".
        "CableTypeChoices": "nautobot.dcim.choices.CableTypeChoices",
        "ConsolePortTypeChoices": "nautobot.dcim.choices.ConsolePortTypeChoices",
        "CustomFieldTypeChoices": "nautobot.extras.choices.CustomFieldTypeChoices",
        "InterfaceTypeChoices": "nautobot.dcim.choices.InterfaceTypeChoices",
        "IPAddressTypeChoices": "nautobot.ipam.choices.IPAddressTypeChoices",
        "PortTypeChoices": "nautobot.dcim.choices.PortTypeChoices",
        "PowerFeedTypeChoices": "nautobot.dcim.choices.PowerFeedTypeChoices",
        "PowerOutletTypeChoices": "nautobot.dcim.choices.PowerOutletTypeChoices",
        "PowerPortTypeChoices": "nautobot.dcim.choices.PowerPortTypeChoices",
        "PrefixTypeChoices": "nautobot.ipam.choices.PrefixTypeChoices",
        "RackTypeChoices": "nautobot.dcim.choices.RackTypeChoices",
        "RelationshipTypeChoices": "nautobot.extras.choices.RelationshipTypeChoices",
        # These choice enums need to be overridden because they get assigned to different names with the same choice set and
        # result in this error:
        #   encountered multiple names for the same choice set
        "JobExecutionTypeIntervalChoices": "nautobot.extras.choices.JobExecutionType",
        # These choice enums need to be overridden because they get assigned to the `protocol` field and
        # result in this error:
        #    enum naming encountered a non-optimally resolvable collision for fields named "protocol".
        "InterfaceRedundancyGroupProtocolChoices": "nautobot.dcim.choices.InterfaceRedundancyGroupProtocolChoices",
        "ServiceProtocolChoices": "nautobot.ipam.choices.ServiceProtocolChoices",
        # These choice enums need to be overridden because they get assigned to the `mode` field and
        # result in this error:
        #    enum naming encountered a non-optimally resolvable collision for fields named "mode".
        "InterfaceModeChoices": "nautobot.dcim.choices.InterfaceModeChoices",
        "WirelessNetworkModeChoices": "nautobot.wireless.choices.WirelessNetworkModeChoices",
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

DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),
        "USER": os.getenv("NAUTOBOT_DB_USER", ""),
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),
        "PORT": os.getenv("NAUTOBOT_DB_PORT", ""),
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", "300")),
        "ENGINE": os.getenv(
            "NAUTOBOT_DB_ENGINE",
            "django_prometheus.db.backends.postgresql" if METRICS_ENABLED else "django.db.backends.postgresql",
        ),
    }
}

# Ensure proper Unicode handling for MySQL
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"]["OPTIONS"] = {"charset": "utf8mb4"}

# The secret key is used to encrypt session keys and salt passwords.
SECRET_KEY = os.getenv("NAUTOBOT_SECRET_KEY", "")

# Default overrides
if "NAUTOBOT_ALLOWED_HOSTS" in os.environ and os.environ["NAUTOBOT_ALLOWED_HOSTS"] != "":
    ALLOWED_HOSTS = os.environ["NAUTOBOT_ALLOWED_HOSTS"].split(" ")
else:
    ALLOWED_HOSTS = []

# Allow CSRF trusted origins to be set via an environment variable
# This allows Nautobot to be run behind a reverse proxy that terminates TLS
# and fix potential issues with CSRF validation
CSRF_TRUSTED_ORIGINS = []
if "NAUTOBOT_CSRF_TRUSTED_ORIGINS" in os.environ and os.environ["NAUTOBOT_CSRF_TRUSTED_ORIGINS"] != "":
    CSRF_TRUSTED_ORIGINS = os.getenv("NAUTOBOT_CSRF_TRUSTED_ORIGINS", "").split(_CONFIG_SETTING_SEPARATOR)

CSRF_FAILURE_VIEW = "nautobot.core.views.csrf_failure"
DATE_FORMAT = os.getenv("NAUTOBOT_DATE_FORMAT", "N j, Y")
DATETIME_FORMAT = os.getenv("NAUTOBOT_DATETIME_FORMAT", "N j, Y g:i a")
DEBUG = is_truthy(os.getenv("NAUTOBOT_DEBUG", "False"))
INTERNAL_IPS = ["127.0.0.1", "::1"]
FORCE_SCRIPT_NAME = None

TESTING = "test" in sys.argv

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

if TESTING:
    # Log to null handler instead of stderr during testing
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"console": {"level": "INFO", "class": "logging.NullHandler"}},
        "loggers": {"nautobot": {"handlers": ["console"], "level": "INFO"}},
    }
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
SESSION_EXPIRE_AT_BROWSER_CLOSE = is_truthy(os.getenv("NAUTOBOT_SESSION_EXPIRE_AT_BROWSER_CLOSE", "False"))
SESSION_COOKIE_AGE = int(os.getenv("NAUTOBOT_SESSION_COOKIE_AGE", "1209600"))  # 2 weeks, in seconds
SESSION_FILE_PATH = os.getenv("NAUTOBOT_SESSION_FILE_PATH", None)
SHORT_DATE_FORMAT = os.getenv("NAUTOBOT_SHORT_DATE_FORMAT", "Y-m-d")
SHORT_DATETIME_FORMAT = os.getenv("NAUTOBOT_SHORT_DATETIME_FORMAT", "Y-m-d H:i")
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
    "corsheaders",
    "django_filters",
    "django_jinja",
    "django_tables2",
    "django_prometheus",
    "social_django",
    "taggit",
    "timezone_field",
    "nautobot.core.apps.NautobotConstanceConfig",  # overridden form of "constance" AppConfig
    "nautobot.core",
    "django.contrib.admin",  # Must be after `nautobot.core` for template overrides
    "django_celery_beat",  # Must be after `nautobot.core` for template overrides
    "django_celery_results",
    "rest_framework",  # Must be after `nautobot.core` for template overrides
    "db_file_storage",
    "nautobot.circuits",
    "nautobot.cloud",
    "nautobot.dcim",
    "nautobot.ipam",
    "nautobot.extras",
    "nautobot.tenancy",
    "nautobot.users",
    "nautobot.virtualization",
    "nautobot.wireless",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "graphene_django",
    "health_check",
    "health_check.storage",
    # We have custom implementations of these in nautobot.extras.health_checks:
    # "health_check.db",
    # "health_check.contrib.migrations",
    # "health_check.contrib.redis",
    "django_extensions",
    "django_ajax_tables",
    "silk",
]

# Middleware
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "silk.middleware.SilkyMiddleware",
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
    "nautobot.core.middleware.UserDefinedTimeZoneMiddleware",
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
            "environment": "jinja2.sandbox.SandboxedEnvironment",
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
CONSTANCE_DATABASE_CACHE_BACKEND = "default"
# Constance defaults to a 24-hour timeout when autofilling its cache, which is undesirable in many cases.
CONSTANCE_DATABASE_CACHE_AUTOFILL_TIMEOUT = int(os.getenv("NAUTOBOT_CACHES_TIMEOUT", "300"))
CONSTANCE_IGNORE_ADMIN_VERSION_CHECK = True  # avoid potential errors in a multi-node deployment

CONSTANCE_ADDITIONAL_FIELDS = {
    "per_page_defaults_field": [
        "nautobot.core.forms.fields.JSONArrayFormField",
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
    "optional_json_field": [
        "django.forms.fields.JSONField",
        {
            "required": False,
        },
    ],
    "optional_date_field": [
        "django.forms.DateField",
        {
            "widget": "nautobot.core.forms.widgets.DatePicker",
            "required": False,
        },
    ],
}

CONSTANCE_CONFIG = {
    "ALLOW_REQUEST_PROFILING": ConstanceConfigItem(
        default=False,
        help_text="Allow users to enable request profiling on their login session.",
        field_type=bool,
    ),
    "BANNER_BOTTOM": ConstanceConfigItem(
        default="",
        help_text="Custom Markdown or limited HTML to display in a banner at the bottom of all pages.",
    ),
    "BANNER_LOGIN": ConstanceConfigItem(
        default="",
        help_text="Custom Markdown or limited HTML to display in a banner at the top of the login page.",
    ),
    "BANNER_TOP": ConstanceConfigItem(
        default="",
        help_text="Custom Markdown or limited HTML to display in a banner at the top of all pages.",
    ),
    "CHANGELOG_RETENTION": ConstanceConfigItem(
        default=90,
        help_text="Number of days to retain object changelog history.\nSet this to 0 to retain changes indefinitely.",
        field_type=int,
    ),
    "DEVICE_NAME_AS_NATURAL_KEY": ConstanceConfigItem(
        default=False,
        help_text="Device names are not guaranteed globally-unique by Nautobot but in practice they often are. "
        "Set this to True to use the device name alone as the natural key for Device objects. "
        "Set this to False to use the sequence (name, tenant, location) as the natural key instead.",
        field_type=bool,
    ),
    "DEPLOYMENT_ID": ConstanceConfigItem(
        default="",
        help_text="Randomly generated UUID used to identify this installation.\n"
        "Used for sending anonymous installation metrics, when settings.INSTALLATION_METRICS_ENABLED is set to True.",
        field_type=str,
    ),
    "JOB_CREATE_FILE_MAX_SIZE": ConstanceConfigItem(
        default=10 << 20,
        help_text=mark_safe(
            "Maximum size (in bytes) of any single file generated by a <code>Job.create_file()</code> call."
        ),
        field_type=int,
    ),
    "LOCATION_NAME_AS_NATURAL_KEY": ConstanceConfigItem(
        default=False,
        help_text="Location names are not guaranteed globally-unique by Nautobot but in practice they often are. "
        "Set this to True to use the location name alone as the natural key for Location objects. "
        "Set this to False to use the sequence (name, parent__name, parent__parent__name, ...) "
        "as the natural key instead.",
        field_type=bool,
    ),
    "MAX_PAGE_SIZE": ConstanceConfigItem(
        default=_MAX_PAGE_SIZE_DEFAULT,
        help_text="Maximum number of objects that a user can list in one UI page or one API call.\n"
        "If set to 0, a user can retrieve an unlimited number of objects.",
        field_type=int,
    ),
    "PAGINATE_COUNT": ConstanceConfigItem(
        default=_PAGINATE_COUNT_DEFAULT,
        help_text="Default number of objects to display per page when listing objects in the UI and/or REST API.",
        field_type=int,
    ),
    "PER_PAGE_DEFAULTS": ConstanceConfigItem(
        default=[25, 50, 100, 250, 500, 1000],
        help_text="Pagination options to present to the user to choose amongst.\n"
        "For proper user experience, this list should include the PAGINATE_COUNT and MAX_PAGE_SIZE values as options.",
        # Use custom field type defined above
        field_type="per_page_defaults_field",
    ),
    "NETWORK_DRIVERS": ConstanceConfigItem(
        default={},
        help_text=mark_safe(
            "Extend or override default Platform.network_driver translations provided by "
            '<a href="https://netutils.readthedocs.io/en/latest/user/lib_use_cases_lib_mapper/">netutils</a>. '
            "Enter a dictionary in JSON format, for example:\n"
            '<pre><code class="language-json">{\n'
            '    "netmiko": {"my_network_driver": "cisco_ios"},\n'
            '    "pyats": {"my_network_driver": "iosxe"} \n'
            "}</code></pre>",
        ),
        # Use custom field type defined above
        field_type="optional_json_field",
    ),
    "NTC_SUPPORT_CONTRACT_EXPIRATION_DATE": ConstanceConfigItem(
        default="",
        help_text="Expiration date for an active Nautobot support contract with Network to Code. "
        "This value is displayed in the About page to provide additional support information.",
        field_type="optional_date_field",
    ),
    "PREFER_IPV4": ConstanceConfigItem(
        default=False,
        help_text="Whether to prefer IPv4 primary addresses over IPv6 primary addresses for devices.",
        field_type=bool,
    ),
    "RACK_ELEVATION_DEFAULT_UNIT_HEIGHT": ConstanceConfigItem(
        default=22, help_text="Default height (in pixels) of a rack unit in a rack elevation diagram", field_type=int
    ),
    "RACK_ELEVATION_DEFAULT_UNIT_WIDTH": ConstanceConfigItem(
        default=230, help_text="Default width (in pixels) of a rack unit in a rack elevation diagram", field_type=int
    ),
    "RACK_ELEVATION_UNIT_TWO_DIGIT_FORMAT": ConstanceConfigItem(
        default=False,
        help_text="Enables two-digit format for the rack unit numbering in a rack elevation diagram",
        field_type=bool,
    ),
    "RELEASE_CHECK_TIMEOUT": ConstanceConfigItem(
        default=24 * 3600,
        help_text="Number of seconds (must be at least 3600, or one hour) to cache the result of a release check "
        "before checking again for a new release.",
        # Use custom field type defined above
        field_type="release_check_timeout_field",
    ),
    "RELEASE_CHECK_URL": ConstanceConfigItem(
        default="",
        help_text="URL of GitHub repository REST API endpoint to poll periodically for availability of new Nautobot releases.\n"
        'This can be set to the official repository "https://api.github.com/repos/nautobot/nautobot/releases" or '
        "a custom fork.\nSet this to an empty string to disable automatic update checks.",
        # Use custom field type defined above
        field_type="release_check_url_field",
    ),
    "SUPPORT_MESSAGE": ConstanceConfigItem(
        default="",
        help_text="Help message to include on 4xx and 5xx error pages. "
        "Markdown is supported, as are some HTML tags and attributes.\n"
        "If unspecified, instructions to join Network to Code's Slack community will be provided.",
    ),
}

CONSTANCE_CONFIG_FIELDSETS = {
    "Banners": ["BANNER_LOGIN", "BANNER_TOP", "BANNER_BOTTOM"],
    "Change Logging": ["CHANGELOG_RETENTION"],
    "Device Connectivity": ["NETWORK_DRIVERS", "PREFER_IPV4"],
    "Installation Metrics": ["DEPLOYMENT_ID"],
    "Natural Keys": ["DEVICE_NAME_AS_NATURAL_KEY", "LOCATION_NAME_AS_NATURAL_KEY"],
    "Pagination": ["PAGINATE_COUNT", "MAX_PAGE_SIZE", "PER_PAGE_DEFAULTS"],
    "Performance": ["JOB_CREATE_FILE_MAX_SIZE"],
    "Rack Elevation Rendering": [
        "RACK_ELEVATION_DEFAULT_UNIT_HEIGHT",
        "RACK_ELEVATION_DEFAULT_UNIT_WIDTH",
        "RACK_ELEVATION_UNIT_TWO_DIGIT_FORMAT",
    ],
    "Release Checking": ["RELEASE_CHECK_URL", "RELEASE_CHECK_TIMEOUT"],
    "User Interface": ["SUPPORT_MESSAGE", "NTC_SUPPORT_CONTRACT_EXPIRATION_DATE"],
    "Debugging": ["ALLOW_REQUEST_PROFILING"],
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

# The django-redis cache is used to establish concurrent locks using Redis.
CACHES = {
    "default": {
        "BACKEND": os.getenv(
            "NAUTOBOT_CACHES_BACKEND",
            "django_prometheus.cache.backends.redis.RedisCache" if METRICS_ENABLED else "django_redis.cache.RedisCache",
        ),
        "LOCATION": parse_redis_connection(redis_database=1),
        "TIMEOUT": int(os.getenv("NAUTOBOT_CACHES_TIMEOUT", "300")),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": "",
        },
    }
}

# Number of seconds to cache ContentType lookups. Set to 0 to disable caching.
CONTENT_TYPE_CACHE_TIMEOUT = int(os.getenv("NAUTOBOT_CONTENT_TYPE_CACHE_TIMEOUT", "0"))

#
# Celery (used for background processing)
#

# Celery Beat heartbeat file path - will be touched by Beat each time it wakes up as a proof-of-health.
CELERY_BEAT_HEARTBEAT_FILE = os.getenv(
    "NAUTOBOT_CELERY_BEAT_HEARTBEAT_FILE",
    os.path.join(tempfile.gettempdir(), "nautobot_celery_beat_heartbeat"),
)

# Celery broker URL used to tell workers where queues are located
CELERY_BROKER_URL = os.getenv("NAUTOBOT_CELERY_BROKER_URL", parse_redis_connection(redis_database=0))

# Celery results backend URL to tell workers where to publish task results - DO NOT CHANGE THIS
CELERY_RESULT_BACKEND = "nautobot.core.celery.backends.NautobotDatabaseBackend"

# Enables extended task result attributes (name, args, kwargs, worker, retries, queue, delivery_info) to be written to backend.
CELERY_RESULT_EXTENDED = True

# A value of None or 0 means results will never expire (depending on backend specifications).
CELERY_RESULT_EXPIRES = None

# Instruct celery to report the started status of a job, instead of just `pending`, `finished`, or `failed`
CELERY_TASK_TRACK_STARTED = True

# If enabled, a `task-sent` event will be sent for every task so tasks can be tracked before they're consumed by a worker.
CELERY_TASK_SEND_SENT_EVENT = True

# How many tasks a worker is allowed to reserve for its own consumption and execution.
# If set to zero (not recommended) a single worker can reserve all tasks even if other workers are free.
# For short running tasks (such as webhooks) you may want to set this to a larger number to increase throughput.
# Conversely, for long running tasks (such as SSoT or Golden-Config Jobs at scale) you may want to set this to 1
# so that a worker executing a long-running task will not prefetch other tasks, which would block their execution
# until the long-running task completes.
# https://docs.celeryq.dev/en/stable/userguide/optimizing.html#prefetch-limits
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv("NAUTOBOT_CELERY_WORKER_PREFETCH_MULTIPLIER", "4"))

# If enabled stdout and stderr of running jobs will be redirected to the task logger.
CELERY_WORKER_REDIRECT_STDOUTS = is_truthy(os.getenv("NAUTOBOT_CELERY_WORKER_REDIRECT_STDOUTS", "True"))

# The log level of log messages generated by redirected job stdout and stderr.
# Can be one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.
CELERY_WORKER_REDIRECT_STDOUTS_LEVEL = os.getenv("NAUTOBOT_CELERY_WORKER_REDIRECT_STDOUTS_LEVEL", "WARNING")

# Send task-related events so that tasks can be monitored using tools like flower.
# Sets the default value for the workers -E argument.
CELERY_WORKER_SEND_TASK_EVENTS = True

# Default celery queue name that will be used by workers and tasks if no queue is specified
CELERY_TASK_DEFAULT_QUEUE = os.getenv("NAUTOBOT_CELERY_TASK_DEFAULT_QUEUE", "default")

# Global task time limits (seconds)
# Exceeding the soft limit will result in a SoftTimeLimitExceeded exception,
# while exceeding the hard limit will result in a SIGKILL.
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("NAUTOBOT_CELERY_TASK_SOFT_TIME_LIMIT", str(5 * 60)))
CELERY_TASK_TIME_LIMIT = int(os.getenv("NAUTOBOT_CELERY_TASK_TIME_LIMIT", str(10 * 60)))

# Ports for prometheus metric HTTP server running on the celery worker.
# Normally this should be set to a single port, unless you have multiple workers running on a single machine, i.e.
# sharing the same available ports. In that case you need to specify a range of ports greater than or equal to the
# highest amount of workers you are running on a single machine (comma-separated, like "8080,8081,8082"). You can then
# use the `target_limit` parameter to the Prometheus `scrape_config` to ensure you are not getting duplicate metrics in
# that case. Set this to an empty string to disable it.
CELERY_WORKER_PROMETHEUS_PORTS = []
if os.getenv("NAUTOBOT_CELERY_WORKER_PROMETHEUS_PORTS"):
    CELERY_WORKER_PROMETHEUS_PORTS = [
        int(value) for value in os.getenv("NAUTOBOT_CELERY_WORKER_PROMETHEUS_PORTS").split(_CONFIG_SETTING_SEPARATOR)
    ]

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
    "header_bullet": os.getenv(
        "NAUTOBOT_BRANDING_FILEPATHS_HEADER_BULLET", None
    ),  # bullet image used for various view headers
    "nav_bullet": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_NAV_BULLET", None),  # bullet image used for nav menu headers
    "css": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_CSS", None),  # Custom global CSS
    "javascript": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_JAVASCRIPT", None),  # Custom global JavaScript
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


# Custom JSON schema serializer field type mappingss. These will be added to
# `NautobotProcessingMixin.TYPE_MAP`.
# Format: `{serializer_field_class.__name__}` => `{json_schema_type}`
# See: https://github.com/yoyowallet/drf-react-template-framework#settings
DRF_REACT_TEMPLATE_TYPE_MAP = {
    "ContentTypeField": {"type": "string", "enum": "choices"},
    "CustomFieldsDataField": {"type": "object", "widget": "textarea"},
    "DateTimeField": {"type": "string", "format": "date-time", "widget": "date-time"},
    "ImageField": {"type": "string", "format": "data-url"},
    "IPFieldSerializer": {"type": "string"},
    "JSONField": {"type": "string", "widget": "textarea"},
    "MultipleChoiceJSONField": {"type": "array", "required": [], "enum": "choices"},
    "ManyRelatedField": {"type": "array", "required": []},
    #
    # Foreign Key fields
    #
    # enum=choices is the one that works in the UI as a related field but it
    # includes ALL related objects in the schema.
    # "NautobotHyperlinkedRelatedField": {"type": "string", "enum": "choices"},
    # readOnly=True disables the fields in the UI; not what we want.
    # "NautobotHyperlinkedRelatedField": {"type": "string", "readOnly": True},
    # type=string results in a free text field; also not what we want. For now,
    # however, this will keep things moving so the unit tests pass.
    "NautobotHyperlinkedRelatedField": {"type": "object"},
    "PrimaryKeyRelatedField": {"type": "string", "enum": "choices"},
    "RelationshipsDataField": {"type": "object"},
    "SlugField": {"type": "string"},
    "TimeZoneSerializerField": {"type": "string"},
    "UUIDField": {"type": "string", "format": "uuid"},
}


#
# django-silk is used for optional request profiling for debugging purposes
#

SILKY_PYTHON_PROFILER = True
SILKY_PYTHON_PROFILER_BINARY = True
SILKY_PYTHON_PROFILER_EXTENDED_FILE_NAME = True
SILKY_ANALYZE_QUERIES = False  # See the docs for the implications of turning this on https://github.com/jazzband/django-silk?tab=readme-ov-file#enable-query-analysis
SILKY_AUTHENTICATION = True  # User must login
SILKY_AUTHORISATION = True  # User must have permissions


# This makes it so that only superusers can access the silk UI
def silk_user_permissions(user):
    return user.is_superuser


SILKY_PERMISSIONS = silk_user_permissions


# This ensures profiling only happens when enabled on the sessions. Users are able
# to turn this on or off in their user profile. It also ignores health-check requests.
def silk_request_logging_intercept_logic(request):
    if request.path != "/health/":
        if request.session.get("silk_record_requests", False):
            return True
    return False


SILKY_INTERCEPT_FUNC = silk_request_logging_intercept_logic

#
# Kubernetes settings variables
#

# Host of the kubernetes pod created in the kubernetes cluster
KUBERNETES_DEFAULT_SERVICE_ADDRESS = os.getenv("NAUTOBOT_KUBERNETES_DEFAULT_SERVICE_ADDRESS", "")

# A dictionary that stores the kubernetes pod manifest used to create a job pod in the kubernetes cluster
KUBERNETES_JOB_MANIFEST = {}

# Name of the kubernetes pod created in the kubernetes cluster
KUBERNETES_JOB_POD_NAME = os.getenv("NAUTOBOT_KUBERNETES_JOB_POD_NAME", "")

# Namespace of the kubernetes pod created in the kubernetes cluster
KUBERNETES_JOB_POD_NAMESPACE = os.getenv("NAUTOBOT_KUBERNETES_JOB_POD_NAMESPACE", "")

# File path to the SSL CA CERT used for authentication to create the job and job pod
KUBERNETES_SSL_CA_CERT_PATH = os.getenv(
    "NAUTOBOT_KUBERNETES_SSL_CA_CERT_PATH", "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
)

# File path to the Bearer token used for authentication to create the job and job pod
KUBERNETES_TOKEN_PATH = os.getenv(
    "NAUTOBOT_KUBERNETES_TOKEN_PATH", "/var/run/secrets/kubernetes.io/serviceaccount/token"
)
