from copy import deepcopy
import csv
from io import BytesIO, StringIO
import json

from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.test import override_settings, TestCase
from django.urls import reverse

from constance import config
from constance.test import override_config
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.settings import api_settings

from nautobot.circuits.models import Provider
from nautobot.core import testing
from nautobot.core.api.parsers import NautobotCSVParser
from nautobot.core.api.renderers import NautobotCSVRenderer
from nautobot.core.api.versioning import NautobotAPIVersioning
from nautobot.core.models.constants import COMPOSITE_KEY_SEPARATOR
from nautobot.dcim import models as dcim_models
from nautobot.dcim.api import serializers as dcim_serializers
from nautobot.extras import choices
from nautobot.extras import models as extras_models
from nautobot.ipam import models as ipam_models
from nautobot.ipam.api import serializers as ipam_serializers


class AppTest(testing.APITestCase):
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


class APIDocsTestCase(TestCase):
    client_class = testing.NautobotTestClient

    def setUp(self):
        # Populate a CustomField to activate CustomFieldSerializer
        content_type = ContentType.objects.get_for_model(dcim_models.Location)
        self.cf_text = extras_models.CustomField(type=choices.CustomFieldTypeChoices.TYPE_TEXT, label="test")
        self.cf_text.save()
        self.cf_text.content_types.set([content_type])
        self.cf_text.save()

    def test_api_docs(self):
        url = reverse("api_docs")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        headers = {
            "HTTP_ACCEPT": "application/vnd.oai.openapi",
        }
        url = reverse("schema")
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, 200)


class APIPaginationTestCase(testing.APITestCase):
    """
    Testing our custom API pagination, OptionalLimitOffsetPagination.

    Since there are no "core" API views that are paginated, we test one of our apps' API views.
    """

    @classmethod
    def setUpTestData(cls):
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


