from unittest import skip

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from nautobot.dcim.models import Site, Region
from nautobot.extras.models import DynamicGroup
from nautobot.utilities.testing import TestCase


@skip("incomplete")
class DynamicGroupTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):

        # FIXME(jathan): Do this all with Device/VirtualMachine, not Site/Region.
        cls.site_ct = ContentType.objects.get_for_model(Site)
        cls.region_ct = ContentType.objects.get_for_model(Region)
        cls.dg_ct = ContentType.objects.get_for_model(DynamicGroup)

        cls.sites = [
            Site.objects.create(name="Site A", slug="site-a"),
            Site.objects.create(name="Site B", slug="site-b"),
            Site.objects.create(name="Site C", slug="site-c"),
        ]

        cls.regions = [
            Region.objects.create(name="Region A", slug="region-a"),
            Region.objects.create(name="Region B", slug="region-b"),
            Region.objects.create(name="Region C", slug="region-c"),
        ]

        cls.groups = [
            DynamicGroup.objects.create(
                name="Sites A/B", slug="sites-a-b", filter={"sites": ["site-a", "site-b"]}, content_type=cls.site_ct
            ),
            DynamicGroup.objects.create(
                name="Regions A/B",
                slug="regions-a-b",
                filter={"regions": ["region-a", "region-b"]},
                content_type=cls.region_ct,
            ),
        ]


class DynamicGroupTest(DynamicGroupTestBase):
    def test_content_type_is_immutable(self):
        """Test that `content_type` is immutable after create."""
        dg = self.groups[0]  # Site DG
        with self.assertRaises(ValidationError):
            dg.content_type = self.region_ct
            dg.validated_save()

    def test_clean_filter_not_dict(self):
        """Test that `filter` validation works."""
        dg = self.groups[0]  # Site DG
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
        with self.assertRaises(ValidationError):
            dg.filter = {"slug": -42}
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
