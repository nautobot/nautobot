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
    """
    if "pytest" not in sys.modules:
        raise unittest.SkipTest("Playwright E2E tests run under pytest (invoke e2e), not nautobot-server test.")
