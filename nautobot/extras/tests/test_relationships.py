import logging
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html

from nautobot.circuits.models import CircuitType
from nautobot.dcim.models import Device, Platform, Rack, Site
from nautobot.dcim.tables import SiteTable
from nautobot.dcim.tests.test_views import create_test_device
from nautobot.ipam.models import VLAN
from nautobot.extras.choices import RelationshipRequiredSideChoices, RelationshipSideChoices, RelationshipTypeChoices
from nautobot.extras.models import Relationship, RelationshipAssociation, Status
from nautobot.utilities.tables import RelationshipColumn
from nautobot.utilities.testing import TestCase
from nautobot.utilities.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
)
from nautobot.utilities.utils import get_route_for_model


class RelationshipBaseTest(TestCase):
    def setUp(self):

        self.site_ct = ContentType.objects.get_for_model(Site)
        self.rack_ct = ContentType.objects.get_for_model(Rack)
        self.vlan_ct = ContentType.objects.get_for_model(VLAN)

        self.sites = Site.objects.all()[:5]

        self.racks = [
            Rack.objects.create(name="Rack A", site=self.sites[0]),
            Rack.objects.create(name="Rack B", site=self.sites[1]),
            Rack.objects.create(name="Rack C", site=self.sites[2]),
        ]

        self.vlans = [
            VLAN.objects.create(name="VLAN A", vid=100, site=self.sites[0]),
            VLAN.objects.create(name="VLAN B", vid=100, site=self.sites[1]),
            VLAN.objects.create(name="VLAN C", vid=100, site=self.sites[2]),
        ]

        self.m2m_1 = Relationship(
            name="Vlan to Rack",
            slug="vlan-rack",
            source_type=self.rack_ct,
            source_label="My Vlans",
            source_filter={"site": [self.sites[0].slug, self.sites[1].slug, self.sites[2].slug]},
            destination_type=self.vlan_ct,
            destination_label="My Racks",
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        self.m2m_1.validated_save()

        self.m2m_2 = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.rack_ct,
            destination_type=self.vlan_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        self.m2m_2.validated_save()

        self.o2m_1 = Relationship(
            name="generic site to vlan",
            slug="site-vlan",
            source_type=self.site_ct,
            destination_type=self.vlan_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        self.o2m_1.validated_save()

        self.o2o_1 = Relationship(
            name="Primary Rack per Site",
            slug="primary-rack-site",
            source_type=self.rack_ct,
            source_hidden=True,
            destination_type=self.site_ct,
            destination_label="Primary Rack",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        self.o2o_1.validated_save()

        # Relationships between objects of the same type

        self.o2o_2 = Relationship(
            name="Alphabetical Sites",
            slug="alphabetical-sites",
            source_type=self.site_ct,
            source_label="Alphabetically Prior",
            destination_type=self.site_ct,
            destination_label="Alphabetically Subsequent",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        self.o2o_2.validated_save()

        self.o2os_1 = Relationship(
            name="Redundant Rack",
            slug="redundant-rack",
            source_type=self.rack_ct,
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
        )
        self.o2os_1.validated_save()

        self.m2ms_1 = Relationship(
            name="Related Sites",
            slug="related-sites",
            source_type=self.site_ct,
            destination_type=self.site_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
        )
        self.m2ms_1.validated_save()

        # Relationships involving a content type that doesn't actually have a backing model.
        # This can occur in practice if, for example, a relationship is defined for a plugin-defined model,
        # then the plugin is subsequently uninstalled or deactivated.
        self.invalid_ct = ContentType.objects.create(app_label="nonexistent", model="nosuchmodel")

        # Don't use validated_save() on these as it will fail due to the invalid content-type
        self.invalid_relationships = [
            Relationship.objects.create(
                name="Invalid Relationship 1",
                slug="invalid-relationship-1",
                source_type=self.site_ct,
                destination_type=self.invalid_ct,
                type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
            ),
            Relationship.objects.create(
                name="Invalid Relationship 2",
                slug="invalid-relationship-2",
                source_type=self.invalid_ct,
                destination_type=self.site_ct,
                type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
            ),
            Relationship.objects.create(
                name="Invalid Relationship 3",
                slug="invalid-relationship-3",
                source_type=self.invalid_ct,
                destination_type=self.invalid_ct,
                type=RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
            ),
        ]


class RelationshipTest(RelationshipBaseTest):
    def test_clean_filter_not_dict(self):
        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.site_ct,
            source_filter=["a list not a dict"],
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        with self.assertRaises(ValidationError) as handler:
            m2m.clean()
        expected_errors = {"source_filter": ["Filter for dcim.Site must be a dictionary"]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_clean_filter_not_valid(self):
        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.site_ct,
            source_filter={"notvalid": "not a region"},
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        with self.assertRaises(ValidationError) as handler:
            m2m.clean()
        expected_errors = {"source_filter": ["'notvalid' is not a valid filter parameter for dcim.Site object"]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.site_ct,
            source_filter={"region": "not a list"},
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        with self.assertRaises(ValidationError) as handler:
            m2m.clean()
        expected_errors = {"source_filter": ["'region': Enter a list of values."]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.site_ct,
            source_filter={"region": ["not a valid region"]},
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        with self.assertRaises(ValidationError) as handler:
            m2m.clean()
        expected_errors = {
            "source_filter": [
                "'region': Select a valid choice. not a valid region is not one of the available choices."
            ]
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_clean_valid(self):
        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.site_ct,
            source_filter={"name": [self.sites[1].slug]},
            destination_type=self.rack_ct,
            destination_filter={"site": [self.sites[0].slug]},
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        m2m.clean()

    def test_clean_invalid_asymmetric(self):
        """For a symmetric relationship, source and destination properties must match if specified."""
        o2os = Relationship(
            name="Site to Site",
            slug="site-to-site",
            source_type=self.site_ct,
            source_label="Site A",
            source_hidden=True,
            source_filter={"name": ["site-a"]},
            destination_type=self.rack_ct,
            destination_label="Site B",
            destination_hidden=False,
            destination_filter={"name": ["site-b"]},
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
        )

        with self.assertRaises(ValidationError) as handler:
            o2os.clean()
        expected_errors = {
            "destination_type": ["Must match source_type for a symmetric relationship"],
            "destination_label": ["Must match source_label for a symmetric relationship"],
            "destination_hidden": ["Must match source_hidden for a symmetric relationship"],
            "destination_filter": ["Must match source_filter for a symmetric relationship"],
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

        # Check ValidationError is raised when a relationship is marked as required and symmetric
        expected_exception = ValidationError({"required_on": ["Symmetric relationships cannot be marked as required."]})
        with self.assertRaises(ValidationError) as err:
            Relationship(
                name="This shouldn't validate",
                slug="vlans-vlans-m2m",
                type="symmetric-many-to-many",
                source_type=self.vlan_ct,
                destination_type=self.vlan_ct,
                required_on="destination",
            ).validated_save()
        self.assertEqual(expected_exception, err.exception)
        with self.assertRaises(ValidationError) as err:
            Relationship(
                name="This shouldn't validate",
                slug="vlans-vlans-o2o",
                type="symmetric-one-to-one",
                source_type=self.vlan_ct,
                destination_type=self.vlan_ct,
                required_on="destination",
            ).validated_save()
        self.assertEqual(expected_exception, err.exception)

    def test_clean_valid_symmetric_implicit(self):
        """For a symmetric relationship, omitted relevant properties are autofilled on clean."""
        o2os = Relationship(
            name="Site to Site",
            slug="site-to-site",
            source_type=self.site_ct,
            destination_type=self.site_ct,
            source_label="Site",
            destination_filter={"name": ["site-b"]},
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
        )

        o2os.clean()
        self.assertEqual(o2os.destination_label, "Site")
        self.assertEqual(o2os.source_filter, {"name": ["site-b"]})
        self.assertEqual(o2os.source_type, o2os.destination_type)
        self.assertEqual(o2os.source_label, o2os.destination_label)
        self.assertEqual(o2os.source_hidden, o2os.destination_hidden)
        self.assertEqual(o2os.source_filter, o2os.destination_filter)

    def test_get_label_input(self):
        with self.assertRaises(ValueError):
            self.m2m_1.get_label("wrongside")

    def test_get_label_with_label(self):
        self.assertEqual(self.m2m_1.get_label("source"), "My Vlans")
        self.assertEqual(self.m2m_1.get_label("destination"), "My Racks")

    def test_get_label_without_label_defined(self):
        self.assertEqual(self.m2m_2.get_label("source"), "VLANs")
        self.assertEqual(self.m2m_2.get_label("destination"), "racks")
        self.assertEqual(self.m2ms_1.get_label("source"), "sites")
        self.assertEqual(self.m2ms_1.get_label("destination"), "sites")
        self.assertEqual(self.m2ms_1.get_label("peer"), "sites")

    def test_has_many_input(self):
        with self.assertRaises(ValueError):
            self.m2m_1.has_many("wrongside")

    def test_has_many(self):
        self.assertTrue(self.m2m_1.has_many("source"))
        self.assertTrue(self.m2m_1.has_many("destination"))
        self.assertFalse(self.o2m_1.has_many("source"))
        self.assertTrue(self.m2m_1.has_many("destination"))
        self.assertFalse(self.o2o_1.has_many("source"))
        self.assertFalse(self.o2o_1.has_many("destination"))
        self.assertFalse(self.o2o_2.has_many("source"))
        self.assertFalse(self.o2o_2.has_many("destination"))
        self.assertFalse(self.o2os_1.has_many("source"))
        self.assertFalse(self.o2os_1.has_many("destination"))
        self.assertFalse(self.o2os_1.has_many("peer"))
        self.assertTrue(self.m2ms_1.has_many("source"))
        self.assertTrue(self.m2ms_1.has_many("destination"))
        self.assertTrue(self.m2ms_1.has_many("peer"))

    def test_to_form_field_m2m(self):

        field = self.m2m_1.to_form_field("source")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelMultipleChoiceField)
        self.assertEqual(field.label, "My Vlans")
        self.assertEqual(field.query_params, {})

        field = self.m2m_1.to_form_field("destination")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelMultipleChoiceField)
        self.assertEqual(field.label, "My Racks")
        self.assertEqual(field.query_params, {"site": [self.sites[0].slug, self.sites[1].slug, self.sites[2].slug]})

        field = self.m2ms_1.to_form_field("peer")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelMultipleChoiceField)
        self.assertEqual(field.query_params, {})

    def test_to_form_field_o2m(self):

        field = self.o2m_1.to_form_field("source")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelMultipleChoiceField)
        self.assertEqual(field.label, "VLANs")

        field = self.o2m_1.to_form_field("destination")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelChoiceField)
        self.assertEqual(field.label, "site")

    def test_to_form_field_o2o(self):
        field = self.o2o_1.to_form_field("source")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelChoiceField)
        self.assertEqual(field.label, "site")

        field = self.o2o_1.to_form_field("destination")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelChoiceField)
        self.assertEqual(field.label, "Primary Rack")

        field = self.o2os_1.to_form_field("peer")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelChoiceField)
        self.assertEqual(field.label, "rack")


class RelationshipAssociationTest(RelationshipBaseTest):
    def setUp(self):
        super().setUp()

        self.invalid_object_pks = [
            uuid.uuid4(),
            uuid.uuid4(),
        ]

        self.invalid_relationship_associations = [
            RelationshipAssociation(
                relationship=self.invalid_relationships[0],
                source=self.sites[1],
                destination_type=self.invalid_ct,
                destination_id=self.invalid_object_pks[1],
            ),
            RelationshipAssociation(
                relationship=self.invalid_relationships[1],
                source_type=self.invalid_ct,
                source_id=self.invalid_object_pks[0],
                destination=self.sites[1],
            ),
            RelationshipAssociation(
                relationship=self.invalid_relationships[2],
                source_type=self.invalid_ct,
                source_id=self.invalid_object_pks[0],
                destination_type=self.invalid_ct,
                destination_id=self.invalid_object_pks[1],
            ),
        ]
        for cra in self.invalid_relationship_associations:
            cra.validated_save()

    def test_create_invalid_relationship_association(self):
        """Test creation of invalid relationship association restricted by destination/source filter."""

        relationship = Relationship.objects.create(
            name="Site to Rack Rel 1",
            slug="site-to-rack-rel-1",
            source_type=self.site_ct,
            source_filter={"name": [self.sites[0].name]},
            destination_type=self.rack_ct,
            destination_label="Primary Rack",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
            destination_filter={"name": [self.racks[0].name]},
        )

        associations = (
            (
                "source",
                RelationshipAssociation(relationship=relationship, source=self.sites[1], destination=self.racks[0]),
            ),
            (
                "destination",
                RelationshipAssociation(relationship=relationship, source=self.sites[0], destination=self.racks[1]),
            ),
        )

        for side_name, association in associations:
            side = getattr(association, side_name)
            with self.assertRaises(ValidationError) as handler:
                association.validated_save()
            expected_errors = {side_name: [f"{side} violates {relationship} {side_name}_filter restriction"]}
            self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_exception_not_raised_when_updating_instance_with_relationship_type_o2o_or_o2m(self):
        """Validate 'Unable to create more than one relationship-association...' not raise when updating instance with
        type one-to-one, symmetric-one-to-one, one-to-many relationship."""

        # Assert Exception not raise updating source of RelationshipAssociation with one-to-many relationship type
        cra_1 = RelationshipAssociation(relationship=self.o2m_1, source=self.sites[0], destination=self.vlans[1])
        cra_1.validated_save()

        cra_1.source = self.sites[1]
        cra_1.validated_save()

        self.assertEqual(cra_1.source, self.sites[1])

        # Validate Exception not raised when calling .validated_save() on a RelationshipAssociation instance without making any update
        cra_1.validated_save()

        # Assert Exception not raise updating source of RelationshipAssociation with one-to-one relationship type
        cra_2 = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.sites[0])
        cra_2.validated_save()

        cra_2.source = self.racks[1]
        cra_2.validated_save()

        self.assertEqual(cra_2.source, self.racks[1])

        # Assert Exception not raise updating destination of RelationshipAssociation with one-to-one relationship type
        cra_3 = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[2], destination=self.sites[2])
        cra_3.validated_save()

        cra_3.destination = self.sites[4]
        cra_3.validated_save()

        self.assertEqual(cra_3.destination, self.sites[4])

        # Assert Exception not raise updating destination of RelationshipAssociation with symmetric-one-to-one relationship type
        cra_4 = RelationshipAssociation(relationship=self.o2os_1, source=self.racks[0], destination=self.racks[2])
        cra_4.validated_save()

        cra_4.destination = self.racks[1]
        cra_4.validated_save()

        self.assertEqual(cra_4.destination, self.racks[1])

    def test_clean_wrong_type(self):
        # Create with the wrong source Type
        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.m2m_1, source=self.sites[0], destination=self.vlans[0])
            cra.clean()
        expected_errors = {"source_type": ["source_type has a different value than defined in Vlan to Rack"]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

        # Create with the wrong destination Type
        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.racks[0])
            cra.clean()
        expected_errors = {"destination_type": ["destination_type has a different value than defined in Vlan to Rack"]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_clean_check_quantity_o2o(self):
        """Validate that one-to-one relationships can't have more than one relationship association per side."""

        cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.sites[0])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[1], destination=self.sites[1])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.o2os_1, source=self.racks[0], destination=self.racks[1])
        cra.validated_save()

        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.sites[2])
            cra.clean()

        expected_errors = {
            "source": ["Unable to create more than one Primary Rack per Site association from Rack A (source)"]
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[2], destination=self.sites[0])
            cra.clean()
        expected_errors = {
            "destination": [
                f"Unable to create more than one Primary Rack per Site association to {self.sites[0].name} (destination)"
            ]
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2os_1, source=self.racks[0], destination=self.racks[2])
            cra.clean()
        expected_errors = {"source": ["Unable to create more than one Redundant Rack association from Rack A (source)"]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

        # Slightly tricky case - a symmetric one-to-one relationship where the proposed *source* is already in use
        # as a *destination* in a different RelationshipAssociation
        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2os_1, source=self.racks[1], destination=self.racks[2])
            cra.clean()
        expected_errors = {
            "source": ["Unable to create more than one Redundant Rack association involving Rack B (peer)"]
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_clean_check_quantity_o2m(self):
        """Validate that one-to-many relationships can't have more than one relationship association per source."""

        cra = RelationshipAssociation(relationship=self.o2m_1, source=self.sites[0], destination=self.vlans[0])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.o2m_1, source=self.sites[0], destination=self.vlans[1])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.o2m_1, source=self.sites[1], destination=self.vlans[2])
        cra.validated_save()

        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2m_1, source=self.sites[2], destination=self.vlans[0])
            cra.clean()
        expected_errors = {
            "destination": [
                "Unable to create more than one generic site to vlan association to VLAN A (100) (destination)",
            ],
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

        # Shouldn't be possible to create another copy of the same RelationshipAssociation
        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2m_1, source=self.sites[0], destination=self.vlans[0])
            cra.validated_save()
        expected_errors = {
            "__all__": [
                "Relationship association with this Relationship, Source type, Source id, Destination type "
                "and Destination id already exists."
            ],
            "destination": [
                "Unable to create more than one generic site to vlan association to VLAN A (100) (destination)",
            ],
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_clean_check_quantity_m2m(self):
        """Validate that many-to-many relationship can have many relationship associations."""
        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[1])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[1], destination=self.vlans[2])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[2], destination=self.vlans[0])
        cra.validated_save()

        # Shouldn't be possible to create another copy of the same RelationshipAssociation
        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0])
            cra.validated_save()
        expected_errors = {
            "__all__": [
                "Relationship association with this Relationship, Source type, Source id, Destination type "
                "and Destination id already exists."
            ],
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

        cra = RelationshipAssociation(relationship=self.m2ms_1, source=self.sites[0], destination=self.sites[1])
        cra.validated_save()

        # Shouldn't be possible to create a mirrored copy of the same symmetric RelationshipAssociation
        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.m2ms_1, source=self.sites[1], destination=self.sites[0])
            cra.validated_save()
        expected_errors = {
            "__all__": [
                f"A Related Sites association already exists between {self.sites[1].name} and {self.sites[0].name}"
            ]
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_get_peer(self):
        """Validate that the get_peer() method works correctly."""
        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0])
        cra.validated_save()

        self.assertEqual(cra.get_peer(self.racks[0]), self.vlans[0])
        self.assertEqual(cra.get_peer(self.vlans[0]), self.racks[0])
        self.assertEqual(cra.get_peer(self.vlans[1]), None)

    def test_get_peer_invalid(self):
        """Validate that get_peer() handles lookup errors gracefully."""
        self.assertEqual(
            self.invalid_relationship_associations[0].get_peer(self.invalid_relationship_associations[0].source), None
        )
        self.assertEqual(
            self.invalid_relationship_associations[1].get_peer(self.invalid_relationship_associations[1].destination),
            None,
        )
        self.assertEqual(self.invalid_relationship_associations[2].get_peer(None), None)

    def test_str(self):
        """Validate that the str() method works correctly."""
        associations = [
            RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.sites[1]),
            RelationshipAssociation(relationship=self.o2os_1, source=self.racks[0], destination=self.racks[1]),
        ]
        for association in associations:
            association.validated_save()

        self.assertEqual(str(associations[0]), f"{self.racks[0]} -> {self.sites[1]} - {self.o2o_1}")
        self.assertEqual(str(associations[1]), f"{self.racks[0]} <-> {self.racks[1]} - {self.o2os_1}")
        self.assertEqual(
            str(self.invalid_relationship_associations[0]),
            f"{self.sites[1]} -> unknown - {self.invalid_relationships[0]}",
        )
        self.assertEqual(
            str(self.invalid_relationship_associations[1]),
            f"unknown -> {self.sites[1]} - {self.invalid_relationships[1]}",
        )
        self.assertEqual(
            str(self.invalid_relationship_associations[2]),
            f"unknown <-> unknown - {self.invalid_relationships[2]}",
        )

    def test_get_relationships_data(self):
        # In addition to the invalid associations for sites[1] defined in self.setUp(), add some valid ones
        associations = [
            RelationshipAssociation(relationship=self.o2m_1, source=self.sites[1], destination=self.vlans[0]),
            RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.sites[1]),
            RelationshipAssociation(relationship=self.o2o_2, source=self.sites[0], destination=self.sites[1]),
        ]
        for association in associations:
            association.validated_save()

        with self.assertLogs(logger=logging.getLogger("nautobot.extras.models.relationships"), level="ERROR"):
            data = self.sites[1].get_relationships_data()
        self.maxDiff = None
        # assertEqual doesn't work well on the entire data at once because it includes things like queryset objects
        self.assertEqual(sorted(data.keys()), ["destination", "peer", "source"])
        self.assertEqual(set(data["destination"].keys()), {self.o2o_1, self.o2o_2, self.invalid_relationships[1]})
        self.assertEqual(
            data["destination"][self.o2o_1],
            {
                "has_many": False,
                "label": "Primary Rack",
                "peer_type": self.rack_ct,
                "url": reverse("dcim:rack", kwargs={"pk": self.racks[0].pk}),
                "value": self.racks[0],
            },
        )
        self.assertEqual(
            data["destination"][self.o2o_2],
            {
                "has_many": False,
                "label": "Alphabetically Subsequent",
                "peer_type": self.site_ct,
                "url": reverse("dcim:site", kwargs={"slug": self.sites[0].slug}),
                "value": self.sites[0],
            },
        )
        self.assertEqual(
            data["destination"][self.invalid_relationships[1]],
            {
                "has_many": False,
                "label": "Invalid Relationship 2",
                "peer_type": self.invalid_ct,
                "url": None,
                "value": None,
            },
        )
        self.assertEqual(set(data["peer"].keys()), {self.m2ms_1})
        # Peer queryset is complex, but evaluates to an empty list in this case
        self.assertEqual(list(data["peer"][self.m2ms_1]["queryset"]), [])
        del data["peer"][self.m2ms_1]["queryset"]
        self.assertEqual(
            data["peer"][self.m2ms_1],
            {
                "has_many": True,
                "label": "sites",
                "peer_type": self.site_ct,
                "value": None,
            },
        )
        self.assertEqual(set(data["source"].keys()), {self.o2m_1, self.o2o_2, self.invalid_relationships[0]})
        self.assertEqual(list(data["source"][self.o2m_1]["queryset"]), [associations[0]])
        del data["source"][self.o2m_1]["queryset"]
        self.assertEqual(
            data["source"][self.o2m_1],
            {
                "has_many": True,
                "label": "VLANs",
                "peer_type": self.vlan_ct,
                "value": None,
            },
        )
        self.assertEqual(
            data["source"][self.o2o_2],
            {
                "has_many": False,
                "label": "Alphabetically Prior",
                "peer_type": self.site_ct,
                "url": None,
                "value": None,
            },
        )
        self.assertEqual(
            data["source"][self.invalid_relationships[0]],
            {
                "has_many": False,
                "label": "Invalid Relationship 1",
                "peer_type": self.invalid_ct,
                "url": None,
                # value is None because the related object can't actually be found
                "value": None,
            },
        )

    def test_delete_cascade(self):
        """Verify that a RelationshipAssociation is deleted if either of the associated records is deleted."""
        initial_count = RelationshipAssociation.objects.count()
        # Create new sites because protected error might be raised if we use test fixtures here.
        sites = (
            Site.objects.create(name="new site 1"),
            Site.objects.create(name="new site 2"),
            Site.objects.create(name="new site 3"),
            Site.objects.create(name="new site 4"),
        )
        associations = [
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0]),
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[1]),
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[1], destination=self.vlans[0]),
            # Create an association loop just to make sure it works correctly on deletion
            RelationshipAssociation(relationship=self.o2o_2, source=sites[2], destination=sites[3]),
            RelationshipAssociation(relationship=self.o2o_2, source=sites[3], destination=sites[2]),
        ]
        for association in associations:
            association.validated_save()
        # Create a self-referential association as well; validated_save() would correctly reject this one as invalid
        RelationshipAssociation.objects.create(relationship=self.o2o_2, source=sites[0], destination=sites[0])

        self.assertEqual(6 + initial_count, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when their 'source' object is deleted
        self.racks[0].delete()

        # Both relations involving racks[0] should have been deleted
        # The relation between racks[1] and vlans[0] should remain, as should the site relations
        self.assertEqual(4 + initial_count, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when their 'destination' object is deleted
        self.vlans[0].delete()

        # Site relation remains
        self.assertEqual(3 + initial_count, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when there's a loop of source/destination references
        sites[3].delete()
        self.assertEqual(1 + initial_count, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when the same object is both source and destination
        sites[0].delete()
        self.assertEqual(initial_count, RelationshipAssociation.objects.count())

    def test_generic_relation(self):
        """Verify that the GenericRelations on the involved models work correctly."""
        associations = (
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0]),
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[1]),
            RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.sites[0]),
        )
        for association in associations:
            association.validated_save()

        # Check that the GenericRelation lookup works correctly
        self.assertEqual(3, self.racks[0].source_for_associations.count())
        self.assertEqual(0, self.racks[0].destination_for_associations.count())
        self.assertEqual(0, self.vlans[0].source_for_associations.count())
        self.assertEqual(1, self.vlans[0].destination_for_associations.count())

        # Check that the related_query_names work correctly for each individual RelationshipAssociation
        self.assertEqual([self.racks[0]], list(associations[0].source_dcim_rack.all()))
        self.assertEqual([self.vlans[0]], list(associations[0].destination_ipam_vlan.all()))
        self.assertEqual([], list(associations[0].destination_dcim_site.all()))

        self.assertEqual([self.racks[0]], list(associations[1].source_dcim_rack.all()))
        self.assertEqual([self.vlans[1]], list(associations[1].destination_ipam_vlan.all()))
        self.assertEqual([], list(associations[1].destination_dcim_site.all()))

        self.assertEqual([self.racks[0]], list(associations[2].source_dcim_rack.all()))
        self.assertEqual([], list(associations[2].destination_ipam_vlan.all()))
        self.assertEqual([self.sites[0]], list(associations[2].destination_dcim_site.all()))

        # Check that the related query names can be used for filtering as well
        self.assertEqual(3, RelationshipAssociation.objects.filter(source_dcim_rack=self.racks[0]).count())
        self.assertEqual(2, RelationshipAssociation.objects.filter(destination_ipam_vlan__isnull=False).count())
        self.assertEqual(1, RelationshipAssociation.objects.filter(destination_ipam_vlan=self.vlans[0]).count())
        self.assertEqual(1, RelationshipAssociation.objects.filter(destination_ipam_vlan=self.vlans[1]).count())
        self.assertEqual(1, RelationshipAssociation.objects.filter(destination_dcim_site=self.sites[0]).count())


