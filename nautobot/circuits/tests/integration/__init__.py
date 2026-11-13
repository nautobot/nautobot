"""Playwright tests and page objects for the circuits app."""

# Stops `nautobot-server test` from importing this package; see nautobot.playwright.
from nautobot.playwright import load_tests  # noqa: F401
