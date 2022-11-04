import random

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse

from nautobot.dcim.choices import PortTypeChoices
from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.forms import DeviceFilterForm, DeviceForm
from nautobot.dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    FrontPort,
    Location,
    LocationType,
    Manufacturer,
    RearPort,
    Site,
)
from nautobot.extras.choices import DynamicGroupOperatorChoices
from nautobot.extras.filters import DynamicGroupFilterSet, DynamicGroupMembershipFilterSet
from nautobot.extras.models import DynamicGroup, DynamicGroupMembership, Status
from nautobot.ipam.models import Prefix
from nautobot.utilities.forms.fields import MultiValueCharField
from nautobot.utilities.forms.widgets import MultiValueCharInput
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
            Site.objects.create(name="Site 4", slug="site-4"),
        ]

        cls.manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        cls.device_type = DeviceType.objects.create(
            manufacturer=cls.manufacturer,
            model="device Type 1",
            slug="device-type-1",
        )
        cls.device_role = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1", color="ff0000")
        cls.status_active = Status.objects.get_for_model(Device).get(slug="active")
        cls.status_planned = Status.objects.get_for_model(Device).get(slug="planned")
        cls.status_staged = Status.objects.get_for_model(Device).get(slug="staged")

        cls.devices = [
            Device.objects.create(
                name="device-site-1",
                status=cls.status_active,
                device_role=cls.device_role,
                device_type=cls.device_type,
                site=cls.sites[0],
            ),
            Device.objects.create(
                name="device-site-2",
                status=cls.status_active,
                device_role=cls.device_role,
                device_type=cls.device_type,
                serial="abc123",
                site=cls.sites[1],
            ),
            Device.objects.create(
                name="device-site-3",
                status=cls.status_planned,
                device_role=cls.device_role,
                device_type=cls.device_type,
                site=cls.sites[2],
            ),
            Device.objects.create(
                name="device-site-4",
                status=cls.status_staged,
                device_role=cls.device_role,
                device_type=cls.device_type,
                site=cls.sites[3],
            ),
        ]

        cls.groups = [
            DynamicGroup.objects.create(
                name="Parent",
                slug="parent",
                description="The parent group with no filter",
                filter={},
                content_type=cls.device_ct,
            ),
            # Site-1 only
            DynamicGroup.objects.create(
                name="First Child",
                slug="first-child",
                description="The first child group",
                filter={"site": ["site-1"]},
                content_type=cls.device_ct,
            ),
            # Site-2 only
            DynamicGroup.objects.create(
                name="Second Child",
                slug="second-child",
                description="A second child group",
                filter={"site": ["site-3"]},
                content_type=cls.device_ct,
            ),
            # Empty filter to use for testing nesting.
            DynamicGroup.objects.create(
                name="Third Child",
                slug="third-child",
                description="A third child group with a child of its own",
                filter={},
                content_type=cls.device_ct,
            ),
            # Nested child of third-child to test ancestors/descendants
            DynamicGroup.objects.create(
                name="Nested Child",
                slug="nested-child",
                description="This will be the child of third-child",
                filter={"status": ["active"]},
                content_type=cls.device_ct,
            ),
            # No matches (bogus/invalid name match)
            DynamicGroup.objects.create(
                name="Invalid Filter",
                slug="invalid-filter",
                description="A group with a non-matching filter",
                filter={"name": ["bogus"]},
                content_type=cls.device_ct,
            ),
            DynamicGroup.objects.create(
                name="MultiValueCharFilter",
                slug="multivaluecharfilter",
                description="A group with a multivaluechar filter",
                filter={"name": ["device-1", "device-2", "device-3"]},
                content_type=cls.device_ct,
            ),
        ]

        cls.parent = cls.groups[0]
        cls.first_child = cls.groups[1]
        cls.second_child = cls.groups[2]
        cls.third_child = cls.groups[3]
        cls.nested_child = cls.groups[4]
        cls.invalid_filter = cls.groups[5]

        # Setup the group membership hiearchy to use for graph testing
        cls.memberships = [
            DynamicGroupMembership.objects.create(
                parent_group=cls.parent,
                group=cls.first_child,
                weight=10,
                operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
            ),
            DynamicGroupMembership.objects.create(
                parent_group=cls.parent,
                group=cls.second_child,
                weight=20,
                operator=DynamicGroupOperatorChoices.OPERATOR_UNION,
            ),
            DynamicGroupMembership.objects.create(
                parent_group=cls.parent,
                group=cls.third_child,
                weight=30,
                operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
            ),
            DynamicGroupMembership.objects.create(
                parent_group=cls.third_child,
                group=cls.nested_child,
                weight=10,
                operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
            ),
        ]

    def assertQuerySetEqual(self, left_qs, right_qs):
        """Compare two querysets and assert that they are equal."""
        self.assertEqual(
            sorted(left_qs.values_list("pk", flat=True)),
            sorted(right_qs.values_list("pk", flat=True)),
        )