class APIVersioningTestCase(testing.APITestCase):
    """
    Testing our custom API versioning, NautobotAPIVersioning.
    """

    OVERRIDE_REST_FRAMEWORK = deepcopy(settings.REST_FRAMEWORK)
    # For Nautobot 2.0, the default/only supported API version is 2.0, which limits our ability to test with multiple
    # or min/max versions. For test purposes we force there to be some extra versions available.
    EXTRA_ALLOWED_VERSIONS = [
        f"{settings.VERSION_MAJOR - 1}.99",
        *settings.REST_FRAMEWORK["ALLOWED_VERSIONS"],
        f"{settings.VERSION_MAJOR}.{settings.VERSION_MINOR + 1}",
    ]
    OVERRIDE_REST_FRAMEWORK["ALLOWED_VERSIONS"] = EXTRA_ALLOWED_VERSIONS
    OVERRIDE_REST_FRAMEWORK["DEFAULT_VERSION"] = EXTRA_ALLOWED_VERSIONS[-1]

    def test_default_version(self):
        """Test that a request with no specific API version gets the default version, which is the current version."""
        url = reverse("api-root")
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], api_settings.DEFAULT_VERSION)
        self.assertEqual(response["API-Version"], f"{settings.VERSION_MAJOR}.{settings.VERSION_MINOR}")

        with override_settings(REST_FRAMEWORK=self.OVERRIDE_REST_FRAMEWORK):
            response = self.client.get(url, **self.header)
            self.assertHttpStatus(response, 200)
            self.assertIn("API-Version", response)
            self.assertEqual(response["API-Version"], self.OVERRIDE_REST_FRAMEWORK["DEFAULT_VERSION"])
            self.assertEqual(response["API-Version"], f"{settings.VERSION_MAJOR}.{settings.VERSION_MINOR + 1}")

    def test_allowed_versions(self):
        """Test that all expected versions are supported."""
        for minor_version in range(0, settings.VERSION_MINOR + 1):
            version = f"{settings.VERSION_MAJOR}.{minor_version}"
            self.assertIn(version, settings.REST_FRAMEWORK["ALLOWED_VERSIONS"])
            self.assertIn(version, api_settings.ALLOWED_VERSIONS)
            self.assertIn(version, NautobotAPIVersioning.allowed_versions)

    def test_header_version(self):
        """Test that the API version can be specified via the HTTP Accept header."""
        url = reverse("api-root")

        min_version = api_settings.ALLOWED_VERSIONS[0]
        self.set_api_version(min_version)
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], min_version)

        default_version = api_settings.DEFAULT_VERSION
        self.set_api_version(default_version)
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], default_version)

        max_version = api_settings.ALLOWED_VERSIONS[-1]
        self.set_api_version(min_version)
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], max_version)

        invalid_version = "0.0"
        self.set_api_version(invalid_version)
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 406)  # Not Acceptable
        for version in api_settings.ALLOWED_VERSIONS:
            self.assertIn(version, response.data["detail"])

        # Also test with explicitly added additional allowed versions
        with override_settings(REST_FRAMEWORK=self.OVERRIDE_REST_FRAMEWORK):
            min_version = self.EXTRA_ALLOWED_VERSIONS[0]
            self.set_api_version(min_version)
            response = self.client.get(url, **self.header)
            self.assertHttpStatus(response, 200)
            self.assertIn("API-Version", response)
            self.assertEqual(response["API-Version"], min_version)

            max_version = self.EXTRA_ALLOWED_VERSIONS[-1]
            self.set_api_version(max_version)
            response = self.client.get(url, **self.header)
            self.assertHttpStatus(response, 200)
            self.assertIn("API-Version", response)
            self.assertEqual(response["API-Version"], max_version)

            invalid_version = "0.0"
            self.set_api_version(invalid_version)
            response = self.client.get(url, **self.header)
            self.assertHttpStatus(response, 406)  # Not Acceptable
            for version in self.EXTRA_ALLOWED_VERSIONS:
                self.assertIn(version, response.data["detail"])

    def test_query_version(self):
        """Test that the API version can be specified via a query parameter."""
        url = reverse("api-root")

        min_version = api_settings.ALLOWED_VERSIONS[0]
        response = self.client.get(f"{url}?api_version={min_version}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], min_version)

        default_version = api_settings.DEFAULT_VERSION
        response = self.client.get(f"{url}?api_version={default_version}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], default_version)

        max_version = api_settings.ALLOWED_VERSIONS[-1]
        response = self.client.get(f"{url}?api_version={max_version}", **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], max_version)

        invalid_version = "0.0"
        response = self.client.get(f"{url}?api_version={invalid_version}", **self.header)
        self.assertHttpStatus(response, 404)
        for version in api_settings.ALLOWED_VERSIONS:
            self.assertIn(version, response.data["detail"])

        # Also test with explicitly added additional allowed versions
        with override_settings(REST_FRAMEWORK=self.OVERRIDE_REST_FRAMEWORK):
            min_version = self.EXTRA_ALLOWED_VERSIONS[0]
            response = self.client.get(f"{url}?api_version={min_version}", **self.header)
            self.assertHttpStatus(response, 200)
            self.assertIn("API-Version", response)
            self.assertEqual(response["API-Version"], min_version)

            max_version = self.EXTRA_ALLOWED_VERSIONS[-1]
            response = self.client.get(f"{url}?api_version={max_version}", **self.header)
            self.assertHttpStatus(response, 200)
            self.assertIn("API-Version", response)
            self.assertEqual(response["API-Version"], max_version)

            invalid_version = "0.0"
            response = self.client.get(f"{url}?api_version={invalid_version}", **self.header)
            self.assertHttpStatus(response, 404)
            for version in self.EXTRA_ALLOWED_VERSIONS:
                self.assertIn(version, response.data["detail"])

    @override_settings(REST_FRAMEWORK=OVERRIDE_REST_FRAMEWORK)
    def test_header_and_query_version(self):
        """Test the behavior when the API version is specified in both the Accept header *and* a query parameter."""
        url = reverse("api-root")

        min_version = self.EXTRA_ALLOWED_VERSIONS[0]
        max_version = self.EXTRA_ALLOWED_VERSIONS[-1]
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


class LookupTypeChoicesTestCase(testing.APITestCase):
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
            response = self.client.get(url + "?content_type=dcim.location&field_name=fake", **self.header)

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data, "field_name not found")

    def test_get_lookup_choices(self):
        url = reverse("core-api:filtersetfield-list-lookupchoices")
        response = self.client.get(url + "?content_type=dcim.location&field_name=status", **self.header)

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


