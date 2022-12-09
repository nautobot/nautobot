import json

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from constance import config
from constance.test import override_config

from nautobot.circuits.models import Provider
from nautobot.core.choices import DynamicGroupOperatorChoices
from nautobot.core.models.dynamic_groups import DynamicGroup, DynamicGroupMembership
from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from nautobot.extras.models import Status
from nautobot.utilities.testing import APITestCase, APIViewTestCases


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


class DynamicGroupTestMixin:
    """Mixin for Dynamic Group test cases to re-use the same set of common fixtures."""

    @classmethod
    def setUpTestData(cls):
        # Create the objects required for devices.
        sites = [
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
            Site.objects.create(name="Site 3", slug="site-3"),
        ]

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="device Type 1",
            slug="device-type-1",
        )
        device_role = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1", color="ff0000")
        status_active = Status.objects.get(slug="active")
        status_planned = Status.objects.get(slug="planned")
        Device.objects.create(
            name="device-site-1",
            status=status_active,
            device_role=device_role,
            device_type=device_type,
            site=sites[0],
        )
        Device.objects.create(
            name="device-site-2",
            status=status_active,
            device_role=device_role,
            device_type=device_type,
            site=sites[1],
        )
        Device.objects.create(
            name="device-site-3",
            status=status_planned,
            device_role=device_role,
            device_type=device_type,
            site=sites[2],
        )

        # Then the DynamicGroups.
        cls.content_type = ContentType.objects.get_for_model(Device)
        cls.groups = [
            DynamicGroup.objects.create(
                name="API DynamicGroup 1",
                slug="api-dynamicgroup-1",
                content_type=cls.content_type,
                filter={"status": ["active"]},
            ),
            DynamicGroup.objects.create(
                name="API DynamicGroup 2",
                slug="api-dynamicgroup-2",
                content_type=cls.content_type,
                filter={"status": ["planned"]},
            ),
            DynamicGroup.objects.create(
                name="API DynamicGroup 3",
                slug="api-dynamicgroup-3",
                content_type=cls.content_type,
                filter={"site": ["site-3"]},
            ),
        ]


class DynamicGroupTest(DynamicGroupTestMixin, APIViewTestCases.APIViewTestCase):
    model = DynamicGroup
    brief_fields = ["content_type", "display", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "API DynamicGroup 4",
            "slug": "api-dynamicgroup-4",
            "content_type": "dcim.device",
            "filter": {"site": ["site-1"]},
        },
        {
            "name": "API DynamicGroup 5",
            "slug": "api-dynamicgroup-5",
            "content_type": "dcim.device",
            "filter": {"has_interfaces": False},
        },
        {
            "name": "API DynamicGroup 6",
            "slug": "api-dynamicgroup-6",
            "content_type": "dcim.device",
            "filter": {"site": ["site-2"]},
        },
    ]

    def test_get_members(self):
        """Test that the `/members/` API endpoint returns what is expected."""
        self.add_permissions("core.view_dynamicgroup")
        instance = DynamicGroup.objects.first()
        member_count = instance.members.count()
        url = reverse("core-api:dynamicgroup-members", kwargs={"pk": instance.pk})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(member_count, len(response.json()["results"]))


class DynamicGroupMembershipTest(DynamicGroupTestMixin, APIViewTestCases.APIViewTestCase):
    model = DynamicGroupMembership
    brief_fields = ["display", "group", "id", "operator", "parent_group", "url", "weight"]
    choices_fields = ["operator"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        parent = DynamicGroup.objects.create(
            name="parent",
            slug="parent",
            content_type=cls.content_type,
            filter={},
        )
        parent2 = DynamicGroup.objects.create(
            name="parent2",
            slug="parent2",
            content_type=cls.content_type,
            filter={},
        )
        group1, group2, group3 = cls.groups

        DynamicGroupMembership.objects.create(
            parent_group=parent,
            group=group1,
            operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
            weight=10,
        )
        DynamicGroupMembership.objects.create(
            parent_group=parent,
            group=group2,
            operator=DynamicGroupOperatorChoices.OPERATOR_UNION,
            weight=20,
        )
        DynamicGroupMembership.objects.create(
            parent_group=parent,
            group=group3,
            operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
            weight=30,
        )

        cls.create_data = [
            {
                "parent_group": parent2.pk,
                "group": group1.pk,
                "operator": DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
                "weight": 10,
            },
            {
                "parent_group": parent2.pk,
                "group": group2.pk,
                "operator": DynamicGroupOperatorChoices.OPERATOR_UNION,
                "weight": 20,
            },
            {
                "parent_group": parent2.pk,
                "group": group3.pk,
                "operator": DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
                "weight": 30,
            },
        ]
