"""Core Playwright fixtures.

Shared fixtures, including creation and teardown (create_object, status_for, auth_page, ...)
are provided by nautobot.playwright.fixtures, registered in the repo-root conftest. Run
`pytest --fixtures` to list them.
"""

# pytest injects fixtures by parameter name, so a fixture that consumes another one
# deliberately shadows it; pylint reads that as redefinition.
# pylint: disable=redefined-outer-name

import pytest

from nautobot.playwright.helpers import unique_name


@pytest.fixture
def user_favorites(api):
    """Callable that sets the session user's navbar favorites. The original list is restored on teardown.

    Favorites are one JSON list in `/api/users/config/`, not REST records, so there is no
    per-record delete. The API token and the browser login must be the same user.
    """

    def _patch(favorites):
        response = api.patch("/api/users/config/", data={"navbar_favorites": favorites})
        if not response.ok:
            pytest.fail(f"PATCH /api/users/config/ returned {response.status}: {response.text()}")

    response = api.get("/api/users/config/")
    if not response.ok:
        pytest.fail(f"GET /api/users/config/ returned {response.status}: {response.text()}")
    original = response.json().get("navbar_favorites", [])

    yield lambda *favorites: _patch(list(favorites))

    _patch(original)


@pytest.fixture
def created_location_with_child(create_object, status_for):
    """Return the API record of a location that this test creates, with a child location under it.

    The child is needed because the tree caret and the "filter to descendants" link on the Locations
    list render only for a row that has children (`children_exists` in `dcim/tables/template_code.py`).
    """
    unique = unique_name()
    status = status_for("dcim.location")["id"]
    location_type = create_object("dcim/location-types/", name=f"{unique}-site")
    child_location_type = create_object("dcim/location-types/", name=f"{unique}-building", parent=location_type["id"])
    location = create_object(
        "dcim/locations/", name=f"{unique}-location", location_type=location_type["id"], status=status
    )
    create_object(
        "dcim/locations/",
        name=f"{unique}-child-location",
        location_type=child_location_type["id"],
        parent=location["id"],
        status=status,
    )
    return location