class GenerateLookupValueDomElementViewTestCase(testing.APITestCase):
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
            response = self.client.get(url + "?content_type=dcim.location&field_name=fake", **self.header)

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data, "field_name not found")

    def test_get_lookup_value_dom_element(self):
        url = reverse("core-api:filtersetfield-retrieve-lookupvaluedomelement")
        response = self.client.get(f"{url}?content_type=dcim.location&field_name=name", **self.header)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            '<select name="name" class="form-control nautobot-select2-multi-value-char" data-multiple="1" id="id_for_name" multiple>\n</select>',
        )

        # Also assert JSON representation
        self.header["HTTP_ACCEPT"] = "application/json"
        response = self.client.get(f"{url}?content_type=dcim.location&field_name=name&as_json", **self.header)
        self.assertEqual(response.status_code, 200)
        expected_response = {
            "field_type": "MultiValueCharField",
            "attrs": {"class": "form-control nautobot-select2-multi-value-char", "data-multiple": 1},
            "choices": [],
            "is_required": False,
        }
        self.assertEqual(response.data, expected_response)

    def test_get_lookup_value_dom_element_for_configcontext(self):
        url = reverse("core-api:filtersetfield-retrieve-lookupvaluedomelement")
        response = self.client.get(url + "?content_type=extras.configcontext&field_name=role", **self.header)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            (
                '<select name="role" class="form-control nautobot-select2-api" data-multiple="1" '
                'data-query-param-content_types="[&quot;dcim.device&quot;, &quot;virtualization.virtualmachine&quot;]" '
                'display-field="display" value-field="name" data-depth="0" data-url="/api/extras/roles/" id="id_for_role" '
                "multiple>\n</select>"
            ),
        )

        with self.subTest("Assert correct lookup field dom element is generated"):
            response = self.client.get(url + "?content_type=dcim.location&field_name=name", **self.header)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data,
                '<select name="name" class="form-control nautobot-select2-multi-value-char" data-multiple="1" id="id_for_name" multiple>\n</select>',
            )

        with self.subTest("Assert TempFilterForm is used if model filterform raises error at initialization"):
            # The generation of a lookup field DOM representation is dependent on the ModelForm of the field;;
            # if an error occurs when initializing the ModelForm, it should fall back to creating a temp ModelForm.
            # Because the InterfaceModelForm requires a device to initialize, this is a perfect example to test that
            # the Temp ModelForm is used.
            response = self.client.get(url + "?content_type=dcim.interface&field_name=name", **self.header)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data,
                '<select name="name" class="form-control nautobot-select2-multi-value-char" data-multiple="1" id="id_for_name" multiple>\n</select>',
            )


