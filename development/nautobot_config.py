"""Nautobot development configuration file."""

import os

from nautobot.core.settings import *  # noqa: F403  # undefined-local-with-import-star

# The above results in various F405 undefined-local-with-import-star-usage,
# "may be undefined, or defined from star imports",
# which we suppress on a case-by-case basis below
from nautobot.core.settings_funcs import is_truthy

SECRET_KEY = os.getenv("NAUTOBOT_SECRET_KEY", "012345678901234567890123456789012345678901234567890123456789")

#
# Debugging defaults to True rather than False for the development environment
#
DEBUG = is_truthy(os.getenv("NAUTOBOT_DEBUG", "True"))


# Django Debug Toolbar - enabled only when debugging
if DEBUG:
    if "debug_toolbar" not in INSTALLED_APPS:  # noqa: F405
        INSTALLED_APPS.append("debug_toolbar")  # noqa: F405
    if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:  # noqa: F405
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    # By default the toolbar only displays when the request is coming from one of INTERNAL_IPS.
    # For the Docker dev environment, we don't know in advance what that IP may be, so override to skip that check
    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: DEBUG}

# Do *not* send anonymized install metrics when post_upgrade or send_installation_metrics management commands are run
INSTALLATION_METRICS_ENABLED = is_truthy(os.getenv("NAUTOBOT_INSTALLATION_METRICS_ENABLED", "False"))

#
# Logging for the development environment, taking into account the redefinition of DEBUG above
#

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"
LOGGING["loggers"]["nautobot"]["handlers"] = ["verbose_console" if DEBUG else "normal_console"]  # noqa: F405
LOGGING["loggers"]["nautobot"]["level"] = LOG_LEVEL  # noqa: F405

# Enable the following to setup structlog logging for Nautobot.
# Configures defined loggers to use structlog and overwrites all formatters and handlers.
#
# from nautobot.core.settings_funcs import setup_structlog_logging
# setup_structlog_logging(
#     LOGGING,
#     INSTALLED_APPS,
#     MIDDLEWARE,
#     log_level="DEBUG" if DEBUG else "INFO",
#     debug_db=False,  # Set to True to log all database queries
#     plain_format=bool(DEBUG),  # Set to True to use human-readable structlog format over JSON
# )

#
# Plugins
#

PLUGINS = [
    "example_app",
]

CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]
CORS_ALLOW_CREDENTIALS = True
SESSION_COOKIE_SAMESITE = None

#
# Development Environment for SSO
# Configure `invoke.yml` based on example for SSO development environment
#

# OIDC Dev ENV
if is_truthy(os.getenv("ENABLE_OIDC", "False")):
    import requests

    AUTHENTICATION_BACKENDS = (
        "social_core.backends.keycloak.KeycloakOAuth2",
        "nautobot.core.authentication.ObjectPermissionBackend",
    )
    SOCIAL_AUTH_KEYCLOAK_KEY = "nautobot"
    SOCIAL_AUTH_KEYCLOAK_SECRET = "7b1c3527-8702-4742-af69-2b74ee5742e8"  # noqa: S105  # hardcoded-password-string
    SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY = requests.get("http://keycloak:8087/realms/nautobot/", timeout=15).json()[
        "public_key"
    ]
    SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL = "http://localhost:8087/realms/nautobot/protocol/openid-connect/auth"
    SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = "http://keycloak:8087/realms/nautobot/protocol/openid-connect/token"  # noqa: S105  # hardcoded-password-string
    SOCIAL_AUTH_KEYCLOAK_VERIFY_SSL = False

METRICS_ENABLED = True
METRICS_AUTHENTICATED = False
METRICS_DISABLED_APPS = []

CELERY_WORKER_PROMETHEUS_PORTS = [8080]

