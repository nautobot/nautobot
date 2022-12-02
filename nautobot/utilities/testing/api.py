from typing import Optional, Sequence, Union

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.test import override_settings, tag
from django.utils.text import slugify
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase as _APITransactionTestCase

from nautobot.users.models import ObjectPermission, Token
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.models import ChangeLoggedModel
from nautobot.extras.registry import registry
from nautobot.utilities.testing.mixins import NautobotTestCaseMixin
from nautobot.utilities.utils import get_changes_for_model, get_filterset_for_model, get_route_for_model
from .utils import disable_warnings, get_deletable_objects
from .views import ModelTestCase


__all__ = (
    "APITestCase",
    "APIViewTestCases",
)


#
# REST API Tests
#


@tag("api")
class APITestCase(ModelTestCase):
    """
    Base test case for API requests.

    client_class: Test client class
    api_version: Specific API version to test. Leave unset to test the default behavior. Override with set_api_version()
    """

    client_class = APIClient
    api_version = None

    def setUp(self):
        """
        Create a token for API calls.
        """
        # Do not initialize the client, it conflicts with the APIClient.
        super().setUpNautobot(client=False)
        self.token = Token.objects.create(user=self.user)
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
        viewname = get_route_for_model(instance, "detail", api=True)
        return reverse(viewname, kwargs={"pk": instance.pk})

    def _get_list_url(self):
        viewname = get_route_for_model(self.model, "list", api=True)
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
                with disable_warnings("django.request"):
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
            with disable_warnings("django.request"):
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
            obj_perm = ObjectPermission(
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
            self.assertIsInstance(response.data["display"], str)
            # Fields that should be present in appropriate model serializers:
            if issubclass(self.model, ChangeLoggedModel):
                self.assertIn("created", response.data)
                self.assertIn("last_updated", response.data)
            # Fields that should be absent by default (opt-in fields):
            self.assertNotIn("computed_fields", response.data)
            self.assertNotIn("relationships", response.data)

            # If opt-in fields are supported on this model, make sure they can be opted into

            custom_fields_registry = registry["model_features"]["custom_fields"]
            # computed fields and custom fields use the same registry
            cf_supported = self.model._meta.model_name in custom_fields_registry.get(self.model._meta.app_label, {})
            if cf_supported:  # custom_fields is not an opt-in field, it should always be present if supported
                self.assertIn("custom_fields", response.data)
                self.assertIsInstance(response.data["custom_fields"], dict)

            relationships_registry = registry["model_features"]["relationships"]
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

    class ListObjectsViewTestCase(APITestCase):
        brief_fields = []
        choices_fields = None
        filterset = None

        def get_filterset(self):
            return self.filterset or get_filterset_for_model(self.model)

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
                with disable_warnings("django.request"):
                    self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_403_FORBIDDEN)
            else:
                # TODO(Glenn): if we're passing **self.header, we are *by definition* **NOT** anonymous!!
                response = self.client.get(url, **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertIsInstance(response.data, dict)
                self.assertIn("results", response.data)
                self.assertEqual(len(response.data["results"]), self._get_queryset().count())

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_brief(self):
            """
            GET a list of objects using the "brief" parameter.
            """
            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
            url = f"{self._get_list_url()}?brief=1"
            response = self.client.get(url, **self.header)

            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertIsInstance(response.data, dict)
            self.assertIn("results", response.data)
            self.assertEqual(len(response.data["results"]), self._get_queryset().count())
            self.assertEqual(
                sorted(response.data["results"][0]),
                self.brief_fields,
                "In order to test the brief API parameter the brief fields need to be manually added to "
                "self.brief_fields. If this is already the case, perhaps the serializer is implemented incorrectly?",
            )

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_without_permission(self):
            """
            GET a list of objects as an authenticated user without the required permission.
            """
            url = self._get_list_url()

            # Try GET without permission
            with disable_warnings("django.request"):
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
            obj_perm = ObjectPermission(
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

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[], STRICT_FILTERING=True)
        def test_list_objects_unknown_filter_strict_filtering(self):
            """
            GET a list of objects with an unknown filter parameter and strict filtering, expect a 400 response.
            """
            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
            with disable_warnings("django.request"):
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
            with self.assertLogs("nautobot.utilities.filters") as cm:
                response = self.client.get(f"{self._get_list_url()}?ice_cream_flavor=rocky-road", **self.header)
            self.assertEqual(
                cm.output,
                [
                    f"WARNING:nautobot.utilities.filters:{self.get_filterset().__name__}: "
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

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_status_options_returns_expected_choices(self):
            # Set to self.choices_fields as empty set to compare classes that shouldn't have any choice fields on serializer.
            if not self.choices_fields:
                self.choices_fields = set()

            # Don't bother testing if there's no `status` field.
            if "status" not in self.choices_fields:
                self.skipTest("Object does not contain a `status` field.")

            # Save self.user as superuser to be able to view available choices on list views.
            self.user.is_superuser = True
            self.user.save()

            response = self.client.options(self._get_list_url(), **self.header)
            data = response.json()

            self.assertIn("actions", data)
            self.assertIn("POST", data["actions"])

            actions = data["actions"]["POST"]
            choices = actions["status"]["choices"]

            # Import Status here to avoid circular import issues w/ test utilities.
            from nautobot.extras.models import Status  # noqa

            # Assert that the expected Status objects matches what is emitted.
            statuses = Status.objects.get_for_model(self.model)
            expected = [{"value": v, "display": d} for (v, d) in statuses.values_list("slug", "name")]
            self.assertListEqual(choices, expected)

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
            with disable_warnings("django.request"):
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
            self.assertEqual(obj.slug, expected_slug)

        def test_create_object(self):
            """
            POST a single object with permission.
            """
            # Add object-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["add"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            initial_count = self._get_queryset().count()
            for i, create_data in enumerate(self.create_data):
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
                    objectchanges = get_changes_for_model(instance)
                    self.assertEqual(len(objectchanges), 1)
                    self.assertEqual(objectchanges[0].action, ObjectChangeActionChoices.ACTION_CREATE)

        def test_bulk_create_objects(self):
            """
            POST a set of objects in a single request.
            """
            # Add object-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["add"])
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
            with disable_warnings("django.request"):
                response = self.client.patch(url, update_data, format="json", **self.header)
                self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

        def test_update_object(self):
            """
            PATCH a single object identified by its ID.
            """
            instance = self._get_queryset().first()
            url = self._get_detail_url(instance)
            update_data = self.update_data or getattr(self, "create_data")[0]

            # Add object-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["change"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            response = self.client.patch(url, update_data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            instance.refresh_from_db()
            self.assertInstanceEqual(instance, update_data, exclude=self.validation_excluded_fields, api=True)

            # Verify ObjectChange creation
            if hasattr(self.model, "to_objectchange"):
                objectchanges = get_changes_for_model(instance)
                self.assertEqual(len(objectchanges), 1)
                self.assertEqual(objectchanges[0].action, ObjectChangeActionChoices.ACTION_UPDATE)

        def test_bulk_update_objects(self):
            """
            PATCH a set of objects in a single request.
            """
            if self.bulk_update_data is None:
                self.skipTest("Bulk update data not set")

            # Add object-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["change"])
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
        def test_options_objects_returns_display_and_value(self):
            """
            Make an OPTIONS request for a list endpoint and validate choices use the display and value keys.
            """
            # Save self.user as superuser to be able to view available choices on list views.
            self.user.is_superuser = True
            self.user.save()

            response = self.client.options(self._get_list_url(), **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            data = response.json()

            self.assertIn("actions", data)

            # Grab any field that has choices defined (fields with enums)
            if "POST" in data["actions"]:
                field_choices = {k: v["choices"] for k, v in data["actions"]["POST"].items() if "choices" in v}
            elif "PUT" in data["actions"]:  # JobModelViewSet supports editing but not creation
                field_choices = {k: v["choices"] for k, v in data["actions"]["PUT"].items() if "choices" in v}
            else:
                self.fail(f"Neither PUT nor POST are available actions in: {data['actions']}")

            # Will successfully assert if field_choices has entries and will not fail if model as no enum choices
            # Broken down to provide better failure messages
            for field, choices in field_choices.items():
                for choice in choices:
                    self.assertIn("display", choice, f"A choice in {field} is missing the display key")
                    self.assertIn("value", choice, f"A choice in {field} is missing the value key")

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

            # Grab any field name that has choices defined (fields with enums)
            if "POST" in data["actions"]:
                field_choices = {k for k, v in data["actions"]["POST"].items() if "choices" in v}
            elif "PUT" in data["actions"]:  # JobModelViewSet supports editing but not creation
                field_choices = {k for k, v in data["actions"]["PUT"].items() if "choices" in v}
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
            instance = get_deletable_objects(self.model, self._get_queryset()).first()
            if instance is None:
                self.fail("Couldn't find a single deletable object!")
            return instance

        def get_deletable_object_pks(self):
            """
            Get a list of PKs corresponding to objects that can be safely bulk-deleted.

            For some models this may just be any random objects, but when we have FKs with `on_delete=models.PROTECT`
            (as is often the case) we need to find or create an instance that doesn't have such entanglements.
            """
            instances = get_deletable_objects(self.model, self._get_queryset()).values_list("pk", flat=True)[:3]
            if len(instances) < 3:
                self.fail(f"Couldn't find 3 deletable objects, only found {len(instances)}!")
            return instances

        def test_delete_object_without_permission(self):
            """
            DELETE a single object without permission.
            """
            url = self._get_detail_url(self.get_deletable_object())

            # Try DELETE without permission
            with disable_warnings("django.request"):
                response = self.client.delete(url, **self.header)
                self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

        def test_delete_object(self):
            """
            DELETE a single object identified by its primary key.
            """
            instance = self.get_deletable_object()
            url = self._get_detail_url(instance)

            # Add object-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["delete"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            response = self.client.delete(url, **self.header)
            self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
            self.assertFalse(self._get_queryset().filter(pk=instance.pk).exists())

            # Verify ObjectChange creation
            if hasattr(self.model, "to_objectchange"):
                objectchanges = get_changes_for_model(instance)
                self.assertEqual(len(objectchanges), 1)
                self.assertEqual(objectchanges[0].action, ObjectChangeActionChoices.ACTION_DELETE)

        def test_bulk_delete_objects(self):
            """
            DELETE a set of objects in a single request.
            """
            id_list = self.get_deletable_object_pks()
            # Add object-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["delete"])
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
            if hasattr(self.model, "notes"):
                instance1 = self._get_queryset().first()
                # Add object-level permission
                obj_perm = ObjectPermission(
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
class APITransactionTestCase(_APITransactionTestCase, NautobotTestCaseMixin):
    def setUp(self):
        """
        Create a superuser and token for API calls.
        """
        super().setUpNautobot()
        self.user.is_superuser = True
        self.user.save()
        self.token = Token.objects.create(user=self.user)
        self.header = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}
