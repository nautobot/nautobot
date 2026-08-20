"""Structural guarantees for the Playwright E2E packaging.

The E2E suite (``nautobot/e2e/``, ``nautobot/*/tests/e2e/``) is black-box: a pytest
process pointed at a URL, with no Django settings, ORM, or database involvement. That
property is load-bearing (it is what lets the same suite run against any deployed
instance) but nothing in normal CI exercises it directly, because the CI job's
environment happens to carry a Nautobot config. These meta-tests enforce it.
"""

import importlib.util
import os
import subprocess
import sys
import unittest


class E2EPackagingTestCase(unittest.TestCase):
    """Enforce the decoupling contract between the E2E suite and the Django runtime."""

    @unittest.skipIf(
        importlib.util.find_spec("playwright") is None,
        "The e2e dependency group is not installed (poetry install --with e2e).",
    )
    def test_e2e_package_imports_without_django_settings(self):
        """``nautobot.e2e`` must import in a process with no Nautobot configuration.

        Guards against relocating the shared E2E infrastructure under ``nautobot.core``
        (whose package __init__ initializes the Celery app from Django settings) or
        adding imports to it that drag in the Django runtime. Either regression would
        make every E2E run require a local ``nautobot_config.py``, even when the
        instance under test is remote, silently breaking the suite's black-box
        property. See the "End-to-End Testing with Playwright" documentation.
        """
        env = {
            key: value for key, value in os.environ.items() if key not in ("NAUTOBOT_CONFIG", "DJANGO_SETTINGS_MODULE")
        }
        snippet = (
            "import sys\n"
            "import nautobot.e2e.base_page\n"
            "import nautobot.e2e.fixtures\n"
            "import nautobot.e2e.list_page\n"
            "sys.exit(1 if 'nautobot.core' in sys.modules else 0)\n"
        )
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", snippet],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            "Importing nautobot.e2e in a settings-free process failed or pulled in nautobot.core. "
            f"stderr:\n{result.stderr}",
        )
