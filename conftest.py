"""Repository-root pytest configuration.

pytest runs only the Playwright test suites (`[tool.pytest.ini_options]` in
pyproject.toml points collection at `nautobot/*/tests/integration`); the
unittest-based suites are unaffected and run under `nautobot-server test` as always.

The shared fixture surface is registered here because pytest only honors
`pytest_plugins` in the rootdir conftest.
"""

pytest_plugins = ["nautobot.playwright.fixtures"]
