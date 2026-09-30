"""Shared infrastructure for the Playwright test suite.

Playwright tests are pytest tests. They live in per-app
`nautobot/<app>/tests/integration/` packages and run via `invoke playwright`.
`nautobot.playwright` holds the pieces every app's Playwright tests share:
the page-object base classes, the pytest fixtures, and the `load_tests`
guard that keeps unittest's `nautobot-server test` discovery out.
"""

import unittest


def load_tests(loader, tests, pattern):  # pylint: disable=unused-argument
    """Keep `nautobot-server test` discovery out of a Playwright test package.

    Re-export this in each `nautobot/<app>/tests/integration/__init__.py`:

        from nautobot.playwright import load_tests  # noqa: F401

    This is unittest's `load_tests` protocol. When a package defines it, discovery
    calls it instead of recursing into the package, so the pytest-only test modules
    (which import Playwright and pytest) are never imported by the unittest runner and
    no environment needs the playwright dependency group just to run `nautobot-server
    test`. pytest ignores this hook entirely and collects the package normally.
    """
    return unittest.TestSuite()
