"""Playwright tests for the circuits app. Run with `invoke playwright --app circuits`."""

# Stops `nautobot-server test` from importing this package; see nautobot.playwright.
from nautobot.playwright import load_tests  # noqa: F401
