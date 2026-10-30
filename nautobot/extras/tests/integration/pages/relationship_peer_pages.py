"""Page objects for the detail views of the two peers in the relationship tests (manufacturer and platform)."""

from playwright.sync_api import expect

from nautobot.playwright.detail_page import DetailPage


class RelationshipPeerDetailPage(DetailPage):
    """A detail view's Relationships panel, on the main tab or the Advanced tab.

    Subclasses set `DETAIL_PATH` and `VERBOSE_NAME`.
    """

    _RELATIONSHIPS_PANEL = "Relationships"

    def _relationship_panels_showing(self, tab_id, peer_name):
        """Locator for Relationships panels in *tab_id* that show *peer_name*.

        Matches on the peer rather than on the panel alone: another relationship on the
        instance can add a Relationships panel this test did not create.
        """
        return self.panel(self._RELATIONSHIPS_PANEL, within=self._tab_pane(tab_id)).filter(has_text=peer_name)

    def expect_relationship_peer(self, tab_id, peer_name):
        """Assert (auto-retrying) that exactly one Relationships panel on tab *tab_id* shows *peer_name*, and that it is visible."""
        expect(self._relationship_panels_showing(tab_id, peer_name)).to_be_visible()

    def expect_no_relationship_peer(self, tab_id, peer_name):
        """Assert (auto-retrying) that the tab *tab_id* exists and no Relationships panel in it shows *peer_name*."""
        expect(self._tab_pane(tab_id)).to_have_count(1)
        expect(self._relationship_panels_showing(tab_id, peer_name)).to_have_count(0)


class ManufacturerDetailPage(RelationshipPeerDetailPage):
    """The Manufacturer detail view."""

    DETAIL_PATH = "/dcim/manufacturers/{pk}/"
    VERBOSE_NAME = "Manufacturer"


class PlatformDetailPage(RelationshipPeerDetailPage):
    """The Platform detail view."""

    DETAIL_PATH = "/dcim/platforms/{pk}/"
    VERBOSE_NAME = "Platform"
