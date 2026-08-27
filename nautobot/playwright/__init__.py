"""Shared infrastructure for the Playwright test suite.

Playwright tests live in per-app `nautobot/<app>/tests/integration/` packages and are
pytest tests, run via `invoke playwright`. The unittest-based `nautobot-server test`
runner neither discovers nor needs them (see `load_tests` below). This package holds
everything they share: the page-object base classes, the pytest fixture surface, and
that discovery guard.
"""

import unittest


def load_tests(loader, tests, pattern):  # pylint: disable=unused-argument
    """Keep `nautobot-server test` discovery out of a Playwright test package.

    Re-export this in each `nautobot/<app>/tests/integration/__init__.py`:

        from nautobot.playwright import load_tests  # noqa: F401

    This is unittest's `load_tests` protocol: when a package defines it, discovery
    calls it instead of recursing into the package, so the pytest-only test modules
    (which import Playwright and pytest) are never imported by the unittest runner and
    no environment needs the playwright dependency group just to run `nautobot-server
    test`. Returning an empty suite, rather than raising `unittest.SkipTest` at
    import time, matters: a SkipTest placeholder is a dynamically created test class
    that cannot be pickled, which crashes Django's `--parallel` test runner. pytest
    ignores this hook entirely and collects the package normally.
    """
    return unittest.TestSuite()
