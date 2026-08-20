"""Shared infrastructure for Playwright end-to-end tests.

E2E tests live in per-app ``nautobot/<app>/tests/e2e/`` packages and run under pytest
(``invoke e2e``), never under ``nautobot-server test``. This package holds everything
they share: the page-object base classes, the pytest fixture surface, and the guard
that keeps the unittest runner away from pytest-only modules.
"""

import sys
import unittest


def block_unittest_discovery():
    """Keep ``nautobot-server test`` discovery out of a Playwright E2E package.

    Call this at the top of each ``nautobot/<app>/tests/e2e/__init__.py``. E2E modules
    import Playwright and pytest at import time, so letting unittest discovery import
    them would fail in environments without the ``e2e`` dependency group installed.
    Raising ``unittest.SkipTest`` at import time makes discovery record the package as
    a single skip and never enter it; under pytest (the only intended runner, already
    imported by the time collection starts) this is a no-op.

    Known edge: the heuristic also no-ops when pytest is *ambiently* loaded in a
    ``nautobot-server test`` process (``time_machine``, a testing-group dependency,
    imports pytest opportunistically when it is installed, so a full-suite run can
    have it loaded before later apps' e2e packages are reached). That is safe by
    construction: pytest being importable means the ``e2e`` group is installed, so
    the e2e modules import cleanly, and function-style pytest tests are never
    collected by unittest (verified: zero collected, zero loader errors). The guard's
    real job is the environment where the imports would crash, which is exactly the
    environment where pytest is absent and the guard fires.
    """
    if "pytest" not in sys.modules:
        raise unittest.SkipTest("Playwright E2E tests run under pytest (invoke e2e), not nautobot-server test.")
