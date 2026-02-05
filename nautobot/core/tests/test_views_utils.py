import urllib.parse

from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.db import ProgrammingError

from nautobot.core.models.querysets import count_related
from nautobot.core.testing import TestCase
from nautobot.core.views.utils import (
    check_filter_for_display,
    get_bulk_queryset_from_view,
    get_saved_views_for_user,
    prepare_cloned_fields,
)
from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.models import Device, DeviceRedundancyGroup, DeviceType, InventoryItem, Location, Manufacturer
from nautobot.extras.models import Role, SavedView, Status
from nautobot.ipam.models import Namespace, VRF
from nautobot.users.models import ObjectPermission, User


class CheckFilterForDisplayTest(TestCase):
    def test_check_filter_for_display(self):
        """Validate the operation of check_filter_for_display()."""

        device_filter_set_filters = DeviceFilterSet().filters

        with self.subTest("Test invalid filter case (field_name not found)"):
            expected_output = {
                "name": "fake_field_name",
                "display": "fake_field_name",
                "values": [{"name": "example_field_value", "display": "example_field_value"}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "fake_field_name", ["example_field_value"]),
                expected_output,
            )

        with self.subTest("Test values are converted to list"):
            expected_output = {
                "name": "fake_field_name",
                "display": "fake_field_name",
                "values": [{"name": "example_field_value", "display": "example_field_value"}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "fake_field_name", "example_field_value"),
                expected_output,
            )

        with self.subTest("Test get field label, none exists (fallback)"):
            expected_output = {
                "name": "id",
                "display": "Id",
                "values": [{"name": "example_field_value", "display": "example_field_value"}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "id", ["example_field_value"]), expected_output
            )

        with self.subTest("Test get field label, exists"):
            expected_output = {
                "name": "has_interfaces",
                "display": "Has interfaces",
                "values": [{"name": "example_field_value", "display": "example_field_value"}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "has_interfaces", ["example_field_value"]),
                expected_output,
            )

        with self.subTest(
            "Test get value display, falls back to string representation (also NaturalKeyOrPKMultipleChoiceFilter)"
        ):
            example_obj = DeviceRedundancyGroup.objects.first()
            expected_output = {
                "name": "device_redundancy_group",
                "display": "Device Redundancy Group (name or ID)",
                "values": [{"name": str(example_obj.pk), "display": str(example_obj)}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "device_redundancy_group", [str(example_obj.pk)]),
                expected_output,
            )

        # TODO(glenn): We need some filters that *aren't* getting updated to the new pattern - maybe in example_app?
        # with self.subTest("Test get value display (also legacy filter ModelMultipleChoiceFilter)"):
        #     example_obj = DeviceType.objects.first()
        #     expected_output = {
        #         "name": "device_type_id",
        #         "display": "Device type (ID)",
        #         "values": [{"name": str(example_obj.pk), "display": example_obj.display}],
        #     }

        #     self.assertEqual(
        #         check_filter_for_display(device_filter_set_filters, "device_type_id", [str(example_obj.pk)]),
        #         expected_output,
        #     )

        # with self.subTest("Test skip non-UUID value display (legacy, ex: ModelMultipleChoiceFilter)"):
        #     expected_output = {
        #         "name": "manufacturer",
        #         "display": "Manufacturer (slug)",
        #         "values": [{"name": "fake_slug", "display": "fake_slug"}],
        #     }

        # with self.assertEqual(
        #     check_filter_for_display(device_filter_set_filters, "manufacturer", ["fake_slug"]), expected_output
        # )


