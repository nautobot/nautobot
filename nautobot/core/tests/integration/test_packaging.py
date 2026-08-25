"""Structural guarantees for the Playwright test packaging.

The Playwright suite is black-box: a pytest process pointed at a URL, with no Django
settings, ORM, or database involvement. That property is what lets the same suite run
against any deployed instance but nothing exercises it implicitly,
because CI environments carry a Nautobot config. This meta-test enforces it.
"""

import os
import subprocess
import sys
import textwrap

# Run in a subprocess so the check starts from a clean interpreter: this test's own
# process has Django fully loaded, which would mask exactly what is being asserted.
# Every submodule is discovered rather than listed, so a module added to
# nautobot/playwright/ later is covered without editing this test.
IMPORT_PROBE = textwrap.dedent(
    """
    import importlib
    import pkgutil
    import sys

    import nautobot.playwright

    def _reraise(name):
        raise

    names = [
        module.name
        for module in pkgutil.walk_packages(
            nautobot.playwright.__path__, f"{nautobot.playwright.__name__}.", onerror=_reraise
        )
    ]
    if not names:
        sys.exit(2)
    for name in names:
        importlib.import_module(name)
    sys.exit(1 if "nautobot.core" in sys.modules else 0)
    """
)


def test_playwright_package_imports_without_django_settings():
    """Every `nautobot.playwright` module must import with no Nautobot configuration.

    Guards against relocating the shared Playwright infrastructure under `nautobot.core`
    (whose package __init__ initializes the Celery app from Django settings) or adding
    imports to it that pull in the Django runtime. Either would make every
    Playwright run require a local `nautobot_config.py`, even when the instance under test
    is remote, which breaks the suite's black-box property. Checks `sys.modules`
    membership rather than import success alone, because `nautobot.core` imports
    cleanly without settings because Celery binds them lazily, while still pulling
    Django into the process. See the "Playwright Testing" documentation.
    """
    env = {key: value for key, value in os.environ.items() if key not in ("NAUTOBOT_CONFIG", "DJANGO_SETTINGS_MODULE")}
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", IMPORT_PROBE],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode != 2, (
        "Discovered no nautobot.playwright submodules to check; this test would pass vacuously."
    )
    assert result.returncode == 0, (
        "Importing every nautobot.playwright module in a settings-free process failed, "
        f"or one of them pulled in nautobot.core. stderr:\n{result.stderr}"
    )
