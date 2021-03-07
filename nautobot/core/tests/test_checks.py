from django.test import TestCase
from django.test import override_settings

from nautobot.core import checks


class CheckCacheopsDefaultsTest(TestCase):
    @override_settings(
        CACHEOPS_DEFAULTS={"timeout": 0},
    )
    def test_timeout_invalid(self):
        """Error if CACHEOPS_DEFAULTS['timeout'] is 0."""
        self.assertEqual(checks.cache_timeout_check(None), [checks.E001])
