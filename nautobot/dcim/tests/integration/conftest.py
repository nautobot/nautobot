"""DCIM Playwright fixtures: thin named fixtures over the shared `create_object` factory.

Shared fixtures, including creation and teardown (create_object, status_for, auth_page, ...)
are provided by nautobot.playwright.fixtures, registered in the repo-root conftest. Run
`pytest --fixtures` to list them.
Fixtures here decide which objects a DCIM test starts from.
"""

# pytest injects fixtures by parameter name, so a fixture that consumes another one
# deliberately shadows it; pylint reads that as redefinition.
# pylint: disable=redefined-outer-name

import pytest

from nautobot.playwright.helpers import unique_name


@pytest.fixture
def created_location_tree(create_object, status_for):
    """A location family owned by this test, in a location type of its own.

    Creates a parent with two children, plus a decoy parent with its own child, so a
    parent-filter test can assert both inclusion (the children) and exclusion (the
    decoy's child) against records this test controls, regardless of other data in the
    instance. All records use a unique `ZZZ-test-` prefixed name and are deleted on teardown.
    """
    unique = unique_name()
    status = status_for("dcim.location")["id"]
    location_type = create_object("dcim/location-types", name=f"{unique}-type", nestable=True)
    parent = create_object("dcim/locations", name=f"{unique}-parent", location_type=location_type["id"], status=status)
    children = [
        create_object(
            "dcim/locations",
            name=f"{unique}-child-{index}",
            location_type=location_type["id"],
            status=status,
            parent=parent["id"],
        )
        for index in (1, 2)
    ]
    decoy = create_object("dcim/locations", name=f"{unique}-decoy", location_type=location_type["id"], status=status)
    decoy_child = create_object(
        "dcim/locations",
        name=f"{unique}-decoy-child",
        location_type=location_type["id"],
        status=status,
        parent=decoy["id"],
    )
    return {"parent": parent, "children": children, "decoy": decoy, "decoy_child": decoy_child}


@pytest.fixture
def created_manufacturer(create_object):
    """A manufacturer owned by this test."""
    return create_object("dcim/manufacturers", name=unique_name())


@pytest.fixture
def created_device(create_object, status_for):
    """A device owned by this test, with its own location type, location, manufacturer, device type and role.

    Returns the device and the records that name its fields, since the API represents
    them by id and URL only.
    """
    unique = unique_name()
    # Create a location type as a prerequisite for the device's location.
    location_type = create_object("dcim/location-types", name=f"{unique}-location-type", content_types=["dcim.device"])
    location = create_object(
        "dcim/locations",
        name=f"{unique}-location",
        location_type=location_type["id"],
        status=status_for("dcim.location")["id"],
    )
    manufacturer = create_object("dcim/manufacturers", name=f"{unique}-manufacturer")
    device_type = create_object(
        "dcim/device-types",
        model=f"{unique}-model",
        manufacturer=manufacturer["id"],
        part_number=f"{unique}-part",
    )
    role = create_object("extras/roles", name=f"{unique}-role", content_types=["dcim.device"])
    status = status_for("dcim.device")
    device = create_object(
        "dcim/devices",
        name=unique,
        location=location["id"],
        device_type=device_type["id"],
        role=role["id"],
        status=status["id"],
    )
    return {
        "device": device,
        "location": location,
        "device_type": device_type,
        "role": role,
        "status": status,
    }


@pytest.fixture
def created_pdu(create_object, created_device):
    """`created_device` with a power port and outlet, the smallest device that renders the Power Utilization panel."""
    device_id = created_device["device"]["id"]
    # Not "Input" to avoid matching the panel's first column header.
    power_port = create_object("dcim/power-ports", device=device_id, name="Inlet A")
    power_outlet = create_object("dcim/power-outlets", device=device_id, name="Outlet A", power_port=power_port["id"])
    return {**created_device, "power_port": power_port, "power_outlet": power_outlet}
