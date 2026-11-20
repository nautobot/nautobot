"""Page object for the Custom Field detail view (/extras/custom-fields/<pk>/)."""

from playwright.sync_api import expect

from nautobot.playwright.detail_page import DetailPage


class CustomFieldDetailPage(DetailPage):
    """The Custom Field detail view. Adds the Custom Field Choices panel to DetailPage."""

    DETAIL_PATH = "/extras/custom-fields/{pk}/"
    VERBOSE_NAME = "Custom Field"

    _CHOICES_PANEL = "Custom Field Choices"

    def _choice_cell(self, value):
        """Locator for the Custom Field Choices panel's cell that shows *value*."""
        return self.panel(self._CHOICES_PANEL).get_by_role("cell", name=value, exact=True)

    def expect_choice(self, value):
        """Assert (auto-retrying) that the Custom Field Choices panel lists *value*."""
        expect(self._choice_cell(value)).to_be_visible()

    def expect_no_choice(self, value):
        """Assert (auto-retrying) that the Custom Field Choices panel does not list *value*."""
        expect(self._choice_cell(value)).to_have_count(0)
