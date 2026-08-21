import csv
from io import BytesIO, StringIO
import json
import os
from unittest import skip
import uuid

from constance import config
from constance.test import override_config
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connections, DEFAULT_DB_ALIAS
from django.test import override_settings, RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory, force_authenticate
import yaml

from nautobot.circuits.models import Provider
from nautobot.core import testing
from nautobot.core.api.parsers import NautobotCSVParser
from nautobot.core.api.renderers import NautobotCSVRenderer
from nautobot.core.api.utils import get_serializer_for_model, get_view_name
from nautobot.core.api.versioning import NautobotAPIVersioning
from nautobot.core.api.views import ModelViewSet
from nautobot.core.constants import COMPOSITE_KEY_SEPARATOR
from nautobot.core.templatetags.helpers import humanize_speed
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.dcim import models as dcim_models
from nautobot.dcim.api import serializers as dcim_serializers
from nautobot.extras import choices, models as extras_models
from nautobot.ipam import filters as ipam_filters, models as ipam_models
from nautobot.ipam.api import serializers as ipam_serializers, views as ipam_api_views
from nautobot.tenancy import models as tenancy_models
from nautobot.users.models import ObjectPermission

User = get_user_model()


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
        user = User.objects.create_user(username="nautobotuser")
        self.client.force_login(user)

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

    def test_default_version(self):
        """Test that a request with no specific API version gets the default version, which is the current version."""
        url = reverse("api-root")
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, 200)
        self.assertIn("API-Version", response)
        self.assertEqual(response["API-Version"], api_settings.DEFAULT_VERSION)
        self.assertEqual(response["API-Version"], f"{settings.VERSION_MAJOR}.{settings.VERSION_MINOR}")

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
        self.set_api_version(max_version)
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

    def test_header_and_query_version(self):
        """Test the behavior when the API version is specified in both the Accept header *and* a query parameter."""
        url = reverse("api-root")

        min_version = api_settings.ALLOWED_VERSIONS[0]
        max_version = api_settings.ALLOWED_VERSIONS[-1]
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
                'data-query-param-exclude_m2m="[&quot;true&quot;]" '
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

    @override_settings(ALLOWED_HOSTS=["*"])
    def test_render_success(self):
        location_type = dcim_models.LocationType.objects.filter(parent__isnull=False).first()

        request = RequestFactory().get(reverse("dcim-api:location-list"), ACCEPT="text/csv")
        setattr(request, "accepted_media_type", ["text/csv"])

        data = dcim_serializers.LocationTypeSerializer(
            instance=location_type, context={"request": request, "depth": 0}
        ).data
        csv_text = NautobotCSVRenderer().render(data)

        # Make sure a) it's well-constructed parsable CSV and b) it contains what we expect it to, within reason
        reader = csv.DictReader(StringIO(csv_text))
        read_data = next(iter(reader))
        self.assertIn("id", read_data)
        self.assertEqual(read_data["id"], str(location_type.id))
        self.assertIn("display", read_data)
        self.assertEqual(read_data["display"], location_type.display)
        self.assertNotIn("composite_key", read_data)
        self.assertIn("name", read_data)
        self.assertEqual(read_data["name"], location_type.name)
        self.assertIn("content_types", read_data)
        # rendering/parsing of content-types field is tested elsewhere
        self.assertIn("description", read_data)
        self.assertEqual(read_data["description"], location_type.description)
        self.assertIn("nestable", read_data)
        self.assertEqual(read_data["nestable"], str(location_type.nestable))
        self.assertIn("parent__name", read_data)
        self.assertEqual(read_data["parent__name"], location_type.parent.name)


