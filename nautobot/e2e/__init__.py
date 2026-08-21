"""Shared infrastructure for Playwright end-to-end tests.

E2E tests live in per-app ``nautobot/<app>/tests/e2e/`` packages and run under pytest
(``invoke e2e``), never under ``nautobot-server test``. This package holds everything
they share: the page-object base classes, the pytest fixture surface, and the guard
that keeps the unittest runner away from pytest-only modules.
"""

import unittest


def load_tests(loader, tests, pattern):  # pylint: disable=unused-argument
    """Keep ``nautobot-server test`` discovery out of a Playwright E2E package.

    Re-export this in each ``nautobot/<app>/tests/e2e/__init__.py``::

        from nautobot.e2e import load_tests  # noqa: F401

    This is unittest's ``load_tests`` protocol: when a package defines it, discovery
    calls it instead of recursing into the package, so the pytest-only test modules
    (which import Playwright and pytest) are never imported by the unittest runner and
    no environment needs the e2e dependency group just to run ``nautobot-server
    test``. Returning an empty suite, rather than raising ``unittest.SkipTest`` at
    import time, matters: a SkipTest placeholder is a dynamically created test class
    that cannot be pickled, which crashes Django's ``--parallel`` test runner. pytest
    ignores this hook entirely and collects the package normally.
    """
    return unittest.TestSuite()
