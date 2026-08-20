"""DCIM E2E fixtures: thin named fixtures over the shared ``create_object`` factory.

The factory (``nautobot.e2e.fixtures``) owns creation and teardown;
fixtures here only decide which objects a DCIM test starts from.
"""

from uuid import uuid4

import pytest


@pytest.fixture
def created_location_tree(create_object, status_id_for):
    """A location family owned by this test, in a location type of its own.

    Creates a parent with two children, plus a decoy parent with its own child, so a
    parent-filter test can assert both inclusion (the children) and exclusion (the
    decoy's child) against records this test controls, regardless of what other data
    the instance holds. All records use a unique ``ZZZ-e2e-`` prefixed name and are
    deleted on teardown.
    """
    unique = f"ZZZ-e2e-{uuid4().hex[:8]}"
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
