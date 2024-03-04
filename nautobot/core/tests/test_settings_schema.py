import os
import sys
from unittest import mock, TestCase

from django.conf import global_settings as django_defaults
from django.test import tag
import faker
from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.validators import Draft202012Validator
import yaml

from nautobot.core.settings_funcs import is_truthy

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
            self.settings_schema = yaml.safe_load(schemafile)
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
            sorted(self.settings_schema["properties"], key=lambda s: s.replace("_", " ")),
            list(self.settings_schema["properties"]),
        )

    def test_schema_valid(self):
        """Test the validity of the JSON Schema in settings.yaml as a JSON schema."""
        try:
            Draft202012Validator.check_schema(self.settings_schema)
        except SchemaError as e:
            raise ValidationError({"data_schema": e.message}) from e

    def test_schema_documentation_valid(self):
        """
        Check for unrecognized keys in the schema that might indicate an incorrect attempt at defining documentation.
        """
        Draft202012Validator(schema=SETTINGS_DOCUMENTATION_SCHEMA).validate(self.settings_schema)

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch.object(sys, "argv", [])  # to trick settings.TESTING to evaluate to False
    def test_default_settings_vs_schema(self):
        """Check the default settings in nautobot.core.settings against the schema."""
        # Force reimport of settings module after mocking out os.environ and sys.argv above
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

        # Test that settings variables are accurately described in the schema
        for key in keys:
            with self.subTest(f"Checking for settings attribute {key} in the settings schema"):
                self.assertIn(key, self.settings_schema["properties"])
            if key not in self.settings_schema["properties"]:
                continue

            with self.subTest(f"Checking default value for settings attribute {key} against the schema"):
                if self.settings_schema["properties"][key].get("$ref", None) in [
                    "#/definitions/absolute_path",
                    "#/definitions/callable",
                    "#/definitions/relative_path",
                ]:
                    # Functions like UI_RACK_VIEW_TRUNCATE_FUNCTION don't have a default expressable in JSON Schema,
                    # and path-like defaults probably depend on the user context
                    continue

                if self.settings_schema["properties"][key].get("default_literal", None):
                    # Probably a complicated setting that isn't easily documentable in JSON schema
                    continue

                # Is the default in the settings correctly documented?
                self.assertEqual(getattr(nautobot_settings, key), self.settings_schema["properties"][key]["default"])

        # Test that schema properties actually exist in the settings
        for key in self.settings_schema["properties"]:
            if key in getattr(nautobot_settings, "CONSTANCE_CONFIG"):
                # Constance settings don't have a value set by default in nautobot.core.settings,
                # but they have a default in CONSTANCE_CONFIG
                with self.subTest(f"Checking default value for Constance attribute {key} against the schema"):
                    self.assertEqual(
                        nautobot_settings.CONSTANCE_CONFIG[key].default,
                        self.settings_schema["properties"][key]["default"],
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
                    self.assertEqual(getattr(django_defaults, key), self.settings_schema["properties"][key]["default"])

    def test_environment_variable_settings(self):
        """Check that settings with an environment_variable key are set from the environment."""

        fake = faker.Faker()

        def _get_fake_value(value_type):
            if value_type == "boolean":
                return str(fake.boolean())
            elif value_type == "integer":
                return str(fake.random_int())
            return f"FAKE_ENV_{fake.word()}"

        with mock.patch.dict(os.environ, {}):
            # Set fake environment vars based on defined schema types
            for key, value in self.settings_schema["properties"].items():
                if "environment_variable" not in value:
                    continue
                setting_type = value.get("type", "string")
                env_var = value["environment_variable"]

                # ALLOWED_HOSTS is a special case (space separated instead of commas)
                if key == "ALLOWED_HOSTS":
                    os.environ[env_var] = " ".join(_get_fake_value("string") for _ in range(3))
                elif setting_type == "array":
                    children_type = value.get("items", {}).get("type", "string")
                    os.environ[env_var] = ",".join(_get_fake_value(children_type) for _ in range(3))
                else:
                    os.environ[env_var] = _get_fake_value(setting_type)

            # Force reimport of settings module after mocking out os.environ above
            sys.modules.pop("nautobot.core.settings", None)
            import nautobot.core.settings as nautobot_settings

            # Test that settings are loaded from the mocked environment
            for key, value in self.settings_schema["properties"].items():
                if key not in nautobot_settings.__dict__.keys():
                    continue
                if "environment_variable" not in self.settings_schema["properties"][key]:
                    continue
                with self.subTest(f"Checking environment variable for settings attribute {key}"):
                    setting_type = value.get("type", "string")
                    env_var = self.settings_schema["properties"][key]["environment_variable"]
                    # ALLOWED_HOSTS is a special case (space separated instead of commas)
                    if key == "ALLOWED_HOSTS":
                        expected_value = os.environ[env_var].split(" ")
                    elif setting_type == "array":
                        children_type = value.get("items", {}).get("type", "string")
                        if children_type == "integer":
                            expected_value = [int(v) for v in os.environ[env_var].split(",")]
                        else:
                            expected_value = os.environ[env_var].split(",")
                    elif setting_type == "boolean":
                        expected_value = is_truthy(os.environ[env_var])
                    elif setting_type == "integer":
                        expected_value = int(os.environ[env_var])
                    else:
                        expected_value = os.environ[env_var]
                    self.assertEqual(getattr(nautobot_settings, key), expected_value)
