"""Structural guarantees for the Playwright test packaging.

The Playwright suite is a pytest process pointed at a URL, with no Django
settings, ORM, or database needed, which lets the suite run against
any deployed instance. Because of this, nautobot.playwright must import without Django
which could break silently. An accidental Django import would only surface on a host
without a config pointed at a remote instance. This test fails immediately instead.
"""

import os
import subprocess
import sys
import textwrap

# The probe runs in a subprocess so it starts from a clean interpreter. Whatever the
# hosting pytest process has already imported (today or after future conftest changes)
# can then neither mask nor fabricate the result. Every submodule is discovered rather
# than listed, so a module added to nautobot/playwright/ later is covered without
# editing this test.
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
    """Every nautobot.playwright module must import with no Nautobot configuration.
▎
▎   The check is sys.modules membership, not import success alone: nautobot.core
    imports cleanly without settings (Celery binds them lazily) while still pulling
▎   Django into the process.
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
        "Discovered no nautobot.playwright submodules to check; this test would pass while checking nothing."
    )
    assert result.returncode == 0, (
        "Importing every nautobot.playwright module in a settings-free process failed, "
        f"or one of them pulled in nautobot.core. stderr:\n{result.stderr}"
    )