class NautobotCSVParserTest(TestCase):
    """
    Some unit tests for the NautobotCSVParser.

    The class is also exercised by APIViewTestCases.CreateObjectViewTestCase.test_recreate_object_csv for each API.
    """

    def test_serializer_class_required(self):
        with self.assertRaises(ParseError) as cm:
            NautobotCSVParser().parse(BytesIO(b""))
        self.assertEqual(str(cm.exception), "No serializer_class was provided by the parser_context")

        with self.assertRaises(ParseError) as cm:
            NautobotCSVParser().parse(BytesIO(b""), parser_context={"serializer_class": None})
        self.assertEqual(str(cm.exception), "Serializer class for this parser_context is None, unable to proceed")

    def test_parse_success(self):
        status = extras_models.Status.objects.first()  # pylint: disable=redefined-outer-name
        tags = extras_models.Tag.objects.get_for_model(ipam_models.VLAN)
        location = dcim_models.Location.objects.filter(parent__isnull=False).first()

        csv_data = "\n".join(
            [
                # the "foobar" column is not understood by the serializer; per usual REST API behavior, it'll be skipped
                "vid,name,foobar,description,status,tags,tenant,location__name,location__parent__name",
                f'22,hello,huh?,"It, I say, is a living!",{status.name},"{tags.first().name},{tags.last().name}",,{location.name},{location.parent.name}',
            ]
        )

        data = NautobotCSVParser().parse(
            BytesIO(csv_data.encode("utf-8")),
            parser_context={"serializer_class": ipam_serializers.VLANSerializer},
        )

        self.assertEqual(
            data,
            [
                {
                    "vid": "22",  # parser could be enhanced to turn this to an int, but the serializer can handle it
                    "name": "hello",
                    "description": "It, I say, is a living!",
                    "status": status.name,  # will be understood as a composite-key by the serializer
                    "tags": [tags.first().name, tags.last().name],  # understood as a list of composite-keys
                    "tenant": None,
                    "location": {  # parsed representation of CSV data: `location__name`,`location__parent__name`
                        "name": location.name,
                        "parent": {"name": location.parent.name},
                    },
                },
            ],
        )

    def test_parse_bad_header(self):
        csv_data = "\n".join(
            [
                "vid,name,,description",
                "22,hello,huh?,a description",
            ]
        )
        with self.assertRaises(ParseError) as cm:
            NautobotCSVParser().parse(
                BytesIO(csv_data.encode("utf-8")),
                parser_context={"serializer_class": ipam_serializers.VLANSerializer},
            )
        self.assertEqual(str(cm.exception), "Row 1: Column 3: missing/empty header for this column")


class NautobotCSVRendererTest(TestCase):
    """
    Some unit tests for the NautobotCSVParser.

    The class is also exercised by APIViewTestCases.CreateObjectViewTestCase.test_recreate_object_csv and
    APIViewTestCases.ListObjectsViewTestCase.test_list_objects_csv for each API.
    """

    def test_render_success(self):
        location_type = dcim_models.LocationType.objects.filter(parent__isnull=False).first()
        data = dcim_serializers.LocationTypeSerializer(
            instance=location_type, context={"request": None, "depth": 1}
        ).data
        csv_text = NautobotCSVRenderer().render(data)

        # Make sure a) it's well-constructed parsable CSV and b) it contains what we expect it to, within reason
        reader = csv.DictReader(StringIO(csv_text))
        read_data = list(reader)[0]
        self.assertIn("id", read_data)
        self.assertEqual(read_data["id"], str(location_type.id))
        self.assertIn("display", read_data)
        self.assertEqual(read_data["display"], location_type.display)
        self.assertIn("composite_key", read_data)
        self.assertEqual(read_data["composite_key"], location_type.composite_key)
        self.assertIn("name", read_data)
        self.assertEqual(read_data["name"], location_type.name)
        self.assertIn("content_types", read_data)
        # rendering/parsing of content-types field is tested elsewhere
        self.assertIn("description", read_data)
        self.assertEqual(read_data["description"], location_type.description)
        self.assertIn("nestable", read_data)
        self.assertEqual(read_data["nestable"], str(location_type.nestable))
        self.assertIn("parent", read_data)
        self.assertEqual(read_data["parent"], location_type.parent.composite_key)


