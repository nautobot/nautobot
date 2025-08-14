import contextlib
import re
from typing import Optional, Sequence
from unittest import mock, skipIf
import uuid

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import URLValidator
from django.db.models import ManyToManyField, Model, QuerySet
from django.test import override_settings, tag, TestCase as _TestCase
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape
from django.utils.http import urlencode
from django.utils.text import slugify
from tree_queries.models import TreeNode

from nautobot.core.jobs.bulk_actions import BulkEditObjects
from nautobot.core.models.generics import PrimaryModel
from nautobot.core.models.tree_queries import TreeModel
from nautobot.core.templatetags import helpers
from nautobot.core.testing import mixins, utils
from nautobot.core.utils import lookup
from nautobot.dcim.models.device_components import ComponentModel
from nautobot.extras import choices as extras_choices, models as extras_models, querysets as extras_querysets
from nautobot.extras.forms import CustomFieldModelFormMixin, RelationshipModelFormMixin
from nautobot.extras.models import CustomFieldModel, RelationshipModel
from nautobot.extras.models.jobs import JobResult
from nautobot.extras.models.mixins import NotesMixin
from nautobot.ipam.models import Prefix
from nautobot.users import models as users_models

__all__ = (
    "ModelTestCase",
    "ModelViewTestCase",
    "TestCase",
    "ViewTestCases",
)


@tag("unit")
@override_settings(PAGINATE_COUNT=65000)
class TestCase(mixins.NautobotTestCaseMixin, _TestCase):
    """Base class for all Nautobot-specific unit tests."""

    def setUp(self):
        """Initialize user and client."""
        super().setUpNautobot()


class ModelTestCase(TestCase):
    """
    Parent class for TestCases which deal with models.
    """

    model = None
    # Optional, list of Relationships populated in setUpTestData for testing with this model
    # Be sure to also create RelationshipAssociations using these Relationships!
    relationships: Optional[Sequence[extras_models.Relationship]] = None
    # Optional, list of CustomFields populated in setUpTestData for testing with this model
    # Be sure to also populate these fields on your test data!
    custom_fields: Optional[Sequence[extras_models.CustomField]] = None

    def _get_queryset(self):
        """
        Return a base queryset suitable for use in test methods.
        """
        return self.model.objects.all()


#
# UI Tests
#


@tag("performance")
class ModelViewTestCase(ModelTestCase):
    """
    Base TestCase for model views. Subclass to test individual views.
    """

    reverse_url_attribute = None
    """
    Name of instance field to pass as a kwarg when looking up URLs for creating/editing/deleting a model instance.

    If unspecified, "pk" and "slug" will be tried, in that order.
    """

    def _get_base_url(self):
        """
        Return the base format string for a view URL for the test.

        Examples: "dcim:device_{}", "plugins:example_app:example_model_{}"

        Override this if needed for testing of views that don't correspond directly to self.model,
        for example the DCIM "interface-connections" and "console-connections" view tests.
        """
        app_name = apps.get_app_config(app_label=self.model._meta.app_label).name
        # AppConfig.name accounts for NautobotApps that are not built at the root of the package
        if app_name in settings.PLUGINS:
            return f"plugins:{self.model._meta.app_label}:{self.model._meta.model_name}_{{}}"
        return f"{self.model._meta.app_label}:{self.model._meta.model_name}_{{}}"

    def _get_url(self, action, instance=None):
        """
        Return the URL string for a specific action and optionally a specific model instance.

        Override this if needed for testing of views whose names don't follow
        the [plugins]:<app_label>:<model_name>_<action> naming convention.
        """
        url_format = self._get_base_url()

        # If no instance was provided, assume we don't need a unique identifier
        if instance is None:
            return reverse(url_format.format(action))

        if self.reverse_url_attribute:
            return reverse(
                url_format.format(action),
                kwargs={self.reverse_url_attribute: getattr(instance, self.reverse_url_attribute)},
            )

        try:
            # Default to using the PK to retrieve the URL for an object
            return reverse(url_format.format(action), kwargs={"pk": instance.pk})
        except NoReverseMatch:
            # Attempt to resolve using slug as the unique identifier if one exists
            if hasattr(self.model, "slug"):
                return reverse(url_format.format(action), kwargs={"slug": instance.slug})
            raise


