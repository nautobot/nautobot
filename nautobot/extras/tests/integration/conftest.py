"""Extras Playwright fixtures: thin named fixtures over the shared `create_object` factory.

Shared fixtures, including creation and teardown (create_object, status_for, auth_page, ...)
are provided by nautobot.playwright.fixtures, registered in the repo-root conftest. Run
`pytest --fixtures` to list them.
Fixtures here decide which objects an Extras test starts from.
"""

# pytest injects fixtures by parameter name, so a fixture that consumes another one
# deliberately shadows it; pylint reads that as redefinition.
# pylint: disable=redefined-outer-name

import pytest

# Re-exported so pytest registers them for the Extras tests too.
from nautobot.dcim.tests.integration.conftest import created_device, created_manufacturer  # noqa: F401
from nautobot.playwright.helpers import unique_name


@pytest.fixture
def created_device_set(create_object, status_for, created_device):  # noqa: F811  the fixture re-exported above
    """Devices owned by this test, split across two locations of their own.

    Builds on created_device: its location gets a second device, and a second location of
    the same type gets one more, so a group filtered on those locations has a membership
    known in advance, regardless of other data in the instance. All records are deleted on
    teardown.
    """
    first_location = created_device["location"]
    second_location = create_object(
        "dcim/locations/",
        name=unique_name(),
        location_type=first_location["location_type"]["id"],
        status=status_for("dcim.location")["id"],
    )

    def _create_device(location):
        return create_object(
            "dcim/devices/",
            name=unique_name(),
            location=location["id"],
            device_type=created_device["device_type"]["id"],
            role=created_device["role"]["id"],
            status=created_device["status"]["id"],
        )

    return {
        "first_location": first_location,
        "first_devices": [created_device["device"], _create_device(first_location)],
        "second_location": second_location,
        "second_devices": [_create_device(second_location)],
    }


@pytest.fixture
def created_dynamic_group(create_object, created_device_set):
    """A device group owned by this test, filtered on the first location of `created_device_set`.

    Created through the REST API, which (unlike the UI) calculates the cached membership
    on save, so the group starts with the first location's devices as its members.
    """
    return create_object(
        "extras/dynamic-groups/",
        name=unique_name(),
        content_type="dcim.device",
        group_type="dynamic-filter",
        filter={"location": [created_device_set["first_location"]["name"]]},
    )


@pytest.fixture
def dynamic_group_cleanup(api):
    """Collect the ids of dynamic groups created through the UI and delete them on teardown.

    A UI-created group's id is only known after the add form redirects, so the test
    appends it here as soon as it has it. A 404 is ignored, like `create_object`'s teardown.
    """
    created = []
    yield created
    for pk in created:
        response = api.delete(f"/api/extras/dynamic-groups/{pk}/")
        if not response.ok and response.status != 404:
            pytest.fail(f"DELETE /api/extras/dynamic-groups/{pk}/ returned {response.status}: {response.text()[:200]}")
