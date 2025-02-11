import random

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError, QuerySet
from django.urls import reverse

from nautobot.core.forms.fields import MultiMatchModelMultipleChoiceField, MultiValueCharField
from nautobot.core.forms.widgets import APISelectMultiple, MultiValueCharInput
from nautobot.core.testing import TestCase
from nautobot.core.testing.filters import FilterTestCases
from nautobot.dcim.choices import PortTypeChoices
from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.forms import DeviceFilterForm, DeviceForm
from nautobot.dcim.models import (
    Controller,
    Device,
    DeviceType,
    FrontPort,
    Location,
    LocationType,
    Manufacturer,
    RearPort,
)
from nautobot.extras.choices import (
    CustomFieldFilterLogicChoices,
    CustomFieldTypeChoices,
    DynamicGroupOperatorChoices,
    DynamicGroupTypeChoices,
    RelationshipTypeChoices,
)
from nautobot.extras.filters import DynamicGroupFilterSet, DynamicGroupMembershipFilterSet
from nautobot.extras.models import (
    CustomField,
    DynamicGroup,
    DynamicGroupMembership,
    Relationship,
    RelationshipAssociation,
    Role,
    Status,
    Tag,
)
from nautobot.extras.utils import fixup_dynamic_group_group_types
from nautobot.ipam.models import IPAddress, Prefix
from nautobot.ipam.querysets import PrefixQuerySet
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import VirtualMachine


class DynamicGroupTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Controller.objects.filter(controller_device__isnull=False).delete()
        Device.objects.all().delete()
        cls.device_ct = ContentType.objects.get_for_model(Device)
        cls.dynamicgroup_ct = ContentType.objects.get_for_model(DynamicGroup)
        cls.lt = LocationType.objects.get(name="Campus")

        loc_status = Status.objects.get_for_model(Location).first()
        cls.locations = [
            Location.objects.create(name="Location 1", location_type=cls.lt, status=loc_status),
            Location.objects.create(name="Location 2", location_type=cls.lt, status=loc_status),
            Location.objects.create(name="Location 3", location_type=cls.lt, status=loc_status),
            Location.objects.create(name="Location 4", location_type=cls.lt, status=loc_status),
        ]

        cls.manufacturer = Manufacturer.objects.first()
        cls.device_type = DeviceType.objects.create(
            manufacturer=cls.manufacturer, model="Test Dynamic Groups Device Type"
        )
        cls.device_role = Role.objects.get_for_model(Device).first()
        statuses = Status.objects.get_for_model(Device)
        cls.status_1 = statuses[0]
        cls.status_2 = statuses[1]
        cls.status_3 = statuses[2]

        cls.devices = [
            Device.objects.create(
                name="device-location-1",
                status=cls.status_1,
                role=cls.device_role,
                device_type=cls.device_type,
                location=cls.locations[0],
            ),
            Device.objects.create(
                name="device-location-2",
                status=cls.status_1,
                role=cls.device_role,
                device_type=cls.device_type,
                serial="abc123",
                location=cls.locations[1],
            ),
            Device.objects.create(
                name="device-location-3",
                status=cls.status_2,
                role=cls.device_role,
                device_type=cls.device_type,
                location=cls.locations[2],
            ),
            Device.objects.create(
                name="device-location-4",
                status=cls.status_3,
                role=cls.device_role,
                device_type=cls.device_type,
                location=cls.locations[3],
            ),
        ]

        cls.groups = [
            DynamicGroup.objects.create(
                name="Parent",
                description="The parent group with no filter",
                group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET,
                content_type=cls.device_ct,
            ),
            # Location-1 only
            DynamicGroup.objects.create(
                name="First Child",
                description="The first child group",
                filter={"location": ["Location 1"]},
                content_type=cls.device_ct,
            ),
            # Location-2 only
            DynamicGroup.objects.create(
                name="Second Child",
                description="A second child group",
                filter={"location": ["Location 3"]},
                content_type=cls.device_ct,
            ),
            # Empty filter to use for testing nesting.
            DynamicGroup.objects.create(
                name="Third Child",
                description="A third child group with a child of its own",
                group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET,
                content_type=cls.device_ct,
            ),
            # Nested child of third-child to test ancestors/descendants
            DynamicGroup.objects.create(
                name="Nested Child",
                description="This will be the child of third-child",
                filter={"status": [statuses[0].name]},
                content_type=cls.device_ct,
            ),
            # No matches (bogus name match)
            DynamicGroup.objects.create(
                name="No Match Filter",
                description="A group with a non-matching filter",
                filter={"name": ["bogus"]},
                content_type=cls.device_ct,
            ),
            DynamicGroup.objects.create(
                name="MultiValueCharFilter",
                description="A group with a multivaluechar filter",
                filter={"name": ["device-1", "device-2", "device-3"]},
                content_type=cls.device_ct,
            ),
        ]
        for group in cls.groups:
            group.validated_save()

        cls.parent = cls.groups[0]
        cls.first_child = cls.groups[1]
        cls.second_child = cls.groups[2]
        cls.third_child = cls.groups[3]
        cls.nested_child = cls.groups[4]
        cls.no_match_filter = cls.groups[5]
        cls.invalid_filter = DynamicGroup.objects.create(
            name="Invalid Filter",
            description="A group with a filter that's invalid",
            filter={"platform": ["invalidvalue"]},
            content_type=cls.device_ct,
        )
        cls.groups.append(cls.invalid_filter)

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


