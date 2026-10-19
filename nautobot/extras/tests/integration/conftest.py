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


@pytest.fixture(scope="session")
def content_type_id(api):
    """Callable returning the id of the content type named like "dcim.platform", the value its form option submits."""
    cache = {}

    def _lookup(content_type):
        if content_type not in cache:
            app_label, model = content_type.split(".")
            response = api.get("/api/extras/content-types/", params={"app_label": app_label, "model": model})
            if not response.ok:
                pytest.fail(f"Content type lookup for {content_type} returned {response.status}: {response.text()}")
            results = response.json()["results"]
            if len(results) != 1:
                pytest.fail(f"Expected one content type {content_type}, got {len(results)}")
            cache[content_type] = results[0]["id"]
        return cache[content_type]

    return _lookup


@pytest.fixture
def delete_on_teardown(api):
    """Callable registering records a test creates through the UI, by *endpoint* and *filters*, for deletion on teardown.

    Register before submitting the form. Teardown looks the records up by the filters, so a
    record is deleted even when the test fails before it reads the new id.
    """
    registered = []

    def _register(endpoint, **filters):
        registered.append((endpoint, filters))

    yield _register

    failures = []
    for endpoint, filters in reversed(registered):
        response = api.get(f"/api/{endpoint}", params=filters)
        if not response.ok:
            failures.append(f"GET /api/{endpoint} {filters} returned {response.status}: {response.text()[:200]}")
            continue
        for record in response.json()["results"]:
            response = api.delete(f"/api/{endpoint}{record['id']}/")
            if not response.ok and response.status != 404:
                failures.append(
                    f"DELETE /api/{endpoint}{record['id']}/ returned {response.status}: {response.text()[:200]}"
                )
    if failures:
        pytest.fail("Test data teardown failed:\n" + "\n".join(failures))


@pytest.fixture
def created_relationship(create_object):
    """A one-to-one relationship from a manufacturer to a platform, with one association between two test-owned peers.

    `advanced_ui` starts False, so the association shows on each peer's main tab.
    """
    unique = unique_name()
    manufacturer = create_object("dcim/manufacturers/", name=f"{unique}-manufacturer")
    platform = create_object("dcim/platforms/", name=f"{unique}-platform")
    relationship = create_object(
        "extras/relationships/",
        label=unique,
        key=unique.replace("-", "_").lower(),
        type="one-to-one",
        source_type="dcim.manufacturer",
        destination_type="dcim.platform",
    )
    association = create_object(
        "extras/relationship-associations/",
        relationship=relationship["id"],
        source_type="dcim.manufacturer",
        source_id=manufacturer["id"],
        destination_type="dcim.platform",
        destination_id=platform["id"],
    )
    return {
        "relationship": relationship,
        "association": association,
        "manufacturer": manufacturer,
        "platform": platform,
    }
