import os
import sys
from unittest import mock, TestCase

from django.conf import global_settings as django_defaults
from django.test import tag
from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.validators import Draft202012Validator
import yaml

SETTINGS_DOCUMENTATION_SCHEMA = {
    "$id": "https://nautobot.com/2.2/settings-schema/strict",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$vocabulary": {
        "https://json-schema.org/draft/2020-12/vocab/core": True,
        "https://json-schema.org/draft/2020-12/vocab/applicator": True,
        "https://json-schema.org/draft/2020-12/vocab/unevaluated": True,
        "https://json-schema.org/draft/2020-12/vocab/validation": True,
        "https://json-schema.org/draft/2020-12/vocab/meta-data": True,
        "https://json-schema.org/draft/2020-12/vocab/format-annotation": True,
        "https://json-schema.org/draft/2020-12/vocab/content": True,
    },
    "$dynamicAnchor": "meta",
    "$ref": "https://json-schema.org/draft/2020-12/schema",
    "properties": {
        "default_literal": {
            "type": "string",
        },
        "details": {
            "type": "string",
        },
        "environment_variable": {
            "type": "string",
        },
        "is_constance_config": {
            "type": "boolean",
        },
        "is_required_setting": {
            "type": "boolean",
        },
        "see_also": {
            "type": "object",
        },
        "version_added": {
            "type": "string",
        },
    },
    "unevaluatedProperties": False,
}


