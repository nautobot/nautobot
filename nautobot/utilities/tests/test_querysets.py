from django.test.utils import override_settings

from nautobot.dcim.factory import SiteFactory
from nautobot.dcim.models import Site
from nautobot.tenancy.models import Tenant
from nautobot.utilities.testing import TestCase


class QuerySetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        sites = SiteFactory.create_batch(2, has_region=True, has_tenant=True)
        cls.queryset = Site.objects.filter(pk__in=[site.pk for site in sites])

    def test_invalid_with_related(self):
        """Assert that calling with_related with non-relationship field on a queryset fails."""
        with self.assertRaises(ValueError):
            Site.objects.with_related("name").all()

    @override_settings(DEBUG=True)
    def test_foreign_key_with_related(self):
        """Test using with_related on ForeignKey relationships."""
        # Filter to only the sites we created ourselves so we can be sure they have tenants and regions
        sites = self.queryset.with_related("tenant", "region")
        # One query is expected here instead of the five that the default behavior would take.
        with self.assertNumQueries(1):
            # Access the foreign keys to ensure they are loaded from the DB
            for site in sites:
                _ = site.tenant.name
                _ = site.region.name

    @override_settings(DEBUG=True)
    def test_many_to_one_with_related(self):
        """Test using with_related on ForeignKey relationships."""
        # Get a tenant for which we know it has a site
        tenant_pk = self.queryset.first().tenant.pk
        # Two queries are expected here instead of the three queries the default behavior would take.
        with self.assertNumQueries(2):
            tenant = Tenant.objects.with_related("sites").get(pk=tenant_pk)
            # Access the relation to ensure it is loaded from the DB
            _ = tenant.sites.first().name
