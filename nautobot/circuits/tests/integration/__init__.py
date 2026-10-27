"""Playwright tests for the circuits app. Run with `invoke playwright --app circuits`."""

from nautobot.playwright import load_tests  # noqa: F401  keeps unittest discovery out; see nautobot.playwright
