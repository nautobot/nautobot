"""Extras Playwright fixtures: thin named fixtures over the shared `create_object` factory.

Shared fixtures, including creation and teardown (create_object, created_device, status_for, auth_page, ...)
are provided by nautobot.playwright.fixtures, registered in the repo-root conftest. Run
`pytest --fixtures` to list them.
Fixtures here decide which objects an Extras test starts from.
"""

# pytest injects fixtures by parameter name, so a fixture that consumes another one
# deliberately shadows it; pylint reads that as redefinition.
# pylint: disable=redefined-outer-name

import pytest

from nautobot.playwright.helpers import unique_name

# Every computed field below renders this template. `expected_value` is the output for the device.
COMPUTED_FIELD_TEMPLATE = "{{ obj.name }} is awesome!"


def _create_device_computed_field(create_object, device, advanced_ui):
    """Create a Device computed field and return it with the value it renders for *device*."""
    unique = unique_name()
    computed_field = create_object(
        "extras/computed-fields/",
        # The key must be a valid identifier, so the name's dashes become underscores.
        key=unique.replace("-", "_").lower(),
        label=f"{unique} Computed Field",
        content_type="dcim.device",
        template=COMPUTED_FIELD_TEMPLATE,
        advanced_ui=advanced_ui,
    )
    return {**computed_field, "expected_value": f"{device['name']} is awesome!"}


@pytest.fixture
def created_computed_field(create_object, created_device):
    """A Device computed field with `advanced_ui` off, so it renders on the device's main tab.

    The returned dict includes `expected_value`, the text the field renders for `created_device`.
    """
    return _create_device_computed_field(create_object, created_device["device"], advanced_ui=False)


@pytest.fixture
def created_advanced_ui_computed_field(create_object, created_device):
    """A Device computed field with `advanced_ui` on, so it renders only on the device's Advanced tab.

    The returned dict includes `expected_value`, the text the field renders for `created_device`.
    """
    return _create_device_computed_field(create_object, created_device["device"], advanced_ui=True)


# Everything a created webhook has besides its name and conditions. Disabled, so it never sends.
DISABLED_DEVICE_UPDATE_WEBHOOK = {
    "content_types": ["dcim.device"],
    "enabled": False,
    "type_update": True,
    "payload_url": "https://example.com/webhook",
}


@pytest.fixture
def create_webhook(create_object):
    """Callable creating a disabled webhook on device updates with the given *conditions*, deleted after the test."""

    def _create(conditions):
        return create_object(
            "extras/webhooks/", name=unique_name(), conditions=conditions, **DISABLED_DEVICE_UPDATE_WEBHOOK
        )

    return _create


@pytest.fixture
def webhook_name(api):
    """A unique webhook name. A webhook the test saves under it through the form is deleted after the test."""
    name = unique_name()
    yield name
    response = api.get("/api/extras/webhooks/", params={"name": name})
    assert response.ok, f"GET webhooks named {name} returned {response.status}: {response.text()}"
    for webhook in response.json()["results"]:
        deleted = api.delete(f"/api/extras/webhooks/{webhook['id']}/")
        assert deleted.ok, f"DELETE webhook {webhook['id']} returned {deleted.status}: {deleted.text()}"