class WritableNestedSerializerTest(testing.APITestCase):
    """
    Test the operation of WritableNestedSerializer using VLANSerializer as our test subject.
    """

    def setUp(self):
        super().setUp()

        vlan_group_ct = ContentType.objects.get_for_model(ipam_models.VLANGroup)
        vlan_ct = ContentType.objects.get_for_model(ipam_models.VLAN)
        self.locations_types = [
            dcim_models.LocationType.objects.get(name="Campus"),
            dcim_models.LocationType.objects.get(name="Building"),
        ]
        for location_type in self.locations_types:
            location_type.content_types.set([vlan_group_ct, vlan_ct])

        self.statuses = extras_models.Status.objects.get_for_model(dcim_models.Location)
        self.location1 = dcim_models.Location.objects.create(
            location_type=self.locations_types[0], name="Location 1", status=self.statuses[0]
        )
        self.location2 = dcim_models.Location.objects.create(
            location_type=self.locations_types[1],
            name="Location 2",
            parent=self.location1,
            status=self.statuses[0],
        )
        self.location3 = dcim_models.Location.objects.create(
            location_type=self.locations_types[1],
            name="Location 3",
            parent=self.location1,
            status=self.statuses[0],
        )
        self.vlan_group1 = ipam_models.VLANGroup.objects.create(name="Test VLANGroup 1", location=self.location1)
        self.vlan_group2 = ipam_models.VLANGroup.objects.create(name="Test VLANGroup 2", location=self.location2)
        self.vlan_group3 = ipam_models.VLANGroup.objects.create(name="Test VLANGroup 3", location=self.location3)

    def test_related_by_pk(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "location": self.location1.pk,
            "status": self.statuses.first().pk,
            "vlan_group": self.vlan_group1.pk,
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["location"]["url"]), self.absolute_api_url(self.location1))
        vlan = ipam_models.VLAN.objects.get(pk=response.data["id"])
        self.assertEqual(vlan.status, self.statuses.first())
        self.assertEqual(vlan.location, self.location1)

    def test_related_by_pk_no_match(self):
        data = {
            "vid": 160,
            "name": "Test VLAN 160",
            "location": "00000000-0000-0000-0000-0000000009eb",
            "status": self.statuses.first().pk,
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        with testing.disable_warnings("django.request"):
            response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ipam_models.VLAN.objects.filter(name="Test VLAN 100").count(), 0)
        self.assertTrue(response.data["location"][0].startswith("Related object not found"))

    def test_related_by_attributes(self):
        data = {
            "vid": 110,
            "name": "Test VLAN 110",
            "status": self.statuses.first().pk,
            "location": {"name": "Location 1"},
            "vlan_group": self.vlan_group1.pk,
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["location"]["url"]), self.absolute_api_url(self.location1))
        vlan = ipam_models.VLAN.objects.get(pk=response.data["id"])
        self.assertEqual(vlan.location, self.location1)

    def test_related_by_attributes_no_match(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "status": self.statuses.first().pk,
            "location": {"name": "Location X"},
            "vlan_group": self.vlan_group1.pk,
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        with testing.disable_warnings("django.request"):
            response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ipam_models.VLAN.objects.filter(name="Test VLAN 100").count(), 0)
        self.assertTrue(response.data["location"][0].startswith("Related object not found"))

    def test_related_by_attributes_multiple_matches(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "status": self.statuses.first().pk,
            "location": {
                "parent": {
                    "name": self.location1.name,
                },
            },
            "vlan_group": self.vlan_group1.pk,
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        with testing.disable_warnings("django.request"):
            response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ipam_models.VLAN.objects.filter(name="Test VLAN 100").count(), 0)
        self.assertTrue(response.data["location"][0].startswith("Multiple objects match"))

    def test_related_by_composite_key(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "status": self.statuses.first().composite_key,
            "location": self.location1.composite_key,
            "vlan_group": self.vlan_group1.composite_key,
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["location"]["url"]), self.absolute_api_url(self.location1))
        vlan = ipam_models.VLAN.objects.get(pk=response.data["id"])
        self.assertEqual(vlan.location, self.location1)

    def test_related_by_composite_key_no_match(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "status": self.statuses.first().composite_key + COMPOSITE_KEY_SEPARATOR + "xyz",
            "location": self.location1.composite_key + COMPOSITE_KEY_SEPARATOR + "hello" + COMPOSITE_KEY_SEPARATOR,
            "vlan_group": self.vlan_group1.composite_key[1:-1],
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        with testing.disable_warnings("django.request"):
            response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ipam_models.VLAN.objects.filter(name="Test VLAN 100").count(), 0)
        self.assertTrue(response.data["status"][0].startswith("Related object not found"))
        self.assertTrue(response.data["location"][0].startswith("Related object not found"))
        self.assertTrue(response.data["vlan_group"][0].startswith("Related object not found"))

    def test_related_by_invalid(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "location": "XXX",
            "status": self.statuses.first().pk,
            "vlan_group": self.vlan_group2.pk,
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        with testing.disable_warnings("django.request"):
            response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ipam_models.VLAN.objects.filter(name="Test VLAN 100").count(), 0)