class CheckCountRelatedSubquery(TestCase):
    def test_count_related(self):
        """Assert that InventoryItems with the same Manufacturers do not cause issues in count_related subquery."""
        location = Location.objects.filter(parent__isnull=False).first()
        self.manufacturers = Manufacturer.objects.all()[:3]
        devicetype = DeviceType.objects.first()
        devicerole = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        device1 = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            status=device_status,
            location=location,
        )
        self.parent_inventory_item_1 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturers[0], name="Parent Inv 1"
        )
        self.child_inventory_item_1 = InventoryItem.objects.create(
            device=device1,
            manufacturer=self.manufacturers[0],
            name="Child Inv 1",
            parent=self.parent_inventory_item_1,
        )
        self.inventory_item_2 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturers[1], name="Inv 2"
        )
        self.inventory_item_3 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturers[2], name="Inv 3"
        )
        self.inventory_item_4 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturers[2], name="Inv 4"
        )
        try:
            qs = Manufacturer.objects.annotate(inventory_item_count=count_related(InventoryItem, "manufacturer"))
            list(qs)
            self.assertEqual(qs.get(pk=self.manufacturers[0].pk).inventory_item_count, 2)
            self.assertEqual(qs.get(pk=self.manufacturers[1].pk).inventory_item_count, 1)
            self.assertEqual(qs.get(pk=self.manufacturers[2].pk).inventory_item_count, 2)
        except ProgrammingError:
            self.fail("count_related subquery failed with ProgrammingError")

        qs = Device.objects.annotate(
            manufacturer_count=count_related(Manufacturer, "inventory_items__device", distinct=True)
        )
        self.assertEqual(qs.get(pk=device1.pk).manufacturer_count, 3)


class CheckPrepareClonedFields(TestCase):
    name = "Building-02"
    descriptions = ["Complicated Name & Stuff", "Simple Name"]

    def testQueryParameterGeneration(self):
        """Assert that a clone field with a special character, &, is properly escaped"""
        instance = Location.objects.get(name=self.name)
        self.assertIsInstance(instance, Location)
        for description in self.descriptions:
            with self.subTest(f"Testing parameter generation for a model with the name '{description}'"):
                instance.description = description
                query_params = urllib.parse.parse_qs(prepare_cloned_fields(instance))
                self.assertTrue(isinstance(query_params, dict))
                self.assertTrue("description" in query_params.keys())
                self.assertTrue(isinstance(query_params["description"], list))
                self.assertTrue(len(query_params["description"]) == 1)
                self.assertTrue(query_params["description"][0] == description)


class GetSavedViewsForUserTestCase(TestCase):
    """
    Class to test `get_saved_views_for_user`.
    """

    def create_saved_view(self, name, owner=None, is_shared=False):
        """Helper to create a SavedView."""
        return SavedView.objects.create(
            name=name, owner=owner or self.user, view="dcim:device_list", is_shared=is_shared
        )

    def setUp(self):
        super().setUp()
        # We want a clean slate for SavedViews
        SavedView.objects.all().delete()
        self.user2 = User.objects.create_user(username="second_user")
        self.create_saved_view(name="saved_view")
        self.create_saved_view(name="saved_view_shared", is_shared=True)
        self.create_saved_view(name="saved_view_different_owner", owner=self.user2)
        self.create_saved_view(name="saved_view_shared_different_owner", is_shared=True, owner=self.user2)

    def test_user_with_permissions_get_all_saved_views(self):
        """Test if for user with permissions method will return all saved views."""
        self.add_permissions("extras.view_savedview")
        saved_views = get_saved_views_for_user(self.user, "dcim:device_list")
        self.assertEqual(saved_views.count(), 4)
        expected_names = [
            "saved_view",
            "saved_view_different_owner",
            "saved_view_shared",
            "saved_view_shared_different_owner",
        ]
        self.assertEqual(list(saved_views.values_list("name", flat=True)), expected_names)

    def test_user_without_permissions_get_shared_views_and_own_views_only(self):
        """Test if user without permissions can see shared views and own views."""
        saved_views = get_saved_views_for_user(self.user, "dcim:device_list")
        self.assertEqual(saved_views.count(), 3)
        expected_names = ["saved_view", "saved_view_shared", "saved_view_shared_different_owner"]
        self.assertEqual(list(saved_views.values_list("name", flat=True)), expected_names)

    def test_anonymous_user_get_shared_views_only(self):
        """Test if method is working with anonymous users and return only shared views."""
        user = AnonymousUser()
        saved_views = get_saved_views_for_user(user, "dcim:device_list")
        self.assertEqual(saved_views.count(), 2)
        expected_names = ["saved_view_shared", "saved_view_shared_different_owner"]
        self.assertEqual(list(saved_views.values_list("name", flat=True)), expected_names)


