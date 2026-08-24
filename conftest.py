"""Repository-root pytest configuration.

pytest runs only the Playwright E2E suites (``[tool.pytest.ini_options]`` in
pyproject.toml points collection at ``nautobot/*/tests/e2e``); unit and integration
tests are unaffected and run under ``nautobot-server test`` as always.

The shared E2E fixture surface is registered here because pytest only honors
``pytest_plugins`` in the rootdir conftest.
"""

pytest_plugins = ["nautobot.playwright.fixtures"]