# Path to the kubernetes pod manifest yaml file used to create a job pod in the kubernetes cluster.
KUBERNETES_JOB_MANIFEST = {
    "apiVersion": "batch/v1",
    "kind": "Job",
    "metadata": {"name": "nautobot-job"},
    "spec": {
        "ttlSecondsAfterFinished": 5,
        "template": {
            "spec": {
                "containers": [
                    {
                        "env": [
                            {
                                "name": "MYSQL_DATABASE",
                                "valueFrom": {"configMapKeyRef": {"key": "MYSQL_DATABASE", "name": "dev-env"}},
                            },
                            {
                                "name": "MYSQL_PASSWORD",
                                "valueFrom": {"configMapKeyRef": {"key": "MYSQL_PASSWORD", "name": "dev-env"}},
                            },
                            {
                                "name": "MYSQL_ROOT_PASSWORD",
                                "valueFrom": {"configMapKeyRef": {"key": "MYSQL_ROOT_PASSWORD", "name": "dev-env"}},
                            },
                            {
                                "name": "MYSQL_USER",
                                "valueFrom": {"configMapKeyRef": {"key": "MYSQL_USER", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_ALLOWED_HOSTS",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_ALLOWED_HOSTS", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_CHANGELOG_RETENTION",
                                "valueFrom": {
                                    "configMapKeyRef": {"key": "NAUTOBOT_CHANGELOG_RETENTION", "name": "dev-env"}
                                },
                            },
                            {
                                "name": "NAUTOBOT_CONFIG",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_CONFIG", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_CREATE_SUPERUSER",
                                "valueFrom": {
                                    "configMapKeyRef": {"key": "NAUTOBOT_CREATE_SUPERUSER", "name": "dev-env"}
                                },
                            },
                            {
                                "name": "NAUTOBOT_DB_HOST",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_DB_HOST", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_DB_NAME",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_DB_NAME", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_DB_PASSWORD",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_DB_PASSWORD", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_DB_TIMEOUT",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_DB_TIMEOUT", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_DB_USER",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_DB_USER", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_INSTALLATION_METRICS_ENABLED",
                                "valueFrom": {
                                    "configMapKeyRef": {
                                        "key": "NAUTOBOT_INSTALLATION_METRICS_ENABLED",
                                        "name": "dev-env",
                                    }
                                },
                            },
                            {
                                "name": "NAUTOBOT_LOG_DEPRECATION_WARNINGS",
                                "valueFrom": {
                                    "configMapKeyRef": {"key": "NAUTOBOT_LOG_DEPRECATION_WARNINGS", "name": "dev-env"}
                                },
                            },
                            {
                                "name": "NAUTOBOT_NAPALM_TIMEOUT",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_NAPALM_TIMEOUT", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_REDIS_HOST",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_REDIS_HOST", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_REDIS_PASSWORD",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_REDIS_PASSWORD", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_REDIS_PORT",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_REDIS_PORT", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_SECRET_KEY",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_SECRET_KEY", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_SELENIUM_HOST",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_SELENIUM_HOST", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_SELENIUM_URL",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_SELENIUM_URL", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_SUPERUSER_API_TOKEN",
                                "valueFrom": {
                                    "configMapKeyRef": {"key": "NAUTOBOT_SUPERUSER_API_TOKEN", "name": "dev-env"}
                                },
                            },
                            {
                                "name": "NAUTOBOT_SUPERUSER_EMAIL",
                                "valueFrom": {
                                    "configMapKeyRef": {"key": "NAUTOBOT_SUPERUSER_EMAIL", "name": "dev-env"}
                                },
                            },
                            {
                                "name": "NAUTOBOT_SUPERUSER_NAME",
                                "valueFrom": {"configMapKeyRef": {"key": "NAUTOBOT_SUPERUSER_NAME", "name": "dev-env"}},
                            },
                            {
                                "name": "NAUTOBOT_SUPERUSER_PASSWORD",
                                "valueFrom": {
                                    "configMapKeyRef": {"key": "NAUTOBOT_SUPERUSER_PASSWORD", "name": "dev-env"}
                                },
                            },
                            {
                                "name": "PGPASSWORD",
                                "valueFrom": {"configMapKeyRef": {"key": "PGPASSWORD", "name": "dev-env"}},
                            },
                            {
                                "name": "POSTGRES_DB",
                                "valueFrom": {"configMapKeyRef": {"key": "POSTGRES_DB", "name": "dev-env"}},
                            },
                            {
                                "name": "POSTGRES_PASSWORD",
                                "valueFrom": {"configMapKeyRef": {"key": "POSTGRES_PASSWORD", "name": "dev-env"}},
                            },
                            {
                                "name": "POSTGRES_USER",
                                "valueFrom": {"configMapKeyRef": {"key": "POSTGRES_USER", "name": "dev-env"}},
                            },
                            {
                                "name": "REDISCLI_AUTH",
                                "valueFrom": {"configMapKeyRef": {"key": "REDISCLI_AUTH", "name": "dev-env"}},
                            },
                            {
                                "name": "REDIS_PASSWORD",
                                "valueFrom": {"configMapKeyRef": {"key": "REDIS_PASSWORD", "name": "dev-env"}},
                            },
                        ],
                        "name": "nautobot-job",
                        "image": "local/nautobot-dev:local-py3.11",
                        "ports": [{"containerPort": 8080, "protocol": "TCP"}],
                        "tty": True,
                        "volumeMounts": [
                            {"mountPath": "/opt/nautobot/media", "name": "media-root"},
                            {
                                "mountPath": "/opt/nautobot/nautobot_config.py",
                                "name": "nautobot-cm1",
                                "subPath": "nautobot_config.py",
                            },
                        ],
                    }
                ],
                "volumes": [
                    {"name": "media-root", "persistentVolumeClaim": {"claimName": "media-root"}},
                    {
                        "configMap": {
                            "items": [{"key": "nautobot_config.py", "path": "nautobot_config.py"}],
                            "name": "nautobot-cm1",
                        },
                        "name": "nautobot-cm1",
                    },
                ],
                "restartPolicy": "Never",
            }
        },
        "backoffLimit": 0,
    },
}

# Name of the kubernetes pod created in the kubernetes cluster
KUBERNETES_JOB_POD_NAME = "nautobot-job"

# Namespace of the kubernetes pod created in the kubernetes cluster
KUBERNETES_JOB_POD_NAMESPACE = "default"

# Host of the kubernetes pod created in the kubernetes cluster
KUBERNETES_DEFAULT_SERVICE_ADDRESS = "https://kubernetes.default.svc"
