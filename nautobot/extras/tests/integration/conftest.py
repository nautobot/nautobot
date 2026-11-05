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
def created_note(create_object, created_location):
    """A note on `created_location`."""
    return create_object(
        "extras/notes/",
        assigned_object_type="dcim.location",
        assigned_object_id=created_location["id"],
        note=f"{unique_name()} original note",
    )


@pytest.fixture
def created_device_set(create_object, status_for, created_device):
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
def created_static_group(create_object):
    """An empty static device group owned by this test."""
    return create_object(
        "extras/dynamic-groups/",
        name=unique_name(),
        content_type="dcim.device",
        group_type="static",
    )


@pytest.fixture(scope="session")
def require_celery_worker(api):
    """Fail the test up front unless a Celery worker is running to execute the jobs it starts from the UI.

    Without a worker, a job such as Refresh Members is queued but never runs, and the test
    would otherwise fail only after its poll times out.
    """
    response = api.get("/api/status/")
    if not response.ok:
        pytest.fail(f"GET /api/status/ returned {response.status}: {response.text()[:200]}")
    if not response.json()["celery-workers-running"]:
        pytest.fail("No Celery worker is running, so the Refresh Members job would never run.")


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
