"""Extras Playwright fixtures: thin named fixtures over the shared `create_object` factory.

Shared fixtures, including creation and teardown (create_object, status_for, auth_page, ...)
are provided by nautobot.playwright.fixtures, registered in the repo-root conftest. Run
`pytest --fixtures` to list them.
Fixtures here decide which objects an extras test starts from.
"""

# pytest injects fixtures by parameter name, so a fixture that consumes another one
# deliberately shadows it; pylint reads that as redefinition.
# pylint: disable=redefined-outer-name

import pytest

# Imported so pytest registers them for this app too, rather than rebuilding the device graph here.
# created_device needs created_manufacturer. Ruff reads the import as unused (F401) and the
# fixture parameter that consumes it as a redefinition (F811).
from nautobot.dcim.tests.integration.conftest import created_device, created_manufacturer  # noqa: F401
from nautobot.playwright.helpers import unique_name

# The schema created_schema_validation_tree binds its children to, and the data they hold.
# The API validates data against the bound schema on write, so a failing child cannot be
# created directly. Tests make the children fail by changing the schema afterwards.
VALID_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}, "c": {"type": "integer"}},
}
VALID_DATA = {"a": 123, "b": 456, "c": 777}


@pytest.fixture
def update_object(api):
    """Callable that PATCHes *fields* onto the REST object *pk* at *endpoint* and returns the updated record."""

    def _update(endpoint, pk, **fields):
        response = api.patch(f"/api/{endpoint}{pk}/", data=fields)
        if not response.ok:
            pytest.fail(f"PATCH /api/{endpoint}{pk}/ returned {response.status}: {response.text()}")
        return response.json()

    return _update


@pytest.fixture
def schema_names_to_delete(api):
    """A list of config context schema names. Every schema with one of these names is deleted on teardown.

    For schemas a test creates through the UI, which `create_object` cannot track. A test
    adds the name before submitting the form, so the schema is deleted even when an
    assertion fails after it was created.
    """
    names = []
    yield names

    failures = []
    for name in names:
        response = api.get("/api/extras/config-context-schemas/", params={"name": name})
        if not response.ok:
            failures.append(f"GET config context schemas named {name!r} returned {response.status}")
            continue
        for record in response.json()["results"]:
            deleted = api.delete(f"/api/extras/config-context-schemas/{record['id']}/")
            if not deleted.ok and deleted.status != 404:
                failures.append(f"DELETE config context schema {record['id']} returned {deleted.status}")
    if failures:
        pytest.fail("Test data teardown failed:\n" + "\n".join(failures))


@pytest.fixture
def created_schema_validation_tree(create_object, update_object, status_for, created_device):  # noqa: F811
    """A config context schema with one valid config context, device and virtual machine bound to it.

    These are the three kinds of object the schema's Validation tab reports on, each holding
    VALID_DATA. The config context is scoped to the device's location so its data does not
    apply to every device in the instance.
    """
    unique = unique_name()
    schema = create_object("extras/config-context-schemas/", name=f"{unique}-schema", data_schema=VALID_SCHEMA)
    config_context = create_object(
        "extras/config-contexts/",
        name=f"{unique}-context",
        data=VALID_DATA,
        config_context_schema=schema["id"],
        locations=[created_device["location"]["id"]],
    )
    device = update_object(
        "dcim/devices/",
        created_device["device"]["id"],
        local_config_context_data=VALID_DATA,
        local_config_context_schema=schema["id"],
    )
    cluster_type = create_object("virtualization/cluster-types/", name=f"{unique}-cluster-type")
    cluster = create_object("virtualization/clusters/", name=f"{unique}-cluster", cluster_type=cluster_type["id"])
    virtual_machine = create_object(
        "virtualization/virtual-machines/",
        name=f"{unique}-vm",
        cluster=cluster["id"],
        status=status_for("virtualization.virtualmachine")["id"],
        local_config_context_data=VALID_DATA,
        local_config_context_schema=schema["id"],
    )
    return {"schema": schema, "config_context": config_context, "device": device, "virtual_machine": virtual_machine}
