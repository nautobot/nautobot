from django.test.utils import override_settings

from nautobot.dcim.models import Site, Region
from nautobot.tenancy.models import Tenant
from nautobot.utilities.testing import TestCase


class QuerySetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_tenant_names = ["Test-Tenant-1", "Test-Tenant-2"]
        cls.test_region_name = "Test-Region-1"
        cls.tenant_1 = Tenant.objects.create(name=cls.test_tenant_names[0])
        cls.tenant_2 = Tenant.objects.create(name=cls.test_tenant_names[1])
        cls.region = Region.objects.create(name=cls.test_region_name)
        cls.site_1 = Site.objects.create(name="Test-Site-1", tenant=cls.tenant_1, region=cls.region)
        cls.site_2 = Site.objects.create(name="Test-Site-2", tenant=cls.tenant_2, region=cls.region)

    def test_invalid_with_related(self):
        """Assert that calling with_related with non-relationship field on a queryset fails."""
        with self.assertRaises(ValueError):
            Site.objects.with_related("name").all()

    @override_settings(DEBUG=True)
    def test_foreign_key_with_related(self):
        """Test using with_related on ForeignKey relationships."""
        sites = Site.objects.with_related("tenant", "region").all()
        # One query is expected here instead of the five that the default behavior would take.
        with self.assertNumQueries(1):
            # Access the foreign keys to ensure they are loaded from the DB
            for index, site in enumerate(sites):
                self.assertEqual(site.tenant.name, self.test_tenant_names[index])
                self.assertEqual(site.region.name, self.test_region_name)

    @override_settings(DEBUG=True)
    def test_many_to_one_with_related(self):
        """Test using with_related on ForeignKey relationships."""
        tenants = Tenant.objects.with_related("sites").all()
        # Two queries are expected here instead of the three queries the default behavior would take.
        with self.assertNumQueries(2):
            # Access the relation to ensure it is loaded from the DB
            for tenant in tenants:
                self.assertIsNotNone(tenant.sites.first().name)
