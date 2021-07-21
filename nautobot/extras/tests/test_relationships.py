from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from nautobot.dcim.models import Site, Rack
from nautobot.ipam.models import VLAN
from nautobot.extras.choices import *
from nautobot.extras.models import Relationship, RelationshipAssociation
from nautobot.utilities.testing import TestCase
from nautobot.utilities.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
)


class RelationshipBaseTest(TestCase):
    def setUp(self):

        self.site_ct = ContentType.objects.get_for_model(Site)
        self.rack_ct = ContentType.objects.get_for_model(Rack)
        self.vlan_ct = ContentType.objects.get_for_model(VLAN)

        self.m2m_1 = Relationship(
            name="Vlan to Rack",
            slug="vlan-rack",
            source_type=self.rack_ct,
            source_label="My Vlans",
            source_filter={"site": "mysite"},
            destination_type=self.vlan_ct,
            destination_label="My Racks",
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        self.m2m_1.save()

        self.m2m_2 = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.rack_ct,
            destination_type=self.vlan_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        self.m2m_2.save()

        self.o2m_1 = Relationship(
            name="generic site to vlan",
            slug="site-vlan",
            source_type=self.site_ct,
            destination_type=self.vlan_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        self.o2m_1.save()

        self.o2o_1 = Relationship(
            name="Primary Rack per Site",
            slug="primary-rack-site",
            source_type=self.rack_ct,
            source_hidden=True,
            destination_type=self.site_ct,
            destination_label="Primary Rack",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        self.o2o_1.save()

        self.sites = [
            Site.objects.create(name="Site A", slug="site-a"),
            Site.objects.create(name="Site B", slug="site-b"),
            Site.objects.create(name="Site C", slug="site-c"),
        ]

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

    def test_clean_same_object(self):
        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.rack_ct,
            destination_type=self.rack_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        with self.assertRaises(ValidationError):
            m2m.clean()

    def test_clean_valid(self):
        m2m = Relationship(
            name="Another Vlan to Rack",
            slug="vlan-rack-2",
            source_type=self.site_ct,
            source_filter={"name": ["site-b"]},
            destination_type=self.rack_ct,
            destination_filter={"site": ["site-a"]},
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )

        m2m.clean()

    def test_get_label_input(self):
        with self.assertRaises(ValueError):
            self.m2m_1.get_label("wrongside")

    def test_get_label_with_label(self):
        self.assertEqual(self.m2m_1.get_label("source"), "My Vlans")
        self.assertEqual(self.m2m_1.get_label("destination"), "My Racks")

    def test_get_label_without_label_defined(self):
        self.assertEqual(self.m2m_2.get_label("source"), "VLANs")
        self.assertEqual(self.m2m_2.get_label("destination"), "racks")

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
        self.assertEqual(field.query_params, {"site": "mysite"})

    def test_to_form_field_o2m(self):

        field = self.o2m_1.to_form_field("source")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelMultipleChoiceField)
        self.assertEqual(field.label, "VLANs")

        field = self.o2m_1.to_form_field("destination")
        self.assertFalse(field.required)
        self.assertIsInstance(field, DynamicModelChoiceField)
        self.assertEqual(field.label, "site")


class RelationshipAssociationTest(RelationshipBaseTest):
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
        cra.clean()
        cra.save()

        cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[1], destination=self.sites[1])
        cra.clean()
        cra.save()

        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[0], destination=self.sites[2])
            cra.clean()

        expected_errors = {
            "source": ["Unable to create more than one Primary Rack per Site association to Rack A (source)"]
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2o_1, source=self.racks[2], destination=self.sites[0])
            cra.clean()
        expected_errors = {
            "destination": ["Unable to create more than one Primary Rack per Site association to Site A (destination)"]
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_clean_check_quantity_o2m(self):
        """Validate that one-to-many relationships can't have more than one relationship association per source."""

        cra = RelationshipAssociation(relationship=self.o2m_1, source=self.sites[0], destination=self.vlans[0])
        cra.clean()
        cra.save()

        cra = RelationshipAssociation(relationship=self.o2m_1, source=self.sites[0], destination=self.vlans[1])
        cra.clean()
        cra.save()

        cra = RelationshipAssociation(relationship=self.o2m_1, source=self.sites[1], destination=self.vlans[2])
        cra.clean()
        cra.save()

        with self.assertRaises(ValidationError) as handler:
            cra = RelationshipAssociation(relationship=self.o2m_1, source=self.sites[2], destination=self.vlans[0])
            cra.clean()
        expected_errors = {
            "destination": [
                "Unable to create more than one generic site to vlan association to VLAN A (100) (destination)",
            ],
        }
        self.assertEqual(handler.exception.message_dict, expected_errors)

    def test_clean_check_quantity_m2m(self):
        """Validate that many-to-many relationship can have many relationship associations."""
        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0])
        cra.clean()
        cra.save()

        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[1])
        cra.clean()
        cra.save()

        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[1], destination=self.vlans[2])
        cra.clean()
        cra.save()

        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[2], destination=self.vlans[0])
        cra.clean()

    def test_get_peer(self):
        """Validate that the get_peer() method works correctly."""
        cra = RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0])
        cra.save()

        self.assertEqual(cra.get_peer(self.racks[0]), self.vlans[0])
        self.assertEqual(cra.get_peer(self.vlans[0]), self.racks[0])
        self.assertEqual(cra.get_peer(self.vlans[1]), None)

    def test_delete_cascade(self):
        """Verify that a RelationshipAssociation is deleted if either of the associated records is deleted."""
        RelationshipAssociation.objects.create(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0])
        RelationshipAssociation.objects.create(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[1])
        RelationshipAssociation.objects.create(relationship=self.m2m_1, source=self.racks[1], destination=self.vlans[0])

        self.assertEqual(3, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when their 'source' object is deleted
        self.racks[0].delete()

        # Both relations involving racks[0] should have been deleted
        # The relation between racks[1] and vlans[0] should remain
        self.assertEqual(1, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when their 'destination' object is deleted
        self.vlans[0].delete()

        self.assertEqual(0, RelationshipAssociation.objects.count())

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
