"""Wireless Playwright fixtures: thin named fixtures over the shared `create_object` factory.

Shared fixtures, including creation and teardown (create_object, auth_page, ...) are
provided by nautobot.playwright.fixtures, registered in the repo-root conftest. Run
`pytest --fixtures` to list them.
Fixtures here decide which objects a wireless test starts from.
"""

import pytest

from nautobot.playwright.helpers import unique_name


@pytest.fixture
def created_radio_profile(create_object):
    """A new radio profile with a unique name, deleted after the test."""
    return create_object("wireless/radio-profiles", name=unique_name(), regulatory_domain="PL")
