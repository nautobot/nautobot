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
        relationship = created_relationship["relationship"]
        # Each peer's page, with the label of its side of the relationship and the other peer's name.
        # The manufacturer is the source, so its page shows the source label.
        peers = (
            (
                ManufacturerDetailPage(auth_page, base_url),
                manufacturer["id"],
                relationship["source_label"],
                platform["name"],
            ),
            (
                PlatformDetailPage(auth_page, base_url),
                platform["id"],
                relationship["destination_label"],
                manufacturer["name"],
            ),
        )

        for detail, pk, side_label, other_name in peers:
            detail.navigate(pk)
            detail.expect_relationship_peer("main", side_label, other_name)
            detail.open_tab("advanced")
            detail.expect_no_relationship_peer("advanced", side_label, other_name)

        response = api.patch(f"/api/extras/relationships/{relationship['id']}/", data={"advanced_ui": True})
        assert response.ok, f"PATCH relationship {relationship['id']} returned {response.status}: {response.text()}"

        for detail, pk, side_label, other_name in peers:
            detail.navigate(pk)
            detail.expect_no_relationship_peer("main", side_label, other_name)
            detail.open_tab("advanced")
            detail.expect_relationship_peer("advanced", side_label, other_name)

    @pytest.mark.behavioral
    def test_relationship_symmetric_form_behavior(self, auth_page, base_url, api, content_type_id, create_object):
        """A symmetric type copies the source fields into the disabled destination fields, and the copies are saved."""
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

        # Switching back to a symmetric type copies the source values over the destination type set by hand.
        form.select_type("symmetric-many-to-many")
        form.expect_destination_type(manufacturer_type)
        form.expect_destination_disabled()

        create_object.track("extras/relationships/", label=label)
        relationship_id = form.submit()
        form.expect_flash_message("Created relationship")

        # The destination fields are disabled, and a browser does not post disabled inputs. The form's
        # submit handler re-enables them, so the API shows whether the mirrored values reached the server.
        response = api.get(f"/api/extras/relationships/{relationship_id}/")
        assert response.ok, f"GET relationship {relationship_id} returned {response.status}: {response.text()}"
        relationship = response.json()
        assert relationship["label"] == label
        assert relationship["type"] == "symmetric-many-to-many"
        for side in ("source", "destination"):
            assert relationship[f"{side}_type"] == "dcim.manufacturer", f"{side}_type was not copied from source"
            assert relationship[f"{side}_label"] == "Peers", f"{side}_label was not copied from source"
            assert relationship[f"{side}_filter"] == {"name__ic": "peer"}, f"{side}_filter was not copied from source"
            assert relationship[f"{side}_hidden"] is True, f"{side}_hidden was not copied from source"
