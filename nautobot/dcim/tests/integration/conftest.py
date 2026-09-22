"""DCIM Playwright fixtures: thin named fixtures over the shared `create_object` factory.

Shared fixtures, including creation and teardown (create_object, status_id_for, auth_page, ...)
are provided by nautobot.playwright.fixtures, registered in the repo-root conftest. Run
`pytest --fixtures` to list them.
Fixtures here decide which objects a DCIM test starts from.

A fixture another fixture consumes is defined as `<name>_fixture` and registered under
its bare name. The consuming signature then names the fixture without shadowing a
function in this module.
"""

import pytest

from nautobot.playwright.helpers import unique_name


@pytest.fixture
def created_location_tree(create_object, status_id_for):
    """A location family owned by this test, in a location type of its own.

    Creates a parent with two children, plus a decoy parent with its own child, so a
    parent-filter test can assert both inclusion (the children) and exclusion (the
    decoy's child) against records this test controls, regardless of other data in the
    instance. All records use a unique `ZZZ-test-` prefixed name and are deleted on teardown.
    """
    unique = unique_name()
    status = status_id_for("dcim.location")
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


@pytest.fixture(name="device_status")
def device_status_fixture(api, status_id_for):
    """The Status record a device fixture assigns, as the REST API returns it.

    `status_id_for` caches only the id, and a device's own API representation names its
    status by id and URL alone, so the name the detail page renders is read here.
    """
    status_id = status_id_for("dcim.device")
    response = api.get(f"/api/extras/statuses/{status_id}/")
    if not response.ok:
        pytest.fail(f"GET /api/extras/statuses/{status_id}/ returned {response.status}: {response.text()}")
    return response.json()


@pytest.fixture(name="created_device")
def created_device_fixture(create_object, status_id_for, device_status):
    """A device owned by this test, with the location, device type and role it needs.

    Every prerequisite is created here rather than discovered, so a detail-page assertion
    compares the page against values this test set. The location type declares the device
    content type, which Nautobot requires before a device can be placed in that location.
    Returns the device alongside the records naming its fields, because the device's own
    API representation identifies them by id and URL only.
    """
    unique = unique_name()
    location_type = create_object("dcim/location-types", name=f"{unique}-location-type", content_types=["dcim.device"])
    location = create_object(
        "dcim/locations",
        name=f"{unique}-location",
        location_type=location_type["id"],
        status=status_id_for("dcim.location"),
    )
    manufacturer = create_object("dcim/manufacturers", name=f"{unique}-manufacturer")
    device_type = create_object(
        "dcim/device-types",
        model=f"{unique}-model",
        manufacturer=manufacturer["id"],
        part_number=f"{unique}-part",
    )
    role = create_object("extras/roles", name=f"{unique}-role", content_types=["dcim.device"])
    device = create_object(
        "dcim/devices",
        name=unique,
        location=location["id"],
        device_type=device_type["id"],
        role=role["id"],
        status=device_status["id"],
    )
    return {
        "device": device,
        "location": location,
        "device_type": device_type,
        "role": role,
        "status": device_status,
    }


@pytest.fixture
def created_pdu(create_object, created_device):
    """`created_device` plus the power port and power outlet that make it a PDU.

    `DevicePowerUtilizationPanel`, the one component core renders deferred, renders only
    for a device that has both, so this is the smallest device that exercises deferred
    rendering. Component names are unique per device, so they need no unique prefix, but
    the port is not named "Input": that is also the panel's own first column header, and
    a test asserting the panel lists the port would pass on the header alone.
    """
    device_id = created_device["device"]["id"]
    power_port = create_object("dcim/power-ports", device=device_id, name="Inlet A")
    power_outlet = create_object("dcim/power-outlets", device=device_id, name="Outlet A", power_port=power_port["id"])
    return {**created_device, "power_port": power_port, "power_outlet": power_outlet}
