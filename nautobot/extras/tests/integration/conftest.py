"""Extras Playwright fixtures: thin named fixtures over the shared `create_object` factory.

Shared fixtures, including creation and teardown (create_object, auth_page, ...) are
provided by nautobot.playwright.fixtures, registered in the repo-root conftest. Run
`pytest --fixtures` to list them.
Fixtures here decide which objects an extras test starts from.
"""

import pytest

from nautobot.playwright.helpers import unique_name


@pytest.fixture
def created_webhook(create_object):
    """A disabled webhook on device updates, with one condition: status moves from Planned to Active."""
    return create_object(
        "extras/webhooks/",
        name=unique_name(),
        content_types=["dcim.device"],
        enabled=False,
        type_update=True,
        payload_url="https://example.com/webhook",
        conditions=[
            {
                "negate": False,
                "preset": "field_transition",
                "type": "preset",
                "values": {"field": "status.name", "from": "Planned", "to": "Active"},
            }
        ],
    )
