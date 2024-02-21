"""Tests for the 'nautobot-server' CLI command."""

# ruff: noqa: S603,S607
#       Ruff doesn't like subprocess, and especially our calling "nautobot-server" instead of "/path/to/nautobot-server"
#       We might consider calling nautobot.core.cli.main() directly instead of using subprocess, but then
#       we should watch for leakage of information and settings when calling nautobot from nautobot.

import os
import re
import subprocess
import tempfile
from unittest import mock, TestCase

from django import __version__ as django_version
from django.conf import settings

from nautobot import __version__ as nautobot_version


class NautobotServerTestCase(TestCase):
    def test_config_path_logic(self):
        # Case #1 - if neither NAUTOBOT_ROOT nor NAUTOBOT_CONFIG environment variables are set, use user's home dir.
        modified_environ = {
            key: value for key, value in os.environ.items() if key not in ["NAUTOBOT_ROOT", "NAUTOBOT_CONFIG"]
        }
        with mock.patch.dict(os.environ, modified_environ, clear=True):
            result = subprocess.run(["nautobot-server", "version"], capture_output=True, check=True, text=True)

        self.assertIn(f"Nautobot version: {nautobot_version}", result.stdout)
        self.assertIn(f"Django version: {django_version}", result.stdout)
        self.assertIn(f"Configuration file: {os.path.expanduser('~/.nautobot/nautobot_config.py')}", result.stdout)

        # Case #2 - if NAUTOBOT_ROOT is set but not NAUTOBOT_CONFIG, use it
        modified_environ["NAUTOBOT_ROOT"] = os.path.dirname(__file__)
        with mock.patch.dict(os.environ, modified_environ, clear=True):
            result = subprocess.run(["nautobot-server", "version"], capture_output=True, check=True, text=True)

        self.assertIn(f"Configuration file: {modified_environ['NAUTOBOT_ROOT']}/nautobot_config.py", result.stdout)

        # Case #3 - if NAUTOBOT_CONFIG is set, it takes priority over NAUTOBOT_ROOT
        modified_environ["NAUTOBOT_CONFIG"] = os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.py")
        with mock.patch.dict(os.environ, modified_environ, clear=True):
            result = subprocess.run(["nautobot-server", "version"], capture_output=True, check=True, text=True)

        self.assertIn(f"Configuration file: {modified_environ['NAUTOBOT_CONFIG']}", result.stdout)

        # Case #4 - if `--config-path` is passed, it takes precedence
        actual_config = settings.SETTINGS_PATH
        with mock.patch.dict(os.environ, modified_environ, clear=True):
            result = subprocess.run(
                ["nautobot-server", "--config-path", actual_config, "version"],
                capture_output=True,
                check=True,
                text=True,
            )

        self.assertIn(f"Nautobot version: {nautobot_version}", result.stdout)
        self.assertIn(f"Django version: {django_version}", result.stdout)
        self.assertIn(f"Configuration file: {actual_config}", result.stdout)

    def test_init_subcommand(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config_path = os.path.join(tempdir, "config.py")
            subprocess.run(
                ["nautobot-server", "init", config_path],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                check=True,
            )
            self.assertTrue(os.path.isfile(config_path))
            with open(config_path, "rt") as fh:
                contents = fh.read()
            # SECRET_KEY should be autopopulated with a random value
            self.assertIn("SECRET_KEY = ", contents)
            secret_key_1 = re.search(r'^SECRET_KEY = .*"([^"]+)"\)$', contents, flags=re.MULTILINE).group(1)
            # INSTALLATION_METRICS_ENABLED should default to True
            self.assertIn(
                'INSTALLATION_METRICS_ENABLED = is_truthy(os.getenv("NAUTOBOT_INSTALLATION_METRICS_ENABLED", "True"))',
                contents,
            )

        with tempfile.TemporaryDirectory() as tempdir:
            config_path = os.path.join(tempdir, "config.py")
            subprocess.run(
                ["nautobot-server", "--config-path", config_path, "init", "--disable-installation-metrics"],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                check=True,
            )
            self.assertTrue(os.path.isfile(config_path))
            with open(config_path, "rt") as fh:
                contents = fh.read()
            # SECRET_KEY should be autopopulated with a random value
            self.assertIn("SECRET_KEY = ", contents)
            secret_key_2 = re.search(r'^SECRET_KEY = .*"([^"]+)"\)$', contents, flags=re.MULTILINE).group(1)
            # INSTALLATION_METRICS_ENABLED should default to False since we passed --disable-installation-metrics
            self.assertIn(
                'INSTALLATION_METRICS_ENABLED = is_truthy(os.getenv("NAUTOBOT_INSTALLATION_METRICS_ENABLED", "False"))',
                contents,
            )

        self.assertNotEqual(secret_key_1, secret_key_2)

    def test_settings_processing(self):
        result = subprocess.run(
            ["nautobot-server", "--config", settings.SETTINGS_PATH, "print_settings"],
            capture_output=True,
            check=True,
            text=True,
        )
        # TODO: we should add a test nautobot_config.py that uses the EXTRA_* settings extensions and test that here.

        # Make sure directories exist
        # TODO: this would be better with a separate test config that defines a different NAUTOBOT_ROOT,
        # since here they should already have been created by us at startup.
        for setting in ["GIT_ROOT", "JOBS_ROOT", "MEDIA_ROOT", "STATIC_ROOT"]:
            path = re.search(rf"{setting} += '(.*)'", result.stdout).group(1)
            self.assertTrue(os.path.isdir(path))

        # Make sure DATABASES are set up correctly
        self.assertRegex(result.stdout, r"DATABASES.*django_prometheus\.db\.backends")  # since METRICS_ENABLED
        self.assertRegex(result.stdout, r"DATABASES.*job_logs")

        # Make sure apps are loaded into INSTALLED_APPS
        self.assertRegex(result.stdout, r"INSTALLED_APPS.*example_app\.ExampleAppConfig")
        self.assertRegex(result.stdout, r"INSTALLED_APPS.*nautobot\.extras\.tests\.example_app_dependency")
