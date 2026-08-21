"""Structural guarantees for the Playwright E2E packaging.

The E2E suite is black-box: a pytest process pointed at a URL, with no Django
settings, ORM, or database involvement. That property is what lets the same suite run
against any deployed instance but nothing exercises it implicitly,
because CI environments carry a Nautobot config. This meta-test enforces it.
"""

import os
import subprocess
import sys


def test_e2e_package_imports_without_django_settings():
    """``nautobot.e2e`` must import in a process with no Nautobot configuration.

    Guards against relocating the shared E2E infrastructure under ``nautobot.core``
    (whose package __init__ initializes the Celery app from Django settings) or adding
    imports to it that pull in the Django runtime. Either would make every
    E2E run require a local ``nautobot_config.py``, even when the instance under test
    is remote, which breaks the suite's black-box property. Checks ``sys.modules``
    membership rather than import success alone, because ``nautobot.core`` imports
    cleanly without settings because Celery binds them lazily, while still pulling
    Django into the process. See the "End-to-End Testing" documentation.
    """
    env = {key: value for key, value in os.environ.items() if key not in ("NAUTOBOT_CONFIG", "DJANGO_SETTINGS_MODULE")}
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
    assert result.returncode == 0, (
        f"Importing nautobot.e2e in a settings-free process failed or pulled in nautobot.core. stderr:\n{result.stderr}"
    )
