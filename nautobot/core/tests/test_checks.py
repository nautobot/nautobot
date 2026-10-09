from django.test import override_settings, TestCase

from nautobot.core import checks
from nautobot.dcim.choices import DeviceUniquenessChoices

SETTING = "NAUTOBOT_RATE_LIMITING_CUSTOM_COMPLEXITY_COST_ESTIMATION_FUNCTION"
NOT_A_FUNCTION = "a string, not a function"


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

    def test_check_for_removed_storage_settings(self):
        """Error if any removed storage settings are set."""

        for setting_name, value in [
            ("DEFAULT_FILE_STORAGE", "django.core.files.storage.FileSystemStorage"),
            ("JOB_FILE_IO_STORAGE", "db_file_storage.storage.DatabaseFileStorage"),
            ("STATICFILES_STORAGE", "django.contrib.staticfiles.storage.StaticFilesStorage"),
            ("STORAGE_BACKEND", "django.core.files.storage.FileSystemStorage"),
            ("STORAGE_CONFIG", "{}"),
        ]:
            with override_settings(**{setting_name: value}):
                self.assertNotEqual(checks.check_for_removed_storage_settings(None), [])

        # No warnings with default nautobot_config
        self.assertEqual(checks.check_for_removed_storage_settings(None), [])

    @override_settings(**{SETTING: ""})
    def test_check_custom_complexity_cost_estimation_function_unset(self):
        """No error when the setting is empty, which is the default."""
        errors = checks.check_custom_rate_limiting_complexity_cost_estimation_function(None)

        self.assertEqual(errors, [])

    @override_settings(**{SETTING: "nautobot.core.checks.check_release_check_url"})
    def test_check_custom_complexity_cost_estimation_function_importable(self):
        """No error when the dotted path resolves to a callable."""
        errors = checks.check_custom_rate_limiting_complexity_cost_estimation_function(None)

        self.assertEqual(errors, [])

    @override_settings(**{SETTING: "no_such_module.cost_function"})
    def test_check_custom_complexity_cost_estimation_function_unimportable_module(self):
        """Error if the module in the dotted path cannot be imported."""
        errors = checks.check_custom_rate_limiting_complexity_cost_estimation_function(None)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "nautobot.core.E012")

    @override_settings(**{SETTING: "nautobot.core.checks.no_such_attribute"})
    def test_check_custom_complexity_cost_estimation_function_missing_attribute(self):
        """Error if the module imports but does not define the named attribute."""
        errors = checks.check_custom_rate_limiting_complexity_cost_estimation_function(None)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "nautobot.core.E012")

    @override_settings(**{SETTING: "nautobot.core.tests.test_checks.NOT_A_FUNCTION"})
    def test_check_custom_complexity_cost_estimation_function_not_callable(self):
        """Error if the dotted path resolves to something that cannot be called."""
        errors = checks.check_custom_rate_limiting_complexity_cost_estimation_function(None)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "nautobot.core.E013")
