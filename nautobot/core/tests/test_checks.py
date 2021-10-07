from django.test import TestCase
from django.test import override_settings

from nautobot.core import checks


class CheckCoreSettingsTest(TestCase):
    @override_settings(
        CACHEOPS_DEFAULTS={"timeout": 0},
    )
    def test_check_cache_timeout(self):
        """Error if CACHEOPS_DEFAULTS['timeout'] is 0."""
        self.assertEqual(checks.check_cache_timeout(None), [checks.E001])

    @override_settings(
        AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
    )
    def test_check_object_permissions_backend(self):
        """
        Error if 'nautobot.core.authentication.ObjectPermissionBackend' not in AUTHENTICATION_BACKENDS.
        """
        self.assertEqual(checks.check_object_permissions_backend(None), [checks.E002])

    @override_settings(
        RELEASE_CHECK_TIMEOUT=0,
    )
    def test_check_release_check_timeout(self):
        """Error if RELEASE_CHECK_TIMEOUT < 3600."""
        self.assertEqual(checks.check_release_check_timeout(None), [checks.E003])

    @override_settings(
        RELEASE_CHECK_URL="bogus url://tom.horse",
    )
    def test_check_release_check_url(self):
        """Error if RELEASE_CHECK_URL is not a valid URL."""
        self.assertEqual(checks.check_release_check_url(None), [checks.E004])

    @override_settings(
        STORAGE_BACKEND=None,
        STORAGE_CONFIG={"test_key": "test_value"},
    )
    def test_check_storage_config_and_backend(self):
        """Warn if STORAGE_CONFIG and STORAGE_BACKEND aren't mutually set."""
        self.assertEqual(checks.check_storage_config_and_backend(None), [checks.W005])

    @override_settings(
        MAINTENANCE_MODE=True,
        SESSION_ENGINE="django.contrib.sessions.backends.db",
    )
    def test_check_maintenance_mode(self):
        """Error if MAINTENANCE_MODE is set and yet SESSION_ENGINE is still storing sessions in the db."""
        self.assertEqual(checks.check_maintenance_mode(None), [checks.E005])
