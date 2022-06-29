from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse

from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.forms import DeviceForm, DeviceFilterForm
from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from nautobot.extras.choices import DynamicGroupOperatorChoices
from nautobot.extras.models import DynamicGroup, DynamicGroupMembership, Status
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
                status=cls.status_planned,
                device_role=cls.device_role,
                device_type=cls.device_type,
                site=cls.sites[1],
            ),
            Device.objects.create(
                name="device-site-3",
                status=cls.status_active,
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

        # Assert that the groups we got from `get_for_object()` match the lookup
        # from the group instance itself.
        device1_groups = DynamicGroup.objects.get_for_object(device1)
        self.assertQuerySetEqual(device1_groups, device1.dynamic_groups)

    def test_members(self):
        """Test `DynamicGroup.members`."""
        group = self.first_child
        device1 = self.devices[0]
        device2 = self.devices[1]

        self.assertIn(device1, group.members)
        self.assertNotIn(device2, group.members)

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
        group = self.first_child
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
        self.assertEqual(sorted(form.fields), sorted(filter_fields))

    def test_get_initial(self):
        """Test `DynamicGroup.get_initial()`."""
        group1 = self.first_child  # Filter has `site`
        group2 = self.invalid_filter  # Filter has `name`

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

    def test_add_child(self):
        """Test `DynamicGroup.add_child()`."""
        self.parent.add_child(
            child=self.invalid_filter,
            operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
            weight=10,
        )
        self.assertTrue(self.parent.children.filter(slug=self.invalid_filter.slug).exists())

    def test_remove_child(self):
        """Test `DynamicGroup.remove_child()`."""
        self.parent.remove_child(self.third_child)
        self.assertFalse(self.parent.children.filter(slug=self.third_child.slug).exists())

    def test_generate_query_for_filter(self):
        """Test `DynamicGroup.generate_query_for_filter()`."""
        group = self.parent  # Any group will do, so why not this one?
        value = ["site-3"]
        query = group.generate_query_for_filter(
            filter_field=group.filterset_class.declared_filters["site"],
            value=value,
        )

        # Assert that both querysets resturn the same results
        group_qs = group.get_queryset().filter(query)
        device_qs = Device.objects.filter(site__slug__in=value)
        self.assertQuerySetEqual(group_qs, device_qs)

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
        process_qs = group.process_group_filters(group=group)
        self.assertQuerySetEqual(group_qs, process_qs)

    def test_get_ancestors(self):
        """Test `DynamicGroup.get_ancestors()`."""
        expected = ["third-child", "second-child", "first-child", "parent"]
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

    def test_ancestors(self):
        """Test `DynamicGroup.ancestors`."""
        a1 = self.parent.get_ancestors()
        a2 = self.parent.ancestors.all()
        self.assertEqual(list(a1), list(a2))

    def test_descendants(self):
        """Test `DynamicGroup.descendants`."""
        d1 = self.parent.get_descendants()
        d2 = self.parent.descendants.all()
        self.assertEqual(list(d1), list(d2))

    def test_ancestors_tree(self):
        """Test `DynamicGroup.ancestors_tree()`."""
        a_tree = self.nested_child.ancestors_tree()
        self.assertIn(self.parent, a_tree[self.third_child])

    def test_descendants_tree(self):
        """Test `DynamicGroup.descendants_tree()`."""
        d_tree = self.parent.descendants_tree()
        self.assertIn(self.nested_child, d_tree[self.third_child])

    # def test_flatten_tree(self):
    # def test__ordered_filter(self):
    # def test_reversibility (generating a Q object)
    # def test_process_group_filters(self):
    # def test_good_group(self): (well-constructed)
    # def test_bad_group(self): (poorly-constructed; makes no sense)
    # def test_chainable_filtering(self): from ancestors/descendants


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
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 6)

    def test_search(self):
        tests = {
            "Devices No Filter": 0,  # name
            "Invalid Filter": 1,  # name
            "invalid-filter": 1,  # slug
            "A group with a non-matching filter": 1,  # description
            "dcim": 6,  # content_type__app_label
            "device": 6,  # content_type__model
        }
        for value, cnt in tests.items():
            params = {"q": value}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), cnt)