class DynamicGroupModelTest(DynamicGroupTestBase):  # TODO: BaseModelTestCase mixin?
    """DynamicGroup model tests."""

    def test_content_type_is_immutable(self):
        """Test that `content_type` is immutable after create."""
        instance = self.groups[0]
        with self.assertRaises(ValidationError):
            instance.content_type = self.dynamicgroup_ct
            instance.validated_save()

    def test_full_clean_filter_not_dict(self):
        """Test that invalid filter types raise errors."""
        instance = self.groups[0]
        with self.assertRaises(ValidationError):
            instance.filter = None
            instance.validated_save()

        with self.assertRaises(ValidationError):
            instance.filter = []
            instance.validated_save()

        with self.assertRaises(ValidationError):
            instance.filter = "location=ams01"
            instance.validated_save()

    def test_full_clean_filter_not_valid(self):
        """Test that an invalid filter dict raises an error."""
        instance = self.groups[0]
        with self.assertRaises(ValidationError):
            instance.filter = {"location": -42}
            instance.validated_save()

    def test_clean_fields_exclude_filter(self):
        """Test that filter validation is skipped when an appropriate `exclude` parameter is provided."""
        instance = self.groups[0]
        instance.filter = {"platform": -42}
        instance.clean_fields(exclude=["filter"])
        instance.full_clean(exclude=["filter"])

        with self.assertRaises(ValidationError):
            instance.clean_fields()
        with self.assertRaises(ValidationError):
            instance.full_clean()

    def test_full_clean_valid(self):
        """Test a clean validation."""
        set_group = self.groups[0]
        filter_group = self.groups[1]
        old_filter = filter_group.filter

        # Overload the filter and validate that it is the same afterward.
        new_filter = {"has_interfaces": True}
        with self.assertRaises(ValidationError):
            set_group.set_filter(new_filter)
            set_group.validated_save()
        filter_group.set_filter(new_filter)
        filter_group.validated_save()
        self.assertEqual(filter_group.filter, new_filter)

        # Restore the old filter.
        filter_group.filter = old_filter
        filter_group.save()

    def test_get_for_object(self):
        """Test `DynamicGroup.objects.get_for_object()`."""
        device1 = self.devices[0]  # device-location-1
        device4 = self.devices[-1]  # device-location-4

        # Assert that the groups we got from `get_for_object()` match the lookup
        # from the group instance itself.
        device1_groups = DynamicGroup.objects.get_for_object(device1)
        self.assertQuerysetEqualAndNotEmpty(device1_groups, device1.dynamic_groups)

        # Device4 should not be in ANY Dynamic Groups.
        device4_groups = DynamicGroup.objects.get_for_object(device4)
        self.assertEqual(list(device4_groups), [])
        self.assertQuerysetEqual(device4.dynamic_groups, [])

    def test_members(self):
        """Test `DynamicGroup.members`."""
        group = self.first_child
        device1 = self.devices[0]
        device2 = self.devices[1]

        self.assertIn(device1, group.members)
        self.assertNotIn(device2, group.members)

    def test_static_member_operations(self):
        sg = DynamicGroup.objects.create(
            name="All Prefixes",
            content_type=ContentType.objects.get_for_model(Prefix),
            group_type=DynamicGroupTypeChoices.TYPE_STATIC,
        )
        self.assertIsInstance(sg.members, PrefixQuerySet)
        self.assertEqual(sg.members.count(), 0)
        # test type validation
        with self.assertRaises(TypeError):
            sg.add_members([IPAddress.objects.first()])
        # test bulk addition
        sg.add_members(Prefix.objects.filter(ip_version=4))
        self.assertIsInstance(sg.members, PrefixQuerySet)
        self.assertQuerysetEqualAndNotEmpty(sg.members, Prefix.objects.filter(ip_version=4))
        # test cumulative construction and alternate code path
        sg.add_members(list(Prefix.objects.filter(ip_version=6)))
        self.assertQuerysetEqualAndNotEmpty(sg.members, Prefix.objects.all())
        self.assertEqual(sg.static_group_associations.count(), Prefix.objects.all().count())
        # test duplicate objects aren't re-added
        sg.add_members(Prefix.objects.all())
        self.assertQuerysetEqualAndNotEmpty(sg.members, Prefix.objects.all())
        self.assertEqual(sg.static_group_associations.count(), Prefix.objects.all().count())
        # test idempotence and alternate code path
        sg.add_members(list(Prefix.objects.all()))
        self.assertQuerysetEqualAndNotEmpty(sg.members, Prefix.objects.all())
        self.assertEqual(sg.static_group_associations.count(), Prefix.objects.all().count())

        # test bulk removal
        sg.remove_members(Prefix.objects.filter(ip_version=4))
        self.assertQuerysetEqualAndNotEmpty(sg.members, Prefix.objects.filter(ip_version=6))
        self.assertEqual(sg.static_group_associations.count(), Prefix.objects.filter(ip_version=6).count())
        # test idempotence and alternate code path
        sg.remove_members(list(Prefix.objects.filter(ip_version=4)))
        self.assertQuerysetEqualAndNotEmpty(sg.members, Prefix.objects.filter(ip_version=6))
        self.assertEqual(sg.static_group_associations.count(), Prefix.objects.filter(ip_version=6).count())
        # test cumulative removal and alternate code path
        sg.remove_members(list(Prefix.objects.filter(ip_version=6)))
        self.assertQuerysetEqual(sg.members, Prefix.objects.none())
        self.assertEqual(sg.static_group_associations.count(), 0)

        # test property setter
        sg.members = Prefix.objects.filter(ip_version=4)
        self.assertQuerysetEqualAndNotEmpty(sg.members, Prefix.objects.filter(ip_version=4))
        sg.members = Prefix.objects.filter(ip_version=6)
        self.assertQuerysetEqualAndNotEmpty(sg.members, Prefix.objects.filter(ip_version=6))
        sg.members = list(Prefix.objects.filter(ip_version=4))
        self.assertQuerysetEqualAndNotEmpty(sg.members, Prefix.objects.filter(ip_version=4))
        sg.members = list(Prefix.objects.filter(ip_version=6))
        self.assertQuerysetEqualAndNotEmpty(sg.members, Prefix.objects.filter(ip_version=6))

        self.assertIsInstance(Prefix.objects.filter(ip_version=6).first().dynamic_groups, QuerySet)
        self.assertIn(sg, list(Prefix.objects.filter(ip_version=6).first().dynamic_groups))

    # TODO negative test that members=, add_members(), remove_members() raise appropriate errors for non-static groups

    def test_members_fail_closed(self):
        """An invalid filter should fail closed, not fail open."""
        self.assertFalse(self.invalid_filter.members.exists())

    def test_members_tree_nodes(self):
        """
        Test `DynamicGroup.members` when filtering on tree nodes like `Location`.
        """
        # Grab some values we'll used to setup the test case.
        device1 = self.devices[0]
        device2 = self.devices[1]
        status = Status.objects.get_for_model(Location).first()

        # Create two LocationTypes (My Region > My Site)
        loc_type_region = LocationType.objects.create(name="My Region")
        loc_type_region.content_types.add(self.device_ct)
        loc_type_site = LocationType.objects.create(name="My Site", parent=loc_type_region)
        loc_type_site.content_types.add(self.device_ct)

        loc_region = Location.objects.create(name="Location A", location_type=loc_type_region, status=status)
        loc_site = Location.objects.create(
            name="Location B", location_type=loc_type_site, parent=loc_region, status=status
        )

        # Add Location A to device1
        device1.location = loc_region
        device1.validated_save()

        # Add Location B to device2
        device2.location = loc_site
        device2.validated_save()

        expected = sorted([device1.name, device2.name])

        # Create the Dynamic Group filtering on Location A
        group = DynamicGroup.objects.create(
            name="Devices Location",
            content_type=self.device_ct,
            filter={"location": ["Location A"]},
        )

        # We are expecting that the group members here should be nested results from any devices
        # that have a Location whose parent is "Location A".
        self.assertEqual(
            sorted(m.name for m in group.members),
            expected,
        )

        # Now also test that an advanced (nested) dynamic group also reports the same number of members.
        parent_group = DynamicGroup.objects.create(
            name="Parent of Devices Location",
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

    def test_has_member(self):
        """Test `DynamicGroup.has_member()`."""
        group = self.first_child
        device1 = self.devices[0]
        device2 = self.devices[1]

        with self.assertApproximateNumQueries(minimum=1, maximum=10):
            group.update_cached_members()
        with self.assertNumQueries(1):
            self.assertTrue(group.has_member(device1))
        with self.assertNumQueries(1):
            self.assertFalse(group.has_member(device2))
        # Test idempotence
        group.update_cached_members()

        # Test fail-closed behavior of an invalid group filter
        group = self.invalid_filter
        with self.assertApproximateNumQueries(minimum=1, maximum=5):
            group.update_cached_members()
        with self.assertNumQueries(1):
            self.assertFalse(group.has_member(device1))
        with self.assertNumQueries(1):
            self.assertFalse(group.has_member(device2))
        # Test idempotence
        group.update_cached_members()

    def test_count(self):
        """Test `DynamicGroup.count`."""
        expected = {
            self.parent.count: 2,
            self.first_child.count: 1,
            self.second_child.count: 1,
            self.third_child.count: 2,
            self.nested_child.count: 2,
            self.no_match_filter.count: 0,
            self.invalid_filter.count: 0,
        }
        for grp, cnt in expected.items():
            self.assertEqual(grp, cnt)

    def test_model(self):
        """Test `DynamicGroup.model`."""
        # New instances should not have a model unless `content_type` is set.
        new_group = DynamicGroup(name="Unsaved Group")
        self.assertIsNone(new_group.model)

        # Setting the content_type will now allow `.model` to be accessed.
        new_group.content_type = self.device_ct
        self.assertIsNotNone(new_group.model)

    def test_object_classes(self):
        """Test `DynamicGroup object_class dynamic population."""
        # New instances should fail to map until `content_type` is set.
        new_group = DynamicGroup(name="Unsaved Group")
        self.assertIsNone(new_group.filterset_class)
        self.assertIsNone(new_group.filterform_class)
        self.assertIsNone(new_group.form_class)

        # Existing groups w/ `content_type` set work as expected.
        group = self.groups[0]
        model = group.content_type.model_class()

        self.assertEqual(group.model, model)
        self.assertEqual(group.filterset_class, DeviceFilterSet)
        self.assertEqual(group.filterform_class, DeviceFilterForm)
        self.assertEqual(group.form_class, DeviceForm)

    def test_get_group_members_url(self):
        """Test `DynamicGroup.get_group_members_url()."""

        # First assert that a basic group with no children, then a group with children, will always
        # link to the members tab on the detail view.
        for group in [self.first_child, self.parent]:
            detail_url = reverse("extras:dynamicgroup", kwargs={"pk": group.pk})
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
        self.assertNotIn("comments", fields)
        self.assertIn("name", fields)
        # See if a CharField is properly converted to a MultiValueCharField In DynamicGroupEditForm.
        self.assertIsInstance(fields["name"], MultiValueCharField)
        self.assertIsInstance(fields["name"].widget, MultiValueCharInput)
        # See if a DynamicModelChoiceField is properly converted to a MultiMatchModelMultipleChoiceField
        self.assertIsInstance(fields["cluster"], MultiMatchModelMultipleChoiceField)
        self.assertIsInstance(fields["cluster"].widget, APISelectMultiple)

    def test_map_filter_fields_with_custom_filter_method(self):
        """
        Test that extension_filters with custom methods can be concatenated into `generate_query_{filter_method}`
        and _map_filter_fields method doesn't brake on string concatenation.
        This is a regression test for issue #6184.
        """
        tenant_content_type = ContentType.objects.get_for_model(Tenant)
        # using Tenant as example app has a custom filter with a custom method.
        group = DynamicGroup(name="tenant", content_type=tenant_content_type)
        self.assertIsInstance(group._map_filter_fields, dict)

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
        expected = ["device-location-1"]
        filterset = group.filterset_class({"has_front_ports": True, "has_rear_ports": True}, Device.objects.all())
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
        group = DynamicGroup(name="pfx", content_type=pfx_content_type)
        filterset = group.filterset_class()  # pylint: disable=not-callable  # should not be None here!
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
        new_group = DynamicGroup(name="Unsaved Group")
        new_filter_fields = new_group.get_filter_fields()
        self.assertEqual(new_filter_fields, {})

        # Existing groups should have actual fields.
        group = self.groups[0]
        filter_fields = group.get_filter_fields()
        self.assertIsInstance(filter_fields, dict)
        self.assertNotEqual(filter_fields, {})
        self.assertNotIn("comments", filter_fields)
        self.assertIn("name", filter_fields)
        self.assertIn("rack", filter_fields)

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
        group1 = self.first_child  # Filter has `location`
        self.assertEqual(group1.get_initial(), group1.filter)
        # Test if MultiValueCharField is properly pre-populated
        group2 = self.groups[6]  # Filter has `name`
        initial = group2.get_initial()
        expected = {"name": ["device-1", "device-2", "device-3"]}
        self.assertEqual(initial, expected)

    def test_set_filter(self):
        """Test `DynamicGroup.set_filter()`."""
        group = self.first_child

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
        new_filter = {"has_interfaces": True}
        group.set_filter(new_filter)
        self.assertEqual(group.filter, new_filter)

        # And a bad input
        bad_filter = {"location": -42}
        with self.assertRaises(ValidationError):
            group.set_filter(bad_filter)

        # Cleanup because we're using class-based fixtures in `setUpTestData()`
        group.refresh_from_db()

    def test_set_filter_on_ipaddress_dynamic_group(self):
        """
        Test `DynamicGroup.set_filter()` for an IPAddress Dynamic Group.
        https://github.com/nautobot/nautobot/issues/6805
        """
        ipaddress_dg = DynamicGroup.objects.create(
            name="IP Address Dynamic Group",
            content_type=ContentType.objects.get_for_model(IPAddress),
            description="IP Address Dynamic Group",
        )
        # Test the fact that set_filter correctly discard an empty PrefixQuerySet
        ipaddress_dg.set_filter({"parent": Prefix.objects.none()})
        self.assertEqual(ipaddress_dg.filter, {})

    def test_add_child(self):
        """Test `DynamicGroup.add_child()`."""
        self.parent.add_child(
            child=self.no_match_filter,
            operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
            weight=10,
        )
        self.assertTrue(self.parent.children.filter(name=self.no_match_filter.name).exists())

    def test_clean_child_validation(self):
        """Test various ways in which adding a child group should fail."""
        parent = self.parent
        parent.filter = {"location": ["Location 1"]}
        parent.group_type = DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER
        child = self.no_match_filter

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
                through_defaults={"operator": DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE, "weight": 10},
            )

    def test_remove_child(self):
        """Test `DynamicGroup.remove_child()`."""
        self.parent.remove_child(self.third_child)
        self.assertFalse(self.parent.children.filter(name=self.third_child.name).exists())

    def test_generate_query_for_filter(self):
        """Test `DynamicGroup._generate_query_for_filter()`."""
        group = self.first_child  # Any filter-based group will do, so why not this one?
        multi_value = ["Location 3"]
        fs = group.filterset_class()
        multi_field = fs.filters["location"]
        multi_query = group._generate_query_for_filter(
            filter_field=multi_field,
            value=multi_value,
        )

        queryset = group.model.objects.all()

        # Assert that both querysets return the same results
        group_qs = queryset.filter(multi_query)
        device_qs = Device.objects.filter(location__name__in=multi_value)
        self.assertQuerysetEqual(group_qs, device_qs, ordered=False)

        # Now do a non-multi-value filter.
        solo_field = fs.filters["has_interfaces"]
        solo_value = False
        solo_query = group._generate_query_for_filter(filter_field=solo_field, value=solo_value)
        solo_qs = queryset.filter(solo_query)
        interface_qs = Device.objects.filter(interfaces__isnull=True)
        self.assertQuerysetEqual(solo_qs, interface_qs, ordered=False)

        # Tags are conjoined in the TagFilterSet, ensure that tags__name is using AND. We know this isn't right
        # since the resulting query actually does tag.name == tag_1 AND tag.name == tag_2, but django_filter does
        # not use Q evaluation for conjoined filters. This function is only used for the display, and the display
        # is good enough to get the point across.
        tags_query = group._generate_query_for_filter(filter_field=fs.filters["tags"], value=["tag_1", "tag_2"])
        self.assertEqual(str(tags_query), "(AND: ('tags__name', 'tag_1'), ('tags__name', 'tag_2'))")

        # Test that a nested field_name w/ `generate_query` works as expected. This is explicitly to
        # test a regression w/ nested name-related values such as `DeviceFilterSet.manufacturer` which
        # filters on `device_type__manufacturer`.
        manufacturer = Manufacturer.objects.first()
        nested_value = [manufacturer.name]
        group.set_filter({"manufacturer": nested_value})
        group.validated_save()

        # We are making sure the filterset generated from the name as an argument results in the same
        # filtered queryset, and more importantly that the nested filter expression `device_type__manufacturer`
        # is automatically used to get the related model name without failing.
        nested_query = group._generate_query_for_filter(filter_field=fs.filters["manufacturer"], value=nested_value)
        nested_qs = queryset.filter(nested_query)
        parent_qs = Device.objects.filter(device_type__manufacturer__name__in=nested_value)
        self.assertQuerysetEqual(nested_qs, parent_qs, ordered=False)

    def test_generate_filter_based_query(self):
        """Test `DynamicGroup._generate_filter_based_query()`."""
        # A group with a filter set will result in a useful Q object.
        child_q = self.second_child._generate_filter_based_query()
        lookup_kwargs = dict(child_q.children)  # {name: value}

        # Assert that both querysets return the same results
        group_qs = self.second_child.members
        device_qs = Device.objects.filter(**lookup_kwargs)
        self.assertQuerysetEqual(group_qs, device_qs, ordered=False)

    def test_get_group_queryset(self):
        """Test `DynamicGroup._get_group_queryset()`."""
        group = self.parent
        group_qs = group._get_group_queryset()

        process_query = group.generate_query()
        base_qs = Device.objects.all()
        process_qs = base_qs.filter(process_query)

        self.assertQuerysetEqual(group_qs, process_qs, ordered=False)

    def test_get_ancestors(self):
        """Test `DynamicGroup.get_ancestors()`."""
        expected = ["Third Child", "Parent"]
        ancestors = [a.name for a in self.nested_child.get_ancestors()]
        self.assertEqual(ancestors, expected)

    def test_get_descendants(self):
        """Test `DynamicGroup.get_descendants()`."""
        expected = ["First Child", "Second Child", "Third Child", "Nested Child"]
        descendants = [d.name for d in self.parent.get_descendants()]
        self.assertEqual(descendants, expected)

    def test_get_siblings(self):
        """Test `DynamicGroup.get_siblings()`."""
        expected = ["First Child", "Second Child"]
        siblings = sorted(s.name for s in self.third_child.get_siblings())
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
        expected = {"First Child": 1, "Second Child": 1, "Third Child": 1, "Nested Child": 2}
        seen = {d.name: d.depth for d in d_flat}
        self.assertEqual(seen, expected)

        # Parent should not be here; nested-child should.
        self.assertNotIn(self.parent, d_flat)
        self.assertIn(self.nested_child, d_flat)

    def test_flatten_ancestors_tree(self):
        """Test `DynamicGroup.flatten_ancestors_tree()`."""
        # Assert ancestors are deterministic
        a_tree = self.nested_child.ancestors_tree()
        a_flat = self.nested_child.flatten_ancestors_tree(a_tree)
        expected = {"Third Child": 1, "Parent": 2}
        seen = {a.name: a.depth for a in a_flat}
        self.assertEqual(seen, expected)

        # Nested-child should not be here; parent should.
        self.assertNotIn(self.nested_child, a_flat)
        self.assertIn(self.parent, a_flat)

    def test_membership_tree(self):
        """Test `DynamicGroup.membership_tree()`."""
        group = self.parent

        d_tree = group.flatten_descendants_tree(group.descendants_tree())
        m_tree = group.membership_tree()

        d_groups = [d.name for d in d_tree]
        m_groups = [m.group.name for m in m_tree]

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
        group_qs = Device.objects.filter(group_query)

        # <DynamicGroupMembership: First Child: intersection (10)>
        # <DynamicGroupMembership: Second Child: union (20)>
        # <DynamicGroupMembership: Third Child: difference (30)>
        group_members = group.dynamic_group_memberships.all()

        # Manually iterate over the groups to assert the same result that the queryset should have,
        # igoring weight since each set of members are already ordered by weight when queried from
        # the database.
        child_set = set(Device.objects.all())
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
        expected = ["device-location-3"]
        self.assertEqual(sorted(group_qs.values_list("name", flat=True)), expected)

    def test_delete(self):
        """Test `DynamicGroup(instance).delete()`."""
        # Has parents
        with self.assertRaises(ProtectedError):
            self.nested_child.delete()

        # Clear the deeply nested child's parents then delete it!
        self.nested_child.parents.clear()
        self.nested_child.delete()

    def test_filter_relationships(self):
        """Test that relationships can be used in filters."""
        prefix_ct = ContentType.objects.get_for_model(Prefix)

        device = self.devices[0]
        prefix = Prefix.objects.first()
        self.assertIsNotNone(prefix)

        relationship = Relationship(
            label="Device to Prefix",
            key="device_to_prefix",
            source_type=self.device_ct,
            source_label="My Prefixes",
            source_filter=None,
            destination_type=prefix_ct,
            destination_label="My Devices",
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        relationship.validated_save()

        ra = RelationshipAssociation(
            relationship=relationship,
            source=device,
            destination=prefix,
        )
        ra.validated_save()

        dg = DynamicGroup(
            name="relationships",
            description="I filter on relationships.",
            filter={"cr_device_to_prefix__destination": [prefix.pk]},
            content_type=self.device_ct,
        )
        dg.validated_save()

        # These should be the same length.
        self.assertEqual(dg.count, 1)

        # And have the same members...
        self.assertIn(device, dg.members)
        expected = [str(device)]
        self.assertEqual(sorted(dg.members.values_list("name", flat=True)), expected)

    def test_filter_custom_fields(self):
        """Test that relationships can be used in filters."""

        device = self.devices[0]

        cf = CustomField.objects.create(
            label="Favorite Food",
            type=CustomFieldTypeChoices.TYPE_TEXT,
            filter_logic=CustomFieldFilterLogicChoices.FILTER_LOOSE,
        )
        cf.content_types.add(self.device_ct)

        device._custom_field_data = {"favorite_food": "bacon"}
        device.validated_save()
        device.refresh_from_db()

        dg = DynamicGroup(
            name="custom_fields",
            description="I filter on custom fields.",
            filter={"cf_favorite_food": "bacon"},
            content_type=self.device_ct,
        )
        dg.validated_save()

        # These should be the same length.
        self.assertEqual(dg.count, 1)

        # And have the same members...
        self.assertIn(device, dg.members)
        expected = [str(device)]
        self.assertEqual(sorted(dg.members.values_list("name", flat=True)), expected)

    def test_filter_search(self):
        """Test that search (`q` filter) can be used in filters."""

        # Rename the device to explicitly match on search.
        device = self.devices[0]
        device.name = "pizza-party-machine"
        device.save()

        dg = DynamicGroup(
            name="custom_fields",
            description="I filter on the q field",
            filter={"q": "party"},  # Let's party! 🎉
            content_type=self.device_ct,
        )
        dg.validated_save()

        # These should be the same length.
        self.assertEqual(dg.count, 1)

        # And have the same members...
        self.assertIn(device, dg.members)
        expected = [str(device)]
        self.assertEqual(sorted(dg.members.values_list("name", flat=True)), expected)

    def test_group_overloaded_filter_form_field(self):
        """FilterForm fields can overload how they pass in the values."""

        prefix_ct = ContentType.objects.get_for_model(Prefix)

        a_tenant = Tenant.objects.first()

        this_dg = DynamicGroup(
            name="Prefix Group",
            description="A group of prefixes with a specific Tenant name.",
            filter={},
            content_type=prefix_ct,
        )
        this_dg.validated_save()

        this_dg.set_filter({"example_app_prefix_tenant_name": [a_tenant]})
        this_dg.validated_save()

    def test_unapplied_tags_can_be_added_to_dynamic_group_filters(self):
        """
        Test that tags without being applied to any member instances can still be added as filters on DynamicGroups
        """
        dg = self.first_child
        unapplied_tag = Tag.objects.create(name="Unapplied Tag")
        unapplied_tag.content_types.set([ContentType.objects.get_for_model(Device)])
        unapplied_tag.save()
        dg.filter["tags"] = [unapplied_tag.pk]
        dg.validated_save()

    def test_member_caching_output(self):
        group = self.first_child

        updated_members = group.update_cached_members()
        self.assertEqual(sorted(list(group.members)), sorted(list(updated_members)))
        self.assertEqual(sorted(list(group.members)), sorted(list(group.members_cached)))


class DynamicGroupMembershipModelTest(DynamicGroupTestBase):  # TODO: BaseModelTestCase mixin?
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
                group=self.no_match_filter,
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


class DynamicGroupMixinModelTest(DynamicGroupTestBase):
    """DynamicGroupMixin model tests."""

    def test_dynamic_groups(self):
        with self.assertApproximateNumQueries(minimum=len(self.groups), maximum=10 * len(self.groups)):
            for group in self.groups:
                group.update_cached_members()
        with self.assertNumQueries(1):
            qs = self.devices[0].dynamic_groups
            list(qs)
        self.assertQuerysetEqualAndNotEmpty(qs, [self.first_child, self.third_child, self.nested_child], ordered=False)

    def test_dynamic_groups_cached(self):
        for group in self.groups:
            group.update_cached_members()
        with self.assertNumQueries(1):
            qs = self.devices[0].dynamic_groups_cached
            list(qs)
        self.assertQuerysetEqualAndNotEmpty(qs, [self.first_child, self.third_child, self.nested_child], ordered=False)

    def test_dynamic_groups_list(self):
        for group in self.groups:
            group.update_cached_members()
        with self.assertNumQueries(1):
            groups = self.devices[0].dynamic_groups_list
        self.assertEqual(set(groups), set([self.first_child, self.third_child, self.nested_child]))

    def test_dynamic_groups_list_cached(self):
        for group in self.groups:
            group.update_cached_members()
        with self.assertNumQueries(1):
            groups = self.devices[0].dynamic_groups_list_cached
        self.assertEqual(set(groups), set([self.first_child, self.third_child, self.nested_child]))


class DynamicGroupFilterTest(DynamicGroupTestBase, FilterTestCases.FilterTestCase):
    """DynamicGroup instance filterset tests."""

    queryset = DynamicGroup.objects.all()
    filterset = DynamicGroupFilterSet
    generic_filter_tests = (
        ["name"],
        ["description"],
        ["group_type"],
        ["tenant", "tenant__name"],
    )

    def test_content_type(self):
        params = {"content_type": ["dcim.device", "virtualization.virtualmachine"]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            DynamicGroup.objects.filter(
                content_type__in=[
                    ContentType.objects.get_for_model(Device),
                    ContentType.objects.get_for_model(VirtualMachine),
                ]
            ),
        )

    def test_search(self):
        tests = {
            "Devices No Filter": 0,  # name
            "Invalid Filter": 1,  # name
            "A group with a non-matching filter": 1,  # description
        }
        for value, cnt in tests.items():
            params = {"q": value}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), cnt)

        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"q": "dcim"}).qs,
            DynamicGroup.objects.filter(content_type__app_label="dcim"),
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"q": "device"}).qs,
            DynamicGroup.objects.filter(content_type__model__icontains="device"),
        )


