import logging
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse

from nautobot.dcim.models import Site, Rack
from nautobot.ipam.models import VLAN
from nautobot.extras.choices import RelationshipTypeChoices
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

        self.sites = [
            Site.objects.create(name="Site A", slug="site-a"),
            Site.objects.create(name="Site B", slug="site-b"),
            Site.objects.create(name="Site C", slug="site-c"),
            Site.objects.create(name="Site D", slug="site-d"),
            Site.objects.create(name="Site E", slug="site-e"),
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

        self.m2m_1 = Relationship(
            name="Vlan to Rack",
            slug="vlan-rack",
            source_type=self.rack_ct,
            source_label="My Vlans",
            source_filter={"site": ["site-a"]},
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
            source_filter={"name": ["site-b"]},
            destination_type=self.rack_ct,
            destination_filter={"site": ["site-a"]},
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
        self.assertEqual(field.query_params, {"site": ["site-a"]})

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
            "destination": ["Unable to create more than one Primary Rack per Site association to Site A (destination)"]
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
        expected_errors = {"__all__": ["A Related Sites association already exists between Site B and Site A"]}
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
        associations = [
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[0]),
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[0], destination=self.vlans[1]),
            RelationshipAssociation(relationship=self.m2m_1, source=self.racks[1], destination=self.vlans[0]),
            # Create an association loop just to make sure it works correctly on deletion
            RelationshipAssociation(relationship=self.o2o_2, source=self.sites[2], destination=self.sites[3]),
            RelationshipAssociation(relationship=self.o2o_2, source=self.sites[3], destination=self.sites[2]),
        ]
        for association in associations:
            association.validated_save()
        # Create a self-referential association as well; validated_save() would correctly reject this one as invalid
        RelationshipAssociation.objects.create(relationship=self.o2o_2, source=self.sites[4], destination=self.sites[4])

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
        self.sites[3].delete()
        self.assertEqual(1 + initial_count, RelationshipAssociation.objects.count())

        # Test automatic deletion of RelationshipAssociations when the same object is both source and destination
        self.sites[4].delete()
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
