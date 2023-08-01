###################################################################
#  This file serves as a base configuration for testing purposes  #
#  only. It is not intended for production use.                   #
###################################################################

import os

from nautobot.core.settings import *  # noqa: F401,F403
from nautobot.core.settings_funcs import parse_redis_connection

ALLOWED_HOSTS = ["nautobot.example.com"]

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

_GROUP_INDEX = os.getenv("NAUTOBOT_TEST_GROUP_INDEX", "")
if _GROUP_INDEX:
    # For tests parallelization
    # Group with index "0" will use Redis DB 4 and 5, group with index "1" will use Redis DB 6 and 7, etc.
    _redis_index = int((int(_GROUP_INDEX) + 2) * 2)
    # Each group will use a separate SQL database
    DATABASES["default"]["TEST"] = {  # noqa: F405
        "NAME": f"nautobot_test{_GROUP_INDEX}",
    }
else:
    # No parallelization
    # Use *different* redis_databases than the ones (0 and 1) used during non-automated-testing operations.
    _redis_index = 2


# Redis variables

CACHES["default"]["LOCATION"] = parse_redis_connection(redis_database=_redis_index)  # noqa: F405
CACHEOPS_REDIS = parse_redis_connection(redis_database=_redis_index + 1)
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

# Metrics need to enabled in this config as overriding them with override_settings will not actually enable them
METRICS_ENABLED = True

TEST_OUTPUT_DIR = os.getenv("NAUTOBOT_TEST_OUTPUT_DIR")
DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT = 0
CONTENT_TYPE_CACHE_TIMEOUT = 0
