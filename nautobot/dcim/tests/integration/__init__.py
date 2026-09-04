"""Playwright tests for the DCIM app. Run with `invoke playwright --app dcim`."""

from nautobot.playwright import load_tests  # noqa: F401  keeps unittest discovery out; see nautobot.playwright