@tag("unit")
class ViewTestCases:
    """
    We keep any TestCases with test_* methods inside a class to prevent unittest from trying to run them.
    """

    class GetObjectViewTestCase(ModelViewTestCase):
        """
        Retrieve a single instance.
        """

        custom_action_required_permissions = {}

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_get_object_anonymous(self):
            # Make the request as an unauthenticated user
            self.client.logout()
            response = self.client.get(self._get_queryset().first().get_absolute_url())
            self.assertHttpStatus(response, 200)
            # TODO: all this is doing is checking that a login link appears somewhere on the page (i.e. in the nav).
            response_body = response.content.decode(response.charset)
            self.assertIn(
                "/login/?next=" + self._get_queryset().first().get_absolute_url(), response_body, msg=response_body
            )

            # The "Change Log" tab should appear in the response since we have all exempt permissions
            if issubclass(self.model, extras_models.ChangeLoggedModel):
                self.assertBodyContains(response, "Change Log")

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_get_object_without_permission(self):
            instance = self._get_queryset().first()

            # Try GET without permission
            with utils.disable_warnings("django.request"):
                response = self.client.get(instance.get_absolute_url())
                self.assertHttpStatus(response, [403, 404])
                response_body = response.content.decode(response.charset)
                self.assertNotIn("/login/", response_body, msg=response_body)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_get_object_with_permission(self):
            instance = self._get_queryset().first()

            # Add model-level permission
            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")

            # Try GET with model-level permission
            response = self.client.get(instance.get_absolute_url())
            # The object's display name or string representation should appear in the response body
            self.assertBodyContains(response, escape(getattr(instance, "display", str(instance))))

            # If any Relationships are defined, they should appear in the response
            if self.relationships is not None:
                for relationship in self.relationships:  # false positive pylint: disable=not-an-iterable
                    content_type = ContentType.objects.get_for_model(instance)
                    if content_type == relationship.source_type:
                        self.assertBodyContains(
                            response,
                            escape(relationship.get_label(extras_choices.RelationshipSideChoices.SIDE_SOURCE)),
                        )
                    if content_type == relationship.destination_type:
                        self.assertBodyContains(
                            response,
                            escape(relationship.get_label(extras_choices.RelationshipSideChoices.SIDE_DESTINATION)),
                        )

            # If any Custom Fields are defined, they should appear in the response
            if self.custom_fields is not None:
                for custom_field in self.custom_fields:  # false positive pylint: disable=not-an-iterable
                    self.assertBodyContains(response, escape(str(custom_field)))
                    if custom_field.type == extras_choices.CustomFieldTypeChoices.TYPE_MULTISELECT:
                        for value in instance.cf.get(custom_field.key):
                            self.assertBodyContains(response, escape(str(value)))
                    else:
                        self.assertBodyContains(response, escape(str(instance.cf.get(custom_field.key) or "")))

            return response  # for consumption by child test cases if desired

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_get_object_with_constrained_permission(self):
            instance1, instance2 = self._get_queryset().all()[:2]

            # Add object-level permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={"pk": instance1.pk},
                # To get a different rendering flow than the `test_get_object_with_permission` test above,
                # enable additional permissions for this object so that add/edit/delete buttons are rendered.
                actions=["view", "add", "change", "delete"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Try GET to permitted object
            response = self.client.get(instance1.get_absolute_url())
            self.assertHttpStatus(response, 200)

            # Try GET to non-permitted object
            self.assertHttpStatus(self.client.get(instance2.get_absolute_url()), 404)

            return response  # for consumption by child test cases if desired

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_has_advanced_tab(self):
            instance = self._get_queryset().first()

            # Add model-level permission
            obj_perm = users_models.ObjectPermission(name="Test permission", actions=["view"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            response = self.client.get(instance.get_absolute_url())
            self.assertBodyContains(response, f"{instance.get_absolute_url()}#advanced")
            self.assertBodyContains(response, "Advanced")

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_custom_actions(self):
            instance = self._get_queryset().first()
            for url_name, required_permissions in self.custom_action_required_permissions.items():
                url = reverse(url_name, kwargs={"pk": instance.pk})
                self.assertHttpStatus(self.client.get(url), 403)
                for permission in required_permissions[:-1]:
                    self.add_permissions(permission)
                    self.assertHttpStatus(self.client.get(url), 403)

                self.add_permissions(required_permissions[-1])
                self.assertHttpStatus(self.client.get(url), 200)
                # delete the permissions here so that repetitive calls to add_permissions do not create duplicate permissions.
                self.remove_permissions(*required_permissions)

    class GetObjectChangelogViewTestCase(ModelViewTestCase):
        """
        View the changelog for an instance.
        """

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_get_object_changelog(self):
            obj = self._get_queryset().first()
            url = self._get_url("changelog", obj)
            response = self.client.get(url)
            self.assertHttpStatus(response, 200)

            # Test for https://github.com/nautobot/nautobot/issues/5214
            if getattr(obj, "is_contact_associable_model", False):
                self.assertBodyContains(
                    response,
                    f'href="{obj.get_absolute_url()}#contacts" onclick="switch_tab(this.href)"',
                )
            else:
                self.assertNotContains(response, f"{obj.get_absolute_url()}#contacts")

    class GetObjectNotesViewTestCase(ModelViewTestCase):
        """
        View the notes for an instance.
        """

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_get_object_notes(self):
            if hasattr(self.model, "notes"):
                obj = self._get_queryset().first()
                url = self._get_url("notes", obj)
                response = self.client.get(url)
                self.assertHttpStatus(response, 200)

                # Test for https://github.com/nautobot/nautobot/issues/5214
                if getattr(obj, "is_contact_associable_model", False):
                    self.assertBodyContains(
                        response,
                        f'href="{obj.get_absolute_url()}#contacts" onclick="switch_tab(this.href)"',
                    )
                else:
                    self.assertNotContains(response, f"{obj.get_absolute_url()}#contacts")

    class CreateObjectViewTestCase(ModelViewTestCase):
        """
        Create a single new instance.

        :form_data: Data to be used when creating a new object.
        """

        form_data = {}
        slug_source = None
        slugify_function = staticmethod(slugify)
        slug_test_object = ""
        expected_create_form_buttons = [
            '<button type="submit" name="_create" class="btn btn-primary">Create</button>',
            '<button type="submit" name="_addanother" class="btn btn-primary">Create and Add Another</button>',
        ]
        expected_edit_form_buttons = ['<button type="submit" name="_update" class="btn btn-primary">Update</button>']

        def test_create_object_without_permission(self):
            # Try GET without permission
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("add")), 403)

            # Try POST without permission
            request = {
                "path": self._get_url("add"),
                "data": utils.post_data(self.form_data),
            }
            response = self.client.post(**request)
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(response, 403)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_create_object_with_permission(self):
            initial_count = self._get_queryset().count()

            # Assign unconstrained permission
            self.add_permissions(f"{self.model._meta.app_label}.add_{self.model._meta.model_name}")

            # Try GET with model-level permission
            response = self.client.get(self._get_url("add"))
            self.assertHttpStatus(response, 200)
            # The response content should contain the expected form buttons
            for button in self.expected_create_form_buttons:
                self.assertBodyContains(response, button)
            # The response content should not contain the expected form buttons
            for button in self.expected_edit_form_buttons:
                self.assertNotContains(response, button)

            # Try POST with model-level permission
            request = {
                "path": self._get_url("add"),
                "data": utils.post_data(self.form_data),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            self.assertEqual(initial_count + 1, self._get_queryset().count())
            # order_by() is no supported by django TreeNode,
            # So we directly retrieve the instance by "slug" or "name".
            if isinstance(self._get_queryset().first(), TreeNode):
                filter_by = self.slug_source if getattr(self, "slug_source", None) else "name"
                instance = self._get_queryset().get(**{filter_by: self.form_data.get(filter_by)})
                self.assertInstanceEqual(instance, self.form_data)
            else:
                if hasattr(self.model, "last_updated"):
                    instance = self._get_queryset().order_by("last_updated").last()
                    self.assertInstanceEqual(instance, self.form_data)
                else:
                    instance = self._get_queryset().last()
                    self.assertInstanceEqual(instance, self.form_data)

            if hasattr(self.model, "to_objectchange"):
                # Verify ObjectChange creation
                objectchanges = lookup.get_changes_for_model(instance)
                self.assertEqual(len(objectchanges), 1)
                # Assert that Created By table row is updated with the user that created the object
                self.assertEqual(objectchanges[0].action, extras_choices.ObjectChangeActionChoices.ACTION_CREATE)
                # Validate if detail view exists
                validate = URLValidator()
                try:
                    detail_url = instance.get_absolute_url()
                    validate(detail_url)
                    response = self.client.get(detail_url)
                    self.assertBodyContains(response, f"{detail_url}#advanced")
                    self.assertBodyContains(response, "<td>Created By</td>", html=True)
                    self.assertBodyContains(response, f"<td>{self.user.username}</td>", html=True)
                except (AttributeError, ValidationError):
                    # Instance does not have a valid detail view, do nothing here.
                    pass

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_create_object_with_constrained_permission(self):
            initial_count = self._get_queryset().count()

            # Assign constrained permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={"pk": str(uuid.uuid4())},  # Match a non-existent pk (i.e., deny all)
                actions=["add"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Try GET with object-level permission
            self.assertHttpStatus(self.client.get(self._get_url("add")), 200)

            # Try to create an object (not permitted)
            request = {
                "path": self._get_url("add"),
                "data": utils.post_data(self.form_data),
            }
            self.assertHttpStatus(self.client.post(**request), 200)
            self.assertEqual(initial_count, self._get_queryset().count())  # Check that no object was created

            # Update the ObjectPermission to allow creation
            obj_perm.constraints = {"pk__isnull": False}
            obj_perm.save()

            # Try to create an object (permitted)
            request = {
                "path": self._get_url("add"),
                "data": utils.post_data(self.form_data),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            self.assertEqual(initial_count + 1, self._get_queryset().count())
            # order_by() is no supported by django TreeNode,
            # So we directly retrieve the instance by "slug".
            if isinstance(self._get_queryset().first(), TreeNode):
                filter_by = self.slug_source if getattr(self, "slug_source", None) else "name"
                instance = self._get_queryset().get(**{filter_by: self.form_data.get(filter_by)})
                self.assertInstanceEqual(instance, self.form_data)
            else:
                if hasattr(self.model, "last_updated"):
                    self.assertInstanceEqual(self._get_queryset().order_by("last_updated").last(), self.form_data)
                else:
                    self.assertInstanceEqual(self._get_queryset().last(), self.form_data)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_extra_feature_form_fields_present(self):
            model_class = self.model
            model_form = lookup.get_form_for_model(model_class)
            fields = model_form.base_fields
            if isinstance(model_class, CustomFieldModel):
                self.assertTrue(issubclass(CustomFieldModelFormMixin, model_form))
            if isinstance(model_class, RelationshipModel):
                self.assertTrue(issubclass(RelationshipModelFormMixin, model_form))
            if isinstance(model_class, NotesMixin):
                self.assertIsNotNone(fields.get("object_note"))
            if isinstance(model_class, PrimaryModel):
                self.assertIsNotNone(fields.get("tags"))

    class EditObjectViewTestCase(ModelViewTestCase):
        """
        Edit a single existing instance.

        :update_data: Data to be used when updating the first existing object, fall back to form_data if not provided.
        :form_data: Fall back to this data if update_data is not provided, for backward compatibility.
        """

        form_data = {}
        update_data = {}
        expected_edit_form_buttons = ['<button type="submit" name="_update" class="btn btn-primary">Update</button>']
        expected_create_form_buttons = [
            '<button type="submit" name="_create" class="btn btn-primary">Create</button>',
            '<button type="submit" name="_addanother" class="btn btn-primary">Create and Add Another</button>',
        ]

        def test_edit_object_without_permission(self):
            instance = self._get_queryset().first()

            # Try GET without permission
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("edit", instance)), [403, 404])

            # Try POST without permission
            update_data = self.update_data or self.form_data
            request = {
                "path": self._get_url("edit", instance),
                "data": utils.post_data(update_data),
            }
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.post(**request), [403, 404])

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_edit_object_with_permission(self):
            instance = self._get_queryset().first()

            # Assign model-level permission
            self.add_permissions(f"{self.model._meta.app_label}.change_{self.model._meta.model_name}")

            # Try GET with model-level permission
            response = self.client.get(self._get_url("edit", instance))
            self.assertHttpStatus(response, 200)
            # The response content should contain the expected form buttons
            for button in self.expected_edit_form_buttons:
                self.assertBodyContains(response, button)

            # The response content should not contain the unexpected form buttons
            for button in self.expected_create_form_buttons:
                self.assertNotContains(response, button)

            # Try POST with model-level permission
            update_data = self.update_data or self.form_data
            request = {
                "path": self._get_url("edit", instance),
                "data": utils.post_data(update_data),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            self.assertInstanceEqual(self._get_queryset().get(pk=instance.pk), update_data)

            if hasattr(self.model, "to_objectchange"):
                # Verify ObjectChange creation
                objectchanges = lookup.get_changes_for_model(instance)
                self.assertEqual(objectchanges[0].action, extras_choices.ObjectChangeActionChoices.ACTION_UPDATE)
                # Validate if detail view exists
                validate = URLValidator()
                try:
                    detail_url = instance.get_absolute_url()
                    validate(detail_url)
                    response = self.client.get(detail_url)
                    self.assertBodyContains(response, f"{detail_url}#advanced")
                    self.assertBodyContains(response, "<td>Last Updated By</td>", html=True)
                    self.assertBodyContains(response, f"<td>{self.user.username}</td>", html=True)
                except (AttributeError, ValidationError):
                    # Instance does not have a valid detail view, do nothing here.
                    pass

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_edit_object_with_constrained_permission(self):
            instance1, instance2 = self._get_queryset().all()[:2]

            # Assign constrained permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={"pk": instance1.pk},
                actions=["change"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Try GET with a permitted object
            self.assertHttpStatus(self.client.get(self._get_url("edit", instance1)), 200)

            # Try GET with a non-permitted object
            self.assertHttpStatus(self.client.get(self._get_url("edit", instance2)), 404)

            # Try to edit a permitted object
            update_data = self.update_data or self.form_data
            request = {
                "path": self._get_url("edit", instance1),
                "data": utils.post_data(update_data),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            self.assertInstanceEqual(self._get_queryset().get(pk=instance1.pk), update_data)

            # Try to edit a non-permitted object
            request = {
                "path": self._get_url("edit", instance2),
                "data": utils.post_data(update_data),
            }
            self.assertHttpStatus(self.client.post(**request), 404)

    class DeleteObjectViewTestCase(ModelViewTestCase):
        """
        Delete a single instance.
        """

        def get_deletable_object(self):
            """
            Get an instance that can be deleted.

            For some models this may just be any random object, but when we have FKs with `on_delete=models.PROTECT`
            (as is often the case) we need to find or create an instance that doesn't have such entanglements.
            """
            instance = utils.get_deletable_objects(self.model, self._get_queryset()).first()
            if instance is None:
                self.fail("Couldn't find a single deletable object!")
            return instance

        def test_delete_object_without_permission(self):
            instance = self.get_deletable_object()

            # Try GET without permission
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("delete", instance)), [403, 404])

            # Try POST without permission
            request = {
                "path": self._get_url("delete", instance),
                "data": utils.post_data({"confirm": True}),
            }
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.post(**request), [403, 404])

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_delete_object_with_permission(self):
            instance = self.get_deletable_object()
            instance_note_pk_list = []
            assigned_object_type = ContentType.objects.get_for_model(self.model)
            if hasattr(self.model, "notes") and isinstance(instance.notes, extras_querysets.NotesQuerySet):
                notes = (
                    extras_models.Note(
                        assigned_object_type=assigned_object_type, assigned_object_id=instance.id, note="hello 1"
                    ),
                    extras_models.Note(
                        assigned_object_type=assigned_object_type, assigned_object_id=instance.id, note="hello 2"
                    ),
                    extras_models.Note(
                        assigned_object_type=assigned_object_type, assigned_object_id=instance.id, note="hello 3"
                    ),
                )
                for note in notes:
                    note.validated_save()
                    instance_note_pk_list.append(note.pk)

            # Assign model-level permission
            self.add_permissions(f"{self.model._meta.app_label}.delete_{self.model._meta.model_name}")

            # Try GET with model-level permission
            self.assertHttpStatus(self.client.get(self._get_url("delete", instance)), 200)

            # Try POST with model-level permission
            request = {
                "path": self._get_url("delete", instance),
                "data": utils.post_data({"confirm": True}),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            with self.assertRaises(ObjectDoesNotExist):
                self._get_queryset().get(pk=instance.pk)

            if hasattr(self.model, "to_objectchange"):
                # Verify ObjectChange creation
                objectchanges = lookup.get_changes_for_model(instance)
                self.assertEqual(objectchanges[0].action, extras_choices.ObjectChangeActionChoices.ACTION_DELETE)

            if hasattr(self.model, "notes") and isinstance(instance.notes, extras_querysets.NotesQuerySet):
                # Verify Notes deletion
                with self.assertRaises(ObjectDoesNotExist):
                    extras_models.Note.objects.get(assigned_object_id=instance.pk)

                note_objectchanges = extras_models.ObjectChange.objects.filter(
                    changed_object_id__in=instance_note_pk_list
                )
                self.assertEqual(note_objectchanges.count(), 3)
                for object_change in note_objectchanges:
                    self.assertEqual(object_change.action, extras_choices.ObjectChangeActionChoices.ACTION_DELETE)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_delete_object_with_permission_and_xwwwformurlencoded(self):
            instance = self.get_deletable_object()

            # Assign model-level permission
            self.add_permissions(f"{self.model._meta.app_label}.delete_{self.model._meta.model_name}")

            # Try GET with model-level permission
            self.assertHttpStatus(self.client.get(self._get_url("delete", instance)), 200)

            # Try POST with model-level permission
            request = {
                "path": self._get_url("delete", instance),
                "data": urlencode({"confirm": True}),
                "content_type": "application/x-www-form-urlencoded",
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            with self.assertRaises(ObjectDoesNotExist):
                self._get_queryset().get(pk=instance.pk)

            if hasattr(self.model, "to_objectchange"):
                # Verify ObjectChange creation
                objectchanges = lookup.get_changes_for_model(instance)
                self.assertEqual(objectchanges[0].action, extras_choices.ObjectChangeActionChoices.ACTION_DELETE)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_delete_object_with_constrained_permission(self):
            instance1 = self.get_deletable_object()
            instance2 = self._get_queryset().exclude(pk=instance1.pk)[0]

            # Assign object-level permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={"pk": instance1.pk},
                actions=["delete"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Try GET with a permitted object
            self.assertHttpStatus(self.client.get(self._get_url("delete", instance1)), 200)

            # Try GET with a non-permitted object
            self.assertHttpStatus(self.client.get(self._get_url("delete", instance2)), 404)

            # Try to delete a permitted object
            request = {
                "path": self._get_url("delete", instance1),
                "data": utils.post_data({"confirm": True}),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            with self.assertRaises(ObjectDoesNotExist):
                self._get_queryset().get(pk=instance1.pk)

            # Try to delete a non-permitted object
            # Note that in the case of tree models, deleting instance1 above may have cascade-deleted to instance2,
            # so to be safe, we need to get another object instance that definitely exists:
            instance3 = self._get_queryset().first()
            request = {
                "path": self._get_url("delete", instance3),
                "data": utils.post_data({"confirm": True}),
            }
            self.assertHttpStatus(self.client.post(**request), 404)
            self.assertTrue(self._get_queryset().filter(pk=instance3.pk).exists())

    class ListObjectsViewTestCase(ModelViewTestCase):
        """
        Retrieve multiple instances.
        """

        filterset = None
        filter_on_field = "name"
        sort_on_field = "tags"

        def get_filterset(self):
            return self.filterset or lookup.get_filterset_for_model(self.model)

        # Helper methods to be overriden by special cases.
        # See ConsoleConnectionsTestCase, InterfaceConnectionsTestCase and PowerConnectionsTestCase
        def get_list_url(self):
            return reverse(helpers.validated_viewname(self.model, "list"))

        def get_title(self):
            return helpers.bettertitle(self.model._meta.verbose_name_plural)

        def get_list_view(self):
            return lookup.get_view_for_model(self.model, view_type="List")

        def test_list_view_has_filter_form(self):
            view = self.get_list_view()
            if hasattr(view, "filterset_form"):  # ObjectListView
                self.assertIsNotNone(view.filterset_form, "List view lacks a FilterForm")
            if hasattr(view, "filterset_form_class"):  # ObjectListViewMixin
                self.assertIsNotNone(view.filterset_form_class, "List viewset lacks a FilterForm")

        def test_table_with_indentation_is_removed_on_filter_or_sort(self):
            self.user.is_superuser = True
            self.user.save()

            if not issubclass(self.model, (TreeModel)) and self.model is not Prefix:
                self.skipTest("Skipping Non TreeModels")

            with self.subTest("Assert indentation is present"):
                response = self.client.get(f"{self._get_url('list')}")
                self.assertBodyContains(response, '<i class="mdi mdi-circle-small"></i>', html=True)

            with self.subTest("Assert indentation is removed on filter"):
                queryset = (
                    self._get_queryset().filter(parent__isnull=False).values_list(self.filter_on_field, flat=True)[:5]
                )
                filter_values = "&".join([f"{self.filter_on_field}={instance_value}" for instance_value in queryset])
                response = self.client.get(f"{self._get_url('list')}?{filter_values}")
                response_body = response.content.decode(response.charset)
                self.assertNotIn('<i class="mdi mdi-circle-small"></i>', response_body)

            with self.subTest("Assert indentation is removed on sort"):
                response = self.client.get(f"{self._get_url('list')}?sort={self.sort_on_field}")
                response_body = response.content.decode(response.charset)
                self.assertNotIn('<i class="mdi mdi-circle-small"></i>', response_body)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_list_objects_anonymous(self):
            # Make the request as an unauthenticated user
            self.client.logout()
            response = self.client.get(self._get_url("list"))
            self.assertHttpStatus(response, 200)
            # TODO: all this is doing is checking that a login link appears somewhere on the page (i.e. in the nav).
            response_body = response.content.decode(response.charset)
            self.assertIn("/login/?next=" + self._get_url("list"), response_body, msg=response_body)

        def test_list_objects_anonymous_with_exempt_permission_for_one_view_only(self):
            # Make the request as an unauthenticated user
            self.client.logout()
            # Test if AnonymousUser can properly render the whole list view
            with override_settings(EXEMPT_VIEW_PERMISSIONS=[self.model._meta.label_lower]):
                response = self.client.get(self._get_url("list"))
                self.assertHttpStatus(response, 200)
                # There should be some rows
                self.assertBodyContains(response, '<tr class="even')
                self.assertBodyContains(response, '<tr class="odd')

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_list_objects_filtered(self):
            instance1, instance2 = self._get_queryset().all()[:2]
            if hasattr(self.model, "name") and instance1.name == instance2.name:
                instance2.name += "X"
                instance2.save()

            response = self.client.get(f"{self._get_url('list')}?id={instance1.pk}")
            self.assertHttpStatus(response, 200)
            content = utils.extract_page_body(response.content.decode(response.charset))
            # There should be only one row in the table
            self.assertIn('<tr class="even', content)
            self.assertNotIn('<tr class="odd', content)
            if hasattr(self.model, "name"):
                self.assertRegex(content, r">\s*" + re.escape(escape(instance1.name)) + r"\s*<", msg=content)
                self.assertNotRegex(content, r">\s*" + re.escape(escape(instance2.name)) + r"\s*<", msg=content)
            with contextlib.suppress(AttributeError):
                # Some models, such as ObjectMetadata, don't have a detail URL
                if instance1.get_absolute_url() in content:
                    self.assertNotIn(instance2.get_absolute_url(), content, msg=content)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], STRICT_FILTERING=True)
        def test_list_objects_unknown_filter_strict_filtering(self):
            """Verify that with STRICT_FILTERING, an unknown filter results in an error message and no matches."""
            response = self.client.get(f"{self._get_url('list')}?ice_cream_flavor=chocolate")
            self.assertBodyContains(response, "Unknown filter field")
            # There should be no table rows displayed except for the empty results row
            self.assertBodyContains(response, "None")

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], STRICT_FILTERING=False)
        def test_list_objects_unknown_filter_no_strict_filtering(self):
            """Verify that without STRICT_FILTERING, an unknown filter is ignored."""
            instance1, instance2 = self._get_queryset().all()[:2]
            if hasattr(self.model, "name") and instance1.name == instance2.name:
                instance2.name += "X"
                instance2.save()

            with self.assertLogs("nautobot.core.filters") as cm:
                response = self.client.get(f"{self._get_url('list')}?ice_cream_flavor=chocolate")
            filterset = self.get_filterset()
            if not filterset:
                self.fail(
                    f"Couldn't find filterset for model {self.model}. The FilterSet class is expected to be in the "
                    "filters module within the application associated with the model and its name is expected to be "
                    f"{self.model.__name__}FilterSet."
                )
            self.assertEqual(
                cm.output,
                [
                    f'WARNING:nautobot.core.filters:{filterset.__name__}: Unknown filter field "ice_cream_flavor"',
                ],
            )
            self.assertHttpStatus(response, 200)
            content = utils.extract_page_body(response.content.decode(response.charset))
            self.assertNotIn("Unknown filter field", content, msg=content)
            self.assertIn("None", content, msg=content)
            # There should be at least two rows in the table
            self.assertIn('<tr class="even', content)
            self.assertIn('<tr class="odd', content)
            if hasattr(self.model, "name"):
                self.assertRegex(content, r">\s*" + re.escape(escape(instance1.name)) + r"\s*<", msg=content)
                self.assertRegex(content, r">\s*" + re.escape(escape(instance2.name)) + r"\s*<", msg=content)
            with contextlib.suppress(AttributeError):
                # Some models, such as ObjectMetadata, don't have a detail URL
                if instance1.get_absolute_url() in content:
                    self.assertIn(instance2.get_absolute_url(), content, msg=content)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_without_permission(self):
            # Try GET without permission
            with utils.disable_warnings("django.request"):
                response = self.client.get(self._get_url("list"))
                self.assertHttpStatus(response, 403)
                response_body = response.content.decode(response.charset)
                self.assertNotIn("/login/", response_body, msg=response_body)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_with_permission(self):
            # Add model-level permission
            self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")

            # Try GET with model-level permission
            response = self.client.get(self._get_url("list"))
            self.assertHttpStatus(response, 200)
            response_body = utils.extract_page_body(response.content.decode(response.charset))

            list_url = self.get_list_url()
            title = self.get_title()

            # Check if breadcrumb is rendered correctly
            self.assertBodyContains(response, f'<a href="{list_url}">{title}</a>', html=True)

            with self.subTest("Assert import-objects URL is absent due to user permissions"):
                self.assertNotIn(
                    reverse("extras:job_run_by_class_path", kwargs={"class_path": "nautobot.core.jobs.ImportObjects"}),
                    response_body,
                )

            if "example_app" in settings.PLUGINS:
                with self.subTest("Assert example-app banner is present"):
                    self.assertIn(
                        f"<div>You are viewing a table of {self.model._meta.verbose_name_plural}</div>", response_body
                    )

            return response

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_objects_with_constrained_permission(self):
            instance1, instance2 = self._get_queryset().all()[:2]
            if hasattr(self.model, "name") and instance1.name == instance2.name:
                instance2.name += "X"
                instance2.save()

            # Add object-level permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={"pk": instance1.pk},
                actions=["view", "add"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Try GET with object-level permission
            response = self.client.get(self._get_url("list"))
            self.assertHttpStatus(response, 200)
            content = utils.extract_page_body(response.content.decode(response.charset))
            if hasattr(self.model, "name"):
                self.assertRegex(content, r">\s*" + re.escape(escape(instance1.name)) + r"\s*<", msg=content)
                self.assertNotRegex(content, r">\s*" + re.escape(escape(instance2.name)) + r"\s*<", msg=content)
            elif hasattr(self.model, "get_absolute_url"):
                self.assertIn(instance1.get_absolute_url(), content, msg=content)
                self.assertNotIn(instance2.get_absolute_url(), content, msg=content)

            view = self.get_list_view()
            if view and hasattr(view, "action_buttons") and "import" in view.action_buttons:
                # Check if import button is present due to user permissions
                self.assertIn(
                    (
                        reverse(
                            "extras:job_run_by_class_path", kwargs={"class_path": "nautobot.core.jobs.ImportObjects"}
                        )
                        + f"?content_type={ContentType.objects.get_for_model(self.model).pk}"
                    ),
                    content,
                )
            else:
                # Import not supported, no button should be present
                self.assertNotIn(
                    reverse("extras:job_run_by_class_path", kwargs={"class_path": "nautobot.core.jobs.ImportObjects"}),
                    content,
                )

        @skipIf(
            "example_app" not in settings.PLUGINS,
            "example_app not in settings.PLUGINS",
        )
        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_list_view_app_banner(self):
            """
            If example app is installed, check if the app banner is rendered correctly in ObjectListView.
            """
            # Add model-level permission
            obj_perm = users_models.ObjectPermission(name="Test permission", actions=["view"])
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Try GET with model-level permission
            response = self.client.get(self._get_url("list"))

            # Check app banner is rendered correctly
            self.assertBodyContains(
                response,
                f"<div>You are viewing a table of {self.model._meta.verbose_name_plural}</div>",
                html=True,
            )

    class CreateMultipleObjectsViewTestCase(ModelViewTestCase):
        """
        Create multiple instances using a single form. Expects the creation of three new instances by default.

        :bulk_create_count: The number of objects expected to be created (default: 3).
        :bulk_create_data: A dictionary of data to be used for bulk object creation.
        """

        bulk_create_count = 3
        bulk_create_data = {}

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_create_multiple_objects_without_permission(self):
            request = {
                "path": self._get_url("add"),
                "data": utils.post_data(self.bulk_create_data),
            }

            # Try POST without permission
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.post(**request), 403)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_create_multiple_objects_with_permission(self):
            initial_count = self._get_queryset().count()
            request = {
                "path": self._get_url("add"),
                "data": utils.post_data(self.bulk_create_data),
            }

            # Assign non-constrained permission
            self.add_permissions(f"{self.model._meta.app_label}.add_{self.model._meta.model_name}")

            # Bulk create objects
            response = self.client.post(**request)
            self.assertHttpStatus(response, 302)
            self.assertEqual(initial_count + self.bulk_create_count, self._get_queryset().count())
            matching_count = 0
            for instance in self._get_queryset().all():
                try:
                    self.assertInstanceEqual(instance, self.bulk_create_data)
                    matching_count += 1
                except AssertionError:
                    pass
            self.assertEqual(matching_count, self.bulk_create_count)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_create_multiple_objects_with_constrained_permission(self):
            initial_count = self._get_queryset().count()
            request = {
                "path": self._get_url("add"),
                "data": utils.post_data(self.bulk_create_data),
            }

            # Assign constrained permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                actions=["add"],
                constraints={"pk": uuid.uuid4()},  # Match a non-existent pk (i.e., deny all)
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Attempt to make the request with unmet constraints
            self.assertHttpStatus(self.client.post(**request), 200)
            self.assertEqual(self._get_queryset().count(), initial_count)

            # Update the ObjectPermission to allow creation
            obj_perm.constraints = {"pk__isnull": False}  # Set constraint to allow all
            obj_perm.save()

            response = self.client.post(**request)
            self.assertHttpStatus(response, 302)
            self.assertEqual(initial_count + self.bulk_create_count, self._get_queryset().count())

            matching_count = 0
            for instance in self._get_queryset().all():
                try:
                    self.assertInstanceEqual(instance, self.bulk_create_data)
                    matching_count += 1
                except AssertionError:
                    pass
            self.assertEqual(matching_count, self.bulk_create_count)

    class BulkEditObjectsViewTestCase(ModelViewTestCase):
        """
        Edit multiple instances.

        :bulk_edit_data: A dictionary of data to be used when bulk editing a set of objects. This data should differ
                         from that used for initial object creation within setUpTestData().
        """

        bulk_edit_data = {}

        def validate_object_data_after_bulk_edit(self, pk_list):
            for instance in self._get_queryset().filter(pk__in=pk_list):
                self.assertInstanceEqual(instance, self.bulk_edit_data)

        def validate_redirect_to_job_result(self, response):
            # Get the last Bulk Edit Objects JobResult created
            job_result = JobResult.objects.filter(name="Bulk Edit Objects").first()
            self.assertIsNotNone(job_result, "No JobResult was created - likely the bulk_edit_data is invalid!")
            # Assert redirect to Job Results
            self.assertRedirects(
                response,
                reverse("extras:jobresult", args=[job_result.pk]),
                status_code=302,
                target_status_code=200,
            )

        def test_bulk_edit_objects_without_permission(self):
            pk_list = list(self._get_queryset().values_list("pk", flat=True)[:3])
            data = {
                "pk": pk_list,
                "_apply": True,  # Form button
            }

            # Try POST without permission
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.post(self._get_url("bulk_edit"), data), 403)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_edit_objects_with_permission(self):
            pk_list = list(self._get_queryset().values_list("pk", flat=True)[:3])
            data = {
                "pk": pk_list,
                "_apply": True,  # Form button
            }

            # Append the form data to the request
            data.update(utils.post_data(self.bulk_edit_data))

            # Assign model-level permission
            self.add_permissions(f"{self.model._meta.app_label}.change_{self.model._meta.model_name}")

            with mock.patch.object(JobResult, "enqueue_job", wraps=JobResult.enqueue_job) as mock_enqueue_job:
                response = self.client.post(self._get_url("bulk_edit"), data)
                self.validate_redirect_to_job_result(response)
                mock_enqueue_job.assert_called()

                # Verify that the provided self.bulk_edit_data was passed through correctly to the job.
                # The below is a bit gross because of multiple layers of data encoding and decoding involved. Sorry!
                job_form = BulkEditObjects.as_form(BulkEditObjects.deserialize_data(mock_enqueue_job.call_args.kwargs))
                job_form.is_valid()
                job_kwargs = job_form.cleaned_data

                bulk_edit_form_class = lookup.get_form_for_model(self.model, form_prefix="BulkEdit")
                bulk_edit_form = bulk_edit_form_class(self.model, job_kwargs["form_data"])
                bulk_edit_form.is_valid()
                passed_bulk_edit_data = bulk_edit_form.cleaned_data

                for key, value in self.bulk_edit_data.items():
                    with self.subTest(key=key):
                        if isinstance(passed_bulk_edit_data.get(key), Model):
                            self.assertEqual(passed_bulk_edit_data.get(key).pk, value)
                        elif isinstance(passed_bulk_edit_data.get(key), QuerySet):
                            self.assertEqual(
                                sorted(passed_bulk_edit_data.get(key).values_list("pk", flat=True)), sorted(value)
                            )
                        else:
                            self.assertEqual(passed_bulk_edit_data.get(key), bulk_edit_form.fields[key].clean(value))

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_edit_objects_nullable_fields(self):
            """Assert that "set null" fields on the bulk-edit form are correctly passed through to the job."""
            bulk_edit_form_class = lookup.get_form_for_model(self.model, form_prefix="BulkEdit")
            bulk_edit_form = bulk_edit_form_class(self.model)
            if not getattr(bulk_edit_form, "nullable_fields", ()):
                self.skipTest(f"no nullable fields on {bulk_edit_form_class}")

            for field_name in bulk_edit_form.nullable_fields:
                with self.subTest(field_name=field_name):
                    if field_name.startswith("cf_"):
                        # TODO check whether customfield is nullable
                        continue
                    if field_name.startswith("cr_"):
                        # TODO check whether relationship is required
                        continue
                    model_field = self.model._meta.get_field(field_name)
                    if isinstance(model_field, ManyToManyField):
                        # always nullable
                        continue
                    self.assertTrue(model_field.null or model_field.blank)

            pk_list = list(self._get_queryset().values_list("pk", flat=True)[:3])
            data = {
                "pk": pk_list,
                "_apply": True,  # Form button
                "_nullify": list(bulk_edit_form.nullable_fields),
            }

            # Assign model-level permission
            self.add_permissions(f"{self.model._meta.app_label}.change_{self.model._meta.model_name}")

            with mock.patch.object(JobResult, "enqueue_job", wraps=JobResult.enqueue_job) as mock_enqueue_job:
                response = self.client.post(self._get_url("bulk_edit"), data)
                self.validate_redirect_to_job_result(response)
                mock_enqueue_job.assert_called()

                self.assertEqual(mock_enqueue_job.call_args.kwargs["form_data"].get("_nullify"), data["_nullify"])

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_edit_form_contains_all_pks(self):
            # We are testing the intermediary step of all bulk_edit.
            # i.e. "_all" passed in the form.
            pk_list = self._get_queryset().values_list("pk", flat=True)
            selected_data = {
                "_all": "on",
            }
            # Assign model-level permission
            self.add_permissions(f"{self.model._meta.app_label}.change_{self.model._meta.model_name}")

            # Try POST with model-level permission
            response = self.client.post(self._get_url("bulk_edit"), selected_data)
            # Expect a 200 status cause we are only rendering the bulk edit table.
            # after pressing Edit Selected button.
            self.assertHttpStatus(response, 200)
            response_body = utils.extract_page_body(response.content.decode(response.charset))
            # Assert the table which shows all the selected objects is not part of the html body in edit all case
            self.assertNotIn('<table class="table table-hover table-headings">', response_body)
            # Check if all the pks are passed into the BulkEditForm/BulkUpdateForm
            for pk in pk_list:
                self.assertNotIn(str(pk), response_body)
            self.assertInHTML(
                '<input type="hidden" name="_all" value="True" class="form-control" placeholder="None" id="id__all">',
                response_body,
            )

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_edit_form_contains_all_filtered(self):
            # We are testing the intermediary step of bulk editing all filtered objects.
            # i.e. "_all" passed in the form and filter using query params.
            self.add_permissions(f"{self.model._meta.app_label}.change_{self.model._meta.model_name}")

            pk_iter = iter(self._get_queryset().values_list("pk", flat=True))
            try:
                first_pk = next(pk_iter)
                second_pk = next(pk_iter)
                third_pk = next(pk_iter)
            except StopIteration:
                self.fail(f"Test requires at least three instances of {self.model._meta.model_name} to be defined.")

            post_data = utils.post_data(self.bulk_edit_data)

            # Open bulk update form with first two objects
            selected_data = {
                "_all": "on",
                **post_data,
            }
            query_string = urlencode({"id": (first_pk, second_pk)}, doseq=True)
            response = self.client.post(f"{self._get_url('bulk_edit')}?{query_string}", selected_data)
            # Expect a 200 status cause we are only rendering the bulk edit table after pressing Edit Selected button.
            self.assertHttpStatus(response, 200)
            response_body = utils.extract_page_body(response.content.decode(response.charset))
            # Check if all pks is not part of the html.
            self.assertNotIn(str(first_pk), response_body)
            self.assertNotIn(str(second_pk), response_body)
            self.assertNotIn(str(third_pk), response_body)
            self.assertIn("Editing 2 ", response_body)
            self.assertInHTML(
                '<input type="hidden" name="_all" value="True" class="form-control" placeholder="None" id="id__all">',
                response_body,
            )

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_edit_objects_with_constrained_permission(self):
            # Select some objects that are *not* already set to match the first value in self.bulk_edit_data or null.
            # We have to exclude null cases because Django filter()/exclude() doesn't like `__in=[None]` as a case.
            attr_name = next(iter(self.bulk_edit_data.keys()))
            objects = (
                self._get_queryset()
                .exclude(**{attr_name: self.bulk_edit_data[attr_name]})
                .exclude(**{f"{attr_name}__isnull": True})
            )[:3]
            self.assertEqual(objects.count(), 3)
            pk_list = list(objects.values_list("pk", flat=True))

            # Define a permission that permits the above objects, but will not permit them after updating them.
            field = self.model._meta.get_field(attr_name)
            values = [field.value_from_object(obj) for obj in objects]

            # Assign constrained permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={f"{attr_name}__in": values},
                actions=["change"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Build form data
            data = {
                "pk": pk_list,
                "_apply": True,  # Form button
            }
            data.update(utils.post_data(self.bulk_edit_data))

            with mock.patch.object(JobResult, "enqueue_job", wraps=JobResult.enqueue_job) as mock_enqueue_job:
                # Attempt to bulk edit permitted objects into a non-permitted state
                response = self.client.post(self._get_url("bulk_edit"), data)
                # NOTE: There is no way of testing constrained failure as bulk edit is a system Job;
                # and can only be tested by checking JobLogs.
                self.validate_redirect_to_job_result(response)
                mock_enqueue_job.assert_called()

    class BulkDeleteObjectsViewTestCase(ModelViewTestCase):
        """
        Delete multiple instances.
        """

        def get_deletable_object_pks(self):
            """
            Get a list of PKs corresponding to objects that can be safely bulk-deleted.

            For some models this may just be any random objects, but when we have FKs with `on_delete=models.PROTECT`
            (as is often the case) we need to find or create an instance that doesn't have such entanglements.
            """
            return utils.get_deletable_objects(self.model, self._get_queryset()).values_list("pk", flat=True)[:3]

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_bulk_delete_objects_without_permission(self):
            pk_list = self.get_deletable_object_pks()
            data = {
                "pk": pk_list,
                "confirm": True,
                "_confirm": True,  # Form button
            }

            # Try POST without permission
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.post(self._get_url("bulk_delete"), data), 403)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_bulk_delete_objects_with_permission(self):
            pk_list = self.get_deletable_object_pks()
            data = {
                "pk": pk_list,
                "confirm": True,
                "_confirm": True,  # Form button
            }

            # Assign unconstrained permission
            self.add_permissions(
                f"{self.model._meta.app_label}.delete_{self.model._meta.model_name}", "extras.view_jobresult"
            )

            response = self.client.post(self._get_url("bulk_delete"), data)
            job_result = JobResult.objects.filter(name="Bulk Delete Objects").first()
            self.assertRedirects(
                response,
                reverse("extras:jobresult", args=[job_result.pk]),
                status_code=302,
                target_status_code=200,
            )

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_bulk_delete_form_contains_all_objects(self):
            # We are testing the intermediary step of bulk_delete all objects.
            # i.e. "_all" passed in the form.
            selected_data = {
                "confirm": True,
                "_all": "on",
            }

            # Assign unconstrained permission
            self.add_permissions(f"{self.model._meta.app_label}.delete_{self.model._meta.model_name}")

            # Try POST with the selected data first. Emulating selecting all -> pressing Delete Selected button.
            response = self.client.post(self._get_url("bulk_delete"), selected_data)
            self.assertHttpStatus(response, 200)
            response_body = utils.extract_page_body(response.content.decode(response.charset))
            # Assert the table which shows all the selected objects is not part of the html body in delete all case
            self.assertNotIn('<table class="table table-hover table-headings">', response_body)
            # Assert none of the hidden input fields for each of the pks that would be deleted is part of the html body
            for pk in self._get_queryset().values_list("pk", flat=True):
                self.assertNotIn(str(pk), response_body)
            self.assertInHTML('<input type="hidden" name="_all" value="true" />', response_body)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_delete_form_contains_all_filtered(self):
            # We are testing the intermediary step of bulk_delete all with additional filter.
            # i.e. "_all" passed in the form and filter using query params.
            self.add_permissions(f"{self.model._meta.app_label}.delete_{self.model._meta.model_name}")

            pk_iter = iter(self._get_queryset().values_list("pk", flat=True))
            try:
                first_pk = next(pk_iter)
                second_pk = next(pk_iter)
                third_pk = next(pk_iter)
            except StopIteration:
                self.fail(f"Test requires at least three instances of {self.model._meta.model_name} to be defined.")

            # Open bulk delete form with first two objects
            selected_data = {
                "pk": third_pk,  # This is ignored when filtering with "_all"
                "_all": "on",
            }
            query_string = urlencode({"id": (first_pk, second_pk)}, doseq=True)
            response = self.client.post(f"{self._get_url('bulk_delete')}?{query_string}", selected_data)
            # Expect a 200 status cause we are only rendering the bulk delete table after pressing Delete Selected button.
            self.assertHttpStatus(response, 200)
            response_body = utils.extract_page_body(response.content.decode(response.charset))
            # Check if all pks is not part of the html.
            self.assertNotIn(str(first_pk), response_body)
            self.assertNotIn(str(second_pk), response_body)
            self.assertNotIn(str(third_pk), response_body)
            self.assertIn("<strong>Warning:</strong> The following operation will delete 2 ", response_body)
            self.assertInHTML('<input type="hidden" name="_all" value="true" />', response_body)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
        def test_bulk_delete_objects_with_constrained_permission(self):
            pk_list = self.get_deletable_object_pks()
            initial_count = self._get_queryset().count()
            data = {
                "pk": pk_list,
                "confirm": True,
                "_confirm": True,  # Form button
            }

            # Assign constrained permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={"pk": str(uuid.uuid4())},  # Match a non-existent pk (i.e., deny all)
                actions=["delete"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Attempt to bulk delete non-permitted objects
            self.assertHttpStatus(self.client.post(self._get_url("bulk_delete"), data), 302)
            self.assertEqual(self._get_queryset().count(), initial_count)

            # Update permission constraints
            obj_perm.constraints = {"pk__isnull": False}  # Match a non-existent pk (i.e., allow all)
            obj_perm.save()

            # User would be redirected to Job Result therefore user needs to have permission to view Job Result
            self.add_permissions("extras.view_jobresult")
            response = self.client.post(self._get_url("bulk_delete"), data)
            job_result = JobResult.objects.filter(name="Bulk Delete Objects").first()
            self.assertRedirects(
                response,
                reverse("extras:jobresult", args=[job_result.pk]),
                status_code=302,
                target_status_code=200,
            )

    class BulkRenameObjectsViewTestCase(ModelViewTestCase):
        """
        Rename multiple instances.
        """

        rename_data = {
            "find": "^(.*)$",
            "replace": "\\1X",  # Append an X to the original value
            "use_regex": True,
        }

        def test_bulk_rename_objects_without_permission(self):
            pk_list = list(self._get_queryset().values_list("pk", flat=True)[:3])
            data = {
                "pk": pk_list,
                "_apply": True,  # Form button
            }
            data.update(self.rename_data)

            # Test GET without permission
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.get(self._get_url("bulk_rename")), 403)

            # Try POST without permission
            with utils.disable_warnings("django.request"):
                self.assertHttpStatus(self.client.post(self._get_url("bulk_rename"), data), 403)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_rename_objects_with_permission(self):
            objects = list(self._get_queryset().all()[:3])
            pk_list = [obj.pk for obj in objects]
            data = {
                "pk": pk_list,
                "_apply": True,  # Form button
            }
            data.update(self.rename_data)

            # Assign model-level permission
            self.add_permissions(f"{self.model._meta.app_label}.change_{self.model._meta.model_name}")

            # Try POST with model-level permission
            self.assertHttpStatus(self.client.post(self._get_url("bulk_rename"), data), 302)
            for i, instance in enumerate(self._get_queryset().filter(pk__in=pk_list)):
                name = getattr(instance, "name")
                expected_name = getattr(objects[i], "name") + "X"
                self.assertEqual(name, expected_name)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_rename_objects_with_constrained_permission(self):
            objects = list(self._get_queryset().all()[:3])
            pk_list = [obj.pk for obj in objects]
            data = {
                "pk": pk_list,
                "_apply": True,  # Form button
            }
            data.update(self.rename_data)

            # Assign constrained permission
            obj_perm = users_models.ObjectPermission(
                name="Test permission",
                constraints={"name__regex": "[^X]$"},
                actions=["change"],
            )
            obj_perm.save()
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

            # Attempt to bulk edit permitted objects into a non-permitted state
            response = self.client.post(self._get_url("bulk_rename"), data)
            self.assertHttpStatus(response, 200)

            # Update permission constraints
            obj_perm.constraints = {"pk__gt": 0}
            obj_perm.save()

            # Bulk rename permitted objects
            self.assertHttpStatus(self.client.post(self._get_url("bulk_rename"), data), 302)
            for i, instance in enumerate(self._get_queryset().filter(pk__in=pk_list)):
                name = getattr(instance, "name")
                expected_name = getattr(objects[i], "name") + "X"
                self.assertEqual(name, expected_name)

    class PrimaryObjectViewTestCase(
        GetObjectViewTestCase,
        GetObjectChangelogViewTestCase,
        GetObjectNotesViewTestCase,
        CreateObjectViewTestCase,
        EditObjectViewTestCase,
        DeleteObjectViewTestCase,
        ListObjectsViewTestCase,
        BulkEditObjectsViewTestCase,
        BulkDeleteObjectsViewTestCase,
    ):
        """
        TestCase suitable for testing all standard View functions for primary objects
        """

        maxDiff = None

    class OrganizationalObjectViewTestCase(
        GetObjectViewTestCase,
        GetObjectChangelogViewTestCase,
        GetObjectNotesViewTestCase,
        CreateObjectViewTestCase,
        EditObjectViewTestCase,
        DeleteObjectViewTestCase,
        ListObjectsViewTestCase,
        BulkDeleteObjectsViewTestCase,
    ):
        """
        TestCase suitable for all organizational objects
        """

        maxDiff = None

    class DeviceComponentTemplateViewTestCase(
        EditObjectViewTestCase,
        DeleteObjectViewTestCase,
        CreateMultipleObjectsViewTestCase,
        BulkEditObjectsViewTestCase,
        BulkRenameObjectsViewTestCase,
        BulkDeleteObjectsViewTestCase,
    ):
        """
        TestCase suitable for testing device component template models (ConsolePortTemplates, InterfaceTemplates, etc.)
        """

        maxDiff = None

    class DeviceComponentViewTestCase(
        GetObjectViewTestCase,
        GetObjectChangelogViewTestCase,
        GetObjectNotesViewTestCase,
        EditObjectViewTestCase,
        DeleteObjectViewTestCase,
        ListObjectsViewTestCase,
        CreateMultipleObjectsViewTestCase,
        BulkEditObjectsViewTestCase,
        BulkRenameObjectsViewTestCase,
        BulkDeleteObjectsViewTestCase,
    ):
        """
        TestCase suitable for testing device component models (ConsolePorts, Interfaces, etc.)
        """

        maxDiff = None
        bulk_add_data = None
        """Used for bulk-add (distinct from bulk-create) view testing; self.bulk_create_data will be used if unset."""
        selected_objects: list[ComponentModel]
        selected_objects_parent_name: str

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_add_component(self):
            """Test bulk-adding this component to devices/virtual-machines."""
            self.add_permissions(f"{self.model._meta.app_label}.add_{self.model._meta.model_name}")

            initial_count = self._get_queryset().count()

            data = (self.bulk_add_data or self.bulk_create_data).copy()

            # Load the device-bulk-add or virtualmachine-bulk-add form
            if "device" in data:
                url = reverse(f"dcim:device_bulk_add_{self.model._meta.model_name}")
                request = {
                    "path": url,
                    "data": utils.post_data({"pk": data["device"]}),
                }
            else:
                url = reverse(f"virtualization:virtualmachine_bulk_add_{self.model._meta.model_name}")
                request = {
                    "path": url,
                    "data": utils.post_data({"pk": data["virtual_machine"]}),
                }
            self.assertHttpStatus(self.client.post(**request), 200)

            # Post to the device-bulk-add or virtualmachine-bulk-add form to create records
            if "device" in data:
                data["pk"] = data.pop("device")
            else:
                data["pk"] = data.pop("virtual_machine")
            data["_create"] = ""
            request["data"] = utils.post_data(data)
            self.assertHttpStatus(self.client.post(**request), 302)

            updated_count = self._get_queryset().count()
            self.assertEqual(updated_count, initial_count + self.bulk_create_count)

            matching_count = 0
            for instance in self._get_queryset().all():
                try:
                    self.assertInstanceEqual(instance, (self.bulk_add_data or self.bulk_create_data))
                    matching_count += 1
                except AssertionError:
                    pass
            self.assertEqual(matching_count, self.bulk_create_count)

        @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
        def test_bulk_rename(self):
            self.add_permissions(f"{self.model._meta.app_label}.change_{self.model._meta.model_name}")

            objects = self.selected_objects
            pk_list = [obj.pk for obj in objects]
            # Apply button not yet clicked
            data = {"pk": pk_list}
            data.update(self.rename_data)
            verbose_name_plural = self.model._meta.verbose_name_plural

            with self.subTest("Assert device name in HTML"):
                response = self.client.post(self._get_url("bulk_rename"), data)
                message = (
                    f"Renaming {len(objects)} {helpers.bettertitle(verbose_name_plural)} "
                    f"on {self.selected_objects_parent_name}"
                )
                self.assertBodyContains(response, message)

            with self.subTest("Assert update successfully"):
                data["_apply"] = True  # Form Apply button
                response = self.client.post(self._get_url("bulk_rename"), data)
                self.assertHttpStatus(response, 302)
                queryset = self._get_queryset().filter(pk__in=pk_list)
                for instance in objects:
                    self.assertEqual(queryset.get(pk=instance.pk).name, f"{instance.name}X")

            with self.subTest("Assert if no valid objects selected return with error"):
                for values in ([], [str(uuid.uuid4())]):
                    data["pk"] = values
                    response = self.client.post(self._get_url("bulk_rename"), data, follow=True)
                    expected_message = f"No valid {verbose_name_plural} were selected."
                    self.assertBodyContains(response, expected_message)
