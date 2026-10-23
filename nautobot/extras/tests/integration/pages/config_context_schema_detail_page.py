"""Page object for the Config Context Schema detail view (/extras/config-context-schemas/<pk>/) and its Validation tab."""

from playwright.sync_api import expect

from nautobot.playwright.detail_page import DetailPage


class ConfigContextSchemaDetailPage(DetailPage):
    """The Config Context Schema detail view. Adds the Validation tab to DetailPage."""

    DETAIL_PATH = "/extras/config-context-schemas/{pk}/"
    VERBOSE_NAME = "Config Context Schema"

    # An empty panel renders a single placeholder row with one colspan cell.
    _PANEL_DATA_ROWS = "tbody tr:not(:has(td[colspan]))"
    _VALIDATION_STATE_HEADER = "Validation state"
    _CHECK_ICON = "i.mdi-check-bold"
    _CROSS_ICON = "i.mdi-close-thick"

    def navigate_to_validation_tab(self, pk):
        """Go to the Validation tab of the schema with primary key *pk*.

        The tab is a separate view with its own URL, so it is opened by URL rather than by clicking the tab.
        """
        self._goto(f"{self.DETAIL_PATH.format(pk=pk)}validation/")

    # -------------------------------------------------------------------------
    # Validation tab
    # -------------------------------------------------------------------------

    def _validation_row(self, panel_title, row_name):
        """Locator for the row of panel *panel_title* whose link text is exactly *row_name*."""
        return (
            self.panel(panel_title)
            .locator(self._PANEL_DATA_ROWS)
            .filter(has=self.page.get_by_role("link", name=row_name, exact=True))
        )

    def _validation_cell(self, panel_title, row_name):
        """Locator for the "Validation state" cell of *row_name* in panel *panel_title*.

        Find the column by its header in that panel's own table, because the three tables have
        different columns. Do not look for the check icon anywhere in the row. The Config
        Contexts table shows "Active" with the same icon as a pass.
        """
        panel = self.panel(panel_title)
        expect(panel).to_have_count(1)
        headers = [text.split("\n")[0].strip() for text in panel.locator("table thead th").all_inner_texts()]
        if self._VALIDATION_STATE_HEADER not in headers:
            raise AssertionError(f"The {panel_title} panel has no {self._VALIDATION_STATE_HEADER!r} column: {headers}")
        position = headers.index(self._VALIDATION_STATE_HEADER) + 1
        return self._validation_row(panel_title, row_name).locator(f"td:nth-child({position})")

    def expect_validation_rows(self, panel_title, row_names):
        """Assert (auto-retrying) that panel *panel_title* lists exactly the objects named in *row_names*."""
        expect(self.panel(panel_title).locator(self._PANEL_DATA_ROWS)).to_have_count(len(row_names))
        for row_name in row_names:
            expect(self._validation_row(panel_title, row_name)).to_have_count(1)

    def expect_validation_passed(self, panel_title, row_name):
        """Assert (auto-retrying) that *row_name* in panel *panel_title* shows a pass and no error."""
        cell = self._validation_cell(panel_title, row_name)
        expect(cell.locator(self._CHECK_ICON)).to_have_count(1)
        expect(cell.locator(self._CROSS_ICON)).to_have_count(0)
        expect(cell).to_have_text("")

    def expect_validation_failed(self, panel_title, row_name, message):
        """Assert (auto-retrying) that *row_name* in panel *panel_title* shows a failure with *message*."""
        cell = self._validation_cell(panel_title, row_name)
        expect(cell.locator(self._CROSS_ICON)).to_have_count(1)
        expect(cell.locator(self._CHECK_ICON)).to_have_count(0)
        expect(cell).to_contain_text(message)
