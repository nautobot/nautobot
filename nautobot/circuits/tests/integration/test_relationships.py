import uuid

from django.contrib.contenttypes.models import ContentType

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import PowerPanel, Location, LocationType
from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import Relationship, RelationshipAssociation, Status


class CircuitRelationshipsTestCase(SeleniumTestCase):
    """
    Integration test to check relationships show on a circuit termination in the UI
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)
        location_type = LocationType.objects.get(name="Campus")
        location_ct = ContentType.objects.get_for_model(Location)
        circuit_termination_ct = ContentType.objects.get_for_model(CircuitTermination)
        provider_ct = ContentType.objects.get_for_model(Provider)
        power_panel_ct = ContentType.objects.get_for_model(PowerPanel)
        circuit_status = Status.objects.get_for_model(Circuit).first()
        location_status = Status.objects.get_for_model(Location).first()
        provider1 = Provider.objects.create(
            name="Test Provider 1",
        )
        provider2 = Provider.objects.create(
            name="Test Provider 2",
        )
        circuit_type = CircuitType.objects.create(
            name="Test Circuit Type",
        )
        circuit = Circuit.objects.create(
            provider=provider1,
            cid="1234",
            circuit_type=circuit_type,
            status=circuit_status,
        )
        location = Location.objects.create(
            name="Test Location",
            status=location_status,
            location_type=location_type,
        )
        circuit_termination = CircuitTermination.objects.create(
            circuit=circuit,
            term_side="A",
            location=location,
        )
        power_panel = PowerPanel.objects.create(
            location=location,
            name="Test Power Panel",
        )
        m2m = Relationship.objects.create(
            label="Termination 2 Provider m2m",
            key="termination_2_provider_m2m",
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
            label="Termination 2 Location o2m",
            key="termination_2_provider_o2m",
            source_type=circuit_termination_ct,
            destination_type=location_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        RelationshipAssociation.objects.create(
            relationship=o2m,
            source=circuit_termination,
            destination=location,
        )
        o2o = Relationship.objects.create(
            label="Termination 2 Power Panel o2o",
            key="termination_2_power_panel_o2o",
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
            label="Termination 2 Nonexistent",
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
        self.browser.links.find_by_partial_text("Circuits").click()

        # Click Circuits link
        self.browser.links.find_by_partial_text("Circuits")[1].click()

        # Click on the circuit link (circuit created in setUp)
        self.browser.links.find_by_partial_text("1234").click()

        # Verify custom relationships are visible
        self.assertTrue(self.browser.is_text_present("Power Panel"))
        self.assertTrue(self.browser.is_text_present("2 providers"))
        self.assertTrue(self.browser.is_text_present("1 location"))
        self.assertTrue(self.browser.is_text_present("1 nonexistentmodel(s)"))
