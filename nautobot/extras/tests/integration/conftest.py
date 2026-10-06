"""Extras Playwright fixtures: thin named fixtures over the shared `create_object` factory."""

# pytest injects fixtures by parameter name, so a fixture that consumes another one
# deliberately shadows it; pylint reads that as redefinition.
# pylint: disable=redefined-outer-name

import pytest

from nautobot.playwright.helpers import unique_name


@pytest.fixture
def created_location(create_object, status_for):
    """A location owned by this test, in a location type of its own."""
    unique = unique_name()
    location_type = create_object("dcim/location-types/", name=f"{unique}-type")
    return create_object(
        "dcim/locations/",
        name=f"{unique}-location",
        location_type=location_type["id"],
        status=status_for("dcim.location")["id"],
    )


@pytest.fixture
def created_note(create_object, created_location):
    """A note on `created_location`."""
    return create_object(
        "extras/notes/",
        assigned_object_type="dcim.location",
        assigned_object_id=created_location["id"],
        note=f"{unique_name()} original note",
    )
