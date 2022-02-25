from unittest import skip

from django.contrib.contenttypes.models import ContentType
# from django.core.exceptions import ValidationError

from nautobot.dcim.models import Site, Region
from nautobot.extras.models import DynamicGroup
from nautobot.utilities.testing import TestCase


@skip("incomplete")
class DynamicGroupBaseTest(TestCase):
    def setUp(self):

        self.site_ct = ContentType.objects.get_for_model(Site)
        self.region_ct = ContentType.objects.get_for_model(Region)
        self.dg_ct = ContentType.objects.get_for_model(DynamicGroup)

        self.sites = [
            Site.objects.create(name="Site A", slug="site-a"),
            Site.objects.create(name="Site B", slug="site-b"),
            Site.objects.create(name="Site C", slug="site-c"),
            Site.objects.create(name="Site D", slug="site-d"),
            Site.objects.create(name="Site E", slug="site-e"),
        ]

        self.regions = [
            Region.objects.create(name="Region A", slug="region-a"),
            Region.objects.create(name="Region B", slug="region-a"),
            Region.objects.create(name="Region C", slug="region-a"),
        ]


"""
class DynamicGroupTest(DynamicGroupBaseTest):
    def test_clean_filter_not_dict(self):
        pass

    def test_clean_filter_not_valid(self):
        pass

    def test_clean_valid(self):
        pass

"""


"""
# Test DynamicGroup stuff
- content_type is immutable after create

# Test DynamicGroupMap stuff

# Test DynamicGroupForm stuff

# Test filtering
"""
