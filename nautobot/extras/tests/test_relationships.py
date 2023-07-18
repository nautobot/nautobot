import logging
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html

from nautobot.circuits.models import CircuitType
from nautobot.core.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
)
from nautobot.core.tables import RelationshipColumn
from nautobot.core.testing import TestCase
from nautobot.core.testing.models import ModelTestCases
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.dcim.models import Device, Platform, Rack, Location, LocationType
from nautobot.dcim.tables import LocationTable
from nautobot.dcim.tests.test_views import create_test_device
from nautobot.ipam.models import VLAN, VLANGroup
from nautobot.extras.choices import RelationshipRequiredSideChoices, RelationshipSideChoices, RelationshipTypeChoices
from nautobot.extras.models import Relationship, RelationshipAssociation, Status


class RelationshipBaseTest:
    @classmethod
    def setUpTestData(cls):
        cls.location_ct = ContentType.objects.get_for_model(Location)
        cls.rack_ct = ContentType.objects.get_for_model(Rack)
        cls.vlan_ct = ContentType.objects.get_for_model(VLAN)

        cls.locations = Location.objects.get_for_model(Rack).get_for_model(VLAN)[:5]

        cls.rack_status = Status.objects.get_for_model(Rack).first()
        cls.racks = [
            Rack.objects.create(name="Rack A", location=cls.locations[0], status=cls.rack_status),
            Rack.objects.create(name="Rack B", location=cls.locations[1], status=cls.rack_status),
            Rack.objects.create(name="Rack C", location=cls.locations[2], status=cls.rack_status),
        ]

        cls.vlan_status = Status.objects.get_for_model(VLAN).first()
        cls.vlan_group = VLANGroup.objects.create(name="Relationship Test VLANGroup")
        cls.vlans = [
            VLAN.objects.create(
                name="VLAN A", vid=100, location=cls.locations[0], status=cls.vlan_status, vlan_group=cls.vlan_group
            ),
            VLAN.objects.create(
                name="VLAN B", vid=101, location=cls.locations[1], status=cls.vlan_status, vlan_group=cls.vlan_group
            ),
            VLAN.objects.create(
                name="VLAN C", vid=102, location=cls.locations[2], status=cls.vlan_status, vlan_group=cls.vlan_group
            ),
        ]

        cls.m2m_1 = Relationship(
            label="VLAN to Rack",
            key="vlan_rack",
            source_type=cls.rack_ct,
            source_label="My VLANs",
            source_filter={"location": [cls.locations[0].name, cls.locations[1].name, cls.locations[2].name]},
            destination_type=cls.vlan_ct,
            destination_label="My Racks",
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        cls.m2m_1.validated_save()

        cls.m2m_2 = Relationship(
            label="Another VLAN to Rack",
            key="vlan_rack_2",
            source_type=cls.rack_ct,
            destination_type=cls.vlan_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        cls.m2m_2.validated_save()

        cls.o2m_1 = Relationship(
            label="generic location to vlan",
            key="location_vlan",
            source_type=cls.location_ct,
            destination_type=cls.vlan_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        cls.o2m_1.validated_save()

        cls.o2o_1 = Relationship(
            label="Primary Rack per Location",
            key="primary_rack_location",
            source_type=cls.rack_ct,
            source_hidden=True,
            destination_type=cls.location_ct,
            destination_label="Primary Rack",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        cls.o2o_1.validated_save()

        # Relationships between objects of the same type

        cls.o2o_2 = Relationship(
            label="Alphabetical Locations",
            key="alphabetical_locations",
            source_type=cls.location_ct,
            source_label="Alphabetically Prior",
            destination_type=cls.location_ct,
            destination_label="Alphabetically Subsequent",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        cls.o2o_2.validated_save()

        cls.o2os_1 = Relationship(
            label="Redundant Rack",
            key="redundant_rack",
            source_type=cls.rack_ct,
            destination_type=cls.rack_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
        )
        cls.o2os_1.validated_save()

        cls.m2ms_1 = Relationship(
            label="Related Locations",
            key="related_locations",
            source_type=cls.location_ct,
            destination_type=cls.location_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
        )
        cls.m2ms_1.validated_save()

        # Relationships involving a content type that doesn't actually have a backing model.
        # This can occur in practice if, for example, a relationship is defined for a plugin-defined model,
        # then the plugin is subsequently uninstalled or deactivated.
        cls.invalid_ct = ContentType.objects.create(app_label="nonexistent", model="nosuchmodel")

        # Don't use validated_save() on these as it will fail due to the invalid content-type
        cls.invalid_relationships = [
            Relationship.objects.create(
                label="Invalid Relationship 1",
                key="invalid_relationship_1",
                source_type=cls.location_ct,
                destination_type=cls.invalid_ct,
                type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
            ),
            Relationship.objects.create(
                label="Invalid Relationship 2",
                key="invalid_relationship_2",
                source_type=cls.invalid_ct,
                destination_type=cls.location_ct,
                type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
            ),
            Relationship.objects.create(
                label="Invalid Relationship 3",
                key="invalid_relationship_3",
                source_type=cls.invalid_ct,
                destination_type=cls.invalid_ct,
                type=RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
            ),
        ]


class RelationshipTest(RelationshipBaseTest, ModelTestCases.BaseModelTestCase):
    model = Relationship

    def test_clean_filter_not_dict(self):
        m2m = Relationship(
            label="Another VLAN to Rack",
            key="vlan_rack_2",
            source_type=self.location_ct,
            source_filter=["a list not a dict"],
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        with self.assertRaises(ValidationError) as handler:
            m2m.clean()
        expected_errors = {"source_filter": ["Filter for dcim.Location must be a dictionary"]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_clean_filter_not_valid(self):
        m2m = Relationship(
            label="Another VLAN to Rack",
            key="vlan_rack_2",
            source_type=self.location_ct,
            source_filter={"notvalid": "not a location"},
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        with self.assertRaises(ValidationError) as handler:
            m2m.clean()
        expected_errors = {"source_filter": ["'notvalid' is not a valid filter parameter for dcim.Location object"]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

        m2m = Relationship(
            label="Another VLAN to Rack",
            key="vlan_rack_2",
            source_type=self.location_ct,
            source_filter={"parent": "not a list"},
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        with self.assertRaises(ValidationError) as handler:
            m2m.clean()
        expected_errors = {"source_filter": ["'parent': Enter a list of values."]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

        m2m = Relationship(
            label="Another VLAN to Rack",
            key="vlan_rack_2",
            source_type=self.location_ct,
            source_filter={"parent": ["not a valid location"]},
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        with self.assertRaises(ValidationError) as handler:
            m2m.clean()
        expected_errors = {
            "source_filter": [
                "'parent': Select a valid choice. not a valid location is not one of the available choices."
            ]
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_clean_valid(self):
        m2m = Relationship(
            label="Another VLAN to Rack",
            key="vlan_rack_2",
            source_type=self.location_ct,
            source_filter={"name": [self.locations[1].name]},
            destination_type=self.rack_ct,
            destination_filter={"location": [self.locations[0].name]},
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        m2m.clean()

    def test_clean_invalid_asymmetric(self):
        """For a symmetric relationship, source and destination properties must match if specified."""
        o2os = Relationship(
            label="Location to Location",
            key="location_to_location",
            source_type=self.location_ct,
            source_label="Location A",
            source_hidden=True,
            source_filter={"name": ["location-a"]},
            destination_type=self.rack_ct,
            destination_label="Location B",
            destination_hidden=False,
            destination_filter={"name": ["location-b"]},
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
                label="This shouldn't validate",
                key="vlans_vlans_m2m",
                type="symmetric-many-to-many",
                source_type=self.vlan_ct,
                destination_type=self.vlan_ct,
                required_on="destination",
            ).validated_save()
        self.assertEqual(expected_exception, err.exception)
        with self.assertRaises(ValidationError) as err:
            Relationship(
                label="This shouldn't validate",
                key="vlans_vlans_o2o",
                type="symmetric-one-to-one",
                source_type=self.vlan_ct,
                destination_type=self.vlan_ct,
                required_on="destination",
            ).validated_save()
        self.assertEqual(expected_exception, err.exception)

    def test_clean_valid_symmetric_implicit(self):
        """For a symmetric relationship, omitted relevant properties are autofilled on clean."""
        o2os = Relationship(
            label="Location to Location",
            key="location_to_location",
            source_type=self.location_ct,
            destination_type=self.location_ct,
            source_label="Location",
            destination_filter={"name": ["location-b"]},
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
        )

        o2os.clean()
        self.assertEqual(o2os.destination_label, "Location")
        self.assertEqual(o2os.source_filter, {"name": ["location-b"]})
        self.assertEqual(o2os.source_type, o2os.destination_type)
        self.assertEqual(o2os.source_label, o2os.destination_label)
        self.assertEqual(o2os.source_hidden, o2os.destination_hidden)
        self.assertEqual(o2os.source_filter, o2os.destination_filter)

    def test_get_label_input(self):
        with self.assertRaises(ValueError):
            self.m2m_1.get_label("wrongside")

    def test_get_label_with_label(self):
        self.assertEqual(self.m2m_1.get_label("source"), "My VLANs")
        self.assertEqual(self.m2m_1.get_label("destination"), "My Racks")

    def test_get_label_without_label_defined(self):
        self.assertEqual(self.m2m_2.get_label("source"), "VLANs")
        self.assertEqual(self.m2m_2.get_label("destination"), "racks")
        self.assertEqual(self.m2ms_1.get_label("source"), "locations")
        self.assertEqual(self.m2ms_1.get_label("destination"), "locations")
        self.assertEqual(self.m2ms_1.get_label("peer"), "locations")

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
        self.assertEqual(field.label, "My VLANs")
        self.assertEqual(field.query_params, {})

        field = self.m2m_1.to_form_field("destination")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelMultipleChoiceField)
        self.assertEqual(field.label, "My Racks")
        self.assertEqual(
            field.query_params, {"location": [self.locations[0].name, self.locations[1].name, self.locations[2].name]}
        )

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
        self.assertEqual(field.label, "location")

    def test_to_form_field_o2o(self):
        field = self.o2o_1.to_form_field("source")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelChoiceField)
        self.assertEqual(field.label, "location")

        field = self.o2o_1.to_form_field("destination")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelChoiceField)
        self.assertEqual(field.label, "Primary Rack")

        field = self.o2os_1.to_form_field("peer")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelChoiceField)
        self.assertEqual(field.label, "rack")

    def test_check_if_key_is_graphql_safe(self):
        """
        Check the GraphQL validation method on CustomField Key Attribute.
        """
        # Check if it catches the cr.key starting with a digit.
        cr1 = Relationship(
            label="VLANs to VLANs",
            key="12_vlans_to_vlans",
            type="symmetric-many-to-many",
            source_type=self.vlan_ct,
            destination_type=self.vlan_ct,
        )
        with self.assertRaises(ValidationError) as error:
            cr1.validated_save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )
        # Check if it catches the cr.key with whitespace.
        cr1.key = "test 1"
        with self.assertRaises(ValidationError) as error:
            cr1.validated_save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )
        # Check if it catches the cr.key with hyphens.
        cr1.key = "test-1-relationship"
        with self.assertRaises(ValidationError) as error:
            cr1.validated_save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )
        # Check if it catches the cr.key with special characters
        cr1.key = "test_1_rela)(&dship"
        with self.assertRaises(ValidationError) as error:
            cr1.validated_save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )


class RelationshipAssociationTest(RelationshipBaseTest, ModelTestCases.BaseModelTestCase):
    model = RelationshipAssociation

    def setUp(self):
        super().setUp()

        self.invalid_object_pks = [
            uuid.uuid4(),
            uuid.uuid4(),
        ]

        self.invalid_relationship_associations = [
            RelationshipAssociation(
                relationship=self.invalid_relationships[0],
                source=self.locations[1],
                destination_type=self.invalid_ct,
                destination_id=self.invalid_object_pks[1],
            ),
            RelationshipAssociation(
                relationship=self.invalid_relationships[1],
                source_type=self.invalid_ct,
                source_id=self.invalid_object_pks[0],
                destination=self.locations[1],
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
            label="Location to Rack Rel 1",
            key="location_to_rack_rel_1",
            source_type=self.location_ct,
            source_filter={"name": [self.locations[0].name]},
            destination_type=self.rack_ct,
            destination_label="Primary Rack",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
            destination_filter={"name": [self.racks[0].name]},
        )

        associations = (
            (
                "source",
                RelationshipAssociation(relationship=relationship, source=self.locations[1], destination=self.racks[0]),
            ),
            (
                "destination",
                RelationshipAssociation(relationship=relationship, source=self.locations[0], destination=self.racks[1]),
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
        cra_1 = RelationshipAssociation(relationship=self.o2m_1, source=self.locations[0], destination=self.vlans[1])
        cra_1.validated_save()

        cra_1.source = self.locations[1]
        cra_1.validated_save()

        self.assertEqual(cra_1.source, self.locations[1])

        # Validate Exception not raised when calling .validated_save() on a RelationshipAssociation instance without making any update
        cra_1.validated_save()

        # Assert Exception not raise updating source of RelationshipAssociation with one-to-one relationship type
        cra_2 = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.locations[0])
        cra_2.validated_save()

        cra_2.source = self.racks[1]
        cra_2.validated_save()

        self.assertEqual(cra_2.source, self.racks[1])

        # Assert Exception not raise updating destination of RelationshipAssociation with one-to-one relationship type
        cra_3 = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[2], destination=self.locations[2])
        cra_3.validated_save()

        cra_3.destination = self.locations[4]
        cra_3.validated_save()

        self.assertEqual(cra_3.destination, self.locations[4])

        # Assert Exception not raise updating destination of RelationshipAssociation with symmetric-one-to-one relationship type
        cra_4 = RelationshipAssociation(relationship=self.o2os_1, source=self.racks[0], destination=self.racks[2])
        cra_4.validated_save()

        cra_4.destination = self.racks[1]
        cra_4.validated_save()

        self.assertEqual(cra_4.destination, self.racks[1])

    def test_clean_wrong_type(self):
        # Create with the wrong source Type
        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.m2m_1, source=self.locations[0], destination=self.vlans[0])
            cra.clean()
        expected_errors = {"source_type": ["source_type has a different value than defined in VLAN to Rack"]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

        # Create with the wrong destination Type
        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.racks[0])
            cra.clean()
        expected_errors = {"destination_type": ["destination_type has a different value than defined in VLAN to Rack"]}
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_clean_check_quantity_o2o(self):
        """Validate that one-to-one relationships can't have more than one relationship association per side."""

        cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.locations[0])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[1], destination=self.locations[1])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.o2os_1, source=self.racks[0], destination=self.racks[1])
        cra.validated_save()

        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.locations[2])
            cra.clean()

        expected_errors = {
            "source": ["Unable to create more than one Primary Rack per Location association from Rack A (source)"]
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[2], destination=self.locations[0])
            cra.clean()
        expected_errors = {
            "destination": [
                f"Unable to create more than one Primary Rack per Location association to {self.locations[0].name} (destination)"
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

        cra = RelationshipAssociation(relationship=self.o2m_1, source=self.locations[0], destination=self.vlans[0])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.o2m_1, source=self.locations[0], destination=self.vlans[1])
        cra.validated_save()

        cra = RelationshipAssociation(relationship=self.o2m_1, source=self.locations[1], destination=self.vlans[2])
        cra.validated_save()

        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2m_1, source=self.locations[2], destination=self.vlans[0])
            cra.clean()
        expected_errors = {
            "destination": [
                "Unable to create more than one generic location to vlan association to VLAN A (100) (destination)",
            ],
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

        # Shouldn't be possible to create another copy of the same RelationshipAssociation
        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2m_1, source=self.locations[0], destination=self.vlans[0])
            cra.validated_save()
        expected_errors = {
            "__all__": [
                "Relationship association with this Relationship, Source type, Source id, Destination type "
                "and Destination id already exists."
            ],
            "destination": [
                "Unable to create more than one generic location to vlan association to VLAN A (100) (destination)",
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

        cra = RelationshipAssociation(relationship=self.m2ms_1, source=self.locations[0], destination=self.locations[1])
        cra.validated_save()

        # Shouldn't be possible to create a mirrored copy of the same symmetric RelationshipAssociation
        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(
                relationship=self.m2ms_1, source=self.locations[1], destination=self.locations[0]
            )
            cra.validated_save()
        expected_errors = {
            "__all__": [
                f"A Related Locations association already exists between {self.locations[1].name} and {self.locations[0].name}"
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
            RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.locations[1]),
            RelationshipAssociation(relationship=self.o2os_1, source=self.racks[0], destination=self.racks[1]),
        ]
        for association in associations:
            association.validated_save()

        self.assertEqual(str(associations[0]), f"{self.racks[0]} -> {self.locations[1]} - {self.o2o_1}")
        self.assertEqual(str(associations[1]), f"{self.racks[0]} <-> {self.racks[1]} - {self.o2os_1}")
        self.assertEqual(
            str(self.invalid_relationship_associations[0]),
            f"{self.locations[1]} -> unknown - {self.invalid_relationships[0]}",
        )
        self.assertEqual(
            str(self.invalid_relationship_associations[1]),
            f"unknown -> {self.locations[1]} - {self.invalid_relationships[1]}",
        )
        self.assertEqual(
            str(self.invalid_relationship_associations[2]),
            f"unknown <-> unknown - {self.invalid_relationships[2]}",
        )

    def test_get_relationships_data(self):
        # In addition to the invalid associations for locations[1] defined in self.setUp(), add some valid ones
        associations = [
            RelationshipAssociation(relationship=self.o2m_1, source=self.locations[1], destination=self.vlans[0]),
            RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.locations[1]),
            RelationshipAssociation(relationship=self.o2o_2, source=self.locations[0], destination=self.locations[1]),
        ]
        for association in associations:
            association.validated_save()

        with self.assertLogs(logger=logging.getLogger("nautobot.extras.models.relationships"), level="ERROR"):
            data = self.locations[1].get_relationships_data()
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
                "peer_type": self.location_ct,
                "url": reverse("dcim:location", kwargs={"pk": self.locations[0].pk}),
                "value": self.locations[0],
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
                "label": "locations",
                "peer_type": self.location_ct,
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
                "peer_type": self.location_ct,
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
        # Create new locations because protected error might be raised if we use test fixtures here.
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        locations = (
            Location.objects.create(name="new location 1", location_type=location_type, status=location_status),
            Location.objects.create(name="new location 2", location_type=location_type, status=location_status),
            Location.objects.create(name="new location 3", location_type=location_type, status=location_status),
            Location.objects.create(name="new location 4", location_type=location_type, status=location_status),
        )
        associations = [
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0]),
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[1]),
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[1], destination=self.vlans[0]),
            # Create an association loop just to make sure it works correctly on deletion
            RelationshipAssociation(relationship=self.o2o_2, source=locations[2], destination=locations[3]),
            RelationshipAssociation(relationship=self.o2o_2, source=locations[3], destination=locations[2]),
        ]
        for association in associations:
            association.validated_save()
        # Create a self-referential association as well; validated_save() would correctly reject this one as invalid
        RelationshipAssociation.objects.create(relationship=self.o2o_2, source=locations[0], destination=locations[0])

        self.assertEqual(6 + initial_count, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when their 'source' object is deleted
        self.racks[0].delete()

        # Both relations involving racks[0] should have been deleted
        # The relation between racks[1] and vlans[0] should remain, as should the location relations
        self.assertEqual(4 + initial_count, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when their 'destination' object is deleted
        self.vlans[0].delete()

        # Location relation remains
        self.assertEqual(3 + initial_count, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when there's a loop of source/destination references
        locations[3].delete()
        self.assertEqual(1 + initial_count, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when the same object is both source and destination
        locations[0].delete()
        self.assertEqual(initial_count, RelationshipAssociation.objects.count())

    def test_generic_relation(self):
        """Verify that the GenericRelations on the involved models work correctly."""
        associations = (
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0]),
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[1]),
            RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.locations[0]),
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
        self.assertEqual([], list(associations[0].destination_dcim_location.all()))

        self.assertEqual([self.racks[0]], list(associations[1].source_dcim_rack.all()))
        self.assertEqual([self.vlans[1]], list(associations[1].destination_ipam_vlan.all()))
        self.assertEqual([], list(associations[1].destination_dcim_location.all()))

        self.assertEqual([self.racks[0]], list(associations[2].source_dcim_rack.all()))
        self.assertEqual([], list(associations[2].destination_ipam_vlan.all()))
        self.assertEqual([self.locations[0]], list(associations[2].destination_dcim_location.all()))

        # Check that the related query names can be used for filtering as well
        self.assertEqual(3, RelationshipAssociation.objects.filter(source_dcim_rack=self.racks[0]).count())
        self.assertEqual(2, RelationshipAssociation.objects.filter(destination_ipam_vlan__isnull=False).count())
        self.assertEqual(1, RelationshipAssociation.objects.filter(destination_ipam_vlan=self.vlans[0]).count())
        self.assertEqual(1, RelationshipAssociation.objects.filter(destination_ipam_vlan=self.vlans[1]).count())
        self.assertEqual(1, RelationshipAssociation.objects.filter(destination_dcim_location=self.locations[0]).count())


class RelationshipTableTest(RelationshipBaseTest, TestCase):
    """
    Test inclusion of relationships in object table views.
    """

    def test_relationship_table_render(self):
        queryset = Location.objects.filter(name=self.locations[0].name)
        cr_1 = RelationshipAssociation(
            relationship=self.o2m_1,
            source_id=self.locations[0].id,
            source_type=self.location_ct,
            destination_id=self.vlans[0].id,
            destination_type=self.vlan_ct,
        )
        cr_1.validated_save()
        cr_2 = RelationshipAssociation(
            relationship=self.o2m_1,
            source_id=self.locations[0].id,
            source_type=self.location_ct,
            destination_id=self.vlans[1].id,
            destination_type=self.vlan_ct,
        )
        cr_2.validated_save()
        cr_3 = RelationshipAssociation(
            relationship=self.o2o_1,
            source_id=self.racks[0].id,
            source_type=self.rack_ct,
            destination_id=self.locations[0].id,
            destination_type=self.location_ct,
        )
        cr_3.validated_save()
        cr_4 = RelationshipAssociation(
            relationship=self.o2o_2,
            source_id=self.locations[0].id,
            source_type=self.location_ct,
            destination_id=self.locations[1].id,
            destination_type=self.location_ct,
        )
        cr_4.validated_save()
        cr_5 = RelationshipAssociation(
            relationship=self.m2ms_1,
            source_id=self.locations[0].id,
            source_type=self.location_ct,
            destination_id=self.locations[1].id,
            destination_type=self.location_ct,
        )
        cr_5.validated_save()
        cr_6 = RelationshipAssociation(
            relationship=self.m2ms_1,
            source_id=self.locations[0].id,
            source_type=self.location_ct,
            destination_id=self.locations[3].id,
            destination_type=self.location_ct,
        )
        cr_6.validated_save()

        # Test non-symmetric many to many with same source_type and same destination_type
        self.m2m_same_type = Relationship(
            label="Location to Location",
            key="location_to_location",
            source_type=self.location_ct,
            destination_type=self.location_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        self.m2m_same_type.validated_save()
        cr_7 = RelationshipAssociation(
            relationship=self.m2m_same_type,
            source_id=self.locations[0].id,
            source_type=self.location_ct,
            destination_id=self.locations[2].id,
            destination_type=self.location_ct,
        )
        cr_7.validated_save()

        cr_8 = RelationshipAssociation(
            relationship=self.m2m_same_type,
            source_id=self.locations[3].id,
            source_type=self.location_ct,
            destination_id=self.locations[0].id,
            destination_type=self.location_ct,
        )
        cr_8.validated_save()

        location_table = LocationTable(queryset)

        relationship_column_expected = {
            "location_vlan_src": [
                format_html(
                    '<a href="{}?relationship={}&{}_id={}">{} {}</a>',
                    reverse("extras:relationshipassociation_list"),
                    cr_1.relationship.key,
                    "source",
                    self.locations[0].id,
                    2,
                    "VLANs",
                )
            ],
            "primary_rack_location_dst": [
                f'<a href="{self.racks[0].get_absolute_url()}">{self.racks[0].__str__()}</a>'
            ],
            "alphabetical_locations_src": [
                f'<a href="{self.locations[1].get_absolute_url()}">{self.locations[1].__str__()}</a>'
            ],
            "related_locations_peer": [
                format_html(
                    '<a href="{}?relationship={}&{}_id={}">{} {}</a>',
                    reverse("extras:relationshipassociation_list"),
                    cr_5.relationship.key,
                    "peer",
                    self.locations[0].id,
                    2,
                    "locations",
                )
            ],
            "location_to_location_src": [
                format_html(
                    '<a href="{}?relationship={}&{}_id={}">{} {}</a>',
                    reverse("extras:relationshipassociation_list"),
                    cr_7.relationship.key,
                    "source",
                    self.locations[0].id,
                    1,
                    "location",
                )
            ],
            "location_to_location_dst": [
                format_html(
                    '<a href="{}?relationship={}&{}_id={}">{} {}</a>',
                    reverse("extras:relationshipassociation_list"),
                    cr_8.relationship.key,
                    "destination",
                    self.locations[0].id,
                    1,
                    "location",
                )
            ],
        }
        bound_row = location_table.rows[0]

        for col_name, col_expected_value in relationship_column_expected.items():
            internal_col_name = "cr_" + col_name
            relationship_column = location_table.base_columns.get(internal_col_name)
            self.assertIsNotNone(relationship_column)
            self.assertIsInstance(relationship_column, RelationshipColumn)

            rendered_value = bound_row.get_cell(internal_col_name)
            # Test if the expected value is in the rendered value.
            # Exact match is difficult because the order of rendering is unpredictable.
            for value in col_expected_value:
                self.assertIn(value, rendered_value)


class RequiredRelationshipTestMixin:
    """Common test mixin for both view and API tests dealing with required relationships."""

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
            label="VLANs require at least one Device",
            key="vlans_devices_m2m",
            type="many-to-many",
            source_type=device_ct,
            destination_type=vlan_ct,
            required_on="destination",
        )
        relationship_m2m.validated_save()
        relationship_o2m = Relationship(
            label="Platforms require at least one device",
            key="platform_devices_o2m",
            type="one-to-many",
            source_type=platform_ct,
            destination_type=device_ct,
            required_on="source",
        )
        relationship_o2m.validated_save()
        relationship_o2o = Relationship(
            label="Circuit type requires one platform",
            key="circuittype_platform_o2o",
            type="one-to-one",
            source_type=circuittype_ct,
            destination_type=platform_ct,
            required_on="source",
        )
        relationship_o2o.validated_save()
        vlan_group = VLANGroup.objects.first()

        tests_params = [
            # Required many-to-many:
            {
                "create_data": {
                    "vid": "1",
                    "name": "New VLAN",
                    "status": str(Status.objects.get_for_model(VLAN).first().pk),
                    "vlan_group": str(vlan_group.pk),
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
                        "objects_not_specified": 'You need to specify ["relationships"]["vlans_devices_m2m"]'
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
                    "napalm_args": "null",
                },
                "relationship": relationship_o2m,
                "required_objects_generator": [lambda: create_test_device("Device 3")],
                "expected_errors": {
                    "api": {
                        "objects_nonexistent": "Platforms require at least one device, but no devices exist yet. "
                        "Create a device by posting to /api/dcim/devices/",
                        "objects_not_specified": 'You need to specify ["relationships"]["platform_devices_o2m"]'
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
                },
                "relationship": relationship_o2o,
                "required_objects_generator": [
                    lambda: Platform.objects.create(name="New Platform 2", napalm_args="null")
                ],
                "expected_errors": {
                    "api": {
                        "objects_nonexistent": "Circuit types require a platform, but no platforms exist yet. "
                        "Create a platform by posting to /api/dcim/platforms/",
                        "objects_not_specified": 'You need to specify ["relationships"]["circuittype_platform_o2o"]'
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

            test_msg = f"Testing {from_model._meta.verbose_name} relationship '{params['relationship'].key}'"
            with self.subTest(msg=test_msg):
                # Clear any existing required target model objects that may have been created in previous subTests
                to_model.objects.all().delete()

                # Get count of existing objects:
                existing_count = from_model.objects.count()

                related_field_name = params["relationship"].key
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
