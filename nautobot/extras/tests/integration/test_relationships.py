"""Relationships: where an association shows on its peers' detail views, and the create form's symmetric-type behavior."""

import pytest

from nautobot.extras.tests.integration.pages.relationship_create_page import RelationshipCreatePage
from nautobot.extras.tests.integration.pages.relationship_peer_pages import ManufacturerDetailPage, PlatformDetailPage
from nautobot.playwright.helpers import unique_name


class RelationshipsTestCase:
    """Relationship association placement and the Relationship create form."""

    @pytest.mark.behavioral
    def test_relationship_advanced_ui(self, auth_page, base_url, api, created_relationship):
        """The association shows on both peers' main tab while `advanced_ui` is False, and only on their Advanced tab once it is True."""
        manufacturer = created_relationship["manufacturer"]
        platform = created_relationship["platform"]
        # Each peer's page, with the other peer's name that its Relationships panel should show.
        peers = (
            (ManufacturerDetailPage(auth_page, base_url), manufacturer["id"], platform["name"]),
            (PlatformDetailPage(auth_page, base_url), platform["id"], manufacturer["name"]),
        )

        for detail, pk, other_name in peers:
            detail.navigate(pk)
            detail.expect_relationship_peer("main", other_name)
            detail.expect_no_relationship_peer("advanced", other_name)

        relationship_id = created_relationship["relationship"]["id"]
        response = api.patch(f"/api/extras/relationships/{relationship_id}/", data={"advanced_ui": True})
        assert response.ok, f"PATCH relationship {relationship_id} returned {response.status}: {response.text()}"

        for detail, pk, other_name in peers:
            detail.navigate(pk)
            detail.expect_no_relationship_peer("main", other_name)
            detail.open_tab("advanced")
            detail.expect_relationship_peer("advanced", other_name)

    @pytest.mark.behavioral
    def test_relationship_symmetric_form_behavior(self, auth_page, base_url, api, content_type_id, delete_on_teardown):
        """A symmetric type mirrors the source fields onto disabled destination fields, and the mirrored values persist."""
        manufacturer_type = content_type_id("dcim.manufacturer")
        platform_type = content_type_id("dcim.platform")
        label = unique_name()
        filter_json = '{"name__ic": "peer"}'

        form = RelationshipCreatePage(auth_page, base_url)
        form.navigate()
        form.fill_label(label)
        form.select_object_type("source", manufacturer_type)
        form.fill_side("source", "Peers", filter_json, hidden=True)

        form.select_type("symmetric-many-to-many")
        form.expect_destination(manufacturer_type, "Peers", filter_json, hidden=True)
        form.expect_destination_disabled()

        form.select_type("many-to-many")
        form.expect_destination_enabled()
        form.select_object_type("destination", platform_type)
        form.expect_destination_type(platform_type)

        # Switching back re-applies the mirror over the manual destination change.
        form.select_type("symmetric-many-to-many")
        form.expect_destination_type(manufacturer_type)
        form.expect_destination_disabled()

        delete_on_teardown("extras/relationships/", label=label)
        relationship_id = form.submit()
        form.expect_flash_message("Created relationship")

        response = api.get(f"/api/extras/relationships/{relationship_id}/")
        assert response.ok, f"GET relationship {relationship_id} returned {response.status}: {response.text()}"
        relationship = response.json()
        assert relationship["label"] == label
        assert relationship["type"] == "symmetric-many-to-many"
        for side in ("source", "destination"):
            assert relationship[f"{side}_type"] == "dcim.manufacturer", f"{side}_type was not mirrored"
            assert relationship[f"{side}_label"] == "Peers", f"{side}_label was not mirrored"
            assert relationship[f"{side}_filter"] == {"name__ic": "peer"}, f"{side}_filter was not mirrored"
            assert relationship[f"{side}_hidden"] is True, f"{side}_hidden was not mirrored"
