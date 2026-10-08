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

# The template every computed field below renders; `expected_value` is its output for the device.
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

    Includes `expected_value`, the text the field renders for `created_device`.
    """
    return _create_device_computed_field(create_object, created_device["device"], advanced_ui=False)


@pytest.fixture
def created_advanced_ui_computed_field(create_object, created_device):
    """A Device computed field with `advanced_ui` on, so it renders only on the device's Advanced tab.

    Includes `expected_value`, the text the field renders for `created_device`.
    """
    return _create_device_computed_field(create_object, created_device["device"], advanced_ui=True)


@pytest.fixture(scope="session")
def api_computed_field_value(api):
    """Callable returning the value the REST API renders for one computed field of an object.

    Computed fields are opt-in on the REST API, so the object is fetched with
    `?include=computed_fields`.
    """

    def _value(endpoint, pk, key):
        response = api.get(f"/api/{endpoint}{pk}/", params={"include": "computed_fields"})
        if not response.ok:
            pytest.fail(f"GET /api/{endpoint}{pk}/ returned {response.status}: {response.text()}")
        return response.json()["computed_fields"][key]

    return _value