class DynamicGroupMembershipFilterTest(DynamicGroupTestBase, FilterTestCases.FilterTestCase):
    """DynamicGroupMembership instance filterset tests."""

    queryset = DynamicGroupMembership.objects.all()
    filterset = DynamicGroupMembershipFilterSet
    generic_filter_tests = (
        ["operator"],
        ["weight"],
        ["group", "group__id"],
        ["group", "group__name"],
        # ["parent_group", "parent_group__id"],  # would work but we only have 2 valid parent groups
        # ["parent_group", "parent_group__name"],  # would work but we only have 2 valid parent groups
    )
    exclude_q_filter_predicates = ["operator"]

    def test_parent_group(self):
        parent_group_pk = self.queryset.first().parent_group.pk  # expecting 3
        parent_group_name = self.queryset.last().parent_group.name  # expecting 1
        params = {"parent_group": [parent_group_pk, parent_group_name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_search(self):
        tests = {
            "intersection": 2,  # operator
            "First Child": 1,  # group__name
            "Parent": 3,  # parent_group__name,
            "Third Child": 2,  # parent_group__name OR group__name,
        }
        for value, cnt in tests.items():
            params = {"q": value}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), cnt)


class DynamicGroupFixupTestCase(TestCase):
    """Check for the correct functioning of the fixup_dynamic_group_group_types() data migration helper function."""

    def test_fixup_dynamic_group_group_types(self):
        device_ct = ContentType.objects.get_for_model(Device)

        good_grandparent_group = DynamicGroup.objects.create(
            name="Good Grandparent",
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET,
            content_type=device_ct,
        )
        bad_grandparent_group = DynamicGroup.objects.create(
            name="Bad Grandparent",
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER,  # wrong, but possible due to #6329
            content_type=device_ct,
        )
        good_parent_group = DynamicGroup.objects.create(
            name="Good Parent",
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET,
            content_type=device_ct,
        )
        bad_parent_group = DynamicGroup.objects.create(
            name="Bad Parent",
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER,  # wrong, #6329 again
            content_type=device_ct,
        )
        good_child_group = DynamicGroup.objects.create(
            name="Good Child",
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER,
            content_type=device_ct,
            filter={"status": [Status.objects.get_for_model(Device).first().name]},
        )
        bad_child_group = DynamicGroup.objects.create(
            name="Bad Child",
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET,  # wrong, #6329 again
            content_type=device_ct,
            filter={"status": [Status.objects.get_for_model(Device).first().name]},
        )

        DynamicGroupMembership.objects.create(
            parent_group=good_grandparent_group,
            group=good_parent_group,
            weight=10,
            operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
        )
        DynamicGroupMembership.objects.create(
            parent_group=bad_grandparent_group,
            group=bad_parent_group,
            weight=10,
            operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
        )
        DynamicGroupMembership.objects.create(
            parent_group=good_parent_group,
            group=good_child_group,
            weight=10,
            operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
        )
        DynamicGroupMembership.objects.create(
            parent_group=bad_parent_group,
            group=bad_child_group,
            weight=10,
            operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
        )

        good_standalone_group_1 = DynamicGroup.objects.create(
            name="Good Standalone Group 1",
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER,
            content_type=device_ct,
            # empty filter - this is OK!
        )
        good_standalone_group_2 = DynamicGroup.objects.create(
            name="Good Standalone Group 2",
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET,
            content_type=device_ct,
        )
        bad_standalone_group = DynamicGroup.objects.create(
            name="Bad Standalone Group",
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET,
            content_type=device_ct,
            filter={"status": [Status.objects.get_for_model(Device).first().name]},
        )

        # DynamicGroupMembership.save() will actually auto-fixup the type on bad_parent_group and bad_grandparent_group.
        # Make them wrong again:
        bad_grandparent_group.group_type = DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER
        bad_grandparent_group.save()
        bad_parent_group.group_type = DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER
        bad_parent_group.save()

        count_1, count_2 = fixup_dynamic_group_group_types(apps)

        self.assertEqual(count_1, 2)  # bad_grandparent_group, bad_parent_group
        self.assertEqual(count_2, 2)  # bad_child_group, bad_standalone_group

        good_grandparent_group.refresh_from_db()
        self.assertEqual(good_grandparent_group.group_type, DynamicGroupTypeChoices.TYPE_DYNAMIC_SET)  # unchanged
        bad_grandparent_group.refresh_from_db()
        self.assertEqual(bad_grandparent_group.group_type, DynamicGroupTypeChoices.TYPE_DYNAMIC_SET)  # fixed
        good_parent_group.refresh_from_db()
        self.assertEqual(good_parent_group.group_type, DynamicGroupTypeChoices.TYPE_DYNAMIC_SET)  # unchanged
        bad_parent_group.refresh_from_db()
        self.assertEqual(bad_parent_group.group_type, DynamicGroupTypeChoices.TYPE_DYNAMIC_SET)  # fixed
        good_child_group.refresh_from_db()
        self.assertEqual(good_child_group.group_type, DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER)  # unchanged
        bad_child_group.refresh_from_db()
        self.assertEqual(bad_child_group.group_type, DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER)  # fixed
        good_standalone_group_1.refresh_from_db()
        self.assertEqual(good_standalone_group_1.group_type, DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER)  # unchanged
        good_standalone_group_2.refresh_from_db()
        self.assertEqual(good_standalone_group_2.group_type, DynamicGroupTypeChoices.TYPE_DYNAMIC_SET)  # unchanged
        bad_standalone_group.refresh_from_db()
        self.assertEqual(bad_standalone_group.group_type, DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER)  # fixed
