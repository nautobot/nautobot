"""The REST API documentation page (/api/docs/), rendered by Swagger UI."""

import pytest

from nautobot.core.tests.integration.pages.api_docs_page import ApiDocsPage


class ApiDocsTestCase:
    """Sending a request to an endpoint from the API docs page."""

    @pytest.mark.behavioral
    def test_location_list_endpoint_returns_200(self, auth_page, base_url):
        """Filter to the location endpoints, send a request to the location list endpoint, and get a 200 response."""
        api_docs = ApiDocsPage(auth_page, base_url)
        api_docs.navigate()

        api_docs.filter_endpoints("/dcim/locations/")
        api_docs.try_out_operation("dcim", "dcim_locations_list")
        api_docs.expect_response_status("dcim", "dcim_locations_list", "200")