class APIOrderingTestCase(testing.APITestCase):
    """
    Testing integration with DRF's OrderingFilter.
    """

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("circuits-api:provider-list")
        cls.field_type_map = {
            "CharField": "name",
            "IntegerField": "asn",
            "URLField": "portal_url",
            "TextField": "admin_contact",
            "DateTimeField": "created",
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_ascending_sort(self):
        """Tests that results are returned in the expected ascending order."""

        for field_type, field_name in self.field_type_map.items():
            with self.subTest(f"Testing {field_type}"):
                response = self.client.get(f"{self.url}?sort={field_name}&limit=10", **self.header)
                self.assertHttpStatus(response, 200)
                self.assertEqual(
                    list(map(lambda p: p["id"], response.data["results"])),
                    list(
                        map(
                            lambda p: str(p),  # pylint: disable=unnecessary-lambda
                            Provider.objects.order_by(field_name).values_list("id", flat=True)[:10],
                        )
                    ),
                )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_descending_sort(self):
        """Tests that results are returned in the expected descending order."""

        for field_type, field_name in self.field_type_map.items():
            with self.subTest(f"Testing {field_type}"):
                response = self.client.get(f"{self.url}?sort=-{field_name}&limit=10", **self.header)
                self.assertHttpStatus(response, 200)
                self.assertEqual(
                    list(map(lambda p: p["id"], response.data["results"])),
                    list(
                        map(
                            lambda p: str(p),  # pylint: disable=unnecessary-lambda
                            Provider.objects.order_by(f"-{field_name}").values_list("id", flat=True)[:10],
                        )
                    ),
                )


class NewUIGetMenuAPIViewTestCase(testing.APITestCase):
    def test_get_menu(self):
        """Asset response from new ui nav menu api returns a well formatted registry["new_ui_nav_menu"] expected by nautobot-ui."""
        url = reverse("ui-api:get-menu")
        response = self.client.get(url, **self.header)
        expected_response = {
            "Inventory": {
                "Devices": {
                    "Devices": "/dcim/devices/",
                    "Device Types": "/dcim/device-types/",
                    "Platforms": "/dcim/platforms/",
                    "Manufacturers": "/dcim/manufacturers/",
                    "Virtual Chassis": "/dcim/virtual-chassis/",
                    "Device Redundancy Groups": "/dcim/device-redundancy-groups/",
                    "Connections": {
                        "Cables": "/dcim/cables/",
                        "Console Connections": "/dcim/console-connections/",
                        "Power Connections": "/dcim/power-connections/",
                        "Interface Connections": "/dcim/interface-connections/",
                    },
                    "Components": {
                        "Interfaces": "/dcim/interfaces/",
                        "Front Ports": "/dcim/front-ports/",
                        "Rear Ports": "/dcim/rear-ports/",
                        "Console Ports": "/dcim/console-ports/",
                        "Console Server Ports": "/dcim/console-server-ports/",
                        "Power Ports": "/dcim/power-ports/",
                        "Power Outlets": "/dcim/power-outlets/",
                        "Device Bays": "/dcim/device-bays/",
                        "Inventory Items": "/dcim/inventory-items/",
                    },
                    "Dynamic Groups": "/extras/dynamic-groups/",
                    "Racks": "/dcim/racks/",
                    "Rack Groups": "/dcim/rack-groups/",
                    "Rack Reservations": "/dcim/rack-reservations/",
                    "Rack Elevations": "/dcim/rack-elevations/",
                },
                "Organization": {"Locations": "/dcim/locations/", "Location Types": "/dcim/location-types/"},
                "Tenancy": {"Tenants": "/tenancy/tenants/", "Tenant Groups": "/tenancy/tenant-groups/"},
                "Circuits": {
                    "Circuits": "/circuits/circuits/",
                    "Circuit Terminations": "/circuits/circuit-terminations/",
                    "Circuit Types": "/circuits/circuit-types/",
                    "Providers": "/circuits/providers/",
                    "Provider Networks": "/circuits/provider-networks/",
                },
                "Power": {"Power Feeds": "/dcim/power-feeds/", "Power Panels": "/dcim/power-panels/"},
                "Virtualization": {
                    "Virtual Machines": "/virtualization/virtual-machines/",
                    "VM Interfaces": "/virtualization/interfaces/",
                    "Clusters": "/virtualization/clusters/",
                    "Cluster Types": "/virtualization/cluster-types/",
                    "Cluster Groups": "/virtualization/cluster-groups/",
                },
            },
            "Networks": {
                "IP Management": {
                    "IP Addresses": "/ipam/ip-addresses/",
                    "Prefixes": "/ipam/prefixes/",
                    "RIRs": "/ipam/rirs/",
                },
                "Layer 2 / Switching": {"VLANs": "/ipam/vlans/", "VLAN Groups": "/ipam/vlan-groups/"},
                "Layer 3 / Routing": {
                    "Namespaces": "/ipam/namespaces/",
                    "VRFs": "/ipam/vrfs/",
                    "Route Targets": "/ipam/route-targets/",
                },
                "Services": {"Services": "/ipam/services/"},
                "Config Contexts": {
                    "Config Contexts": "/extras/config-contexts/",
                    "Config Context Schemas": "/extras/config-context-schemas/",
                },
            },
            "Security": {"Secrets": {"Secrets": "/extras/secrets/", "Secret Groups": "/extras/secrets-groups/"}},
            "Automation": {
                "Jobs": {
                    "Jobs": "/extras/jobs/",
                    "Job Approval Queue": "/extras/jobs/scheduled-jobs/approval-queue/",
                    "Scheduled Jobs": "/extras/jobs/scheduled-jobs/",
                    "Job Results": "/extras/job-results/",
                    "Job Hooks": "/extras/job-hooks/",
                    "Job Buttons": "/extras/job-buttons/",
                },
                "Extensibility": {
                    "Webhooks": "/extras/webhooks/",
                    "GraphQL Queries": "/extras/graphql-queries/",
                    "Export Templates": "/extras/export-templates/",
                },
            },
            "Platform": {
                "Platform": {
                    "Installed Apps": "/plugins/installed-plugins/",
                    "Git Repositories": "/extras/git-repositories/",
                },
                "Governance": {"Change Log": "/extras/object-changes/"},
                "Reference Data": {"Tags": "/extras/tags/", "Statuses": "/extras/statuses/", "Roles": "/extras/roles/"},
                "Data Management": {
                    "Relationships": "/extras/relationships/",
                    "Computed Fields": "/extras/computed-fields/",
                    "Custom Fields": "/extras/custom-fields/",
                    "Custom Links": "/extras/custom-links/",
                    "Notes": "",
                },
            },
        }
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_response)


