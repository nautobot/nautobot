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


# The schema that created_schema_validation_tree binds its children to, and the data that they
# contain. The API validates data against the bound schema on write, so a failing child cannot
# be created directly. Tests make the children fail by changing the schema afterwards.
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

    Use it for schemas that a test creates through the UI, because `create_object` deletes
    only the records that it created. Add the name before submitting the form, so that the
    schema is deleted even when an assertion fails after the create.
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
def created_schema_validation_tree(create_object, update_object, status_for, created_device):
    """A config context schema with one valid config context, device and virtual machine bound to it.

    These are the three kinds of object that the schema's Validation tab reports on. Each one
    has VALID_DATA as its context data. The config context is scoped to the device's location,
    so its data does not apply to every device in the instance.
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
