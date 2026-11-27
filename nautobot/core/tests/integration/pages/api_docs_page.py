"""Page object for the REST API documentation page (/api/docs/), rendered by Swagger UI."""

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class ApiDocsPage(BasePage):
    """The Swagger UI page that lists the REST API endpoints and can send requests to them."""

    PATH = "/api/docs/"

    # Swagger UI adds the loading class to the filter box until the API schema has loaded.
    _FILTER_INPUT = "input.operation-filter-input"
    _FILTER_INPUT_READY = "input.operation-filter-input:not(.loading)"
    # Swagger UI gives each endpoint block the id "operations-<tag>-<operation id>".
    _OPERATION = "#operations-{tag}-{operation_id}"
    # The clickable summary line that expands or collapses an endpoint block.
    _OPERATION_SUMMARY = ".opblock-summary-control"
    # The status code of the response to the request sent with Execute. The header row
    # has a "Code" cell with the same class, so look only in the table body.
    _RESPONSE_STATUS = ".live-responses-table tbody .response-col_status"
    # The full API schema is large and can take a long time to load.
    _SCHEMA_LOAD_TIMEOUT = 60_000

    def navigate(self):
        """Go to the API docs page and wait until the API schema has loaded."""
        self._goto(self.PATH)
        expect(self.page.locator(self._FILTER_INPUT_READY)).to_be_visible(timeout=self._SCHEMA_LOAD_TIMEOUT)

    def filter_endpoints(self, text):
        """Type *text* into the filter box, so only the endpoints whose path matches it are listed."""
        self.page.locator(self._FILTER_INPUT).fill(text)

    def operation(self, tag, operation_id):
        """Locator for the endpoint block with this *tag* and *operation_id*, e.g. "dcim" and "dcim_locations_list"."""
        return self.page.locator(self._OPERATION.format(tag=tag, operation_id=operation_id))

    def try_out_operation(self, tag, operation_id):
        """Expand the endpoint block, click "Try it out", and then click "Execute" to send the request."""
        operation = self.operation(tag, operation_id)
        operation.locator(self._OPERATION_SUMMARY).click()
        operation.get_by_role("button", name="Try it out").click()
        operation.get_by_role("button", name="Execute").click()

    def expect_response_status(self, tag, operation_id, status):
        """Assert (auto-retrying) that the response to the request sent from the endpoint block has status *status*."""
        expect(self.operation(tag, operation_id).locator(self._RESPONSE_STATUS)).to_have_text(status)
