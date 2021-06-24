from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.test import override_settings, tag
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase as _APITransactionTestCase

from nautobot.users.models import ObjectPermission, Token
from .utils import disable_warnings
from .views import ModelTestCase


__all__ = (
    "APITestCase",
    "APIViewTestCases",
)


# Use the proper swappable User model
User = get_user_model()


#
# REST API Tests
#


class APITestCase(ModelTestCase):
    """
    Base test case for API requests.

    client_class: Test client class
    view_namespace: Namespace for API views. If None, the model's app_label will be used.
    """

    client_class = APIClient
    view_namespace = None

    def setUp(self):
        """
        Create a superuser and token for API calls.
        """
        # Create the test user and assign permissions
        self.user = User.objects.create_user(username="testuser")
        self.add_permissions(*self.user_permissions)
        self.token = Token.objects.create(user=self.user)
        self.header = {"HTTP_AUTHORIZATION": "Token {}".format(self.token.key)}

    def _get_view_namespace(self):
        if self.view_namespace:
            return f"{self.view_namespace}-api"
        if self.model._meta.app_label in settings.PLUGINS:
            return f"plugins-api:{self.model._meta.app_label}-api"
        return f"{self.model._meta.app_label}-api"

    def _get_detail_url(self, instance):
        viewname = f"{self._get_view_namespace()}:{instance._meta.model_name}-detail"
        return reverse(viewname, kwargs={"pk": instance.pk})

    def _get_list_url(self):
        viewname = f"{self._get_view_namespace()}:{self.model._meta.model_name}-list"
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

            # Try GET to permitted object
            url = self._get_detail_url(instance1)
            self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_200_OK)

            # Try GET to non-permitted object
            url = self._get_detail_url(instance2)
            self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_404_NOT_FOUND)

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
                response = self.client.get(url, **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertEqual(len(response.data["results"]), self._get_queryset().count())

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_brief(self):
            """
            GET a list of objects using the "brief" parameter.
            """
            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
            url = f"{self._get_list_url()}?brief=1"
            response = self.client.get(url, **self.header)

            self.assertEqual(len(response.data["results"]), self._get_queryset().count())
            self.assertEqual(sorted(response.data["results"][0]), self.brief_fields)

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
            self.assertEqual(len(response.data["results"]), 2)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_options_objects(self):
            """
            Make an OPTIONS request for a list endpoint.
            """
            response = self.client.options(self._get_list_url(), **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)

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

            # Grab any field that has choices defined (fields with enums)
            field_choices = {k: v["choices"] for k, v in response.json()["actions"]["POST"].items() if "choices" in v}

            # Will successfully assert if field_choices has entries and will not fail if model as no enum choices
            # Broken down to provide better failure messages
            for field, choices in field_choices.items():
                for choice in choices:
                    self.assertIn("display", choice, f"A choice in {field} is missing the display key")
                    self.assertIn("value", choice, f"A choice in {field} is missing the value key")

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_options_returns_expected_choices(self):
            """
            Make an OPTIONS request for a list endpoint and validate choice fields match expected choice fields for serializer.
            """
            # Set to self.choices_fields as empty set to compare classes that shouldn't have any choice fields on serializer.
            if not self.choices_fields:
                self.choices_fields = set()

            # Save self.user as superuser to be able to view available choices on list views.
            self.user.is_superuser = True
            self.user.save()

            response = self.client.options(self._get_list_url(), **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)

            # Grab any field name that has choices defined (fields with enums)
            field_choices = {k for k, v in response.json()["actions"]["POST"].items() if "choices" in v}

            self.assertEqual(set(self.choices_fields), field_choices)

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
            actions = response.json()["actions"]["POST"]
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

        def test_create_object_without_permission(self):
            """
            POST a single object without permission.
            """
            url = self._get_list_url()

            # Try POST without permission
            with disable_warnings("django.request"):
                response = self.client.post(url, self.create_data[0], format="json", **self.header)
                self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

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
                self.assertInstanceEqual(
                    self._get_queryset().get(pk=response.data["id"]),
                    create_data,
                    exclude=self.validation_excluded_fields,
                    api=True,
                )

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

    class UpdateObjectViewTestCase(APITestCase):
        update_data = {}
        bulk_update_data = None
        validation_excluded_fields = []

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
                for field in self.bulk_update_data:
                    self.assertIn(
                        field,
                        obj,
                        f"Bulk update field '{field}' missing from object {i} in response",
                    )
            for instance in self._get_queryset().filter(pk__in=id_list):
                self.assertInstanceEqual(
                    instance,
                    self.bulk_update_data,
                    exclude=self.validation_excluded_fields,
                    api=True,
                )

    class DeleteObjectViewTestCase(APITestCase):
        def test_delete_object_without_permission(self):
            """
            DELETE a single object without permission.
            """
            url = self._get_detail_url(self._get_queryset().first())

            # Try DELETE without permission
            with disable_warnings("django.request"):
                response = self.client.delete(url, **self.header)
                self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

        def test_delete_object(self):
            """
            DELETE a single object identified by its primary key.
            """
            instance = self._get_queryset().first()
            url = self._get_detail_url(instance)

            # Add object-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["delete"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            response = self.client.delete(url, **self.header)
            self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
            self.assertFalse(self._get_queryset().filter(pk=instance.pk).exists())

        def test_bulk_delete_objects(self):
            """
            DELETE a set of objects in a single request.
            """
            # Add object-level permission
            obj_perm = ObjectPermission(name="Test permission", actions=["delete"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            id_list = self._get_queryset().values_list("id", flat=True)
            data = [{"id": id} for id in id_list]

            response = self.client.delete(self._get_list_url(), data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
            self.assertEqual(self._get_queryset().count(), 0)

    class APIViewTestCase(
        GetObjectViewTestCase,
        ListObjectsViewTestCase,
        CreateObjectViewTestCase,
        UpdateObjectViewTestCase,
        DeleteObjectViewTestCase,
    ):
        pass


@tag("unit")
class APITransactionTestCase(_APITransactionTestCase):
    def setUp(self):
        """
        Create a superuser and token for API calls.
        """
        self.user = User.objects.create(username="testuser", is_superuser=True)
        self.token = Token.objects.create(user=self.user)
        self.header = {"HTTP_AUTHORIZATION": "Token {}".format(self.token.key)}

    def assertHttpStatus(self, response, expected_status):
        """
        Provide more detail in the event of an unexpected HTTP response.
        """
        err_message = "Expected HTTP status {}; received {}: {}"
        self.assertEqual(
            response.status_code,
            expected_status,
            err_message.format(expected_status, response.status_code, response.data),
        )
