from email.utils import getaddresses
import os
import sys

import environ

from nautobot.core.settings import *  # noqa F401,F403

env = environ.Env(
    NAUTOBOT_ADMINS=(list, []),
    NAUTOBOT_ALLOWED_HOSTS=(list, []),
    NAUTOBOT_ALLOWED_URL_SCHEMES=(
        tuple,
        (
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
        ),
    ),
    NAUTOBOT_BANNER_TOP=(str, ""),
    NAUTOBOT_BANNER_BOTTOM=(str, ""),
    NAUTOBOT_BANNER_LOGIN=(str, ""),
    NAUTOBOT_BASE_PATH=(str, ""),
    NAUTOBOT_CACHEOPS_ENABLED=(bool, True),
    NAUTOBOT_CACHEOPS_REDIS=(str, ""),
    NAUTOBOT_CHANGELOG_RETENTION=(int, 90),
    NAUTOBOT_CORS_ALLOW_ALL_ORIGINS=(bool, False),
    NAUTOBOT_CORS_ALLOWED_ORIGINS=(list, []),
    NAUTOBOT_CORS_ALLOWED_ORIGIN_REGEXES=(list, []),
    NAUTOBOT_DATE_FORMAT=(str, "N j, Y"),
    NAUTOBOT_DATETIME_FORMAT=(str, "N j, Y g:i a"),
    NAUTOBOT_DEBUG=(bool, False),
    NAUTOBOT_ENFORCE_GLOBAL_UNIQUE=(bool, False),
    NAUTOBOT_EXEMPT_VIEW_PERMISSIONS=(list, []),
    NAUTOBOT_EXTRA_INSTALLED_APPS=(list, []),
    NAUTOBOT_INTERNAL_IPS=(tuple, ("127.0.0.1", "::1")),
    NAUTOBOT_LOGGING=(dict, {}),
    NAUTOBOT_MAINTENANCE_MODE=(bool, False),
    NAUTOBOT_MAX_PAGE_SIZE=(int, 1000),
    NAUTOBOT_METRICS_ENABLED=(bool, False),
    NAUTOBOT_NAPALM_ARGS=(dict, {}),
    NAUTOBOT_NAPALM_PASSWORD=(str, ""),
    NAUTOBOT_NAPALM_TIMEOUT=(int, 30),
    NAUTOBOT_NAPALM_USERNAME=(str, ""),
    NAUTOBOT_PAGINATE_COUNT=(int, 50),
    NAUTOBOT_PLUGINS=(list, []),
    NAUTOBOT_PLUGINS_CONFIG=(dict, {}),
    NAUTOBOT_PREFER_IPV4=(bool, False),
    NAUTOBOT_RACK_ELEVATION_DEFAULT_UNIT_HEIGHT=(int, 22),
    NAUTOBOT_RACK_ELEVATION_DEFAULT_UNIT_WIDTH=(int, 220),
    NAUTOBOT_REDIS_PASSWORD=(str, ""),
    NAUTOBOT_REDIS_PORT=(int, 6379),
    NAUTOBOT_REDIS_SSL=(bool, False),
    NAUTOBOT_REDIS_TIMEOUT=(int, 300),
    NAUTOBOT_REDIS_USER=(str, ""),
    NAUTOBOT_SECRET_KEY=(str, "{{ secret_key }}"),
    NAUTOBOT_RELEASE_CHECK_TIMEOUT=(int, 24 * 3600),
    NAUTOBOT_RELEASE_CHECK_URL=(str, None),
    NAUTOBOT_REMOTE_AUTH_AUTO_CREATE_USER=(bool, True),
    NAUTOBOT_REMOTE_AUTH_BACKEND=(str, "nautobot.core.authentication.RemoteUserBackend"),
    NAUTOBOT_REMOTE_AUTH_DEFAULT_GROUPS=(list, []),
    NAUTOBOT_REMOTE_AUTH_DEFAULT_PERMISSIONS=(dict, {}),
    NAUTOBOT_REMOTE_AUTH_ENABLED=(bool, False),
    NAUTOBOT_REMOTE_AUTH_HEADER=(str, "HTTP_REMOTE_USER"),
    NAUTOBOT_SESSION_COOKIE_AGE=(int, 1209600),  # 2 weeks, in seconds
    NAUTOBOT_SESSION_FILE_PATH=(str, None),
    NAUTOBOT_SOCIAL_AUTH_ENABLED=(bool, False),
    NAUTOBOT_SHORT_DATE_FORMAT=(str, "Y-m-d"),
    NAUTOBOT_SHORT_DATETIME_FORMAT=(str, "Y-m-d H:i"),
    NAUTOBOT_SHORT_TIME_FORMAT=(str, "H:i:s"),
    NAUTOBOT_TIME_FORMAT=(str, "g:i a"),
    NAUTOBOT_TIME_ZONE=(str, "UTC"),
)
environ.Env.read_env()

