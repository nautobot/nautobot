"""Page objects for the detail views of the two peers in the relationship tests (manufacturer and platform)."""

from playwright.sync_api import expect

from nautobot.playwright.detail_page import DetailPage


class RelationshipPeerDetailPage(DetailPage):
    """A detail view's Relationships panels, on the main tab and the Advanced tab. Subclasses set the path."""

    _RELATIONSHIPS_PANEL = "Relationships"

    def _relationship_panels_showing(self, tab_id, peer_name):
        """Locator for Relationships panels in *tab_id* that show *peer_name*.

        Matches on the peer rather than on the panel alone: another relationship on the
        instance can add a Relationships panel this test did not create.
        """
        return self.panel(self._RELATIONSHIPS_PANEL, within=self.tab_pane(tab_id)).filter(has_text=peer_name)

    def expect_relationship_peer(self, tab_id, peer_name):
        """Assert (auto-retrying) that a Relationships panel on tab *tab_id* shows *peer_name*."""
        expect(self._relationship_panels_showing(tab_id, peer_name)).to_have_count(1)

    def expect_no_relationship_peer(self, tab_id, peer_name):
        """Assert (auto-retrying) that no Relationships panel on tab *tab_id* shows *peer_name*."""
        expect(self._relationship_panels_showing(tab_id, peer_name)).to_have_count(0)


class ManufacturerDetailPage(RelationshipPeerDetailPage):
    """The Manufacturer detail view."""

    DETAIL_PATH = "/dcim/manufacturers/{pk}/"
    VERBOSE_NAME = "Manufacturer"


class PlatformDetailPage(RelationshipPeerDetailPage):
    """The Platform detail view."""

    DETAIL_PATH = "/dcim/platforms/{pk}/"
    VERBOSE_NAME = "Platform"
