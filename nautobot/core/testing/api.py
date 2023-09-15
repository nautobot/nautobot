import csv
from io import StringIO
from typing import Optional, Sequence, Union

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import ForeignKey, ManyToManyField
from django.test import override_settings, tag
from django.urls import reverse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.test import APITransactionTestCase as _APITransactionTestCase

from nautobot.core import testing
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.models import fields as core_fields
from nautobot.core.models.tree_queries import TreeModel
from nautobot.core.testing import mixins, views
from nautobot.core.utils import lookup
from nautobot.core.utils.data import is_uuid
from nautobot.extras import choices as extras_choices
from nautobot.extras import models as extras_models
from nautobot.extras import registry
from nautobot.users import models as users_models

__all__ = (
    "APITestCase",
    "APIViewTestCases",
)


#
# REST API Tests
#


@tag("api")
class APITestCase(views.ModelTestCase):
    """
    Base test case for API requests.

    api_version: Specific API version to test. Leave unset to test the default behavior. Override with set_api_version()
    """

    api_version = None

    def setUp(self):
        """
        Create a token for API calls.
        """
        super().setUp()
        self.client.logout()
        self.token = users_models.Token.objects.create(user=self.user)
        self.header = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}
        if self.api_version:
            self.set_api_version(self.api_version)

    def set_api_version(self, api_version):
        """Set or unset a specific API version for requests in this test case."""
        if api_version is None:
            self.header["HTTP_ACCEPT"] = "application/json"
        else:
            self.header["HTTP_ACCEPT"] = f"application/json; version={api_version}"

    def _get_detail_url(self, instance):
        viewname = lookup.get_route_for_model(instance, "detail", api=True)
        return reverse(viewname, kwargs={"pk": instance.pk})

    def _get_list_url(self):
        viewname = lookup.get_route_for_model(self.model, "list", api=True)
        return reverse(viewname)


