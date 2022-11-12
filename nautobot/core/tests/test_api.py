import json

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from constance import config
from constance.test import override_config

from nautobot.circuits.models import Provider
from nautobot.utilities.testing import APITestCase


class AppTest(APITestCase):
    def test_root(self):
        url = reverse("api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)

    def test_status(self):
        url = reverse("api-status")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)

    def test_non_existent_resource(self):
        url = reverse("api-root")
        response = self.client.get(f"{url}/non-existent-resource-url/", **self.header)
        self.assertEqual(response.status_code, 404)
        response_json = json.loads(response.content)
        self.assertEqual(response_json, {"detail": "Not found."})

    def test_docs(self):
        url = reverse("api_docs")
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("text/html", response.headers["Content-Type"])

        # Under drf-yasg, ?format=openapi was the way to get the JSON schema for the docs.
        response = self.client.get(f"{url}?format=openapi", follow=True, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("application/vnd.oai.openapi+json", response.headers["Content-Type"])


class APIPaginationTestCase(APITestCase):
    """
    Testing our custom API pagination, OptionalLimitOffsetPagination.

    Since there are no "core" API views that are paginated, we test one of our apps' API views.
    """

    @classmethod
    def setUpTestData(cls):
        for i in range(10):
            Provider.objects.create(name=f"Provider {i}", slug=f"provider-{i}")

        cls.url = reverse("circuits-api:provider-list")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], PAGINATE_COUNT=5, MAX_PAGE_SIZE=10)
    def test_pagination_defaults_to_paginate_count(self):
        """If no limit is specified, default pagination to settings.PAGINATE_COUNT."""
        response = self.client.get(self.url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), settings.PAGINATE_COUNT)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], PAGINATE_COUNT=5, MAX_PAGE_SIZE=10)
    def test_pagination_respects_specified_limit(self):
        """Request with a specific limit and verify that it's respected."""
        limit = settings.PAGINATE_COUNT - 2
        response = self.client.get(f"{self.url}?limit={limit}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), limit)

        limit = settings.PAGINATE_COUNT + 2  # but still less than MAX_PAGE_SIZE
        response = self.client.get(f"{self.url}?limit={limit}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), limit)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], PAGINATE_COUNT=3, MAX_PAGE_SIZE=5)
    def test_pagination_limits_to_max_page_size(self):
        """Request more than the configured MAX_PAGE_SIZE and verify the limit is enforced."""
        limit = settings.MAX_PAGE_SIZE + 2
        response = self.client.get(f"{self.url}?limit={limit}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), settings.MAX_PAGE_SIZE)

        limit = 0  # as many as permitted
        response = self.client.get(f"{self.url}?limit={limit}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), settings.MAX_PAGE_SIZE)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], PAGINATE_COUNT=5, MAX_PAGE_SIZE=0)
    def test_max_page_size_zero(self):
        """MAX_PAGE_SIZE of zero means no enforced limit."""
        response = self.client.get(self.url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), settings.PAGINATE_COUNT)

        limit = settings.PAGINATE_COUNT
        response = self.client.get(f"{self.url}?limit={limit}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), settings.PAGINATE_COUNT)

        limit = 0  # as many as permitted, i.e. all records
        response = self.client.get(f"{self.url}?limit={limit}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), Provider.objects.count())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @override_config(PAGINATE_COUNT=5, MAX_PAGE_SIZE=10)
    def test_pagination_based_on_constance(self):
        """In the absence of settings values, constance settings should be respected."""
        del settings.PAGINATE_COUNT
        del settings.MAX_PAGE_SIZE

        response = self.client.get(self.url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), config.PAGINATE_COUNT)

        limit = config.PAGINATE_COUNT - 2
        response = self.client.get(f"{self.url}?limit={limit}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), limit)

        limit = config.PAGINATE_COUNT + 2
        response = self.client.get(f"{self.url}?limit={limit}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), limit)

        limit = config.MAX_PAGE_SIZE + 2
        response = self.client.get(f"{self.url}?limit={limit}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), config.MAX_PAGE_SIZE)

        limit = 0  # as many as permitted
        response = self.client.get(f"{self.url}?limit={limit}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertEqual(len(response.data["results"]), config.MAX_PAGE_SIZE)


class APIVersioningTestCase(APITestCase):
    """
    Testing our custom API versioning, NautobotAPIVersioning.
    """

    def test_default_version(self):
        """Test that a request with no specific API version gets the default version."""
        url = reverse("api-root")
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], settings.REST_FRAMEWORK["DEFAULT_VERSION"])

    def test_header_version(self):
        """Test that the API version can be specified via the HTTP Accept header."""
        url = reverse("api-root")

        min_version = settings.REST_FRAMEWORK["ALLOWED_VERSIONS"][0]
        self.set_api_version(min_version)
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], min_version)

        max_version = settings.REST_FRAMEWORK["ALLOWED_VERSIONS"][-1]
        self.set_api_version(max_version)
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], max_version)

        invalid_version = "0.0"
        self.set_api_version(invalid_version)
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 406)  # Not Acceptable
        for version in settings.REST_FRAMEWORK["ALLOWED_VERSIONS"]:
            self.assertIn(version, response.data["detail"])

    def test_query_version(self):
        """Test that the API version can be specified via a query parameter."""
        url = reverse("api-root")

        min_version = settings.REST_FRAMEWORK["ALLOWED_VERSIONS"][0]
        response = self.client.get(f"{url}?api_version={min_version}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], min_version)

        max_version = settings.REST_FRAMEWORK["ALLOWED_VERSIONS"][-1]
        response = self.client.get(f"{url}?api_version={max_version}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], max_version)

        invalid_version = "0.0"
        response = self.client.get(f"{url}?api_version={invalid_version}", **self.header)
        self.assertHttpStatus(response, 404)
        for version in settings.REST_FRAMEWORK["ALLOWED_VERSIONS"]:
            self.assertIn(version, response.data["detail"])

    def test_header_and_query_version(self):
        """Test the behavior when the API version is specified in both the Accept header *and* a query parameter."""
        url = reverse("api-root")

        min_version = settings.REST_FRAMEWORK["ALLOWED_VERSIONS"][0]
        max_version = settings.REST_FRAMEWORK["ALLOWED_VERSIONS"][-1]
        # Specify same version both as Accept header and as query parameter (valid)
        self.set_api_version(max_version)
        response = self.client.get(f"{url}?api_version={max_version}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], max_version)

        # Specify different versions in Accept header and query parameter (invalid)
        response = self.client.get(f"{url}?api_version={min_version}", **self.header)
        self.assertHttpStatus(response, 400)
        self.assertIn("Version mismatch", response.data["detail"])


class LookupTypeChoicesTestCase(APITestCase):
    def test_get_lookup_choices_without_query_params(self):
        url = reverse("core-api:filtersetfield-list-lookupchoices")
        response = self.client.get(url, **self.header)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, "content_type and field_name are required parameters")

    def test_get_lookup_field_data_invalid_query_params(self):
        url = reverse("core-api:filtersetfield-list-lookupchoices")
        with self.subTest("Test invalid content_type"):
            response = self.client.get(url + "?content_type=invalid.contenttypes&field_name=name", **self.header)

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data, "content_type not found")

        with self.subTest("Test invalid field_name"):
            response = self.client.get(url + "?content_type=dcim.site&field_name=fake", **self.header)

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data, "field_name not found")

    def test_get_lookup_choices(self):
        url = reverse("core-api:filtersetfield-list-lookupchoices")
        response = self.client.get(url + "?content_type=dcim.site&field_name=status", **self.header)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [{"id": "status", "name": "exact"}, {"id": "status__n", "name": "not exact (n)"}],
            },
        )


class GenerateLookupValueDomElementViewTestCase(APITestCase):
    def test_get_lookup_field_data_without_query_params(self):
        url = reverse("core-api:filtersetfield-retrieve-lookupvaluedomelement")
        response = self.client.get(url, **self.header)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, "content_type and field_name are required parameters")

    def test_get_lookup_field_data_invalid_query_params(self):
        url = reverse("core-api:filtersetfield-retrieve-lookupvaluedomelement")

        with self.subTest("Test invalid content_type"):
            response = self.client.get(url + "?content_type=invalid.contenttypes&field_name=name", **self.header)

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data, "content_type not found")

        with self.subTest("Test invalid field_name"):
            response = self.client.get(url + "?content_type=dcim.site&field_name=fake", **self.header)

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data, "field_name not found")

    def test_get_lookup_value_dom_element(self):
        url = reverse("core-api:filtersetfield-retrieve-lookupvaluedomelement")
        response = self.client.get(url + "?content_type=dcim.site&field_name=name", **self.header)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "dom_element": '<select name="name" class="form-control nautobot-select2-multi-value-char" data-multiple="1" id="id_for_name" multiple>\n</select>'
            },
        )