class RelationshipTableTest(RelationshipBaseTest):
    """
    Test inclusion of relationships in object table views.
    """

    def test_relationship_table_render(self):
        queryset = Site.objects.filter(name=self.sites[0].name)
        cr_1 = RelationshipAssociation(
            relationship=self.o2m_1,
            source_id=self.sites[0].id,
            source_type=self.site_ct,
            destination_id=self.vlans[0].id,
            destination_type=self.vlan_ct,
        )
        cr_1.validated_save()
        cr_2 = RelationshipAssociation(
            relationship=self.o2m_1,
            source_id=self.sites[0].id,
            source_type=self.site_ct,
            destination_id=self.vlans[1].id,
            destination_type=self.vlan_ct,
        )
        cr_2.validated_save()
        cr_3 = RelationshipAssociation(
            relationship=self.o2o_1,
            source_id=self.racks[0].id,
            source_type=self.rack_ct,
            destination_id=self.sites[0].id,
            destination_type=self.site_ct,
        )
        cr_3.validated_save()
        cr_4 = RelationshipAssociation(
            relationship=self.o2o_2,
            source_id=self.sites[0].id,
            source_type=self.site_ct,
            destination_id=self.sites[1].id,
            destination_type=self.site_ct,
        )
        cr_4.validated_save()
        cr_5 = RelationshipAssociation(
            relationship=self.m2ms_1,
            source_id=self.sites[0].id,
            source_type=self.site_ct,
            destination_id=self.sites[1].id,
            destination_type=self.site_ct,
        )
        cr_5.validated_save()
        cr_6 = RelationshipAssociation(
            relationship=self.m2ms_1,
            source_id=self.sites[0].id,
            source_type=self.site_ct,
            destination_id=self.sites[3].id,
            destination_type=self.site_ct,
        )
        cr_6.validated_save()

        # Test non-symmetric many to many with same source_type and same destination_type
        self.m2m_same_type = Relationship(
            name="Site to Site",
            slug="site-to-site",
            source_type=self.site_ct,
            destination_type=self.site_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        self.m2m_same_type.validated_save()
        cr_7 = RelationshipAssociation(
            relationship=self.m2m_same_type,
            source_id=self.sites[0].id,
            source_type=self.site_ct,
            destination_id=self.sites[2].id,
            destination_type=self.site_ct,
        )
        cr_7.validated_save()

        cr_8 = RelationshipAssociation(
            relationship=self.m2m_same_type,
            source_id=self.sites[3].id,
            source_type=self.site_ct,
            destination_id=self.sites[0].id,
            destination_type=self.site_ct,
        )
        cr_8.validated_save()

        site_table = SiteTable(queryset)

        relationship_column_expected = {
            "site-vlan_src": [
                format_html(
                    '<a href="{}?relationship={}&{}_id={}">{} {}</a>',
                    reverse("extras:relationshipassociation_list"),
                    cr_1.relationship.slug,
                    "source",
                    self.sites[0].id,
                    2,
                    "VLANs",
                )
            ],
            "primary-rack-site_dst": [f'<a href="{self.racks[0].get_absolute_url()}">{self.racks[0].__str__()}</a>'],
            "alphabetical-sites_src": [f'<a href="{self.sites[1].get_absolute_url()}">{self.sites[1].__str__()}</a>'],
            "related-sites_peer": [
                format_html(
                    '<a href="{}?relationship={}&{}_id={}">{} {}</a>',
                    reverse("extras:relationshipassociation_list"),
                    cr_5.relationship.slug,
                    "peer",
                    self.sites[0].id,
                    2,
                    "sites",
                )
            ],
            "site-to-site_src": [
                format_html(
                    '<a href="{}?relationship={}&{}_id={}">{} {}</a>',
                    reverse("extras:relationshipassociation_list"),
                    cr_7.relationship.slug,
                    "source",
                    self.sites[0].id,
                    1,
                    "site",
                )
            ],
            "site-to-site_dst": [
                format_html(
                    '<a href="{}?relationship={}&{}_id={}">{} {}</a>',
                    reverse("extras:relationshipassociation_list"),
                    cr_8.relationship.slug,
                    "destination",
                    self.sites[0].id,
                    1,
                    "site",
                )
            ],
        }
        bound_row = site_table.rows[0]

        for col_name, col_expected_value in relationship_column_expected.items():
            internal_col_name = "cr_" + col_name
            relationship_column = site_table.base_columns.get(internal_col_name)
            self.assertIsNotNone(relationship_column)
            self.assertIsInstance(relationship_column, RelationshipColumn)

            rendered_value = bound_row.get_cell(internal_col_name)
            # Test if the expected value is in the rendered value.
            # Exact match is difficult because the order of rendering is unpredictable.
            for value in col_expected_value:
                self.assertIn(value, rendered_value)


class RequiredRelationshipTestMixin(TestCase):
    def send_data(self, model_class, data, interact_with, action="add", url_kwargs=None):

        # Helper to post data to a URL

        if interact_with == "ui":
            return self.client.post(
                reverse(get_route_for_model(model_class, action), kwargs=url_kwargs),
                data=data,
                follow=True,
            )

        if action == "edit":
            http_method = "patch"
            action = "detail"
        else:
            http_method = "post"
            action = "list"

        return getattr(self.client, http_method)(
            reverse(get_route_for_model(model_class, action, api=True), kwargs=url_kwargs),
            data=data,
            format="json",
            **self.header,
        )

    def required_relationships_test(self, interact_with="ui"):
        """

        Args:
            interact_with: str: ("ui" or "api")

        Note:
            Where it is used, this test is parameterized to prevent code duplication.

        It should not be possible to create an object that has a required relationship without specifying the
        required amount of related objects. It performs the following checks:

        1. Try creating an object when no required target object exists
        2. Try creating an object without specifying required target object(s)
        3. Try creating an object when all required data is present
        4. API interaction scenarios:
           =================================================================
           - Relationship is marked as being not required
           - Object is created without the required relationship data (succeeds)
           - Relationship is marked as being required
           - Object is updated without the required relationship data (fails)
           - Object is updated with the required relationship data (succeeds)
           =================================================================
           - Object is created with the required relationship data (succeeds)
           - Object is updated without specifying "relationships" json key (succeeds, relationship associations
             remain in place)
           - Object is created with the required relationship data (succeeds)
           - Object is updated to remove the relationship data (fails)
           =================================================================

        """

        # Create required relationships:
        device_ct = ContentType.objects.get_for_model(Device)
        platform_ct = ContentType.objects.get_for_model(Platform)
        circuittype_ct = ContentType.objects.get_for_model(CircuitType)
        vlan_ct = ContentType.objects.get_for_model(VLAN)
        relationship_m2m = Relationship(
            name="VLANs require at least one Device",
            slug="vlans-devices-m2m",
            type="many-to-many",
            source_type=device_ct,
            destination_type=vlan_ct,
            required_on="destination",
        )
        relationship_m2m.validated_save()
        relationship_o2m = Relationship(
            name="Platforms require at least one device",
            slug="platform-devices-o2m",
            type="one-to-many",
            source_type=platform_ct,
            destination_type=device_ct,
            required_on="source",
        )
        relationship_o2m.validated_save()
        relationship_o2o = Relationship(
            name="Circuit type requires one platform",
            slug="circuittype-platform-o2o",
            type="one-to-one",
            source_type=circuittype_ct,
            destination_type=platform_ct,
            required_on="source",
        )
        relationship_o2o.validated_save()

        tests_params = [
            # Required many-to-many:
            {
                "create_data": {
                    "vid": "1",
                    "name": "New VLAN",
                    "status": str(Status.objects.get_for_model(VLAN).get(slug="active").pk)
                    if interact_with == "ui"
                    else "active",
                },
                "relationship": relationship_m2m,
                "required_objects_generator": [
                    lambda: create_test_device("Device 1"),
                    lambda: create_test_device("Device 2"),
                ],
                "expected_errors": {
                    "api": {
                        "objects_nonexistent": "VLANs require at least one device, but no devices exist yet. "
                        "Create a device by posting to /api/dcim/devices/",
                        "objects_not_specified": 'You need to specify ["relationships"]["vlans-devices-m2m"]'
                        '["source"]["objects"].',
                    },
                    "ui": {
                        "objects_nonexistent": "VLANs require at least one device, but no devices exist yet.",
                        "objects_not_specified": "You need to select at least one device.",
                    },
                },
            },
            # Required one-to-many:
            {
                "create_data": {
                    "name": "New Platform 1",
                    "slug": "new-platform-1",
                    "napalm_args": "null",
                },
                "relationship": relationship_o2m,
                "required_objects_generator": [lambda: create_test_device("Device 3")],
                "expected_errors": {
                    "api": {
                        "objects_nonexistent": "Platforms require at least one device, but no devices exist yet. "
                        "Create a device by posting to /api/dcim/devices/",
                        "objects_not_specified": 'You need to specify ["relationships"]["platform-devices-o2m"]'
                        '["destination"]["objects"].',
                    },
                    "ui": {
                        "objects_nonexistent": "Platforms require at least one device, but no devices exist yet. ",
                        "objects_not_specified": "You need to select at least one device.",
                    },
                },
            },
            # Required one-to-one:
            {
                "create_data": {
                    "name": "New Circuit Type",
                    "slug": "new-circuit-type",
                },
                "relationship": relationship_o2o,
                "required_objects_generator": [
                    lambda: Platform.objects.create(name="New Platform 2", slug="new-platform-2", napalm_args="null")
                ],
                "expected_errors": {
                    "api": {
                        "objects_nonexistent": "Circuit types require a platform, but no platforms exist yet. "
                        "Create a platform by posting to /api/dcim/platforms/",
                        "objects_not_specified": 'You need to specify ["relationships"]["circuittype-platform-o2o"]'
                        '["destination"]["objects"].',
                    },
                    "ui": {
                        "objects_nonexistent": "Circuit types require a platform, but no platforms exist yet.",
                        "objects_not_specified": "You need to select a platform.",
                    },
                },
            },
        ]

        self.user.is_superuser = True
        self.user.save()
        if interact_with == "ui":
            self.client.force_login(self.user)

        for params in tests_params:

            required_on = params["relationship"].required_on
            target_side = RelationshipSideChoices.OPPOSITE[required_on]
            from_model = getattr(params["relationship"], f"{required_on}_type").model_class()
            to_model = getattr(params["relationship"], f"{target_side}_type").model_class()

            test_msg = f"Testing {from_model._meta.verbose_name} relationship '{params['relationship'].slug}'"
            with self.subTest(msg=test_msg):

                # Clear any existing required target model objects that may have been created in previous subTests
                to_model.objects.all().delete()

                # Get count of existing objects:
                existing_count = from_model.objects.count()

                related_field_name = params["relationship"].slug
                if interact_with == "ui":
                    related_field_name = f"cr_{related_field_name}__{target_side}"

                create_data = params["create_data"]

                # 1. Try creating an object when no required target object exists
                response = self.send_data(from_model, create_data, interact_with)

                if interact_with == "ui":
                    for message in [
                        params["expected_errors"]["ui"]["objects_nonexistent"],
                        params["expected_errors"]["ui"]["objects_not_specified"],
                    ]:
                        self.assertContains(response, message)

                elif interact_with == "api":
                    self.assertHttpStatus(response, 400)
                    expected_error_json = {
                        "relationships": {
                            related_field_name: [
                                params["expected_errors"]["api"]["objects_nonexistent"],
                                params["expected_errors"]["api"]["objects_not_specified"],
                            ]
                        }
                    }
                    self.assertEqual(expected_error_json, response.json())

                # Check that no object was created:
                self.assertEqual(from_model.objects.count(), existing_count)

                # 2. Try creating an object without specifying required target object(s)
                # Create required target objects
                required_object_pks = [instance().pk for instance in params["required_objects_generator"]]

                # one-to-one relationship objects vie the UI form need to specify a pk string
                # instead of a list of pk strings
                if interact_with == "ui" and params["relationship"].type == "one-to-one":
                    required_object_pks = required_object_pks[0]

                response = self.send_data(from_model, create_data, interact_with)

                if interact_with == "ui":
                    self.assertContains(response, params["expected_errors"]["ui"]["objects_not_specified"])

                elif interact_with == "api":
                    self.assertHttpStatus(response, 400)
                    expected_error_json = {
                        "relationships": {
                            related_field_name: [params["expected_errors"]["api"]["objects_not_specified"]]
                        }
                    }
                    self.assertEqual(expected_error_json, response.json())

                # Check that no object was created:
                self.assertEqual(from_model.objects.count(), existing_count)

                # 3. Try creating an object when all required data is present
                if interact_with == "ui":
                    related_objects_data = {related_field_name: required_object_pks}

                elif interact_with == "api":
                    related_objects_data = {
                        "relationships": {related_field_name: {target_side: {"objects": required_object_pks}}}
                    }

                response = self.send_data(from_model, {**create_data, **related_objects_data}, interact_with)

                if interact_with == "ui":
                    self.assertHttpStatus(response, 200)
                    self.assertContains(response, params["create_data"]["name"])
                    self.assertContains(response, "Relationships")

                elif interact_with == "api":
                    self.assertHttpStatus(response, 201)

                # Check object was created:
                self.assertEqual(from_model.objects.count(), existing_count + 1)

                if interact_with == "api":

                    """
                    - Relationship is marked as being not required
                    - Object is created without the required relationship data (succeeds)
                    - Relationship is marked as being required
                    - Object is updated without the required relationship data (fails)
                    - Object is updated with the required relationship data (succeeds)
                    """

                    # Delete the object that was previously created, so we can test with the same data again
                    from_model.objects.get(name=params["create_data"]["name"]).delete()
                    self.assertEqual(from_model.objects.count(), existing_count)

                    # Relationship is marked as being not required
                    params["relationship"].required_on = RelationshipRequiredSideChoices.NEITHER_SIDE_REQUIRED
                    params["relationship"].save()

                    # Object is created without the required relationship data (succeeds)
                    response = self.send_data(from_model, create_data, interact_with)

                    # Check object was created
                    self.assertHttpStatus(response, 201)
                    self.assertEqual(from_model.objects.count(), existing_count + 1)

                    # Relationship is marked as being required
                    params["relationship"].required_on = required_on
                    params["relationship"].save()

                    # Object is updated without the required relationship data (fails)
                    newly_created_object = from_model.objects.get(name=params["create_data"]["name"])
                    response = self.send_data(
                        from_model,
                        {
                            "name": f'{params["create_data"]["name"]} edited',
                            "relationships": {},
                        },
                        interact_with,
                        action="edit",
                        url_kwargs={"pk": newly_created_object.pk},
                    )
                    self.assertHttpStatus(response, 400)
                    expected_error_json = {
                        "relationships": {
                            related_field_name: [params["expected_errors"]["api"]["objects_not_specified"]]
                        }
                    }
                    self.assertEqual(expected_error_json, response.json())

                    # Object is updated with the required relationship data (succeeds)
                    response = self.send_data(
                        from_model,
                        {**{"name": f'{params["create_data"]["name"]} edited'}, **related_objects_data},
                        interact_with,
                        action="edit",
                        url_kwargs={"pk": newly_created_object.pk},
                    )
                    self.assertHttpStatus(response, 200)
                    self.assertEqual(f'{params["create_data"]["name"]} edited', response.json()["name"])

                    """
                    - Object is created with the required relationship data (succeeds)
                    - Object is updated without specifying "relationships" json key (succeeds, relationship
                      remains in place)
                    - Object is updated to remove the relationship data (fails)
                    """

                    # Delete the object that was previously created, so we can test with the same data again
                    from_model.objects.get(name=f'{params["create_data"]["name"]} edited').delete()
                    self.assertEqual(from_model.objects.count(), existing_count)

                    # Object is created with the required relationship data (succeeds)
                    response = self.send_data(from_model, {**create_data, **related_objects_data}, interact_with)
                    self.assertHttpStatus(response, 201)
                    self.assertEqual(params["create_data"]["name"], response.json()["name"])
                    self.assertEqual(from_model.objects.count(), existing_count + 1)

                    # Object is updated without specifying "relationships" json key
                    # (succeeds, relationship associations remain in place)
                    newly_created_object = from_model.objects.get(name=params["create_data"]["name"])
                    response = self.send_data(
                        from_model,
                        {"name": f'{params["create_data"]["name"]} changed'},
                        interact_with,
                        action="edit",
                        url_kwargs={"pk": newly_created_object.pk},
                    )
                    self.assertHttpStatus(response, 200)
                    self.assertEqual(f'{params["create_data"]["name"]} changed', response.json()["name"])

                    # Object is updated to remove the relationship data (fails)
                    response = self.send_data(
                        from_model,
                        {
                            "name": f'{params["create_data"]["name"]} changed again',
                            "relationships": {},
                        },
                        interact_with,
                        action="edit",
                        url_kwargs={"pk": newly_created_object.pk},
                    )
                    self.assertHttpStatus(response, 400)
                    expected_error_json = {
                        "relationships": {
                            related_field_name: [params["expected_errors"]["api"]["objects_not_specified"]]
                        }
                    }
                    self.assertEqual(expected_error_json, response.json())
