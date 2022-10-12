import uuid

from django.contrib.contenttypes.models import ContentType

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.dcim.models import PowerPanel, Site
from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import Relationship, RelationshipAssociation, Status
from nautobot.utilities.testing.integration import SeleniumTestCase


class CircuitRelationshipsTestCase(SeleniumTestCase):
    """
    Integration test to check relationships show on a circuit termination in the UI
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)
        site_ct = ContentType.objects.get_for_model(Site)
        circuit_termination_ct = ContentType.objects.get_for_model(CircuitTermination)
        provider_ct = ContentType.objects.get_for_model(Provider)
        power_panel_ct = ContentType.objects.get_for_model(PowerPanel)
        active_circuit_status = Status.objects.get_for_model(Circuit).get(slug="active")
        active_site_status = Status.objects.get_for_model(Site).get(slug="active")
        provider1 = Provider.objects.create(
            name="Test Provider 1",
            slug="test-provider-1",
        )
        provider2 = Provider.objects.create(
            name="Test Provider 2",
            slug="test-provider-2",
        )
        circuit_type = CircuitType.objects.create(
            name="Test Circuit Type",
            slug="test-circuit-type",
        )
        circuit = Circuit.objects.create(
            provider=provider1,
            cid="1234",
            type=circuit_type,
            status=active_circuit_status,
        )
        site = Site.objects.create(
            name="Test Site",
            slug="test-site",
            status=active_site_status,
        )
        circuit_termination = CircuitTermination.objects.create(
            circuit=circuit,
            term_side="A",
            site=site,
        )
        power_panel = PowerPanel.objects.create(
            site=site,
            name="Test Power Panel",
        )
        m2m = Relationship.objects.create(
            name="Termination 2 Provider m2m",
            slug="termination-2-provider-m2m",
            source_type=circuit_termination_ct,
            destination_type=provider_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        RelationshipAssociation.objects.create(
            relationship=m2m,
            source=circuit_termination,
            destination=provider1,
        )
        RelationshipAssociation.objects.create(
            relationship=m2m,
            source=circuit_termination,
            destination=provider2,
        )
        o2m = Relationship.objects.create(
            name="Termination 2 Site o2m",
            slug="termination-2-provider-o2m",
            source_type=circuit_termination_ct,
            destination_type=site_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        RelationshipAssociation.objects.create(
            relationship=o2m,
            source=circuit_termination,
            destination=site,
        )
        o2o = Relationship.objects.create(
            name="Termination 2 Power Panel o2o",
            slug="termination-2-power-panel-o2o",
            source_type=circuit_termination_ct,
            destination_type=power_panel_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        RelationshipAssociation.objects.create(
            relationship=o2o,
            source=circuit_termination,
            destination=power_panel,
        )
        # https://github.com/nautobot/nautobot/issues/2077
        fake_ct = ContentType.objects.create(app_label="nonexistent", model="nonexistentmodel")
        bad_relation = Relationship.objects.create(
            name="Termination 2 Nonexistent",
            source_type=circuit_termination_ct,
            destination_type=fake_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        RelationshipAssociation.objects.create(
            relationship=bad_relation,
            source=circuit_termination,
            destination_type=fake_ct,
            destination_id=uuid.uuid4(),
        )

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_relationships_are_visible(self):
        """
        Navigate to the circuit created in setUp() and check that the relationships are showing on the page
        """
        self.browser.visit(self.live_server_url)

        # Click Circuits dropdown button
        self.browser.links.find_by_partial_text("Circuits")[0].click()

        # Click Circuits link
        self.browser.links.find_by_partial_text("Circuits")[1].click()

        # Click on the circuit link (circuit created in setUp)
        self.browser.links.find_by_partial_text("1234").click()

        # Verify custom relationships are visible
        self.assertTrue(self.browser.is_text_present("Power Panel"))
        self.assertTrue(self.browser.is_text_present("2 providers"))
        self.assertTrue(self.browser.is_text_present("1 site"))
        self.assertTrue(self.browser.is_text_present("1 nonexistentmodel(s)"))