class GetSettingsAPIViewTestCase(testing.APITestCase):
    def test_get_settings(self):
        """Assert get settings value"""
        url = reverse("ui-api:settings")

        with self.subTest("Test get allowed settings"):
            url_with_filters = f"{url}?name=FEEDBACK_BUTTON_ENABLED"
            response = self.client.get(url_with_filters, **self.header)
            self.assertEqual(response.status_code, 200)
            expected_response = {"FEEDBACK_BUTTON_ENABLED": True}
            self.assertEqual(response.data, expected_response)
        with self.subTest("Test get not-allowed settings"):
            url_with_filters = f"{url}?name=NAPALM_PASSWORD"
            response = self.client.get(url_with_filters, **self.header)
            self.assertEqual(response.status_code, 400)
            expected_response = {"error": "Invalid settings names specified: NAPALM_PASSWORD."}
            self.assertEqual(response.data, expected_response)


class NewUIReadyRoutesAPIViewTestCase(testing.APITestCase):
    def test_new_ui_ready_routes(self):
        """Assert get settings value"""
        url = reverse("ui-api:new-ui-ready-routes")
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        expected_response = [
            "^$",
            "^login\\/$",
            "^dcim\\/device\\-types\\/$",
            "^dcim\\/device\\-types\\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\/$",
            "^dcim\\/devices\\/$",
            "^dcim\\/devices\\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\/$",
            "^dcim\\/locations\\/$",
            "^dcim\\/locations\\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\/$",
            "^ipam\\/ip\\-addresses\\/$",
            "^ipam\\/ip\\-addresses\\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\/$",
        ]
        self.assertEqual(sorted(response.data), sorted(expected_response))
