"""Page objects for the detail views of the two peers in the relationship tests (manufacturer and platform)."""

from playwright.sync_api import expect

from nautobot.playwright.detail_page import DetailPage


class RelationshipPeerDetailPage(DetailPage):
    """A detail view's Relationships panel, on the main tab or the Advanced tab.

    Subclasses set `DETAIL_PATH` and `VERBOSE_NAME`.
    """

    _RELATIONSHIPS_PANEL = "Relationships"

    def _relationship_rows_showing(self, tab_id, side_label, peer_name):
        """Locator for rows of the Relationships panel in *tab_id* whose key is *side_label* and whose value shows *peer_name*.

        Every relationship on the object is a row in the same panel, so the panel's
        presence alone does not show that this test's association is in it.
        """
        panel = self.panel(self._RELATIONSHIPS_PANEL, within=self._tab_pane(tab_id))
        return panel.locator("tr").filter(has_text=side_label).filter(has_text=peer_name)

    def expect_relationship_peer(self, tab_id, side_label, peer_name):
        """Assert (auto-retrying) that exactly one Relationships row on tab *tab_id* shows *side_label* and *peer_name*, and that it is visible."""
        expect(self._relationship_rows_showing(tab_id, side_label, peer_name)).to_be_visible()

    def expect_no_relationship_peer(self, tab_id, side_label, peer_name):
        """Assert (auto-retrying) that the tab *tab_id* exists and no Relationships row in it shows *side_label* and *peer_name*."""
        expect(self._tab_pane(tab_id)).to_have_count(1)
        expect(self._relationship_rows_showing(tab_id, side_label, peer_name)).to_have_count(0)


class ManufacturerDetailPage(RelationshipPeerDetailPage):
    """The Manufacturer detail view."""

    DETAIL_PATH = "/dcim/manufacturers/{pk}/"
    VERBOSE_NAME = "Manufacturer"


class PlatformDetailPage(RelationshipPeerDetailPage):
    """The Platform detail view."""

    DETAIL_PATH = "/dcim/platforms/{pk}/"
    VERBOSE_NAME = "Platform"