#########################
#                       #
#   Required settings   #
#                       #
#########################

# This is a list of valid fully-qualified domain names (FQDNs) for the Nautobot server. Nautobot will not permit write
# access to the server via any other hostnames. The first FQDN in the list will be treated as the preferred name.
#
# Example: ALLOWED_HOSTS = ['nautobot.example.com', 'nautobot.internal.local']
ALLOWED_HOSTS = env("NAUTOBOT_ALLOWED_HOSTS")

# PostgreSQL database configuration. See the Django documentation for a complete list of available parameters:
#   https://docs.djangoproject.com/en/stable/ref/settings/#databases
# Alternatively you can use the NAUTOBOT_DB_URL environment variable, for a list of supported URL patterns:
#   https://github.com/jacobian/dj-database-url
DATABASES = {"default": env.db("NAUTOBOT_DB_URL")}

# Nautobot uses RQ for task scheduling. These are the following defaults.
# For detailed configuration see: https://github.com/rq/django-rq#installation
RQ_QUEUES = {
    "default": {
        "HOST": env("NAUTOBOT_REDIS_HOST"),
        "PORT": env("NAUTOBOT_REDIS_PORT"),
        "DB": 0,
        "PASSWORD": env("NAUTOBOT_REDIS_PASSWORD"),
        "SSL": env("NAUTOBOT_REDIS_SSL"),
        "DEFAULT_TIMEOUT": env("NAUTOBOT_REDIS_TIMEOUT"),
    },
    # "with-sentinel": {
    #     "SENTINELS": [
    #         ("mysentinel.redis.example.com", 6379)
    #         ("othersentinel.redis.example.com", 6379)
    #     ],
    #     "MASTER_NAME": 'nautobot",
    #     "DB": 0,
    #     "PASSWORD": "",
    #     "SOCKET_TIMEOUT": None,
    #     'CONNECTION_KWARGS': {
    #         'socket_connect_timeout': 10,
    #     },
    # },
    "check_releases": {
        "HOST": env("NAUTOBOT_REDIS_HOST"),
        "PORT": env("NAUTOBOT_REDIS_PORT"),
        "DB": 0,
        "PASSWORD": env("NAUTOBOT_REDIS_PASSWORD"),
        "SSL": env("NAUTOBOT_REDIS_SSL"),
        "DEFAULT_TIMEOUT": env("NAUTOBOT_REDIS_TIMEOUT"),
    },
}

# Nautobot uses Cacheops for database query caching. These are the following defaults.
# For detailed configuration see: https://github.com/Suor/django-cacheops#setup
# Set Cache Ops variables
redis_protocol = "rediss" if env("NAUTOBOT_REDIS_SSL") else "redis"
cache_ops_pwd = env("NAUTOBOT_REDIS_PASSWORD")
cache_ops_host = env("NAUTOBOT_REDIS_HOST")
cache_ops_user = env("NAUTOBOT_REDIS_USER")
cache_ops_port = env("NAUTOBOT_REDIS_PORT")

if env("NAUTOBOT_CACHEOPS_REDIS"):
    CACHEOPS_REDIS = env("NAUTOBOT_CACHEOPS_REDIS")
else:
    CACHEOPS_REDIS = f"{redis_protocol}://{cache_ops_user}:{cache_ops_pwd}@{cache_ops_host}:{cache_ops_port}/1"

# This key is used for secure generation of random numbers and strings. It must never be exposed outside of this file.
# For optimal security, SECRET_KEY should be at least 50 characters in length and contain a mix of letters, numbers, and
# symbols. Nautobot will not run without this defined. For more information, see
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-SECRET_KEY
SECRET_KEY = env("NAUTOBOT_SECRET_KEY")


