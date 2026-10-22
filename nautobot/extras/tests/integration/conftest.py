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


def _ok_json(response, request):
    """Return *response*'s JSON body, failing the test with *request* in the message if it is not a success."""
    if not response.ok:
        pytest.fail(f"{request} returned {response.status}: {response.text()[:200]}")
    return response.json() if response.status != 204 else None


@pytest.fixture
def refresh_members_job_on_default_queue(api):
    """Make the default queue the Refresh Members job's only queue for the test, then restore its queue settings.

    The Refresh Members job button submits the job to the first of the job's queues, and
    generate_test_data assigns random queues to jobs. On a seeded instance the job can then
    land on a queue no worker consumes, while the development worker consumes only the
    default queue. The overrides are set so Nautobot does not reset the queues from the job
    class on save.
    """
    job = _ok_json(
        api.get(
            "/api/extras/jobs/",
            params={
                "module_name": "nautobot.core.jobs.groups",
                "job_class_name": "RefreshDynamicGroupCacheJobButtonReceiver",
            },
        ),
        "GET the Refresh Members job",
    )["results"][0]
    job_url = f"/api/extras/jobs/{job['id']}/"
    default_queue = _ok_json(
        api.get("/api/extras/job-queues/", params={"name": "default"}), "GET the default job queue"
    )["results"][0]

    def _assignments():
        return _ok_json(
            api.get("/api/extras/job-queue-assignments/", params={"job": job["id"], "limit": 0}),
            "GET the job's queue assignments",
        )["results"]

    def _set_queues(default_queue_id, queue_ids, overrides):
        # The default queue goes first: Nautobot always adds a job's default queue to its queue list on save.
        _ok_json(
            api.patch(
                job_url,
                data={
                    "default_job_queue": default_queue_id,
                    "default_job_queue_override": overrides["default_job_queue_override"],
                    "job_queues_override": overrides["job_queues_override"],
                },
            ),
            f"PATCH {job_url}",
        )
        assigned = {assignment["job_queue"]["id"]: assignment["id"] for assignment in _assignments()}
        for queue_id in set(queue_ids) - set(assigned):
            _ok_json(
                api.post("/api/extras/job-queue-assignments/", data={"job": job["id"], "job_queue": queue_id}),
                "POST a job queue assignment",
            )
        for queue_id in set(assigned) - set(queue_ids):
            _ok_json(
                api.delete(f"/api/extras/job-queue-assignments/{assigned[queue_id]}/"),
                "DELETE a job queue assignment",
            )

    original_default_queue_id = job["default_job_queue"]["id"]
    original_queue_ids = [assignment["job_queue"]["id"] for assignment in _assignments()]
    original_overrides = {key: job[key] for key in ("default_job_queue_override", "job_queues_override")}

    _set_queues(
        default_queue["id"], [default_queue["id"]], {"default_job_queue_override": True, "job_queues_override": True}
    )
    yield
    _set_queues(original_default_queue_id, original_queue_ids, original_overrides)


@pytest.fixture
def dynamic_group_name(api):
    """A unique dynamic group name. A group the test saves under it through the form is deleted after the test.

    Deleting by name rather than by the pk from the add form's redirect means the group is
    cleaned up even if the save succeeds but the redirect does not.
    """
    name = unique_name()
    yield name
    response = api.get("/api/extras/dynamic-groups/", params={"name": name})
    assert response.ok, f"GET dynamic groups named {name} returned {response.status}: {response.text()}"
    for group in response.json()["results"]:
        deleted = api.delete(f"/api/extras/dynamic-groups/{group['id']}/")
        assert deleted.ok, f"DELETE dynamic group {group['id']} returned {deleted.status}: {deleted.text()}"
