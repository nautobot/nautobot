from unittest import skip

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from nautobot.extras.models import DynamicGroup, Status
from nautobot.utilities.testing import TestCase


# @skip("incomplete")
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
            model="evice Type 1",
            slug="evice-type-1",
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
            DynamicGroup.objects.create(
                name="Devices Sites 1/2",
                slug="devices-sites-1-2",
                filter={"site": ["site-1", "site-2"]},
                content_type=cls.device_ct,
            ),
            DynamicGroup.objects.create(
                name="Devices Site 3",
                slug="devices-site-3",
                filter={"site": ["site-3"]},
                content_type=cls.device_ct,
            ),
        ]


class DynamicGroupTest(DynamicGroupTestBase):
    def test_content_type_is_immutable(self):
        """Test that `content_type` is immutable after create."""
        dg = self.groups[0]
        with self.assertRaises(ValidationError):
            dg.content_type = self.dynamicgroup_ct
            dg.validated_save()

    def test_clean_filter_not_dict(self):
        """Test that `filter` validation works."""
        dg = self.groups[0]
        with self.assertRaises(ValidationError):
            dg.filter = None
            dg.validated_save()

        with self.assertRaises(ValidationError):
            dg.filter = []
            dg.validated_save()

    # FIXME(jathan): Implement validation of the filter value "somehow"? using a
    # Form and `set_filter()`.
    def test_clean_filter_not_valid(self):
        dg = self.groups[0]  # Site DG
        # breakpoint()
        with self.assertRaises(ValidationError):
            dg.filter = {"site": -42}
            dg.validated_save()

    @skip
    def test_clean_valid(self):
        pass


"""
# DynamicGroup model
- content_type is immutable after create
- Test `DynamicGroup.objects.get_for_object()`
- Test that group membership vibes with member reverse lookups
- `DynamicGroup.get_queryset(**kwargs)`
    - Including `flat=True` as is used inside of `get_for_object()`
- Test `.members`
- Test `count`
- Test `map`
- Test `get_group_mmbers_url()`
- Test `get_filter_fields()`
- Test `set_filter()` w/ form (also do the inverse below in form tests)
- Test `get_initial()`
- Test `generate_filter_form()`
- Test `clean()` validation

# DynamicGroupMap class

- Test `dynamicgroup_map_factory()`
- `BaseDynamicGroupMap` tests:
    - Test `base_url`
    - Test `fields`
    - Test `get_queryset()`
    - Test `urlencode`

# Test Forms
- `DynamicGroupForm`
    - Test append_filters
    - Test changelog count



# Test `FilterForm` generation
- Test that `DynamicGroup.set_filter()` results in valid input for `FilterSet`

# Test Filters
- Test `DynamicGroupFilterSet`
  - test_id
  - test_name
  - test_slug
  - test_description
  - test_content_type
  - test search (q)
    - name
    - slug
    - description
    - content_type__app_label
    - content_type__model

# Test API
- Test common views
- Test `members` endpoint

"""