#########################
#                       #
#   Optional settings   #
#                       #
#########################

# Specify one or more name and email address tuples representing Nautobot administrators. These people will be notified of
# application errors (assuming correct email settings are provided).
# ADMINS=Full Name <email-with-name@example.com>,anotheremailwithoutname@example.com
ADMINS = getaddresses(env("NAUTOBOT_ADMINS"))

# URL schemes that are allowed within links in Nautobot
ALLOWED_URL_SCHEMES = env("NAUTOBOT_ALLOWED_URL_SCHEMES")

# Optionally display a persistent banner at the top and/or bottom of every page. HTML is allowed. To display the same
# content in both banners, define BANNER_TOP and set BANNER_BOTTOM = BANNER_TOP.
BANNER_TOP = env("NAUTOBOT_BANNER_TOP")
BANNER_BOTTOM = env("NAUTOBOT_BANNER_BOTTOM")

# Text to include on the login page above the login form. HTML is allowed.
BANNER_LOGIN = env("NAUTOBOT_BANNER_LOGIN")

# Base URL path if accessing Nautobot within a directory. For example, if installed at https://example.com/nautobot/, set:
# BASE_PATH = 'nautobot/'
BASE_PATH = env("NAUTOBOT_BASE_PATH")

# Cache timeout in seconds. Cannot be 0. Defaults to 300 (5 minutes). To disable caching, set CACHEOPS_ENABLED to False
CACHEOPS_DEFAULTS = {"timeout": env("NAUTOBOT_REDIS_TIMEOUT")}

# Set to False to disable caching with cacheops. (Default: True)
CACHEOPS_ENABLED = env("NAUTOBOT_CACHEOPS_ENABLED")

# Maximum number of days to retain logged changes. Set to 0 to retain changes indefinitely. (Default: 90)
CHANGELOG_RETENTION = env("NAUTOBOT_CHANGELOG_RETENTION")

# If True, all origins will be allowed. Other settings restricting allowed origins will be ignored.
# Defaults to False. Setting this to True can be dangerous, as it allows any website to make
# cross-origin requests to yours. Generally you'll want to restrict the list of allowed origins with
# CORS_ALLOWED_ORIGINS or CORS_ALLOWED_ORIGIN_REGEXES.
CORS_ALLOW_ALL_ORIGINS = env("NAUTOBOT_CORS_ALLOW_ALL_ORIGINS")

# A list of origins that are authorized to make cross-site HTTP requests. Defaults to [].
CORS_ALLOWED_ORIGINS = env("NAUTOBOT_CORS_ALLOWED_ORIGINS")

# A list of strings representing regexes that match Origins that are authorized to make cross-site
# HTTP requests. Defaults to [].
CORS_ALLOWED_ORIGIN_REGEXES = env("NAUTOBOT_CORS_ALLOWED_ORIGIN_REGEXES")

# The file path where jobs will be stored. A trailing slash is not needed. Note that the default value of
# this setting is inside the invoking user's home directory.
# JOBS_ROOT = os.path.expanduser('~/.nautobot/jobs')

# Set to True to enable server debugging. WARNING: Debugging introduces a substantial performance penalty and may reveal
# sensitive information about your installation. Only enable debugging while performing testing. Never enable debugging
# on a production system.
DEBUG = env("NAUTOBOT_DEBUG")

# Enforcement of unique IP space can be toggled on a per-VRF basis. To enforce unique IP space
# within the global table (all prefixes and IP addresses not assigned to a VRF), set
# ENFORCE_GLOBAL_UNIQUE to True.
ENFORCE_GLOBAL_UNIQUE = env("NAUTOBOT_ENFORCE_GLOBAL_UNIQUE")

# Exempt certain models from the enforcement of view permissions. Models listed here will be viewable by all users and
# by anonymous users. List models in the form `<app>.<model>`. Add '*' to this list to exempt all models.
EXEMPT_VIEW_PERMISSIONS = env("NAUTOBOT_EXEMPT_VIEW_PERMISSIONS")

