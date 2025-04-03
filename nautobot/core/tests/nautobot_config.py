###################################################################
#  This file serves as a base configuration for testing purposes  #
#  only. It is not intended for production use.                   #
###################################################################

import os

from nautobot.core.settings import *  # noqa: F403  # undefined-local-with-import-star
from nautobot.core.settings_funcs import parse_redis_connection

ALLOWED_HOSTS = ["nautobot.example.com"]

# Discover test jobs from within the Nautobot source code
JOBS_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "extras", "test_jobs"
)

# Enable both example apps
PLUGINS = [
    "example_app",
    "example_app_with_view_override",
]

# Hard-code the SECRET_KEY for simplicity
SECRET_KEY = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"  # noqa: S105  # hardcoded-password-string

# Redis variables

# Use *different* redis_databases than the ones (0 and 1) used during non-automated-testing operations.
CACHES["default"]["LOCATION"] = parse_redis_connection(redis_database=2)  # noqa: F405  # undefined-local-with-import-star-usage

# Testing storages within cli.py
STORAGE_CONFIG = {
    "AWS_ACCESS_KEY_ID": "ASFWDAMWWOQMEOQMWPMDA<WPDA",
    "AWS_SECRET_ACCESS_KEY": "ASFKMWADMsacasdaw/dawrt1231541231231",
    "AWS_STORAGE_BUCKET_NAME": "nautobot",
    "AWS_S3_REGION_NAME": "us-west-1",
}

# Use in-memory Constance backend instead of database backend so that settings don't leak between parallel tests.
CONSTANCE_BACKEND = "constance.backends.memory.MemoryBackend"

# Enable test data factories, as they're a pre-requisite for Nautobot core tests.
TEST_USE_FACTORIES = True
# For now, use a constant PRNG seed for consistent results. In the future we can remove this for fuzzier testing.
TEST_FACTORY_SEED = "Nautobot"

# Make Celery run synchronously (eager), to always store eager results, and run the broker in-memory.
# NOTE: Celery does not honor the TASK_TRACK_STARTED config when running in eager mode, so the job result is not saved until after the task completes.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_STORE_EAGER_RESULT = True
CELERY_BROKER_URL = "memory://"

# Metrics need to enabled in this config as overriding them with override_settings will not actually enable them
METRICS_ENABLED = True

METRICS_AUTHENTICATED = True

CONTENT_TYPE_CACHE_TIMEOUT = 0

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
