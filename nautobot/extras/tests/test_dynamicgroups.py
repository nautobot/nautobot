from unittest import skip

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from nautobot.dcim.models import Site, Region
from nautobot.extras.models import DynamicGroup
from nautobot.utilities.testing import TestCase


# @skip("incomplete")
class DynamicGroupTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):

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
    # Form and `save_filters()`??
    @skip
    def test_clean_filter_not_valid(self):
        dg = self.groups[0]  # Site DG
        with self.assertRaises(ValidationError):
           dg.filter = {"fake": ["not real"]}
           dg.validated_save()

    @skip
    def test_clean_valid(self):
        pass


"""
# Test DynamicGroup stuff
- content_type is immutable after create

# Test DynamicGroupMap stuff

# Test DynamicGroupForm stuff

# Test filtering
"""