# HTTP proxies Nautobot should use when sending outbound HTTP requests (e.g. for webhooks).
# HTTP_PROXIES = {
#     'http': 'http://10.10.1.10:3128',
#     'https': 'http://10.10.1.10:1080',
# }

# IP addresses recognized as internal to the system. The debugging toolbar will be available only to clients accessing
# Nautobot from an internal IP.
INTERNAL_IPS = env("NAUTOBOT_INTERNAL_IPS")

# Enable custom logging. Please see the Django documentation for detailed guidance on configuring custom logs:
#   https://docs.djangoproject.com/en/stable/topics/logging/
LOGGING = env("NAUTOBOT_LOGGING")

# Setting this to True will display a "maintenance mode" banner at the top of every page.
MAINTENANCE_MODE = env("NAUTOBOT_MAINTENANCE_MODE")

# An API consumer can request an arbitrary number of objects =by appending the "limit" parameter to the URL (e.g.
# "?limit=1000"). This setting defines the maximum limit. Setting it to 0 or None will allow an API consumer to request
# all objects by specifying "?limit=0".
MAX_PAGE_SIZE = env("NAUTOBOT_MAX_PAGE_SIZE")

# The file path where uploaded media such as image attachments are stored. A trailing slash is not needed. Note that
# the default value of this setting is within the invoking user's home directory
# MEDIA_ROOT = os.path.expanduser('~/.nautobot/media')

# By default uploaded media is stored on the local filesystem. Using Django-storages is also supported. Provide the
# class path of the storage driver in STORAGE_BACKEND and any configuration options in STORAGE_CONFIG. For example:
# STORAGE_BACKEND = 'storages.backends.s3boto3.S3Boto3Storage'
# STORAGE_CONFIG = {
#     'AWS_ACCESS_KEY_ID': 'Key ID',
#     'AWS_SECRET_ACCESS_KEY': 'Secret',
#     'AWS_STORAGE_BUCKET_NAME': 'nautobot',
#     'AWS_S3_REGION_NAME': 'eu-west-1',
# }

# Expose Prometheus monitoring metrics at the HTTP endpoint '/metrics'
METRICS_ENABLED = env("NAUTOBOT_METRICS_ENABLED")

# Credentials that Nautobot will uses to authenticate to devices when connecting via NAPALM.
NAPALM_USERNAME = env("NAUTOBOT_NAPALM_USERNAME")
NAPALM_PASSWORD = env("NAUTOBOT_NAPALM_PASSWORD")

# NAPALM timeout (in seconds). (Default: 30)
NAPALM_TIMEOUT = env("NAUTOBOT_NAPALM_TIMEOUT")

# NAPALM optional arguments (see https://napalm.readthedocs.io/en/latest/support/#optional-arguments). Arguments must
# be provided as a dictionary.
NAPALM_ARGS = env("NAUTOBOT_NAPALM_ARGS")

# Determine how many objects to display per page within a list. (Default: 50)
PAGINATE_COUNT = env("NAUTOBOT_PAGINATE_COUNT")

# Enable installed plugins. Add the name of each plugin to the list.
PLUGINS = env("NAUTOBOT_PLUGINS")

# Plugins configuration settings. These settings are used by various plugins that the user may have installed.
# Each key in the dictionary is the name of an installed plugin and its value is a dictionary of settings.
PLUGINS_CONFIG = env("NAUTOBOT_PLUGINS_CONFIG")

# When determining the primary IP address for a device, IPv6 is preferred over IPv4 by default. Set this to True to
# prefer IPv4 instead.
PREFER_IPV4 = env("NAUTOBOT_PREFER_IPV4")

# Rack elevation size defaults, in pixels. For best results, the ratio of width to height should be roughly 10:1.
RACK_ELEVATION_DEFAULT_UNIT_HEIGHT = env("NAUTOBOT_RACK_ELEVATION_DEFAULT_UNIT_HEIGHT")
RACK_ELEVATION_DEFAULT_UNIT_WIDTH = env("NAUTOBOT_RACK_ELEVATION_DEFAULT_UNIT_WIDTH")