class GetBulkQuerysetFromViewTestCase(TestCase):
    """Class to test get_bulk_queryset_from_view with VRF."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="testuser", password="testpass", is_superuser=True)  # noqa: S106  # hardcoded-password-func-arg -- ok as this is test code only
        self.vrfs = []
        namespace = Namespace.objects.create(name="test-namespace")
        for i in range(10):
            vrf = VRF.objects.create(
                name=f"VRF {i}",
                description=f"desc-{i % 3}",  # 3 unique descriptions, repeated
                namespace=namespace,
            )
            self.vrfs.append(vrf)
        # SavedView filters by name of VRF 5
        self.saved_view = SavedView.objects.create(
            name="VRF 5 Only",
            owner=self.user,
            view="ipam:vrf_list",
            config={"filter_params": {"name": self.vrfs[5].name}},
        )
        self.saved_view_empty = SavedView.objects.create(
            name="NO Filter Params", owner=self.user, view="ipam:vrf_list", config={"per_page": 50, "sort_order": []}
        )
        self.content_type = ContentType.objects.get_for_model(VRF)

    def test_not_is_all_and_pk_list(self):
        """!is_all and pk_list: Return queryset filtered by pk_list"""
        qs = get_bulk_queryset_from_view(
            user=self.user,
            content_type=self.content_type,
            edit_all=False,
            filter_query_params={},
            pk_list=[self.vrfs[2].pk, self.vrfs[4].pk],
            saved_view_id=None,
            action="change",
        )
        self.assertQuerysetEqual(qs, [self.vrfs[2], self.vrfs[4]], ordered=False)

    def test_not_is_all_and_no_pk_list(self):
        """!is_all and !pk_list: Return empty queryset. This should not normally happen in practice."""
        qs = get_bulk_queryset_from_view(
            user=self.user,
            content_type=self.content_type,
            edit_all=False,
            filter_query_params={},
            pk_list=[],
            saved_view_id=None,
            action="change",
        )
        self.assertEqual(qs.count(), 0)

    def test_is_all_and_no_saved_view_and_no_filter_query_params(self):
        """is_all and !saved_view_id and !filter_query_params: Return all objects"""
        qs = get_bulk_queryset_from_view(
            user=self.user,
            content_type=self.content_type,
            edit_all=True,
            filter_query_params={},
            pk_list=[self.vrfs[2].pk, self.vrfs[4].pk],  # should be ignored but is sent anyway by form
            saved_view_id=None,
            action="change",
        )
        self.assertQuerysetEqual(qs, VRF.objects.all(), ordered=False)

    def test_all_filters_removed_flag_ignores_saved_view(self):
        """
        If filter_query_params contains 'all_filters_removed', the saved view is ignored and all objects are returned.
        """
        # Pass the all_filters_removed flag in filter_query_params
        qs = get_bulk_queryset_from_view(
            user=self.user,
            content_type=self.content_type,
            filter_query_params={"all_filters_removed": [True], "saved_view": [self.saved_view.id]},
            pk_list=[],
            saved_view_id=self.saved_view.id,
            action="change",
            edit_all=True,
        )
        # Should return all VRFs, not just the one from the saved view
        self.assertQuerysetEqual(qs, VRF.objects.all(), ordered=False)

    def test_is_all_and_filter_query_params(self):
        """is_all and filter_query_params: Return queryset filtered by filter_query_params (description)"""
        qs = get_bulk_queryset_from_view(
            user=self.user,
            content_type=self.content_type,
            edit_all=True,
            filter_query_params={"description": ["desc-1"]},
            pk_list=[self.vrfs[2].pk, self.vrfs[4].pk],  # should be ignored but is sent anyway by form
            saved_view_id=None,
            action="change",
        )
        self.assertQuerysetEqual(qs, VRF.objects.filter(description="desc-1"), ordered=False)

    def test_is_all_and_saved_view_id(self):
        """is_all and saved_view_id: Return queryset filtered by saved_view_filter_params (name)"""
        qs = get_bulk_queryset_from_view(
            user=self.user,
            content_type=self.content_type,
            edit_all=True,
            filter_query_params={},
            pk_list=[self.vrfs[2].pk, self.vrfs[4].pk],  # should be ignored but is sent anyway by form
            saved_view_id=self.saved_view.id,
            action="change",
        )
        self.assertQuerysetEqual(qs, [self.vrfs[5]], ordered=False)

    def test_is_all_and_not_saved_view_id_but_saved_view_filter_params(self):
        """is_all and not saved_view_id: Return queryset filtered by filter_query_params (name)"""
        qs = get_bulk_queryset_from_view(
            user=self.user,
            content_type=self.content_type,
            edit_all=True,
            filter_query_params={"name": [self.vrfs[7].name]},
            pk_list=[self.vrfs[2].pk, self.vrfs[4].pk],  # should be ignored but is sent anyway by form
            saved_view_id=None,
            action="change",
        )
        self.assertQuerysetEqual(qs, [self.vrfs[7]], ordered=False)

    def test_queryset_respects_permissions(self):
        """is_all and not saved_view_id: Return queryset filtered by filter_query_params (name)"""
        # Create a non-superuser with no permissions
        limited_permissions_user = User.objects.create_user(
            username="user_no_perms",
            password="testpass",  # noqa: S106  # hardcoded-password-func-arg -- ok as this is test code only
            is_superuser=False,
        )
        # Assign object permission
        obj_perm = ObjectPermission.objects.create(
            name="Test permission",
            constraints={"name": self.vrfs[2].name},
            actions=["view", "change", "delete", "add"],
        )
        obj_perm.users.add(limited_permissions_user)
        obj_perm.object_types.add(self.content_type)

        qs = get_bulk_queryset_from_view(
            user=limited_permissions_user,
            content_type=self.content_type,
            edit_all=True,
            filter_query_params={},
            pk_list=[self.vrfs[3].pk, self.vrfs[4].pk],  # should be ignored but is sent anyway by form
            saved_view_id=None,
            action="change",
        )
        self.assertQuerysetEqual(qs, VRF.objects.filter(name=self.vrfs[2].name), ordered=False)

    def test_querydict_ignores(self):
        """is_all and not saved_view_id: Return queryset filtered by filter_query_params (name)"""
        filter_query_params = {"name": [self.vrfs[7].name], "per_page": [10]}
        qs = get_bulk_queryset_from_view(
            user=self.user,
            content_type=self.content_type,
            edit_all=True,
            filter_query_params=filter_query_params,
            pk_list=[self.vrfs[2].pk, self.vrfs[4].pk],  # should be ignored but is sent anyway by form
            saved_view_id=None,
            action="change",
        )
        self.assertQuerysetEqual(qs, VRF.objects.filter(name=self.vrfs[7].name), ordered=False)

    def test_no_valid_operation_found_raises(self):
        """If no valid operation is found, raise RuntimeError."""
        # Simulate a situation where all logic branches are skipped
        with self.assertRaises(RuntimeError):
            get_bulk_queryset_from_view(
                user=self.user,
                content_type=self.content_type,
                filter_query_params=None,
                pk_list=[],
                saved_view_id=None,
                action="change",
                edit_all=None,  # Not True, so not valid for 'change'
            )

    def test_runtime_error_when_all_param_missing(self):
        """Raise RuntimeError if required *_all param is not provided for the action."""
        with self.assertRaises(RuntimeError):
            get_bulk_queryset_from_view(
                user=self.user,
                content_type=self.content_type,
                filter_query_params={},
                pk_list=[],
                saved_view_id=None,
                action="delete",  # delete_all is missing
            )
        with self.assertRaises(RuntimeError):
            get_bulk_queryset_from_view(
                user=self.user,
                content_type=self.content_type,
                filter_query_params={},
                pk_list=[],
                saved_view_id=None,
                action="change",  # edit_all is missing
            )

    def test_is_all_and_saved_view__with_no_filter_params(self):
        """is_all and saved_view_id with no filter_params in saved view: Return all objects"""
        qs = get_bulk_queryset_from_view(
            user=self.user,
            content_type=self.content_type,
            edit_all=True,
            filter_query_params={},
            pk_list=[self.vrfs[2].pk, self.vrfs[4].pk],  # should be ignored but is sent anyway by form
            saved_view_id=self.saved_view_empty.id,
            action="change",
        )
        self.assertQuerysetEqual(qs, VRF.objects.all(), ordered=False)

    def test_bad_saved_view(self):
        """Test with a saved view ID that does not exist: Return no objects"""
        qs = get_bulk_queryset_from_view(
            user=self.user,
            content_type=self.content_type,
            edit_all=True,
            filter_query_params={},
            pk_list=[self.vrfs[2].pk, self.vrfs[4].pk],  # should be ignored but is sent anyway by form
            saved_view_id="00000000-0000-4000-8000-000000000000",  # valid UUID but does not exist
            action="change",
        )
        self.assertQuerysetEqual(qs, VRF.objects.none(), ordered=False)
