"""App-agnostic E2E machinery tests (the framework itself, not a product page)."""

from nautobot.playwright import load_tests  # noqa: F401  keeps unittest discovery out; see nautobot.playwright
