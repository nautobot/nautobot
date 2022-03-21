from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse

from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.forms import DeviceForm, DeviceFilterForm
from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from nautobot.extras.models import DynamicGroup, Status
from nautobot.extras.filters import DynamicGroupFilterSet
from nautobot.utilities.testing import TestCase


class DynamicGroupTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):

        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.dynamicgroup_ct = ContentType.objects.get_for_model(DynamicGroup)

        cls.sites = [
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
            Site.objects.create(name="Site 3", slug="site-3"),
        ]

        cls.manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        cls.device_type = DeviceType.objects.create(
            manufacturer=cls.manufacturer,
            model="device Type 1",
            slug="device-type-1",
        )
        cls.device_role = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1", color="ff0000")
        cls.device_status = Status.objects.get_for_model(Device).get(slug="active")

        cls.devices = [
            Device.objects.create(
                name="device-site-1",
                status=cls.device_status,
                device_role=cls.device_role,
                device_type=cls.device_type,
                site=cls.sites[0],
            ),
            Device.objects.create(
                name="device-site-2",
                status=cls.device_status,
                device_role=cls.device_role,
                device_type=cls.device_type,
                site=cls.sites[1],
            ),
            Device.objects.create(
                name="device-site-3",
                status=cls.device_status,
                device_role=cls.device_role,
                device_type=cls.device_type,
                site=cls.sites[2],
            ),
        ]

        cls.groups = [
            # Site-1 only
            DynamicGroup.objects.create(
                name="Site 1",
                slug="site-1",
                filter={"site": ["site-1"]},
                content_type=cls.device_ct,
            ),
            # No matches (bogus name match)
            DynamicGroup.objects.create(
                name="No Filter",
                slug="no-filter",
                description="A group with no filter",
                filter={"name": ["bogus"]},
                content_type=cls.device_ct,
            ),
            # Site-2 only
            DynamicGroup.objects.create(
                name="Site 3",
                slug="site-3",
                filter={"site": ["site-3"]},
                content_type=cls.device_ct,
            ),
        ]