class ModelViewSetMixinTest(testing.APITestCase):
    """Unit tests for ModelViewSetMixin, base class for ModelViewSet/ReadOnlyModelViewSet classes."""

    class SimpleIPAddressViewSet(ModelViewSet):
        queryset = ipam_models.IPAddress.objects.all()  # no explicit optimizations
        serializer_class = ipam_serializers.IPAddressSerializer
        filterset_class = ipam_filters.IPAddressFilterSet

    @override_settings(ALLOWED_HOSTS=["*"])  # serializing hyperlinked fields builds absolute URLs
    def test_get_queryset_optimizations(self):
        """Test that the queryset is appropriately optimized based on request parameters."""
        self.user.is_superuser = True
        self.user.save()

        # With exclude_m2m query parameter set to False
        view = self.SimpleIPAddressViewSet()
        view.action_map = {"get": "list"}
        request = APIRequestFactory().get(
            reverse("ipam-api:ipaddress-list"), headers=self.header, data={"exclude_m2m": False}
        )
        force_authenticate(request, user=self.user)
        request = view.initialize_request(request)
        view.setup(request)
        view.initial(request)

        queryset = view.get_queryset()
        # IPAddress plus one natural-key prefetch (parent__namespace), plus four prefetches.
        with self.assertNumQueries(6):
            instance = queryset.first()
        # FK related objects should have been auto-selected
        with self.assertNumQueries(0):
            instance.status
            instance.role
            instance.parent
            instance.tenant
            instance.nat_inside
        # Reverse relations should have been auto-prefetched
        with self.assertNumQueries(0):
            list(instance.nat_outside_list.all())
        # Many-to-many relations should have been auto-prefetched
        with self.assertNumQueries(0):
            list(instance.interfaces.all())
            list(instance.vm_interfaces.all())
            list(instance.tags.all())

        # The `natural_slug` field calls `natural_key()`, which walks related-object natural keys (e.g.
        # parent__namespace). Those relations were prefetched above, so computing it for every object must
        # not issue an additional query per object (this was previously an N+1).
        instances = list(view.get_queryset())
        self.assertGreater(len(instances), 1, "need multiple objects for a meaningful N+1 assertion")
        with self.assertNumQueries(0):
            natural_slugs = [instance.natural_slug for instance in instances]
        # Exercise the real serializer too: natural_slug should render for every object, matching the
        # query-free traversal above. (Full serialization also issues a couple of constant, per-model
        # custom-field metadata lookups, which is why the query-count assertion targets the traversal.)
        data = view.get_serializer(instances, many=True).data
        self.assertEqual([row["natural_slug"] for row in data], natural_slugs)

        # With exclude_m2m query parameter set to True
        view = self.SimpleIPAddressViewSet()
        view.action_map = {"get": "list"}
        request = APIRequestFactory().get(
            reverse("ipam-api:ipaddress-list"), headers=self.header, data={"exclude_m2m": True}
        )
        force_authenticate(request, user=self.user)
        request = view.initialize_request(request)
        view.setup(request)
        view.initial(request)

        queryset = view.get_queryset()
        # IPAddress plus the natural-key prefetch (parent__namespace).
        # exclude_m2m suppresses the additional M2M/reverse prefetches.
        with self.assertNumQueries(2):
            instance = queryset.first()
        # FK related objects should still have been auto-selected
        with self.assertNumQueries(0):
            instance.status
            instance.role
            instance.parent
            instance.tenant
            instance.nat_inside
        # Reverse relations should NOT have been auto-prefetched
        with self.assertNumQueries(1):
            list(instance.nat_outside_list.all())
        # Many-to-many relations should NOT have been auto-prefetched
        with self.assertNumQueries(1):
            list(instance.interfaces.all())
        with self.assertNumQueries(1):
            list(instance.vm_interfaces.all())
        with self.assertNumQueries(1):
            list(instance.tags.all())


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
            location_type.content_types.add(vlan_group_ct, vlan_ct)

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
            "status": self.statuses.first().pk,
            "vlan_group": self.vlan_group1.pk,
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan", "ipam.view_vlangroup", "extras.view_status")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["vlan_group"]["url"]), self.absolute_api_url(self.vlan_group1))
        vlan = ipam_models.VLAN.objects.get(pk=response.data["id"])
        self.assertEqual(vlan.status, self.statuses.first())
        self.assertEqual(vlan.vlan_group, self.vlan_group1)

    def test_related_by_pk_no_match(self):
        data = {
            "vid": 160,
            "name": "Test VLAN 160",
            "status": self.statuses.first().pk,
            "vlan_group": "00000000-0000-0000-0000-0000000009eb",
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        with testing.disable_warnings("django.request"):
            response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ipam_models.VLAN.objects.filter(name="Test VLAN 100").count(), 0)
        self.assertTrue(response.data["vlan_group"][0].startswith("Related object not found"))

    def test_related_by_attributes(self):
        data = {
            "vid": 110,
            "name": "Test VLAN 110",
            "status": self.statuses.first().pk,
            "vlan_group": {"name": self.vlan_group1.name},
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan", "ipam.view_vlangroup", "extras.view_status")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["vlan_group"]["url"]), self.absolute_api_url(self.vlan_group1))
        vlan = ipam_models.VLAN.objects.get(pk=response.data["id"])
        self.assertEqual(vlan.vlan_group, self.vlan_group1)

    def test_related_by_attributes_no_match(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "status": self.statuses.first().pk,
            "vlan_group": {"name": "VLAN GROUP XX"},
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        with testing.disable_warnings("django.request"):
            response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ipam_models.VLAN.objects.filter(name="Test VLAN 100").count(), 0)
        self.assertTrue(response.data["vlan_group"][0].startswith("Related object not found"))

    def test_related_by_attributes_multiple_matches(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "status": self.statuses.first().pk,
            "vlan_group": {
                "location": {
                    "status": {"name": self.vlan_group1.location.status.name},
                }
            },
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan", "ipam.view_vlangroup", "extras.view_status")

        with testing.disable_warnings("django.request"):
            response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ipam_models.VLAN.objects.filter(name="Test VLAN 100").count(), 0)
        self.assertTrue(response.data["vlan_group"][0].startswith("Multiple objects match"))

    @skip("Composite keys aren't being supported at this time")
    def test_related_by_composite_key(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "status": self.statuses.first().composite_key,
            "vlan_group": self.vlan_group1.composite_key,
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["vlan_group"]["url"]), self.absolute_api_url(self.location1))
        vlan = ipam_models.VLAN.objects.get(pk=response.data["id"])
        self.assertEqual(vlan.vlan_group, self.vlan_group1)

    @skip("Composite keys aren't being supported at this time")
    def test_related_by_composite_key_no_match(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "status": self.statuses.first().composite_key + COMPOSITE_KEY_SEPARATOR + "xyz",
            "vlan_group": self.vlan_group1.composite_key[1:-1],
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        with testing.disable_warnings("django.request"):
            response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ipam_models.VLAN.objects.filter(name="Test VLAN 100").count(), 0)
        self.assertTrue(response.data["status"][0].startswith("Related object not found"))
        self.assertTrue(response.data["vlan_group"][0].startswith("Related object not found"))

    def test_related_by_invalid(self):
        data = {
            "vid": 100,
            "name": "Test VLAN 100",
            "status": self.statuses.first().pk,
            "vlan_group": "XXX",
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan")

        with testing.disable_warnings("django.request"):
            response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ipam_models.VLAN.objects.filter(name="Test VLAN 100").count(), 0)

    def test_create_with_specified_id(self):
        data = {
            "id": str(uuid.uuid4()),
            "vid": 400,
            "name": "Test VLAN 400",
            "status": self.statuses.first().pk,
            "vlan_group": self.vlan_group1.pk,
        }
        url = reverse("ipam-api:vlan-list")
        self.add_permissions("ipam.add_vlan", "ipam.view_vlangroup", "extras.view_status")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["vlan_group"]["url"]), self.absolute_api_url(self.vlan_group1))
        self.assertEqual(str(response.data["id"]), data["id"])
        vlan = ipam_models.VLAN.objects.get(pk=response.data["id"])
        self.assertEqual(vlan.status, self.statuses.first())
        self.assertEqual(vlan.vlan_group, self.vlan_group1)