@tag("unit")
class SettingsJSONSchemaTestCase(TestCase):
    """Test for the JSON Schema in nautobot/core/settings.yaml and the actual Nautobot configuration."""

    def setUp(self):
        file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/settings.yaml"
        with open(file_path, "r") as schemafile:
            self.schema_data = yaml.safe_load(schemafile)
        self.maxDiff = None

    def tearDown(self):
        sys.modules.pop("nautobot.core.settings", None)

    def test_schema_keys_sort_alpha(self):
        """
        Assert that the keys in the JSON Schema "properties" are sorted alphabetically.

        Uses a modified version of Python's default string sorting behavior to sort underscores before uppercase letters.
        E.g. "DATE_FORMAT" should come before "DATETIME_FORMAT".
        """

        self.assertEqual(
            sorted(self.schema_data["properties"], key=lambda s: s.replace("_", " ")),
            list(self.schema_data["properties"]),
        )

    def test_schema_valid(self):
        """Test the validity of the JSON Schema in settings.yaml as a JSON schema."""
        try:
            Draft202012Validator.check_schema(self.schema_data)
        except SchemaError as e:
            raise ValidationError({"data_schema": e.message}) from e

    def test_schema_documentation_valid(self):
        """
        Check for unrecognized keys in the schema that might indicate an incorrect attempt at defining documentation.
        """
        Draft202012Validator(schema=SETTINGS_DOCUMENTATION_SCHEMA).validate(self.schema_data)

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch.object(sys, "argv", [])  # to trick settings.TESTING to evaluate to False
    def test_default_settings_vs_schema(self):
        """Check the default settings in nautobot.core.settings against the schema."""
        sys.modules.pop("nautobot.core.settings", None)
        import nautobot.core.settings as nautobot_settings

        # The below settings are not documented in the schema as they're never intended to be modified in a deployment
        # Maybe in the future we can move the Nautobot-specific settings to a constants.py instead?
        FROZEN_SETTINGS = [
            "AUTH_USER_MODEL",
            "BASE_DIR",
            "BRANDING_POWERED_BY_URL",
            "CELERY_ACCEPT_CONTENT",
            "CELERY_BEAT_SCHEDULER",
            "CELERY_RESULT_ACCEPT_CONTENT",
            "CELERY_RESULT_BACKEND",
            "CELERY_RESULT_EXPIRES",
            "CELERY_RESULT_EXTENDED",
            "CELERY_RESULT_SERIALIZER",
            "CELERY_TASK_SEND_SENT_EVENT",
            "CELERY_TASK_SERIALIZER",
            "CELERY_TASK_TRACK_STARTED",
            "CELERY_WORKER_SEND_TASK_EVENTS",
            "CONSTANCE_ADDITIONAL_FIELDS",
            "CONSTANCE_IGNORE_ADMIN_VERSION_CHECK",
            "CONSTANCE_BACKEND",
            "CONSTANCE_CONFIG",
            "CONSTANCE_CONFIG_FIELDSETS",
            "CONSTANCE_DATABASE_CACHE_BACKEND",
            "CONSTANCE_DATABASE_PREFIX",
            "CSRF_FAILURE_VIEW",
            "DATA_UPLOAD_MAX_NUMBER_FIELDS",
            "DEFAULT_AUTO_FIELD",
            "DRF_REACT_TEMPLATE_TYPE_MAP",
            "EXEMPT_EXCLUDE_MODELS",
            "FILTERS_NULL_CHOICE_LABEL",
            "FILTERS_NULL_CHOICE_VALUE",
            "GRAPHENE",
            "HOSTNAME",
            "INSTALLED_APPS",
            "LANGUAGE_CODE",
            "LOG_LEVEL",
            "LOGIN_URL",
            "LOGIN_REDIRECT_URL",
            "MEDIA_URL",
            "MESSAGE_TAGS",
            "MIDDLEWARE",
            "PROMETHEUS_EXPORT_MIGRATIONS",
            "REST_FRAMEWORK",
            "REST_FRAMEWORK_ALLOWED_VERSIONS",
            "REST_FRAMEWORK_VERSION",
            "ROOT_URLCONF",
            "SECURE_PROXY_SSL_HEADER",
            "SHELL_PLUS_DONT_LOAD",
            "SILKY_ANALYZE_QUERIES",
            "SILKY_AUTHENTICATION",
            "SILKY_AUTHORISATION",
            "SILKY_INTERCEPT_FUNC",
            "SILKY_PERMISSIONS",
            "SILKY_PYTHON_PROFILER",
            "SILKY_PYTHON_PROFILER_BINARY",
            "SILKY_PYTHON_PROFILER_EXTENDED_FILE_NAME",
            "SOCIAL_AUTH_POSTGRES_JSONFIELD",
            "SPECTACULAR_SETTINGS",
            "STATIC_URL",
            "STATICFILES_DIRS",
            "TEMPLATES",
            "TESTING",
            "TEST_RUNNER",
            "USE_I18N",
            "USE_TZ",
            "USE_X_FORWARDED_HOST",
            "VERSION",
            "VERSION_MAJOR",
            "VERSION_MINOR",
            "WEBSERVER_WARMUP",
            "WSGI_APPLICATION",
            "X_FRAME_OPTIONS",
        ]
        keys = sorted(nautobot_settings.__dict__.keys())

        # Make sure the above list is up to date and doesn't contain cruft
        for key in FROZEN_SETTINGS:
            with self.subTest(f"Checking for FROZEN_SETTINGS entry {key} in nautobot.core.settings"):
                self.assertIn(key, keys)

        keys = [key for key in keys if key == key.upper() and not key.startswith("_") and key not in FROZEN_SETTINGS]

        for key in keys:
            with self.subTest(f"Checking for settings attribute {key} in the settings schema"):
                self.assertIn(key, self.schema_data["properties"])
            if key not in self.schema_data["properties"]:
                continue

            with self.subTest(f"Checking default value for settings attribute {key} against the schema"):
                if self.schema_data["properties"][key].get("$ref", None) in [
                    "#/definitions/absolute_path",
                    "#/definitions/callable",
                    "#/definitions/relative_path",
                ]:
                    # Functions like UI_RACK_VIEW_TRUNCATE_FUNCTION don't have a default expressable in JSON Schema,
                    # and path-like defaults probably depend on the user context
                    continue
                elif self.schema_data["properties"][key].get("default_literal", None):
                    # Probably a complicated setting that isn't easily documentable in JSON schema
                    continue
                else:
                    # Is the default in the settings correctly documented?
                    self.assertEqual(getattr(nautobot_settings, key), self.schema_data["properties"][key]["default"])

        for key in self.schema_data["properties"]:
            if key in getattr(nautobot_settings, "CONSTANCE_CONFIG"):
                # Constance settings don't have a value set by default in nautobot.core.settings,
                # but they have a default in CONSTANCE_CONFIG
                with self.subTest(f"Checking default value for Constance attribute {key} against the schema"):
                    self.assertEqual(
                        nautobot_settings.CONSTANCE_CONFIG[key].default, self.schema_data["properties"][key]["default"]
                    )
                continue
            with self.subTest(f"Checking for settings schema property {key} in nautobot.core.settings"):
                try:
                    self.assertIn(key, keys)
                except AssertionError as err:
                    if key.startswith("CELERY_"):
                        # Celery defaults aren't explicitly set, they're defined in Celery code
                        continue
                    try:
                        # Maybe it's a default Django setting?
                        self.assertIn(key, django_defaults.__dict__.keys())
                    except AssertionError as err2:
                        raise err from err2
                    self.assertEqual(getattr(django_defaults, key), self.schema_data["properties"][key]["default"])