class DynamicGroupModelTest(DynamicGroupTestBase):
    """DynamicGroup model tests."""

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
        device4 = self.devices[-1]  # site-4

        # Assert that the groups we got from `get_for_object()` match the lookup
        # from the group instance itself.
        device1_groups = DynamicGroup.objects.get_for_object(device1)
        self.assertQuerySetEqual(device1_groups, device1.dynamic_groups)

        # Device4 should not be in ANY Dynamic Groups.
        device4_groups = DynamicGroup.objects.get_for_object(device4)
        self.assertEqual(list(device4_groups), [])
        self.assertQuerySetEqual(device4_groups, device4.dynamic_groups)

    def test_members(self):
        """Test `DynamicGroup.members`."""
        group = self.first_child
        device1 = self.devices[0]
        device2 = self.devices[1]

        self.assertIn(device1, group.members)
        self.assertNotIn(device2, group.members)

    def test_members_tree_nodes(self):
        """
        Test `DynamicGroup.members` when filtering on tree nodes like `Location`.
        """
        # Grab some values we'll used to setup the test case.
        device1 = self.devices[0]
        device2 = self.devices[1]
        site = device1.site
        status = Status.objects.get(slug="active")

        # Create two LocationTypes (My Region > My Site)
        loc_type_region = LocationType.objects.create(name="My Region", slug="my-region")
        loc_type_region.content_types.add(self.device_ct)
        loc_type_site = LocationType.objects.create(name="My Site", slug="my-site", parent=loc_type_region)
        loc_type_site.content_types.add(self.device_ct)

        loc_region = Location.objects.create(name="Location A", location_type=loc_type_region, site=site, status=status)
        loc_site = Location.objects.create(
            name="Location B", location_type=loc_type_site, parent=loc_region, status=status
        )

        # Add Location A to device1
        device1.location = loc_region
        device1.validated_save()

        # Add Location B to device2
        device2.site = device1.site
        device2.location = loc_site
        device2.validated_save()

        expected = sorted([device1.name, device2.name])

        # Create the Dynamic Group filtering on Location A
        group = DynamicGroup.objects.create(
            name="Devices Location",
            slug="devices-location",
            content_type=self.device_ct,
            filter={"location": ["location-a"]},
        )

        # We are expecting that the group members here should be nested results from any devices
        # that have a Location whose parent is "Location A".
        self.assertEqual(
            sorted(m.name for m in group.members),
            expected,
        )

        # Now also test that an advancted (nested) dynamic group, also reports
        # the same number of members.
        parent_group = DynamicGroup.objects.create(
            name="Parent of Devices Location",
            slug="parent-devices-location",
            content_type=self.device_ct,
            filter={},
        )
        parent_group.add_child(
            child=group,
            operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
            weight=10,
        )
        self.assertEqual(
            sorted(m.name for m in parent_group.members),
            expected,
        )

    def test_count(self):
        """Test `DynamicGroup.count`."""
        expected = {
            self.parent.count: 2,
            self.first_child.count: 1,
            self.second_child.count: 1,
            self.third_child.count: 2,
            self.nested_child.count: 2,
            self.invalid_filter.count: 0,
        }
        for grp, cnt in expected.items():
            self.assertEqual(grp, cnt)

    def test_get_queryset(self):
        """Test `DynamicGroup.get_queryset()`."""
        group = self.first_child
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

    def test_get_group_members_url(self):
        """Test `DynamicGroup.get_group_members_url()."""

        # First assert that a basic group with no children, then a group with children, will always
        # link to the members tab on the detail view.
        for group in [self.first_child, self.parent]:
            detail_url = reverse("extras:dynamicgroup", kwargs={"slug": group.slug})
            params = "tab=members"
            url = f"{detail_url}?{params}"
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
        # See if a CharField is properly converted to a MultiValueCharField In DynamicGroupEditForm.
        self.assertIsInstance(fields["name"], MultiValueCharField)
        self.assertIsInstance(fields["name"].widget, MultiValueCharInput)

    def test_map_filter_fields_skip_missing(self):
        """
        Test that missing fields are skipped in `DynamicGroup._map_filter_fields`
        when `Model.dynamic_group_skip_missing_fields` is `True`.
        """
        group = self.groups[0]

        try:
            group.model.dynamic_group_skip_missing_fields = True
            fields = group._map_filter_fields
            # Test that it's a dict with or without certain key fields.
            self.assertIsInstance(fields, dict)
            self.assertNotEqual(fields, {})
            self.assertNotIn("name", fields)
            self.assertNotIn("asset_tag", fields)
            self.assertNotIn("serial", fields)
        finally:
            del group.model.dynamic_group_skip_missing_fields

    def test_map_filter_fields_skip_method_filters_generate_query(self):
        """
        Test that method filters are skipped in `DynamicGroup._map_filter_fields` when the filterset
        for the group's content type has a method named `generate_query_{filter_method}`.
        """
        group = self.groups[0]
        filterset = group.filterset_class()
        fields = group._map_filter_fields

        # We know that `has_primary_ip` fits this bill, so let's test that.
        field_name = "has_primary_ip"
        filter_field = filterset.filters[field_name]

        # Make some field presence assertions
        self.assertIn(field_name, fields)

        # The filterset should have the method name and `generate_query_` method
        self.assertTrue(hasattr(filterset, filter_field.method))
        self.assertTrue(hasattr(filterset, "generate_query_" + filter_field.method))

    # 2.0 TODO(jathan): This is done using `DeviceFilterSet.pass_through_ports` at this time and
    # should be revised as filter fields are vetted.
    def test_filter_method_generate_query(self):
        """
        Test that a filter with a filter method's corresponding `generate_query_{filter_method}` works as intended.
        """
        group = self.groups[0]

        # We're going to test `pass_through_ports`
        device = self.devices[0]
        rear_port = RearPort.objects.create(device=device, name="rp1", positions=1, type=PortTypeChoices.TYPE_8P8C)
        FrontPort.objects.create(
            device=device, name="fp1", type=PortTypeChoices.TYPE_FC, rear_port=rear_port, rear_port_position=1
        )

        # Test that the filter returns the one device to which we added front/rear ports.
        expected = ["device-site-1"]
        filterset = group.filterset_class({"pass_through_ports": True}, Device.objects.all())
        devices = list(filterset.qs.values_list("name", flat=True))
        self.assertEqual(expected, devices)

    # 2.0 TODO(jathan): This is done using Prefix at this time and this should be revised as filter
    # fields are vetted.
    def test_map_filter_fields_skip_method_filters_no_generate_query(self):
        """
        Test that method filters are skipped in `DynamicGroup._map_filter_fields` when the filterset
        for the group's content type DOES NOT have a method named `generate_query_{filter_method}`.

        """
        pfx_content_type = ContentType.objects.get_for_model(Prefix)
        group = DynamicGroup(name="pfx", slug="pfx", content_type=pfx_content_type)
        filterset = group.filterset_class()
        fields = group._map_filter_fields

        # We know that `within_include` does not have a `generate_query_{filter_method}` method.
        field_name = "within_include"
        filter_field = filterset.filters[field_name]

        # Make some field presence assertions
        self.assertNotIn(field_name, fields)

        # The filterset should have the method name BUT NOT `generate_query_` method
        self.assertTrue(hasattr(filterset, filter_field.method))
        self.assertFalse(hasattr(filterset, "generate_query_" + filter_field.method))

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
        self.assertEqual(sorted(form.fields), sorted(filter_fields))

    def test_get_initial(self):
        """Test `DynamicGroup.get_initial()`."""
        group1 = self.first_child  # Filter has `site`
        self.assertEqual(group1.get_initial(), group1.filter)
        # Test if MultiValueCharField is properly pre-populated
        group2 = self.groups[6]  # Filter has `name`
        initial = group2.get_initial()
        expected = {"name": ["device-1", "device-2", "device-3"]}
        self.assertEqual(initial, expected)

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

    def test_add_child(self):
        """Test `DynamicGroup.add_child()`."""
        self.parent.add_child(
            child=self.invalid_filter,
            operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
            weight=10,
        )
        self.assertTrue(self.parent.children.filter(slug=self.invalid_filter.slug).exists())

    def test_clean_child_validation(self):
        """Test various ways in which adding a child group should fail."""
        parent = self.parent
        parent.filter = {"site": ["site-1"]}
        child = self.invalid_filter

        # parent.add_child() should fail
        with self.assertRaises(ValidationError):
            parent.add_child(
                child=child,
                operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
                weight=10,
            )

        # parent.children.add() should fail
        with self.assertRaises(ValidationError):
            parent.children.add(
                child,
                through_defaults=dict(
                    operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
                    weight=10,
                ),
            )

    def test_remove_child(self):
        """Test `DynamicGroup.remove_child()`."""
        self.parent.remove_child(self.third_child)
        self.assertFalse(self.parent.children.filter(slug=self.third_child.slug).exists())

    def test_generate_query_for_filter(self):
        """Test `DynamicGroup.generate_query_for_filter()`."""
        group = self.parent  # Any group will do, so why not this one?
        multi_value = ["site-3"]
        fs = group.filterset_class()
        multi_field = fs.filters["site"]
        multi_query = group.generate_query_for_filter(
            filter_field=multi_field,
            value=multi_value,
        )

        queryset = group.get_queryset()

        # Assert that both querysets resturn the same results
        group_qs = queryset.filter(multi_query)
        device_qs = Device.objects.filter(site__slug__in=multi_value)
        self.assertQuerySetEqual(group_qs, device_qs)

        # Now do a non-multi-value filter.
        # TODO(jathan): If we ever make "serial" a multi-value filter, this will need to be revised.
        solo_field = fs.filters["serial"]
        solo_value = "abc123"
        solo_query = group.generate_query_for_filter(filter_field=solo_field, value=solo_value)
        solo_qs = queryset.filter(solo_query)
        serial_qs = Device.objects.filter(serial__iexact=solo_value)
        self.assertQuerySetEqual(solo_qs, serial_qs)

    def test_generate_query_for_group(self):
        """Test `DynamicGroup.generate_query_for_group()`."""
        group = self.parent

        # A group with an empty filter will have a null `Q` object
        parent_q = group.generate_query_for_group(group)
        self.assertFalse(parent_q)

        # A child group with a filter set will result in a useful Q object.
        child_q = group.generate_query_for_group(self.second_child)
        lookup_kwargs = dict(child_q.children)  # {name: value}

        # Assert that both querysets resturn the same results
        group_qs = group.get_queryset().filter(child_q)
        device_qs = Device.objects.filter(**lookup_kwargs)
        self.assertQuerySetEqual(group_qs, device_qs)

    def test_get_group_queryset(self):
        """Test `DynamicGroup.get_group_queryset()`."""
        # This is literally just calling `process_group_filters(self)` so let's
        # just make sure that it stays consistent until we decide otherwise.
        group = self.parent
        group_qs = group.get_group_queryset()
        process_query = group.generate_query()
        base_qs = group.get_queryset()
        process_qs = base_qs.filter(process_query)

        self.assertQuerySetEqual(group_qs, process_qs)

    def test_get_ancestors(self):
        """Test `DynamicGroup.get_ancestors()`."""
        expected = ["third-child", "parent"]
        ancestors = [a.slug for a in self.nested_child.get_ancestors()]
        self.assertEqual(ancestors, expected)

    def test_get_descendants(self):
        """Test `DynamicGroup.get_descendants()`."""
        expected = ["first-child", "second-child", "third-child", "nested-child"]
        descendants = [d.slug for d in self.parent.get_descendants()]
        self.assertEqual(descendants, expected)

    def test_get_siblings(self):
        """Test `DynamicGroup.get_siblings()`."""
        expected = ["first-child", "second-child"]
        siblings = sorted(s.slug for s in self.third_child.get_siblings())
        self.assertEqual(siblings, expected)

    def test_is_root(self):
        """Test `DynamicGroup.is_root()`."""
        self.assertTrue(self.parent.is_root())
        self.assertFalse(self.nested_child.is_root())

    def test_is_leaf(self):
        """Test `DynamicGroup.is_leaf()`."""
        self.assertFalse(self.parent.is_leaf())
        self.assertTrue(self.nested_child.is_leaf())

    def test_get_ancestors_queryset(self):
        """Test `DynamicGroup.get_ancestors_queryset()`."""
        a1 = self.parent.get_ancestors()
        a2 = self.parent.get_ancestors_queryset()
        self.assertEqual(list(a1), list(a2))

    def test_descendants(self):
        """Test `DynamicGroup.get_descendants_queryset()`."""
        d1 = self.parent.get_descendants()
        d2 = self.parent.get_descendants_queryset()
        self.assertEqual(list(d1), list(d2))

    def test_ancestors_tree(self):
        """Test `DynamicGroup.ancestors_tree()`."""
        a_tree = self.nested_child.ancestors_tree()
        self.assertIn(self.parent, a_tree[self.third_child])

    def test_descendants_tree(self):
        """Test `DynamicGroup.descendants_tree()`."""
        d_tree = self.parent.descendants_tree()
        self.assertIn(self.nested_child, d_tree[self.third_child])

    def test_flatten_descendants_tree(self):
        """Test `DynamicGroup.flatten_descendants_tree()`."""
        # Assert descendants are deterministic
        d_tree = self.parent.descendants_tree()
        d_flat = self.parent.flatten_descendants_tree(d_tree)
        expected = {"first-child": 1, "second-child": 1, "third-child": 1, "nested-child": 2}
        seen = {d.slug: d.depth for d in d_flat}
        self.assertEqual(seen, expected)

        # Parent should not be here; nested-child should.
        self.assertNotIn(self.parent, d_flat)
        self.assertIn(self.nested_child, d_flat)

    def test_flatten_ancestors_tree(self):
        """Test `DynamicGroup.flatten_ancestors_tree()`."""
        # Assert ancestors are deterministic
        a_tree = self.nested_child.ancestors_tree()
        a_flat = self.nested_child.flatten_ancestors_tree(a_tree)
        expected = {"third-child": 1, "parent": 2}
        seen = {a.slug: a.depth for a in a_flat}
        self.assertEqual(seen, expected)

        # Nested-child should not be here; parent should.
        self.assertNotIn(self.nested_child, a_flat)
        self.assertIn(self.parent, a_flat)

    def test_membership_tree(self):
        """Test `DynamicGroup.membership_tree()`."""
        group = self.parent

        d_tree = group.flatten_descendants_tree(group.descendants_tree())
        m_tree = group.membership_tree()

        d_groups = [d.slug for d in d_tree]
        m_groups = [m.group.slug for m in m_tree]

        d_depths = [d.depth for d in d_tree]
        m_depths = [m.depth for m in m_tree]

        # Assert same members, same order.
        self.assertEqual(d_groups, m_groups)
        # Assert same depths.
        self.assertEqual(d_depths, m_depths)

    def test_ordered_queryset_from_pks(self):
        """Test `DynamicGroup.ordered_queryset_from_pks()`."""
        descendants = self.parent.get_descendants()
        pk_list = [d.pk for d in descendants]

        # Assert that ordering is always deterministic by shuffling the list of pks and asserting
        # that the ordered pk matches that shuffled order.
        random.shuffle(pk_list)
        ordered_qs = self.parent.ordered_queryset_from_pks(pk_list)
        self.assertEqual(
            pk_list,
            [o.pk for o in ordered_qs],
        )

    def test_generate_query(self):
        """Test `DynamicGroup.generate_query()`."""
        # Start with parent. Enumerate descendants and their operators to assert correct results.
        group = self.parent
        group_query = group.generate_query()
        group_qs = group.get_queryset().filter(group_query)

        # <DynamicGroupMembership: First Child: intersection (10)>
        # <DynamicGroupMembership: Second Child: union (20)>
        # <DynamicGroupMembership: Third Child: difference (30)>
        group_members = group.dynamic_group_memberships.all()

        # Manually iterate over the groups to assert the same result that the queryset should have,
        # igoring weight since each set of members are already ordered by weight when queried from
        # the database.
        child_set = set(group.get_queryset())
        for member in group_members:
            child_members = set(member.members)
            operator = member.operator
            # Use operator value to call a set method; one of intersection, union, difference and
            # update the results set. (e.g. `child_set.difference(child_members)`
            if operator == "union":
                child_set = child_set | child_members
            elif operator == "difference":
                child_set = child_set - child_members
            elif operator == "intersection":
                child_set = child_set & child_members

        # These should be the same length.
        self.assertEqual(group_qs.count(), len(child_set))

        # And have the same members...
        expected = ["device-site-3"]
        self.assertEqual(sorted(group_qs.values_list("name", flat=True)), expected)

    def test_delete(self):
        """Test `DynamicGroup(instance).delete()`."""
        # Has parents
        with self.assertRaises(ProtectedError):
            self.nested_child.delete()

        # Clear the deeply nested child's parents then delete it!
        self.nested_child.parents.clear()
        self.nested_child.delete()