@override_settings(EXEMPT_VIEW_PERMISSIONS=[])
class DepthPermissionEnforcementTest(testing.APITestCase):
    """
    Test that object-level `view` permissions are enforced on related objects traversed via `?depth=N`.

    A user who lacks permission to view a related object should see it rendered as its brief
    {id, object_type, url} representation (as at depth 0), NOT in full detail and NOT as null. This is
    verified for both regular ForeignKey traversal (VLANGroup -> Location) and GenericForeignKey
    traversal (Note -> assigned_object), including the object-level-constrained case which mirrors the
    behavior of RestrictedQuerySet.restrict().
    """

    def setUp(self):
        super().setUp()
        location_type = dcim_models.LocationType.objects.get(name="Campus")
        location_status = extras_models.Status.objects.get_for_model(dcim_models.Location).first()
        self.viewable_location = dcim_models.Location.objects.create(
            name="Depth Perm Viewable Location", location_type=location_type, status=location_status
        )
        self.hidden_location = dcim_models.Location.objects.create(
            name="Depth Perm Hidden Location", location_type=location_type, status=location_status
        )
        self.viewable_group = ipam_models.VLANGroup.objects.create(
            name="Depth Perm Viewable Group", location=self.viewable_location
        )
        self.hidden_group = ipam_models.VLANGroup.objects.create(
            name="Depth Perm Hidden Group", location=self.hidden_location
        )
        self.vlan_group_list_url = reverse(get_route_for_model(ipam_models.VLANGroup, "list", api=True))

    def _constrain_location_view_permission(self):
        """Grant view permission for only the "viewable" Location (an object-level constraint)."""
        obj_perm = ObjectPermission(
            name="View viewable location only",
            constraints={"pk": str(self.viewable_location.pk)},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(dcim_models.Location))

    @staticmethod
    def _results_by_pk(response):
        return {str(entry["id"]): entry for entry in response.data["results"]}

    def test_fk_related_object_downgraded_when_view_constrained(self):
        """A related FK object the user cannot view is downgraded to brief; a viewable one stays full."""
        self.add_permissions("ipam.view_vlangroup")
        self._constrain_location_view_permission()

        response = self.client.get(f"{self.vlan_group_list_url}?depth=1", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        results = self._results_by_pk(response)

        viewable = results[str(self.viewable_group.pk)]["location"]
        hidden = results[str(self.hidden_group.pk)]["location"]

        # Viewable location -> full detail.
        self.assertGreater(len(viewable.keys()), 4)
        self.assertEqual(viewable["name"], self.viewable_location.name)

        # Hidden location -> brief plus display (not full, and not null). `display` is included because the
        # location would otherwise have been fully serialized at depth=1, giving parity with the UI.
        self.assertIsNotNone(hidden)
        self.assertEqual(set(hidden.keys()), {"id", "object_type", "url", "display"})
        self.assertEqual(str(hidden["id"]), str(self.hidden_location.pk))
        self.assertEqual(hidden["object_type"], "dcim.location")
        self.assertEqual(hidden["url"], self.absolute_api_url(self.hidden_location))
        self.assertEqual(hidden["display"], self.hidden_location.display)

    def test_fk_related_object_full_with_model_level_permission(self):
        """With unconstrained view permission on the related model, both related objects are full."""
        self.add_permissions("ipam.view_vlangroup", "dcim.view_location")
        response = self.client.get(f"{self.vlan_group_list_url}?depth=1", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        results = self._results_by_pk(response)
        for group in (self.viewable_group, self.hidden_group):
            location = results[str(group.pk)]["location"]
            self.assertGreater(len(location.keys()), 3)
            self.assertIn("name", location)

    def test_fk_related_object_brief_without_related_permission(self):
        """With no permission on the related model at all, related objects are brief+display (and not null)."""
        self.add_permissions("ipam.view_vlangroup")
        response = self.client.get(f"{self.vlan_group_list_url}?depth=1", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        results = self._results_by_pk(response)
        for group in (self.viewable_group, self.hidden_group):
            location = results[str(group.pk)]["location"]
            self.assertIsNotNone(location)
            self.assertEqual(set(location.keys()), {"id", "object_type", "url", "display"})
            self.assertEqual(location["display"], group.location.display)

    def test_constrained_permission_check_is_memoized(self):
        """Per-object permission checks are memoized, so shared related objects don't cause N+1 queries.

        This isolates the cost of the permission check itself: the same request is issued before and
        after adding many more primary objects that all reference the SAME two related locations. The
        object-level view constraint means each location's visibility requires a database check, but
        that result is memoized per (model, pk) on the request, so the query count must not grow with
        the number of primary objects. Uses ?exclude_m2m=false so that any many-to-many related objects
        are serialized (and checked) as well.
        """
        self.add_permissions("ipam.view_vlangroup")
        self._constrain_location_view_permission()
        url = f"{self.vlan_group_list_url}?depth=1&exclude_m2m=false"

        with CaptureQueriesContext(connections[DEFAULT_DB_ALIAS]) as baseline_cqc:
            response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        baseline_queries = len(baseline_cqc)

        # Add several more groups that reference the SAME two locations.
        for i in range(6):
            ipam_models.VLANGroup.objects.create(name=f"Depth Perm Extra Viewable {i}", location=self.viewable_location)
            ipam_models.VLANGroup.objects.create(name=f"Depth Perm Extra Hidden {i}", location=self.hidden_location)

        with CaptureQueriesContext(connections[DEFAULT_DB_ALIAS]) as scaled_cqc:
            response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        # The permission check for each distinct location is cached per request, so adding more groups
        # that reference the same locations must not add per-object permission queries.
        self.assertLessEqual(
            len(scaled_cqc),
            baseline_queries + 2,
            "Object-level permission checks were not memoized; depth serialization has an N+1 query.",
        )

    def test_m2m_related_objects_downgraded_when_view_constrained(self):
        """Each member of a many-to-many related field is independently downgraded to brief if not viewable."""
        config_context = extras_models.ConfigContext.objects.create(
            name="Depth Perm Config Context", weight=100, data={"a": 1}
        )
        config_context.locations.set([self.viewable_location, self.hidden_location])
        self.add_permissions("extras.view_configcontext")
        self._constrain_location_view_permission()

        config_context_list_url = reverse(get_route_for_model(extras_models.ConfigContext, "list", api=True))
        # exclude_m2m=false so that the many-to-many `locations` field is serialized at all.
        response = self.client.get(f"{config_context_list_url}?depth=1&exclude_m2m=false", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        locations = self._results_by_pk(response)[str(config_context.pk)]["locations"]
        self.assertEqual(len(locations), 2)
        locations_by_pk = {str(entry["id"]): entry for entry in locations}

        # Viewable location -> full detail.
        viewable = locations_by_pk[str(self.viewable_location.pk)]
        self.assertGreater(len(viewable.keys()), 4)
        self.assertEqual(viewable["name"], self.viewable_location.name)

        # Hidden location -> brief plus display (not full, not null, and not omitted from the list).
        hidden = locations_by_pk[str(self.hidden_location.pk)]
        self.assertEqual(set(hidden.keys()), {"id", "object_type", "url", "display"})
        self.assertEqual(hidden["object_type"], "dcim.location")
        self.assertEqual(hidden["url"], self.absolute_api_url(self.hidden_location))
        self.assertEqual(hidden["display"], self.hidden_location.display)

    def test_gfk_related_object_downgraded_when_view_constrained(self):
        """A GenericForeignKey target the user cannot view is downgraded to brief; a viewable one stays full."""
        viewable_note = extras_models.Note.objects.create(
            note="Viewable note", assigned_object=self.viewable_location, user=self.user
        )
        hidden_note = extras_models.Note.objects.create(
            note="Hidden note", assigned_object=self.hidden_location, user=self.user
        )
        self.add_permissions("extras.view_note")
        self._constrain_location_view_permission()

        note_list_url = reverse(get_route_for_model(extras_models.Note, "list", api=True))
        response = self.client.get(f"{note_list_url}?depth=1", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        results = self._results_by_pk(response)

        viewable = results[str(viewable_note.pk)]["assigned_object"]
        hidden = results[str(hidden_note.pk)]["assigned_object"]

        # Viewable assigned object -> full nested detail (retaining the generic_foreign_key flag).
        self.assertGreater(len(viewable.keys()), 4)
        self.assertEqual(viewable["name"], self.viewable_location.name)
        self.assertTrue(viewable.get("generic_foreign_key"))

        # Hidden assigned object -> brief plus display (no generic_foreign_key flag), not null.
        self.assertIsNotNone(hidden)
        self.assertEqual(set(hidden.keys()), {"id", "object_type", "url", "display"})
        self.assertEqual(str(hidden["id"]), str(self.hidden_location.pk))
        self.assertEqual(hidden["object_type"], "dcim.location")
        self.assertEqual(hidden["display"], self.hidden_location.display)


class InvalidDepthParameterTest(testing.APITestCase):
    """Test that an out-of-range `?depth=` query parameter results in an HTTP 400, not an HTTP 500."""

    def setUp(self):
        super().setUp()
        self.add_permissions("ipam.view_vlangroup")
        self.vlan_group_list_url = reverse(get_route_for_model(ipam_models.VLANGroup, "list", api=True))

    def test_depth_greater_than_max_returns_400(self):
        response = self.client.get(f"{self.vlan_group_list_url}?depth=11", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_negative_depth_returns_400(self):
        response = self.client.get(f"{self.vlan_group_list_url}?depth=-1", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_depth_within_range_returns_200(self):
        response = self.client.get(f"{self.vlan_group_list_url}?depth=10", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)


@override_settings(EXEMPT_VIEW_PERMISSIONS=[])
class WriteRelatedObjectPermissionTest(testing.APITestCase):
    """
    Test that REST API write operations (POST/PATCH) enforce `view` permission on referenced related objects.

    A user may only reference (associate) a related object that they are permitted to view; referencing an
    object they cannot view is rejected with a validation error rather than silently succeeding. Covers regular
    ForeignKey references (VLAN -> VLANGroup) and GenericForeignKey references (Note -> assigned_object).
    """

    def setUp(self):
        super().setUp()
        self.vlan_status = extras_models.Status.objects.get_for_model(ipam_models.VLAN).first()
        self.vlan_group1 = ipam_models.VLANGroup.objects.create(name="Write Perm VLANGroup 1")
        self.vlan_group2 = ipam_models.VLANGroup.objects.create(name="Write Perm VLANGroup 2")
        self.vlan_list_url = reverse("ipam-api:vlan-list")
        self.location = dcim_models.Location.objects.create(
            name="Write Perm Location",
            location_type=dcim_models.LocationType.objects.get(name="Campus"),
            status=extras_models.Status.objects.get_for_model(dcim_models.Location).first(),
        )
        self.note_list_url = reverse("extras-api:note-list")

    def _constrain_vlangroup_view_permission(self):
        """Grant view permission for only vlan_group1 (an object-level constraint)."""
        obj_perm = ObjectPermission(
            name="View VLANGroup 1 only",
            constraints={"pk": str(self.vlan_group1.pk)},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(ipam_models.VLANGroup))

    def test_post_fk_reference_requires_view_permission(self):
        """POST referencing an existing FK related object the user cannot view is rejected."""
        data = {
            "vid": 100,
            "name": "Write Perm VLAN 100",
            "status": self.vlan_status.pk,
            "vlan_group": self.vlan_group1.pk,
        }
        # Can add VLANs and view the referenced Status, but NOT the referenced VLANGroup.
        self.add_permissions("ipam.add_vlan", "extras.view_status")
        with testing.disable_warnings("django.request"):
            response = self.client.post(self.vlan_list_url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(response.data["vlan_group"][0].startswith("Related object not found"))
        self.assertFalse(ipam_models.VLAN.objects.filter(name="Write Perm VLAN 100").exists())

        # Granting view permission on the VLANGroup allows the reference.
        self.add_permissions("ipam.view_vlangroup")
        response = self.client.post(self.vlan_list_url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(ipam_models.VLAN.objects.get(pk=response.data["id"]).vlan_group, self.vlan_group1)

    def test_post_fk_reference_respects_object_level_constraint(self):
        """POST referencing an FK related object outside the user's object-level view constraint is rejected."""
        self.add_permissions("ipam.add_vlan", "extras.view_status")
        self._constrain_vlangroup_view_permission()

        # Referencing the viewable group succeeds.
        response = self.client.post(
            self.vlan_list_url,
            {
                "vid": 101,
                "name": "Write Perm VLAN 101",
                "status": self.vlan_status.pk,
                "vlan_group": self.vlan_group1.pk,
            },
            format="json",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        # Referencing the non-viewable group is rejected.
        with testing.disable_warnings("django.request"):
            response = self.client.post(
                self.vlan_list_url,
                {
                    "vid": 102,
                    "name": "Write Perm VLAN 102",
                    "status": self.vlan_status.pk,
                    "vlan_group": self.vlan_group2.pk,
                },
                format="json",
                **self.header,
            )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(response.data["vlan_group"][0].startswith("Related object not found"))

    def test_patch_fk_reference_requires_view_permission(self):
        """PATCH updating an FK to a related object the user cannot view is rejected and leaves it unchanged."""
        vlan = ipam_models.VLAN.objects.create(
            vid=200, name="Write Perm VLAN 200", status=self.vlan_status, vlan_group=self.vlan_group1
        )
        url = reverse("ipam-api:vlan-detail", kwargs={"pk": vlan.pk})
        # Can change the VLAN, but cannot view vlan_group2.
        self.add_permissions("ipam.change_vlan")
        with testing.disable_warnings("django.request"):
            response = self.client.patch(url, {"vlan_group": self.vlan_group2.pk}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(response.data["vlan_group"][0].startswith("Related object not found"))
        vlan.refresh_from_db()
        self.assertEqual(vlan.vlan_group, self.vlan_group1)

    def test_post_gfk_reference_requires_view_permission(self):
        """POST referencing a GenericForeignKey target the user cannot view is rejected."""
        data = {
            "note": "Write perm test note",
            "assigned_object_type": "dcim.location",
            "assigned_object_id": str(self.location.pk),
        }
        # Can add notes, but cannot view the target Location.
        self.add_permissions("extras.add_note")
        with testing.disable_warnings("django.request"):
            response = self.client.post(self.note_list_url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        # The GenericForeignKey existence + permission check reports on the fk field.
        self.assertIn("assigned_object_id", response.data)
        self.assertFalse(extras_models.Note.objects.filter(note="Write perm test note").exists())

        # Granting view permission on the Location allows the reference.
        self.add_permissions("dcim.view_location")
        response = self.client.post(self.note_list_url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)


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
        cls.maxDiff = None

    def _validate_sorted_response(self, response, queryset, field_name, is_fk_field=False):
        self.assertHttpStatus(response, 200)

        # If the field is a foreign key field, we cannot guarantee the relative order of objects with the same value across multiple objects.
        # Therefore, we directly compare the names of the foreign key objects.
        if is_fk_field:
            api_data = list(map(lambda p: p[field_name]["name"] if p[field_name] else None, response.data["results"]))
            queryset_data = list(queryset.values_list(f"{field_name}__name", flat=True)[:10])
        else:
            api_data = list(map(lambda p: p["id"], response.data["results"]))
            queryset_data = list(
                map(
                    lambda p: str(p),  # pylint: disable=unnecessary-lambda
                    queryset.values_list("id", flat=True)[:10],
                )
            )
        self.assertEqual(api_data, queryset_data)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_ascending_sort(self):
        """Tests that results are returned in the expected ascending order."""

        for field_type, field_name in self.field_type_map.items():
            with self.subTest(f"Testing {field_type} {field_name}"):
                # Use `name` as a secondary sort as fields like `asn` and `admin_contact` may be null
                response = self.client.get(f"{self.url}?sort={field_name},name&limit=10", **self.header)
                self._validate_sorted_response(
                    response, Provider.objects.all().order_by(field_name, "name"), field_name
                )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_descending_sort(self):
        """Tests that results are returned in the expected descending order."""

        for field_type, field_name in self.field_type_map.items():
            with self.subTest(f"Testing {field_type} {field_name}"):
                # Use `name` as a secondary sort as fields like `asn` and `admin_contact` may be null
                response = self.client.get(f"{self.url}?sort=-{field_name},name&limit=10", **self.header)
                self._validate_sorted_response(
                    response, Provider.objects.all().order_by(f"-{field_name}", "name"), field_name
                )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_sorting_tree_node_models(self):
        location_type = dcim_models.LocationType.objects.get(name="Campus")
        locations = dcim_models.Location.objects.filter(location_type=location_type)
        devices = dcim_models.Device.objects.all()

        dcim_models.RackGroup.objects.create(name="Rack Group 0", location=locations[0])
        dcim_models.InventoryItem.objects.create(
            device=devices[0], name="Inventory Item 0", manufacturer=devices[0].device_type.manufacturer
        )

        for i in range(1, 3):
            dcim_models.InventoryItem.objects.create(
                name=f"Inventory Item {i}",
                device=devices[i],
                manufacturer=devices[i].device_type.manufacturer,
                parent=dcim_models.InventoryItem.objects.all()[i - 1],
            )
            dcim_models.RackGroup.objects.create(
                name=f"Rack Group {i}",
                location=locations[i],
                parent=dcim_models.RackGroup.objects.all()[i - 1],
            )

        tree_node_models = [
            dcim_models.Location,
            dcim_models.LocationType,
            dcim_models.RackGroup,
            dcim_models.InventoryItem,
            tenancy_models.TenantGroup,
        ]
        # Each of the table has at-least two sortable field_names in the field_names
        fk_fields = ["location", "parent", "location_type", "manufacturer"]
        model_field_names = ["name", *fk_fields]
        for model_class in tree_node_models:
            url = reverse(get_route_for_model(model_class, "list", api=True))
            serializer = get_serializer_for_model(model_class)
            serializer_avail_fields = set(model_field_names) & set(serializer().fields.keys())
            for field_name in serializer_avail_fields:
                with self.subTest(f'Assert sorting "{model_class.__name__}" using "{field_name}" field name.'):
                    response = self.client.get(f"{url}?sort={field_name}&limit=10&depth=1", **self.header)
                    self._validate_sorted_response(
                        response=response,
                        queryset=model_class.objects.extra(order_by=[field_name]),
                        field_name=field_name,
                        is_fk_field=field_name in fk_fields,
                    )

                with self.subTest(f'Assert inverse sorting "{model_class.__name__}" using "{field_name}" field name.'):
                    response = self.client.get(f"{url}?sort=-{field_name}&limit=10&depth=1", **self.header)
                    self._validate_sorted_response(
                        response=response,
                        queryset=model_class.objects.extra(order_by=[f"-{field_name}"]),
                        field_name=field_name,
                        is_fk_field=field_name in fk_fields,
                    )


class SettingsJSONSchemaViewTestCase(testing.APITestCase):
    """Tests for the /api/settings-schema/ REST API endpoint."""

    def test_correct_response(self):
        file_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/settings.yaml"
        with open(file_path, "r") as schemafile:
            expected_schema_data = yaml.safe_load(schemafile)

        url = reverse("setting_schema_json")
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected_schema_data)


class NautobotGetViewNameTest(TestCase):
    """
    Some unit tests for the get_view_name() functionality.
    """

    @override_settings(ALLOWED_HOSTS=["*"])
    def test_get(self):
        """Assert that the proper view name is displayed for the correct view."""
        viewset = ipam_api_views.PrefixViewSet
        # We need to get a specific view, so we need to set the class kwargs
        view_kwargs = {
            "Prefixes": {"suffix": "List", "basename": "prefix", "detail": False},
            "Prefix": {"suffix": "Instance", "basename": "prefix", "detail": True},
            "Available IPs": {"name": "Available IPs"},
            "Available Prefixes": {"name": "Available Prefixes"},
            "Notes": {"name": "Notes"},
        }
        for view_name, view_kwarg in view_kwargs.items():
            self.assertEqual(view_name, get_view_name(viewset(**view_kwarg)))


class RenderJinjaViewTest(testing.APITestCase):
    """Test case for the RenderJinjaView API view."""

    def test_render_jinja_template(self):
        """
        Test rendering a valid Jinja template.
        """
        interfaces = ["Ethernet1/1", "Ethernet1/2", "Ethernet1/3"]

        template_code = "\n".join(
            [
                r"{% for int in interfaces -%}",
                r"interface {{ int }}",
                r"  speed {{ 1000000000|humanize_speed }}",
                r"  duplex full",
                r"{% endfor %}",
            ]
        )

        expected_response = "\n".join(
            [
                "\n".join(
                    [
                        f"interface {int}",
                        f"  speed {humanize_speed(1000000000)}",
                        r"  duplex full",
                    ]
                )
                for int in interfaces
            ]
            + [""]  # Add an extra newline at the end because jinja whitespace control is "fun"
        )

        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {
                "template_code": template_code,
                "context": {"interfaces": interfaces},
            },
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertSequenceEqual(
            list(response.data.keys()),
            ["rendered_template", "rendered_template_lines", "template_code", "context"],
        )
        self.assertEqual(response.data["rendered_template"], expected_response)
        self.assertEqual(response.data["rendered_template_lines"], expected_response.split("\n"))

    def test_render_jinja_template_does_not_expose_secrets(self):
        """Regression test for GHSA-6jmc-h6f2-46j4: secrets must not be readable through the renderer.

        A non-allowlisted setting fails to render as though it did not exist, rather than returning its
        value.
        """
        response = self.client.post(
            reverse("core-api:render_jinja_template"),
            {"template_code": '{{ "SECRET_KEY" | settings_or_config }}', "context": {}},
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Failed to render Jinja template: SECRET_KEY")

    def test_render_jinja_template_failures(self):
        """
        Test rendering invalid Jinja templates.
        """
        test_data = [
            {
                "template_code": r"{% hello world %}",
                "error_msg": "Encountered unknown tag 'hello'.",
            },
            {
                "template_code": r"{{ hello world %}",
                "error_msg": "expected token 'end of print statement', got 'world'",
            },
        ]

        for data in test_data:
            with self.subTest(data):
                response = self.client.post(
                    reverse("core-api:render_jinja_template"),
                    {
                        "template_code": data["template_code"],
                        "context": {"foo": "bar"},
                    },
                    format="json",
                    **self.header,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertSequenceEqual(list(response.data.keys()), ["detail"])
                self.assertEqual(response.data["detail"], f"Failed to render Jinja template: {data['error_msg']}")
