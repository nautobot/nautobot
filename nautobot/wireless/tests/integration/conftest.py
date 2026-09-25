"""Wireless Playwright fixtures: thin named fixtures over the shared `create_object` factory.

Shared fixtures, including creation and teardown (create_object, wait_for_job_result,
auth_page, ...) are provided by nautobot.playwright.fixtures, registered in the repo-root
conftest. Run `pytest --fixtures` to list them.
Fixtures here decide which objects a wireless test starts from.
"""

import pytest

from nautobot.playwright.helpers import unique_name


@pytest.fixture
def created_radio_profiles(create_object):
    """Three new radio profiles with the same name prefix and no frequency, deleted after the test."""
    prefix = unique_name()
    profiles = [
        create_object("wireless/radio-profiles", name=f"{prefix}-{index}", regulatory_domain="US")
        for index in (1, 2, 3)
    ]
    return {"prefix": prefix, "profiles": profiles}