class DynamicGroupMembershipModelTest(DynamicGroupTestBase):
    """DynamicGroupMembership model tests."""

    def test_clean_content_type(self):
        """Assert that content_type b/w parent/group must match."""
        with self.assertRaises(ValidationError):
            self.first_child.content_type = self.dynamicgroup_ct
            self.parent.add_child(
                child=self.first_child,
                operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
                weight=10,
            )

        # Cleanup because we're using class-based fixtures in `setUpTestData()`
        self.first_child.refresh_from_db()

    def test_clean_block_self(self):
        """Assert that a group cannot be its own child."""
        with self.assertRaises(ValidationError):
            self.parent.add_child(
                child=self.parent,
                operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
                weight=10,
            )

    def test_clean_loop_detection(self):
        """Assert that graph loops are blocked (ancestors can't be a child)."""
        with self.assertRaises(ValidationError):
            self.third_child.add_child(
                child=self.parent,
                operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
                weight=10,
            )

    def test_clean_child_uniqueness(self):
        """Assert that membership uniqueness criteria are enforced."""
        with self.assertRaises(ValidationError):
            self.third_child.add_child(
                child=self.nested_child,
                weight=10,
                operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
            )

    def test_clean_parent_filter_exclusivity(self):
        """Assert that if `parent_group.filter` is set that it blocks creation."""
        with self.assertRaises(ValidationError):
            DynamicGroupMembership.objects.create(
                parent_group=self.first_child,
                group=self.invalid_filter,
                weight=10,
                operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
            )

    def test_group_attributes(self):
        """Test passthrough attributes to `self.group`."""
        mem = self.memberships[0]
        grp = mem.group

        self.assertEqual(mem.name, grp.name)
        self.assertEqual(sorted(mem.members), sorted(grp.members))
        self.assertEqual(mem.count, grp.count)
        self.assertEqual(mem.get_absolute_url(), grp.get_absolute_url())
        self.assertEqual(mem.get_group_members_url(), grp.get_group_members_url())


