###################################################################
#  This file serves as a base configuration for testing purposes  #
#  only. It is not intended for production use.                   #
###################################################################

import os

from nautobot.core.settings import *  # noqa: F401,F403
from nautobot.core.settings_funcs import parse_redis_connection

# No host checks required during tests
ALLOWED_HOSTS = ["*"]

# Discover test jobs from within the Nautobot source code
JOBS_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "extras", "tests", "example_jobs"
)

# Enable both example plugins
PLUGINS = [
    "example_plugin",
    "example_plugin_with_view_override",
]

# Hard-code the SECRET_KEY for simplicity
SECRET_KEY = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Redis variables

# Use *different* redis_databases than the ones (0 and 1) used during non-automated-testing operations.
CACHES["default"]["LOCATION"] = parse_redis_connection(redis_database=2)  # noqa: F405
CACHEOPS_REDIS = parse_redis_connection(redis_database=3)
CACHEOPS_ENABLED = False  # 2.0 TODO(jathan): Remove me.

# Testing storages within cli.py
STORAGE_CONFIG = {
    "AWS_ACCESS_KEY_ID": "ASFWDAMWWOQMEOQMWPMDA<WPDA",
    "AWS_SECRET_ACCESS_KEY": "ASFKMWADMsacasdaw/dawrt1231541231231",
    "AWS_STORAGE_BUCKET_NAME": "nautobot",
    "AWS_S3_REGION_NAME": "us-west-1",
}


# Enable test data factories, as they're a pre-requisite for Nautobot core tests.
TEST_USE_FACTORIES = True
# For now, use a constant PRNG seed for consistent results. In the future we can remove this for fuzzier testing.
TEST_FACTORY_SEED = "Nautobot"
# File in which all performance-specifc test baselines are stored
TEST_PERFORMANCE_BASELINE_FILE = "nautobot/core/tests/performance_baselines.yml"