# Remote authentication support
REMOTE_AUTH_ENABLED = env("NAUTOBOT_REMOTE_AUTH_ENABLED")
REMOTE_AUTH_BACKEND = env("NAUTOBOT_REMOTE_AUTH_BACKEND")
REMOTE_AUTH_HEADER = env("NAUTOBOT_REMOTE_AUTH_HEADER")
REMOTE_AUTH_AUTO_CREATE_USER = env("NAUTOBOT_REMOTE_AUTH_AUTO_CREATE_USER")
REMOTE_AUTH_DEFAULT_GROUPS = env("NAUTOBOT_REMOTE_AUTH_DEFAULT_GROUPS")
REMOTE_AUTH_DEFAULT_PERMISSIONS = env("NAUTOBOT_REMOTE_AUTH_DEFAULT_PERMISSIONS")

# This determines how often the GitHub API is called to check the latest release of Nautobot. Must be at least 1 hour.
RELEASE_CHECK_TIMEOUT = env("NAUTOBOT_RELEASE_CHECK_TIMEOUT")

# This repository is used to check whether there is a new release of Nautobot available. Set to None to disable the
# version check or use the URL below to check for release in the official Nautobot repository.
RELEASE_CHECK_URL = env("NAUTOBOT_RELEASE_CHECK_URL")
# RELEASE_CHECK_URL = 'https://api.github.com/repos/nautobot/nautobot/releases'

# The length of time (in seconds) for which a user will remain logged into the web UI before being prompted to
# re-authenticate. (Default: 1209600 [14 days])
SESSION_COOKIE_AGE = env("NAUTOBOT_SESSION_COOKIE_AGE")

# By default, Nautobot will store session data in the database. Alternatively, a file path can be specified here to use
# local file storage instead. (This can be useful for enabling authentication on a standby instance with read-only
# database access.) Note that the user as which Nautobot runs must have read and write permissions to this path.
SESSION_FILE_PATH = env("NAUTOBOT_SESSION_FILE_PATH")

# Configure SSO, for more information see docs/configuration/authentication/sso.md
SOCIAL_AUTH_ENABLED = env("NAUTOBOT_SOCIAL_AUTH_ENABLED")

# Time zone (default: UTC)
TIME_ZONE = env("NAUTOBOT_TIME_ZONE")

# Date/time formatting. See the following link for supported formats:
# https://docs.djangoproject.com/en/stable/ref/templates/builtins/#date
DATE_FORMAT = env("NAUTOBOT_DATE_FORMAT")
SHORT_DATE_FORMAT = env("NAUTOBOT_SHORT_DATE_FORMAT")
TIME_FORMAT = env("NAUTOBOT_TIME_FORMAT")
SHORT_TIME_FORMAT = env("NAUTOBOT_SHORT_TIME_FORMAT")
DATETIME_FORMAT = env("NAUTOBOT_DATETIME_FORMAT")
SHORT_DATETIME_FORMAT = env("NAUTOBOT_SHORT_DATETIME_FORMAT")

# A list of strings designating all applications that are enabled in this Django installation. Each string should be a dotted Python path to an application configuration class (preferred), or a package containing an application.
# https://nautobot.readthedocs.io/en/latest/configuration/optional-settings/#extra-applications
EXTRA_INSTALLED_APPS = env("NAUTOBOT_EXTRA_INSTALLED_APPS")


#### Extra config for dev container should be moved elsewhere
LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

# Verbose logging during normal development operation, but quiet logging during unit test execution
if not TESTING:
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
                "class": "rq.utils.ColorizingStreamHandler",
                "formatter": "normal",
            },
            "verbose_console": {
                "level": "DEBUG",
                "class": "rq.utils.ColorizingStreamHandler",
                "formatter": "verbose",
            },
        },
        "loggers": {
            "django": {"handlers": ["normal_console"], "level": "INFO"},
            "nautobot": {
                "handlers": ["verbose_console" if DEBUG else "normal_console"],
                "level": LOG_LEVEL,
            },
            "rq.worker": {
                "handlers": ["verbose_console" if DEBUG else "normal_console"],
                "level": LOG_LEVEL,
            },
        },
    }

HIDE_RESTRICTED_UI = os.environ.get("HIDE_RESTRICTED_UI", False)

# Django Debug Toolbar
DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: DEBUG and not TESTING}

if "debug_toolbar" not in INSTALLED_APPS:
    INSTALLED_APPS.append("debug_toolbar")
if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