class DynamicGroupFilterTest(DynamicGroupTestBase):
    """DynamicGroup instance filterset tests."""

    queryset = DynamicGroup.objects.all()
    filterset = DynamicGroupFilterSet

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_name(self):
        params = {"name": ["First Child", "Third Child"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_slug(self):
        params = {"slug": ["invalid-filter"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_content_type(self):
        params = {"content_type": ["dcim.device", "virtualization.virtualmachine"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 7)

    def test_search(self):
        tests = {
            "Devices No Filter": 0,  # name
            "Invalid Filter": 1,  # name
            "invalid-filter": 1,  # slug
            "A group with a non-matching filter": 1,  # description
            "dcim": 7,  # content_type__app_label
            "device": 7,  # content_type__model
        }
        for value, cnt in tests.items():
            params = {"q": value}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), cnt)


class DynamicGroupMembershipFilterTest(DynamicGroupTestBase):
    """DynamicGroupMembership instance filterset tests."""

    queryset = DynamicGroupMembership.objects.all()
    filterset = DynamicGroupMembershipFilterSet

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_operator(self):
        params = {"operator": DynamicGroupOperatorChoices.OPERATOR_INTERSECTION}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_weight(self):
        params = {"weight": [10]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_group(self):
        group_pk = self.queryset.first().group.pk  # expecting 1
        group_slug = self.queryset.last().group.slug  # expecting 1
        params = {"group": [group_pk, group_slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_parent_group(self):
        parent_group_pk = self.queryset.first().parent_group.pk  # expecting 3
        parent_group_slug = self.queryset.last().parent_group.slug  # expecting 1
        params = {"parent_group": [parent_group_pk, parent_group_slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_search(self):
        tests = {
            "intersection": 2,  # operator
            "First Child": 1,  # group__name
            "second-child": 1,  # group__slug
            "Parent": 3,  # parent_group__name,
            "third-child": 2,  # parent_group__slug OR group__slug,
        }
        for value, cnt in tests.items():
            params = {"q": value}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), cnt)
