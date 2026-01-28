from django.test import override_settings, TestCase

from nautobot.core import checks
from nautobot.dcim.choices import DeviceUniquenessChoices


class CheckCoreSettingsTest(TestCase):
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

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        },
    )
    def test_check_nautobotjobfiles_key_in_storages(self):
        """Error if STORAGES dict doesn't include 'nautobotjobfiles' as a key."""
        self.assertEqual(checks.check_storages_includes_nautobotjobfiles(None), [checks.E009])

    @override_settings(
        DEVICE_NAME_AS_NATURAL_KEY=True,
    )
    def test_check_deprecated_device_name_as_natural_key(self):
        """Warn if DEVICE_NAME_AS_NATURAL_KEY is defined in settings."""
        self.assertEqual(
            checks.check_deprecated_device_name_as_natural_key(None),
            [checks.W006],
        )

    @override_settings(
        DEVICE_UNIQUENESS="invalid_value",
    )
    def test_check_invalid_device_uniqueness_value(self):
        """Warn if DEVICE_UNIQUENESS is set to an invalid value."""
        self.assertEqual(
            checks.check_valid_value_for_device_uniqueness(None),
            [checks.W007],
        )

    @override_settings(
        DEVICE_UNIQUENESS=DeviceUniquenessChoices.NAME,
    )
    def test_check_valid_device_uniqueness_value(self):
        """No warning if DEVICE_UNIQUENESS is set to a valid value."""
        self.assertEqual(checks.check_valid_value_for_device_uniqueness(None), [])

    def test_check_for_deprecated_storage_settings(self):
        """Warn if any deprecated storage settings are set."""

        for setting_name, value in [
            ("DEFAULT_FILE_STORAGE", "django.core.files.storage.FileSystemStorage"),
            ("JOB_FILE_IO_STORAGE", "db_file_storage.storage.DatabaseFileStorage"),
            ("STATICFILES_STORAGE", "django.contrib.staticfiles.storage.StaticFilesStorage"),
            ("STORAGE_BACKEND", "django.core.files.storage.FileSystemStorage"),
            ("STORAGE_CONFIG", "{}"),
        ]:
            with override_settings(**{setting_name: value}):
                self.assertNotEqual(checks.check_for_deprecated_storage_settings(None), [])

        # No warnings with default nautobot_config
        self.assertEqual(checks.check_for_deprecated_storage_settings(None), [])