@tag("unit")
class APIViewTestCases:
    class GetObjectViewTestCase(APITestCase):
        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_get_object_anonymous(self):
            """
            GET a single object as an unauthenticated user.
            """
            url = self._get_detail_url(self._get_queryset().first())
            if (
                self.model._meta.app_label,
                self.model._meta.model_name,
            ) in settings.EXEMPT_EXCLUDE_MODELS:
                # Models listed in EXEMPT_EXCLUDE_MODELS should not be accessible to anonymous users
                with testing.disable_warnings("django.request"):
                    self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_403_FORBIDDEN)
            else:
                response = self.client.get(url, **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_get_object_without_permission(self):
            """
            GET a single object as an authenticated user without the required permission.
            """
            url = self._get_detail_url(self._get_queryset().first())

            # Try GET without permission
            with testing.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_403_FORBIDDEN)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_get_object(self):
            """
            GET a single object as an authenticated user with permission to view the object.
            """
            self.assertGreaterEqual(
                self._get_queryset().count(),
                2,
                f"Test requires the creation of at least two {self.model} instances",
            )
            instance1, instance2 = self._get_queryset()[:2]

            # Add object-level permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={"pk": instance1.pk},
                actions=["view"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Try GET to non-permitted object
            url = self._get_detail_url(instance2)
            self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_404_NOT_FOUND)

            # Try GET to permitted object
            url = self._get_detail_url(instance1)
            response = self.client.get(url, **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertIsInstance(response.data, dict)
            # Fields that should be present in *ALL* model serializers:
            self.assertIn("id", response.data)
            self.assertEqual(str(response.data["id"]), str(instance1.pk))  # coerce to str to handle both int and uuid
            self.assertIn("url", response.data)
            self.assertIn("display", response.data)
            self.assertIn("natural_slug", response.data)
            self.assertIsInstance(response.data["display"], str)
            # Fields that should be present in appropriate model serializers:
            if issubclass(self.model, extras_models.ChangeLoggedModel):
                self.assertIn("created", response.data)
                self.assertIn("last_updated", response.data)
            # Fields that should be absent by default (opt-in fields):
            self.assertNotIn("computed_fields", response.data)
            self.assertNotIn("relationships", response.data)

            # If opt-in fields are supported on this model, make sure they can be opted into

            custom_fields_registry = registry.registry["model_features"]["custom_fields"]
            # computed fields and custom fields use the same registry
            cf_supported = self.model._meta.model_name in custom_fields_registry.get(self.model._meta.app_label, {})
            if cf_supported:  # custom_fields is not an opt-in field, it should always be present if supported
                self.assertIn("custom_fields", response.data)
                self.assertIsInstance(response.data["custom_fields"], dict)

            relationships_registry = registry.registry["model_features"]["relationships"]
            rel_supported = self.model._meta.model_name in relationships_registry.get(self.model._meta.app_label, {})
            if cf_supported or rel_supported:
                query_params = []
                if cf_supported:
                    query_params.append("include=computed_fields")
                if rel_supported:
                    query_params.append("include=relationships")
                query_string = "&".join(query_params)
                url = f"{url}?{query_string}"

                response = self.client.get(url, **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertIsInstance(response.data, dict)
                if cf_supported:
                    self.assertIn("computed_fields", response.data)
                    self.assertIsInstance(response.data["computed_fields"], dict)
                else:
                    self.assertNotIn("computed_fields", response.data)
                if rel_supported:
                    self.assertIn("relationships", response.data)
                    self.assertIsInstance(response.data["relationships"], dict)
                else:
                    self.assertNotIn("relationships", response.data)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_options_object(self):
            """
            Make an OPTIONS request for a single object.
            """
            url = self._get_detail_url(self._get_queryset().first())
            response = self.client.options(url, **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)

            with self.subTest("Assert Detail View Config is generated well"):
                # Namings Help
                # 1. detail_view_config: This is the detail view config set in the serializer.Meta.detail_view_config
                # 2. detail_view_schema: This is the retrieve schema generated from an OPTIONS request.
                # 3. advanced_view_config: This is the advanced view config set in the serializer.Meta.advanced_view_config
                # 4. advanced_view_schema: This is the advanced tab schema generated from an OPTIONS request.
                serializer = get_serializer_for_model(self._get_queryset().model)
                advanced_view_schema = response.data["view_options"]["advanced"]

                if getattr(serializer.Meta, "advanced_view_config", None):
                    # Get all custom advanced tab fields
                    advanced_view_config = serializer.Meta.advanced_view_config
                    self.assertGreaterEqual(len(advanced_view_schema), 1)
                    advanced_tab_fields = []
                    advanced_view_layout = advanced_view_config["layout"]
                    for section in advanced_view_layout:
                        for value in section.values():
                            advanced_tab_fields += value["fields"]
                else:
                    # Get default advanced tab fields
                    self.assertEqual(len(advanced_view_schema), 1)
                    self.assertIn("Object Details", advanced_view_schema[0])
                    advanced_tab_fields = advanced_view_schema[0].get("Object Details")["fields"]

                if detail_view_config := getattr(serializer.Meta, "detail_view_config", None):
                    detail_view_schema = response.data["view_options"]["retrieve"]
                    self.assertHttpStatus(response, status.HTTP_200_OK)

                    # According to convention, fields in the advanced tab fields should not exist in
                    # the `detail_view_schema`. Assert this is True.
                    with self.subTest("Assert advanced tab fields should not exist in the detail_view_schema."):
                        if detail_view_config.get("include_others"):
                            # Handle `Other Fields` specially as `Other Field` is dynamically added by nautobot and not part of the serializer view config
                            other_fields = detail_view_schema[0]["Other Fields"]["fields"]
                            for field in advanced_tab_fields:
                                self.assertNotIn(field, other_fields)

                        for col_idx, col in enumerate(detail_view_schema):
                            for group_idx, (group_title, group) in enumerate(col.items()):
                                if group_title == "Other Fields":
                                    continue
                                group_fields = group["fields"]
                                # Config on the serializer
                                fields = detail_view_config["layout"][col_idx][group_title]["fields"]
                                # According to convention, advanced_tab_fields should only exist at the end of the first col group and should be
                                # deleted from any other places it may appear in the layout. Assert this is True.
                                if group_idx == 0 == col_idx:
                                    self.assertFalse(
                                        any(
                                            field in advanced_tab_fields
                                            for field in group_fields[: -len(advanced_tab_fields)]
                                        )
                                    )
                                else:
                                    for field in group_fields:
                                        self.assertNotIn(field, advanced_tab_fields)
                                # Assert response from options correspond to the view config set on the serializer
                                for field in fields:
                                    if field not in advanced_tab_fields:
                                        self.assertIn(field, group_fields)

    class ListObjectsViewTestCase(APITestCase):
        choices_fields = None
        filterset = None

        def get_filterset(self):
            return self.filterset or lookup.get_filterset_for_model(self.model)

        def get_depth_fields(self):
            """Get a list of model fields that could be tested with the ?depth query parameter"""
            depth_fields = []
            for field in self.model._meta.fields:
                if not field.name.startswith("_"):
                    if isinstance(field, (ForeignKey, GenericForeignKey, ManyToManyField, core_fields.TagsField)) and (
                        # we represent content-types as "app_label.modelname" rather than as FKs
                        field.related_model != ContentType
                        # user is a model field on Token but not a field on TokenSerializer
                        and not (field.name == "user" and self.model == users_models.Token)
                    ):
                        depth_fields.append(field.name)
            return depth_fields

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_list_objects_anonymous(self):
            """
            GET a list of objects as an unauthenticated user.
            """
            url = self._get_list_url()
            if (
                self.model._meta.app_label,
                self.model._meta.model_name,
            ) in settings.EXEMPT_EXCLUDE_MODELS:
                # Models listed in EXEMPT_EXCLUDE_MODELS should not be accessible to anonymous users
                with testing.disable_warnings("django.request"):
                    self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_403_FORBIDDEN)
            else:
                # TODO(Glenn): if we're passing **self.header, we are *by definition* **NOT** anonymous!!
                response = self.client.get(url, **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertIsInstance(response.data, dict)
                self.assertIn("results", response.data)
                self.assertEqual(len(response.data["results"]), self._get_queryset().count())

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_depth_0(self):
            """
            GET a list of objects using the "?depth=0" parameter.
            """
            depth_fields = self.get_depth_fields()
            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
            url = f"{self._get_list_url()}?depth=0"
            response = self.client.get(url, **self.header)

            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertIsInstance(response.data, dict)
            self.assertIn("results", response.data)
            self.assertEqual(len(response.data["results"]), self._get_queryset().count())

            for response_data in response.data["results"]:
                for field in depth_fields:
                    self.assertIn(field, response_data)
                    if isinstance(response_data[field], list):
                        for entry in response_data[field]:
                            self.assertIsInstance(entry, dict)
                            self.assertTrue(is_uuid(entry["id"]))
                    else:
                        if response_data[field] is not None:
                            self.assertIsInstance(response_data[field], dict)
                            url = response_data[field]["url"]
                            pk = response_data[field]["id"]
                            object_type = response_data[field]["object_type"]
                            # The response should be a brief API object, containing an ID, object_type, and URL ending in the UUID of the relevant object
                            # http://nautobot.example.com/api/circuits/providers/<uuid>/
                            #                                                    ^^^^^^
                            self.assertTrue(is_uuid(url.split("/")[-2]))
                            self.assertTrue(is_uuid(pk))

                            with self.subTest(f"Assert object_type {object_type} is valid"):
                                app_label, model_name = object_type.split(".")
                                ContentType.objects.get(app_label=app_label, model=model_name)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_depth_1(self):
            """
            GET a list of objects using the "?depth=1" parameter.
            """
            depth_fields = self.get_depth_fields()
            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
            url = f"{self._get_list_url()}?depth=1"
            response = self.client.get(url, **self.header)

            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertIsInstance(response.data, dict)
            self.assertIn("results", response.data)
            self.assertEqual(len(response.data["results"]), self._get_queryset().count())

            for response_data in response.data["results"]:
                for field in depth_fields:
                    self.assertIn(field, response_data)
                    if isinstance(response_data[field], list):
                        for entry in response_data[field]:
                            self.assertIsInstance(entry, dict)
                            self.assertTrue(is_uuid(entry["id"]))
                    else:
                        if response_data[field] is not None:
                            self.assertIsInstance(response_data[field], dict)
                            self.assertTrue(is_uuid(response_data[field]["id"]))

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_without_permission(self):
            """
            GET a list of objects as an authenticated user without the required permission.
            """
            url = self._get_list_url()

            # Try GET without permission
            with testing.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_403_FORBIDDEN)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects(self):
            """
            GET a list of objects as an authenticated user with permission to view the objects.
            """
            self.assertGreaterEqual(
                self._get_queryset().count(),
                3,
                f"Test requires the creation of at least three {self.model} instances",
            )
            instance1, instance2 = self._get_queryset()[:2]

            # Add object-level permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={"pk__in": [instance1.pk, instance2.pk]},
                actions=["view"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Try GET to permitted objects
            response = self.client.get(self._get_list_url(), **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertIsInstance(response.data, dict)
            self.assertIn("results", response.data)
            self.assertEqual(len(response.data["results"]), 2)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_filtered(self):
            """
            GET a list of objects filtered by ID.
            """
            self.assertGreaterEqual(
                self._get_queryset().count(),
                3,
                f"Test requires the creation of at least three {self.model} instances",
            )
            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
            instance1, instance2 = self._get_queryset()[:2]
            response = self.client.get(f"{self._get_list_url()}?id={instance1.pk}&id={instance2.pk}", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertIsInstance(response.data, dict)
            self.assertIn("results", response.data)
            self.assertEqual(len(response.data["results"]), 2)
            for entry in response.data["results"]:
                self.assertIn(str(entry["id"]), [str(instance1.pk), str(instance2.pk)])

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_ascending_ordered(self):
            # Simple sorting check for models with a "name" field
            # TreeModels don't support sorting at this time (order_by is not supported by TreeQuerySet)
            #   They will pass api == queryset tests below but will fail the user expected sort test
            if hasattr(self.model, "name") and not issubclass(self.model, TreeModel):
                self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
                response = self.client.get(f"{self._get_list_url()}?sort=name&limit=3", **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                result_list = list(map(lambda p: p["name"], response.data["results"]))
                self.assertEqual(
                    result_list,
                    list(self._get_queryset().order_by("name").values_list("name", flat=True)[:3]),
                    "API sort not identical to QuerySet.order_by",
                )

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_descending_ordered(self):
            # Simple sorting check for models with a "name" field
            # TreeModels don't support sorting at this time (order_by is not supported by TreeQuerySet)
            #   They will pass api == queryset tests below but will fail the user expected sort test
            if hasattr(self.model, "name") and not issubclass(self.model, TreeModel):
                self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
                response = self.client.get(f"{self._get_list_url()}?sort=-name&limit=3", **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                result_list = list(map(lambda p: p["name"], response.data["results"]))
                self.assertEqual(
                    result_list,
                    list(self._get_queryset().order_by("-name").values_list("name", flat=True)[:3]),
                    "API sort not identical to QuerySet.order_by",
                )

                response_ascending = self.client.get(f"{self._get_list_url()}?sort=name&limit=3", **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                result_list_ascending = list(map(lambda p: p["name"], response_ascending.data["results"]))

                self.assertNotEqual(
                    result_list,
                    result_list_ascending,
                    "Same results obtained when sorting by name and by -name (QuerySet not ordering)",
                )

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[], STRICT_FILTERING=True)
        def test_list_objects_unknown_filter_strict_filtering(self):
            """
            GET a list of objects with an unknown filter parameter and strict filtering, expect a 400 response.
            """
            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
            with testing.disable_warnings("django.request"):
                response = self.client.get(f"{self._get_list_url()}?ice_cream_flavor=rocky-road", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertIsInstance(response.data, dict)
            self.assertIn("ice_cream_flavor", response.data)
            self.assertIsInstance(response.data["ice_cream_flavor"], list)
            self.assertEqual("Unknown filter field", str(response.data["ice_cream_flavor"][0]))

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[], STRICT_FILTERING=False)
        def test_list_objects_unknown_filter_no_strict_filtering(self):
            """
            GET a list of objects with an unknown filter parameter and no strict filtering, expect it to be ignored.
            """
            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
            with self.assertLogs("nautobot.core.filters") as cm:
                response = self.client.get(f"{self._get_list_url()}?ice_cream_flavor=rocky-road", **self.header)
            self.assertEqual(
                cm.output,
                [
                    f"WARNING:nautobot.core.filters:{self.get_filterset().__name__}: "
                    'Unknown filter field "ice_cream_flavor"',
                ],
            )
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertIsInstance(response.data, dict)
            self.assertIn("results", response.data)
            self.assertEqual(len(response.data["results"]), self._get_queryset().count())

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_options_objects(self):
            """
            Make an OPTIONS request for a list endpoint.
            """
            response = self.client.options(self._get_list_url(), **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_csv(self):
            """
            GET a list of objects in CSV format as an authenticated user with permission to view some objects.
            """
            self.assertGreaterEqual(
                self._get_queryset().count(),
                3,
                f"Test requires the creation of at least three {self.model} instances",
            )
            instance1, instance2, instance3 = self._get_queryset()[:3]

            # Add object-level permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={"pk__in": [instance1.pk, instance2.pk]},
                actions=["view"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Try filtered GET to objects specifying CSV format as a query parameter
            response_1 = self.client.get(
                f"{self._get_list_url()}?format=csv&id={instance1.pk}&id={instance3.pk}", **self.header
            )
            self.assertHttpStatus(response_1, status.HTTP_200_OK)
            self.assertEqual(response_1.get("Content-Type"), "text/csv; charset=UTF-8")
            self.assertEqual(
                response_1.get("Content-Disposition"),
                f'attachment; filename="nautobot_{self.model.__name__.lower()}_data.csv"',
            )

            # Try same request specifying CSV format via the ACCEPT header
            response_2 = self.client.get(
                f"{self._get_list_url()}?id={instance1.pk}&id={instance3.pk}", **self.header, HTTP_ACCEPT="text/csv"
            )
            self.assertHttpStatus(response_2, status.HTTP_200_OK)
            self.assertEqual(response_2.get("Content-Type"), "text/csv; charset=UTF-8")
            self.assertEqual(
                response_2.get("Content-Disposition"),
                f'attachment; filename="nautobot_{self.model.__name__.lower()}_data.csv"',
            )

            self.maxDiff = None
            # This check is more useful than it might seem. Any related object that wasn't CSV-converted correctly
            # will likely be rendered incorrectly as an API URL, and that API URL *will* differ between the
            # two responses based on the inclusion or omission of the "?format=csv" parameter. If
            # you run into this, make sure all serializers have `Meta.fields = "__all__"` set.
            self.assertEqual(
                response_1.content.decode(response_1.charset), response_2.content.decode(response_2.charset)
            )

            # Load the csv data back into a list of object dicts
            reader = csv.DictReader(StringIO(response_1.content.decode(response_1.charset)))
            rows = list(reader)
            # Should only have one entry (instance1) since we filtered out instance2 and permissions block instance3
            self.assertEqual(1, len(rows))
            self.assertEqual(rows[0]["id"], str(instance1.pk))
            self.assertEqual(rows[0]["display"], getattr(instance1, "display", str(instance1)))
            if hasattr(self.model, "_custom_field_data"):
                custom_fields = extras_models.CustomField.objects.get_for_model(self.model)
                for cf in custom_fields:
                    self.assertIn(f"cf_{cf.key}", rows[0])
                    self.assertEqual(rows[0][f"cf_{cf.key}"], instance1._custom_field_data.get(cf.key) or "")
            # TODO what other generic tests should we run on the data?

    class CreateObjectViewTestCase(APITestCase):
        create_data = []
        validation_excluded_fields = []
        slug_source: Optional[Union[str, Sequence[str]]] = None
        slugify_function = staticmethod(slugify)

        def test_create_object_without_permission(self):
            """
            POST a single object without permission.
            """
            url = self._get_list_url()

            # Try POST without permission
            with testing.disable_warnings("django.request"):
                response = self.client.post(url, self.create_data[0], format="json", **self.header)
                self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

        def check_expected_slug(self, obj):
            slug_source = self.slug_source if isinstance(self.slug_source, (list, tuple)) else [self.slug_source]
            expected_slug = ""
            for source_item in slug_source:
                # e.g. self.slug_source = ["parent__name", "name"]
                source_keys = source_item.split("__")
                try:
                    val = getattr(obj, source_keys[0])
                    for key in source_keys[1:]:
                        val = getattr(val, key)
                except AttributeError:
                    val = ""
                if val:
                    if expected_slug != "":
                        expected_slug += "-"
                    expected_slug += self.slugify_function(val)

            self.assertNotEqual(expected_slug, "")
            if hasattr(obj, "slug"):
                self.assertEqual(obj.slug, expected_slug)
            else:
                self.assertEqual(obj.key, expected_slug)

        def test_create_object(self):
            """
            POST a single object with permission.
            """
            # Add object-level permission
            obj_perm = users_models.ObjectPermission(name="Test permission", actions=["add"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            initial_count = self._get_queryset().count()
            for i, create_data in enumerate(self.create_data):
                if i == len(self.create_data) - 1:
                    # Test to see if depth parameter is ignored in POST request.
                    response = self.client.post(
                        self._get_list_url() + "?depth=3", create_data, format="json", **self.header
                    )
                else:
                    response = self.client.post(self._get_list_url(), create_data, format="json", **self.header)
                self.assertHttpStatus(response, status.HTTP_201_CREATED)
                self.assertEqual(self._get_queryset().count(), initial_count + i + 1)
                instance = self._get_queryset().get(pk=response.data["id"])
                self.assertInstanceEqual(
                    instance,
                    create_data,
                    exclude=self.validation_excluded_fields,
                    api=True,
                )

                # Check if Slug field is automatically created
                if self.slug_source is not None and "slug" not in create_data:
                    self.check_expected_slug(self._get_queryset().get(pk=response.data["id"]))

                # Verify ObjectChange creation
                if hasattr(self.model, "to_objectchange"):
                    objectchanges = lookup.get_changes_for_model(instance)
                    self.assertEqual(len(objectchanges), 1)
                    self.assertEqual(objectchanges[0].action, extras_choices.ObjectChangeActionChoices.ACTION_CREATE)

        def test_recreate_object_csv(self):
            """CSV export an object, delete it, and recreate it via CSV import."""
            if hasattr(self, "get_deletable_object"):
                # provided by DeleteObjectViewTestCase mixin
                instance = self.get_deletable_object()
            else:
                # try to do it ourselves
                instance = testing.get_deletable_objects(self.model, self._get_queryset()).first()
            if instance is None:
                self.fail("Couldn't find a single deletable object!")

            # Add object-level permission
            obj_perm = users_models.ObjectPermission(name="Test permission", actions=["add", "view"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            response = self.client.get(self._get_detail_url(instance) + "?format=csv", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertEqual(
                response.get("Content-Disposition"),
                f'attachment; filename="nautobot_{self.model.__name__.lower()}_data.csv"',
            )
            csv_data = response.content.decode(response.charset)

            serializer_class = get_serializer_for_model(self.model)
            old_serializer = serializer_class(instance, context={"request": None})
            old_data = old_serializer.data
            instance.delete()

            response = self.client.post(self._get_list_url(), csv_data, content_type="text/csv", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED, csv_data)
            # Note that create via CSV is always treated as a bulk-create, and so the response is always a list of dicts
            new_instance = self._get_queryset().get(pk=response.data[0]["id"])
            self.assertNotEqual(new_instance.pk, instance.pk)

            new_serializer = serializer_class(new_instance, context={"request": None})
            new_data = new_serializer.data
            for field_name, field in new_serializer.fields.items():
                if field.read_only or field.write_only:
                    continue
                if field_name in ["created", "last_updated"]:
                    self.assertNotEqual(
                        old_data[field_name],
                        new_data[field_name],
                        f"{field_name} should have been updated on delete/recreate but it didn't change!",
                    )
                else:
                    self.assertEqual(
                        old_data[field_name],
                        new_data[field_name],
                        f"{field_name} should have been unchanged on delete/recreate but it differs!",
                    )

        def test_bulk_create_objects(self):
            """
            POST a set of objects in a single request.
            """
            # Add object-level permission
            obj_perm = users_models.ObjectPermission(name="Test permission", actions=["add"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            initial_count = self._get_queryset().count()
            response = self.client.post(self._get_list_url(), self.create_data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)
            self.assertEqual(len(response.data), len(self.create_data))
            self.assertEqual(self._get_queryset().count(), initial_count + len(self.create_data))
            for i, obj in enumerate(response.data):
                for field in self.create_data[i]:
                    if field not in self.validation_excluded_fields:
                        self.assertIn(
                            field,
                            obj,
                            f"Bulk create field '{field}' missing from object {i} in response",
                        )
            for i, obj in enumerate(response.data):
                self.assertInstanceEqual(
                    self._get_queryset().get(pk=obj["id"]),
                    self.create_data[i],
                    exclude=self.validation_excluded_fields,
                    api=True,
                )
                if self.slug_source is not None and "slug" not in self.create_data[i]:
                    self.check_expected_slug(self._get_queryset().get(pk=obj["id"]))

    class UpdateObjectViewTestCase(APITestCase):
        update_data = {}
        bulk_update_data: Optional[dict] = None
        validation_excluded_fields = []
        choices_fields = None

        def test_update_object_without_permission(self):
            """
            PATCH a single object without permission.
            """
            url = self._get_detail_url(self._get_queryset().first())
            update_data = self.update_data or getattr(self, "create_data")[0]

            # Try PATCH without permission
            with testing.disable_warnings("django.request"):
                response = self.client.patch(url, update_data, format="json", **self.header)
                self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

        def test_update_object(self):
            """
            PATCH a single object identified by its ID.
            """

            def strip_serialized_object(this_object):
                """
                Only here to work around acceptable differences in PATCH response vs GET response which are known bugs.
                """
                # Work around for https://github.com/nautobot/nautobot/issues/3321
                this_object.pop("last_updated", None)
                # PATCH response always includes "opt-in" fields, but GET response does not.
                this_object.pop("computed_fields", None)
                this_object.pop("config_context", None)
                this_object.pop("relationships", None)

                for value in this_object.values():
                    if isinstance(value, dict):
                        strip_serialized_object(value)
                    elif isinstance(value, list):
                        for list_dict in value:
                            if isinstance(list_dict, dict):
                                strip_serialized_object(list_dict)

            self.maxDiff = None
            instance = self._get_queryset().first()
            url = self._get_detail_url(instance)
            update_data = self.update_data or getattr(self, "create_data")[0]

            # Add object-level permission
            obj_perm = users_models.ObjectPermission(name="Test permission", actions=["change"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Verify that an empty PATCH results in no change to the object.
            # This is to catch issues like https://github.com/nautobot/nautobot/issues/3533

            # Add object-level permission for GET
            obj_perm.actions = ["view"]
            obj_perm.save()
            # Get initial serialized object representation
            get_response = self.client.get(url, **self.header)
            self.assertHttpStatus(get_response, status.HTTP_200_OK)
            initial_serialized_object = get_response.json()
            strip_serialized_object(initial_serialized_object)

            # Redefine object-level permission for PATCH
            obj_perm.actions = ["change"]
            obj_perm.save()

            # Send empty PATCH request
            response = self.client.patch(url, {}, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            serialized_object = response.json()
            strip_serialized_object(serialized_object)
            self.assertEqual(initial_serialized_object, serialized_object)

            # Verify ObjectChange creation -- yes, even though nothing actually changed
            # This may change (hah) at some point -- see https://github.com/nautobot/nautobot/issues/3321
            if hasattr(self.model, "to_objectchange"):
                objectchanges = lookup.get_changes_for_model(instance)
                self.assertEqual(len(objectchanges), 1)
                self.assertEqual(objectchanges[0].action, extras_choices.ObjectChangeActionChoices.ACTION_UPDATE)
                objectchanges.delete()

            # Verify that a PATCH with some data updates that data correctly.
            response = self.client.patch(url, update_data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            # Check for unexpected side effects on fields we DIDN'T intend to update
            for field in initial_serialized_object:
                if field not in update_data:
                    self.assertEqual(initial_serialized_object[field], serialized_object[field])
            instance.refresh_from_db()
            self.assertInstanceEqual(instance, update_data, exclude=self.validation_excluded_fields, api=True)

            # Verify ObjectChange creation
            if hasattr(self.model, "to_objectchange"):
                objectchanges = lookup.get_changes_for_model(instance)
                self.assertEqual(len(objectchanges), 1)
                self.assertEqual(objectchanges[0].action, extras_choices.ObjectChangeActionChoices.ACTION_UPDATE)

        def test_get_put_round_trip(self):
            """GET and then PUT an object and verify that it's accepted and unchanged."""
            self.maxDiff = None
            # Add object-level permission
            obj_perm = users_models.ObjectPermission(name="Test permission", actions=["view", "change"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            instance = self._get_queryset().first()
            url = self._get_detail_url(instance)

            # GET object representation
            opt_in_fields = getattr(get_serializer_for_model(self.model).Meta, "opt_in_fields", None)
            if opt_in_fields:
                url += "?" + "&".join([f"include={field}" for field in opt_in_fields])
            get_response = self.client.get(url, **self.header)
            self.assertHttpStatus(get_response, status.HTTP_200_OK)
            initial_serialized_object = get_response.json()

            # PUT same object representation
            put_response = self.client.put(url, initial_serialized_object, format="json", **self.header)
            self.assertHttpStatus(put_response, status.HTTP_200_OK, initial_serialized_object)
            updated_serialized_object = put_response.json()

            # Work around for https://github.com/nautobot/nautobot/issues/3321
            initial_serialized_object.pop("last_updated", None)
            updated_serialized_object.pop("last_updated", None)
            self.assertEqual(initial_serialized_object, updated_serialized_object)

        def test_bulk_update_objects(self):
            """
            PATCH a set of objects in a single request.
            """
            if self.bulk_update_data is None:
                self.skipTest("Bulk update data not set")

            # Add object-level permission
            obj_perm = users_models.ObjectPermission(name="Test permission", actions=["change"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            id_list = list(self._get_queryset().values_list("id", flat=True)[:3])
            self.assertEqual(len(id_list), 3, "Insufficient number of objects to test bulk update")
            data = [{"id": id, **self.bulk_update_data} for id in id_list]

            response = self.client.patch(self._get_list_url(), data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            for i, obj in enumerate(response.data):
                for field, _value in self.bulk_update_data.items():
                    self.assertIn(
                        field,
                        obj,
                        f"Bulk update field '{field}' missing from object {i} in response",
                    )
                    # TODO(Glenn): shouldn't we also check that obj[field] == value?
            for instance in self._get_queryset().filter(pk__in=id_list):
                self.assertInstanceEqual(
                    instance,
                    self.bulk_update_data,
                    exclude=self.validation_excluded_fields,
                    api=True,
                )

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_options_returns_expected_choices(self):
            """
            Make an OPTIONS request for a list endpoint and validate choices match expected choices for serializer.
            """
            # Set self.choices_fields as empty set to compare classes that shouldn't have any choices on serializer.
            if not self.choices_fields:
                self.choices_fields = set()

            # Save self.user as superuser to be able to view available choices on list views.
            self.user.is_superuser = True
            self.user.save()

            response = self.client.options(self._get_list_url(), **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            data = response.json()

            self.assertIn("actions", data)

            # Grab any field that has choices defined (fields with enums)
            if any(
                [
                    "POST" in data["actions"],
                    "PUT" in data["actions"],
                ]
            ):
                schema = data["schema"]
                props = schema["properties"]
                fields = props.keys()
                field_choices = set()
                for field_name in fields:
                    obj = props[field_name]
                    if "enum" in obj and "enumNames" in obj:
                        enum = obj["enum"]
                        # Zipping to assert that the enum and the mapping have the same number of items.
                        model_field_choices = dict(zip(obj["enumNames"], enum))
                        self.assertEqual(len(enum), len(model_field_choices))
                        field_choices.add(field_name)
            else:
                self.fail(f"Neither PUT nor POST are available actions in: {data['actions']}")

            self.assertEqual(
                set(self.choices_fields),
                field_choices,
                "All field names of choice fields for a given model serializer need to be manually added to "
                "self.choices_fields. If this is already the case, perhaps the serializer is implemented incorrectly?",
            )

    class DeleteObjectViewTestCase(APITestCase):
        def get_deletable_object(self):
            """
            Get an instance that can be deleted.

            For some models this may just be any random object, but when we have FKs with `on_delete=models.PROTECT`
            (as is often the case) we need to find or create an instance that doesn't have such entanglements.
            """
            instance = testing.get_deletable_objects(self.model, self._get_queryset()).first()
            if instance is None:
                self.fail("Couldn't find a single deletable object!")
            return instance

        def get_deletable_object_pks(self):
            """
            Get a list of PKs corresponding to objects that can be safely bulk-deleted.

            For some models this may just be any random objects, but when we have FKs with `on_delete=models.PROTECT`
            (as is often the case) we need to find or create an instance that doesn't have such entanglements.
            """
            instances = testing.get_deletable_objects(self.model, self._get_queryset()).values_list("pk", flat=True)[:3]
            if len(instances) < 3:
                self.fail(f"Couldn't find 3 deletable objects, only found {len(instances)}!")
            return instances

        def test_delete_object_without_permission(self):
            """
            DELETE a single object without permission.
            """
            url = self._get_detail_url(self.get_deletable_object())

            # Try DELETE without permission
            with testing.disable_warnings("django.request"):
                response = self.client.delete(url, **self.header)
                self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

        def test_delete_object(self):
            """
            DELETE a single object identified by its primary key.
            """
            instance = self.get_deletable_object()
            url = self._get_detail_url(instance)

            # Add object-level permission
            obj_perm = users_models.ObjectPermission(name="Test permission", actions=["delete"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            response = self.client.delete(url, **self.header)
            self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
            self.assertFalse(self._get_queryset().filter(pk=instance.pk).exists())

            # Verify ObjectChange creation
            if hasattr(self.model, "to_objectchange"):
                objectchanges = lookup.get_changes_for_model(instance)
                self.assertEqual(len(objectchanges), 1)
                self.assertEqual(objectchanges[0].action, extras_choices.ObjectChangeActionChoices.ACTION_DELETE)

        def test_bulk_delete_objects(self):
            """
            DELETE a set of objects in a single request.
            """
            id_list = self.get_deletable_object_pks()
            # Add object-level permission
            obj_perm = users_models.ObjectPermission(name="Test permission", actions=["delete"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            data = [{"id": id} for id in id_list]

            initial_count = self._get_queryset().count()
            response = self.client.delete(self._get_list_url(), data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self._get_queryset().count(), initial_count - len(id_list))

    class NotesURLViewTestCase(APITestCase):
        """Validate Notes URL on objects that have the Note model Mixin."""

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_notes_url_on_object(self):
            notes = getattr(self.model, "notes", None)
            if notes and isinstance(notes, ForeignKey):
                instance1 = self._get_queryset().first()
                # Add object-level permission
                obj_perm = users_models.ObjectPermission(
                    name="Test permission",
                    constraints={"pk": instance1.pk},
                    actions=["view"],
                )
                obj_perm.save()
                obj_perm.users.add(self.user)
                obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))
                url = self._get_detail_url(instance1)
                response = self.client.get(url, **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertIn("notes_url", response.data)
                self.assertIn(f"{url}notes/", str(response.data["notes_url"]))

    class TreeModelAPIViewTestCaseMixin:
        """Test `?depth=2` query parameter for TreeModel"""

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_depth_2(self):
            """
            GET a list of objects using the "?depth=2" parameter.
            TreeModel Only
            """
            field = "parent"

            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
            url = f"{self._get_list_url()}?depth=2"
            response = self.client.get(url, **self.header)

            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertIsInstance(response.data, dict)
            self.assertIn("results", response.data)
            self.assertEqual(len(response.data["results"]), self._get_queryset().count())

            response_data = response.data["results"]
            for data in response_data:
                # First Level Parent
                self.assertEqual(field in data, True)
                if data[field] is not None:
                    self.assertIsInstance(data[field], dict)
                    self.assertTrue(is_uuid(data[field]["id"]))
                    # Second Level Parent
                    self.assertIn(field, data[field])
                    if data[field][field] is not None:
                        self.assertIsInstance(data[field][field], dict)
                        self.assertTrue(is_uuid(data[field][field]["id"]))

    class APIViewTestCase(
        GetObjectViewTestCase,
        ListObjectsViewTestCase,
        CreateObjectViewTestCase,
        UpdateObjectViewTestCase,
        DeleteObjectViewTestCase,
        NotesURLViewTestCase,
    ):
        pass


@tag("unit")
class APITransactionTestCase(_APITransactionTestCase, mixins.NautobotTestCaseMixin):
    def setUp(self):
        """
        Create a superuser and token for API calls.
        """
        super().setUpNautobot(populate_status=True)
        self.user.is_superuser = True
        self.user.save()
        self.token = users_models.Token.objects.create(user=self.user)
        self.header = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}
