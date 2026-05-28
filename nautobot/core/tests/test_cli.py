import importlib.util
import os.path
from unittest import mock

from nautobot.core.cli import _preprocess_settings, migrate_deprecated_templates
from nautobot.core.testing import TestCase


class TestMigrateTemplates(TestCase):
    def test_template_replacements(self):
        """Verify that all old templates are replaced by a single new template."""
        audit_dict = {}
        for new_template, old_templates in migrate_deprecated_templates.TEMPLATE_REPLACEMENTS.items():
            for old_template in old_templates:
                self.assertNotIn(old_template, audit_dict)
                audit_dict[old_template] = new_template

    def test_replace_template_references_no_change(self):
        content = """
        {% extends "base.html" %}
        {% block content %}
        <h1>Hello, World!</h1>
        {% endblock %}
        """
        replaced_content, was_updated = migrate_deprecated_templates.replace_template_references(content)
        self.assertFalse(was_updated)
        self.assertEqual(replaced_content, content)

    def test_replace_template_references(self):
        original_content = """
        {% extends "generic/object_bulk_import.html" %}
        {% block content %}
        <h1>Hello, World!</h1>
        {% endblock %}
        """
        new_content = """
        {% extends "generic/object_bulk_create.html" %}
        {% block content %}
        <h1>Hello, World!</h1>
        {% endblock %}
        """
        replaced_content, was_updated = migrate_deprecated_templates.replace_template_references(original_content)
        self.assertTrue(was_updated)
        self.assertEqual(replaced_content, new_content)


@mock.patch("nautobot.core.cli.load_plugins")
@mock.patch("nautobot.core.cli.load_event_brokers")
class TestPreprocessSettings(TestCase):
    """Tests for the `_preprocess_settings` function in nautobot.core.cli, as it's important to Nautobot startup."""

    def load_settings_module(self):
        # Load the testing nautobot_config.py as a self-contained module
        config_path = os.path.join(os.path.dirname(__file__), "nautobot_config.py")
        spec = importlib.util.spec_from_file_location("test_nautobot_config", config_path)
        settings_module = importlib.util.module_from_spec(spec)
        # nautobot.core.cli.load_settings would do the below, but obviously we don't want to do that here:
        # sys.modules["nautobot_config"] = settings_module
        spec.loader.exec_module(settings_module)
        return settings_module, config_path

    def test_basic_path(self, mock_load_event_brokers, mock_load_plugins):
        """Basic operation of the function."""
        settings_module, config_path = self.load_settings_module()

        # Process the settings module
        _preprocess_settings(settings_module, config_path)

        # _preprocess_settings should have set SETTINGS_PATH on the module
        self.assertEqual(settings_module.SETTINGS_PATH, config_path)

        # the default test settings have no EXTRA_* settings to handle

        # all media paths should exist
        self.assertTrue(os.path.isdir(settings_module.GIT_ROOT))
        self.assertTrue(os.path.isdir(settings_module.JOBS_ROOT))
        self.assertTrue(os.path.isdir(settings_module.MEDIA_ROOT))
        self.assertTrue(os.path.isdir(os.path.join(settings_module.MEDIA_ROOT, "devicetype-images")))
        self.assertTrue(os.path.isdir(os.path.join(settings_module.MEDIA_ROOT, "image-attachments")))
        self.assertTrue(os.path.isdir(settings_module.STATIC_ROOT))

        # databases should be using the prometheus backends
        self.assertTrue(settings_module.METRICS_ENABLED)
        self.assertIn("django_prometheus.db.backends", settings_module.DATABASES["default"]["ENGINE"])

        # job_logs database connection should exist
        self.assertIn("job_logs", settings_module.DATABASES)
        self.assertIn("TEST", settings_module.DATABASES["job_logs"])
        self.assertEqual(settings_module.DATABASES["job_logs"]["TEST"], {"MIRROR": "default"})
        for key, value in settings_module.DATABASES["default"].items():
            if key == "TEST":
                continue
            self.assertEqual(value, settings_module.DATABASES["job_logs"][key])

        # STORAGES should remain as default
        self.assertEqual(
            settings_module.STORAGES,
            {
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
                "nautobotjobfiles": {"BACKEND": "db_file_storage.storage.DatabaseFileStorage"},
            },
        )

        mock_load_plugins.assert_called_with(settings_module)
        mock_load_event_brokers.assert_called_with(settings_module.EVENT_BROKERS)

    def test_EXTRA_behavior(self, *args):
        """Handling of special settings like EXTRA_INSTALLED_APPS and EXTRA_MIDDLEWARE."""
        settings_module, config_path = self.load_settings_module()

        # Inject EXTRA_INSTALLED_APPS and EXTRA_MIDDLEWARE to the settings module for test purposes
        settings_module.EXTRA_INSTALLED_APPS = ["foo.bar"]
        settings_module.EXTRA_MIDDLEWARE = ("baz.bat",)

        # Process the settings module
        _preprocess_settings(settings_module, config_path)

        self.assertIn("foo.bar", settings_module.INSTALLED_APPS)
        # more specifically:
        self.assertEqual("foo.bar", settings_module.INSTALLED_APPS[-1])
        self.assertIn("baz.bat", settings_module.MIDDLEWARE)
        # more specifically:
        self.assertEqual("baz.bat", settings_module.MIDDLEWARE[-1])