class DynamicGroupModelTest(DynamicGroupTestBase):
    def test_content_type_is_immutable(self):
        """Test that `content_type` is immutable after create."""
        instance = self.groups[0]
        with self.assertRaises(ValidationError):
            instance.content_type = self.dynamicgroup_ct
            instance.validated_save()

    def test_clean_filter_not_dict(self):
        """Test that invalid filter types raise errors."""
        instance = self.groups[0]
        with self.assertRaises(ValidationError):
            instance.filter = None
            instance.validated_save()

        with self.assertRaises(ValidationError):
            instance.filter = []
            instance.validated_save()

        with self.assertRaises(ValidationError):
            instance.filter = "site=ams01"
            instance.validated_save()

    def test_clean_filter_not_valid(self):
        """Test that an invalid filter dict raises an error."""
        instance = self.groups[0]
        with self.assertRaises(ValidationError):
            instance.filter = {"site": -42}
            instance.validated_save()

    def test_clean_valid(self):
        """Test a clean validation."""
        group = self.groups[0]
        group.refresh_from_db()
        old_filter = group.filter

        # Overload the filter and validate that it is the same afterward.
        new_filter = {"interfaces": True}
        group.set_filter(new_filter)
        group.validated_save()
        self.assertEqual(group.filter, new_filter)

        # Restore the old filter.
        group.filter = old_filter
        group.save()

    def test_get_for_object(self):
        """Test `DynamicGroup.objects.get_for_object()`."""
        device1 = self.devices[0]  # site-1
        device2 = self.devices[1]  # site-2

        # Assert that the groups we got from `get_for_object()` match the lookup
        # from the group instance itself.
        device1_groups = DynamicGroup.objects.get_for_object(device1)
        self.assertEqual(
            sorted(device1_groups.values_list("pk", flat=True)),
            sorted(device1.dynamic_groups.values_list("pk", flat=True)),
        )

        # Now assert the inverse for device2 (no groups).
        device2_groups = DynamicGroup.objects.get_for_object(device2)
        self.assertFalse(device2_groups.exists())

    def test_members(self):
        """Test `DynamicGroup.members`."""
        group = self.groups[0]
        device1 = self.devices[0]
        device2 = self.devices[1]

        group_members = group.members
        self.assertIn(device1, group_members)
        self.assertNotIn(device2, group_members)

    def test_count(self):
        """Test `DynamicGroup.count`."""
        group1, group2, group3 = self.groups
        self.assertEqual(group1.count, 1)
        self.assertEqual(group2.count, 0)
        self.assertEqual(group3.count, 1)

    def test_get_queryset(self):
        """Test `DynamicGroup.get_queryset()`."""
        group = self.groups[0]
        device1 = self.devices[0]

        # Test that we can get a full queryset
        qs = group.get_queryset()
        devices = group.model.objects.filter(site=device1.site)

        # Expect a single-member qs/list of Device names (only `device1`)
        expected = [device1.name]
        self.assertIn(device1, devices)
        self.assertIn(device1, qs)
        self.assertEqual(list(map(str, devices)), expected)
        self.assertEqual(list(map(str, qs)), expected)
        self.assertEqual(list(qs), list(devices))

        # A new group that doesn't have a content_type and therefore
        # `self.model`, should raise a RuntimeError
        new_group = DynamicGroup()
        with self.assertRaises(RuntimeError):
            new_group.get_queryset()

    def test_model(self):
        """Test `DynamicGroup.model`."""
        # New instances should not have a model unless `content_type` is set.
        new_group = DynamicGroup(name="Unsaved Group", slug="unsaved-group")
        self.assertIsNone(new_group.model)

        # Setting the content_type will now allow `.model` to be accessed.
        new_group.content_type = self.device_ct
        self.assertIsNotNone(new_group.model)

    def test_set_object_classes(self):
        """Test `DynamicGroup._set_object_classes()`."""
        # New instances should fail to map until `content_type` is set.
        new_group = DynamicGroup(name="Unsaved Group", slug="unsaved-group")
        objects_mapped = new_group._set_object_classes(new_group.model)
        self.assertFalse(objects_mapped)

        # Existing groups w/ `content_type` set work as expected.
        group = self.groups[0]
        model = group.content_type.model_class()
        objects_mapped = group._set_object_classes(model)

        self.assertTrue(objects_mapped)
        self.assertEqual(group.model, model)
        self.assertEqual(group.filterset_class, DeviceFilterSet)
        self.assertEqual(group.filterform_class, DeviceFilterForm)
        self.assertEqual(group.form_class, DeviceForm)

    def test_members_base_url(self):
        """Test `DynamicGroup.members_base_url`."""
        # New instances should not have `members_base_url` unless `content_type` is set.
        new_group = DynamicGroup(name="Unsaved Group", slug="unsaved-group")
        self.assertEqual(new_group.members_base_url, "")

        # Setting the content_type will now allow `.members_base_url` to be accessed.
        new_group.content_type = self.device_ct
        self.assertEqual(new_group.members_base_url, reverse("dcim:device_list"))

    def test_get_group_members_url(self):
        """Test `DynamicGroup.get_group_members_url()."""
        group = self.groups[0]
        base_url = reverse("dcim:device_list")
        params = "site=site-1"
        url = f"{base_url}?{params}"
        self.assertEqual(group.get_group_members_url(), url)

        # If the new group has no attributes or map yet, expect an empty string.
        new_group = DynamicGroup()
        self.assertEqual(new_group.get_group_members_url(), "")

    def test_map_filter_fields(self):
        """Test `DynamicGroup._map_filter_fields`."""
        group = self.groups[0]
        fields = group._map_filter_fields

        # Test that it's a dict with or without certain key fields.
        self.assertIsInstance(fields, dict)
        self.assertNotEqual(fields, {})
        self.assertNotIn("q", fields)
        self.assertIn("name", fields)

    def test_get_filter_fields(self):
        """Test `DynamicGroup.get_filter_fields()`."""
        # New instances should return {} `content_type` is set.
        new_group = DynamicGroup(name="Unsaved Group", slug="unsaved-group")
        new_filter_fields = new_group.get_filter_fields()
        self.assertEqual(new_filter_fields, {})

        # Existing groups should have actual fields.
        group = self.groups[0]
        filter_fields = group.get_filter_fields()
        self.assertIsInstance(filter_fields, dict)
        self.assertNotEqual(filter_fields, {})
        self.assertNotIn("q", filter_fields)
        self.assertIn("name", filter_fields)

    def test_generate_filter_form(self):
        """Test `DynamicGroup.generate_filter_form()`."""
        group = self.groups[0]
        filter_fields = group.get_filter_fields()
        form_class = group.generate_filter_form()
        form = form_class(group.filter)

        # Form should validate just fine from the group's filter
        self.assertTrue(form.is_valid())

        # Form instance should have identical field set to filter fields.
        self.assertEqual(
            sorted(form.fields),
            sorted(filter_fields),
        )

    def test_get_initial(self):
        """Test `DynamicGroup.get_initial()`."""
        group1 = self.groups[0]  # Filter has `site`
        group2 = self.groups[1]  # Filter has `name`

        # Test that a CharField (e.g. `name`) gets flattened. We use group2 for this.
        initial = group2.get_initial()
        expected = {"name": "bogus"}
        self.assertEqual(initial, expected)

        # Otherwise, it just passes through the filter.
        self.assertEqual(group1.get_initial(), group1.filter)

    def test_set_filter(self):
        """Test `DynamicGroup.set_filter()`."""
        group = self.groups[0]

        # Input can come from a form's cleaned_data, such as our generated form. In this case, the
        # filter we set from the form should be identical to what was there already.
        old_filter = group.filter
        form_class = group.generate_filter_form()
        form_class.prefix = None  # We don't want the prefix here right now.
        form = form_class(group.filter)
        form.is_valid()
        group.set_filter(form.cleaned_data)
        self.assertEqual(group.filter, old_filter)

        # Now we'll do it using a manually crafted dict.
        new_filter = {"interfaces": True}
        group.set_filter(new_filter)
        self.assertEqual(group.filter, new_filter)

        # And a bad input
        bad_filter = {"site": -42}
        with self.assertRaises(ValidationError):
            group.set_filter(bad_filter)

        # Cleanup because we're using class-based fixtures in `setUpTestData()`
        group.refresh_from_db()


class DynamicGroupFilterTest(DynamicGroupTestBase):
    queryset = DynamicGroup.objects.all()
    filterset = DynamicGroupFilterSet

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_name(self):
        params = {"name": ["Site 1", "Site 3"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_slug(self):
        params = {"slug": ["no-filter"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_content_type(self):
        params = {"content_type": ["dcim.device", "virtualization.virtualmachine"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_search(self):
        tests = {
            "Devices No Filter": 0,  # name
            "No Filter": 1,  # name
            "no-filter": 1,  # slug
            "A group with no filter": 1,  # description
            "dcim": 3,  # content_type__app_label
            "device": 3,  # content_type__model
        }
        for value, cnt in tests.items():
            params = {"q": value}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), cnt)
