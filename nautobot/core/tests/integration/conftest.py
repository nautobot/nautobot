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
def created_grouped_tenant(create_object):
    """A tenant group with one tenant in it, plus a tenant outside it, all created for this test.

    The Tenant filter form has no name filter in Core, so a search narrows to an owned tenant by its group.
    """
    group = create_object("tenancy/tenant-groups/", name=unique_name())
    tenant = create_object("tenancy/tenants/", name=unique_name(), tenant_group=group["id"])
    other = create_object("tenancy/tenants/", name=unique_name())
    return {"group": group, "tenant": tenant, "other": other}


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
