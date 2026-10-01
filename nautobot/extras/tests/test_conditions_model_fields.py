"""Tests for `nautobot.extras.conditions.model_fields`."""

from django.test import tag

from nautobot.core.models.utils import serialize_object_v2
from nautobot.core.testing import TestCase as NautobotTestCase
from nautobot.dcim.models import Device, Location, LocationType
from nautobot.extras.conditions.model_fields import addressable_fields
from nautobot.extras.models import Status


@tag("unit")
class AddressableFieldsTest(NautobotTestCase):
    """What the field picker offers has to be what a change record holds, name for name."""

    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.create(
            name="Addressable Fields Test",
            location_type=LocationType.objects.create(name="Addressable Fields Test Type"),
            status=Status.objects.get_for_model(Location).first(),
        )
        cls.record = serialize_object_v2(cls.location)

    def entry(self, name, *models):
        """One field of what the picker offers, by name. Against `Location` unless told otherwise."""
        return next(entry for entry in addressable_fields(*models or (Location,)) if entry["name"] == name)

    def test_every_field_is_one_the_record_carries(self):
        """A serializer also declares fields only an annotated queryset fills in, and those never appear."""
        self.assertEqual({field["name"] for field in addressable_fields(Location)}, set(self.record))

    def test_a_relation_offers_what_the_record_nests_under_it(self):
        self.assertEqual({sub["name"] for sub in self.entry("status")["subfields"]}, set(self.record["status"]))

    def test_a_relation_inside_a_relation_is_not_offered(self):
        """A path that stops at a mapping matches nothing, so going deeper would only mislead."""
        self.assertNotIn("parent", {sub["name"] for sub in self.entry("location_type")["subfields"]})

    def test_each_field_carries_the_kind_its_operators_are_chosen_by(self):
        """An unknown kind is left out, because `operators_for_kind` then offers everything, which beats
        guessing wrong."""
        for name, kind in (
            ("name", "text"),
            ("asn", "number"),
            ("created", "date"),
            ("tags", "list"),
            ("display", None),
            ("status", None),
        ):
            with self.subTest(name):
                self.assertEqual(self.entry(name).get("kind"), kind)

    def test_a_subfield_carries_its_kind_too(self):
        subfields = {sub["name"]: sub.get("kind") for sub in self.entry("status")["subfields"]}
        for name, kind in (("color", "text"), ("last_updated", "date")):
            with self.subTest(name):
                self.assertEqual(subfields[name], kind)

    def test_a_relation_says_where_its_objects_can_be_read(self):
        """A form offers the values themselves rather than asking somebody to type a name exactly."""
        self.assertEqual(self.entry("location_type")["values_url"], "/api/dcim/location-types/")

    def test_a_relation_declared_per_object_type_is_narrowed_to_the_types_watched(self):
        """Offering a status no location can hold would only invite a rule that never runs."""
        for label, models, url in (
            ("one type", (Location,), "/api/extras/statuses/?content_types=dcim.location"),
            (
                "two types",
                (Location, Device),
                "/api/extras/statuses/?content_types=dcim.location&content_types=dcim.device",
            ),
        ):
            with self.subTest(label):
                self.assertEqual(self.entry("status", *models)["values_url"], url)

    def test_a_colour_field_asks_for_a_swatch_picker(self):
        """It is text to compare, but a form has a swatch picker for it rather than a box for hex."""
        subfields = {sub["name"]: sub for sub in self.entry("status")["subfields"]}
        self.assertEqual(subfields["color"]["picker"], "color")
        self.assertEqual(subfields["color"]["kind"], "text")
        self.assertNotIn("picker", subfields["name"])

    def test_several_models_offer_only_what_they_share(self):
        """One condition is checked against every selected object type."""
        shared = {field["name"] for field in addressable_fields(Location, Device)}
        location_only = {field["name"] for field in addressable_fields(Location)} - shared

        self.assertIn("name", shared)
        self.assertIn("asn", location_only)
        self.assertEqual(shared, {field["name"] for field in addressable_fields(Device)} & set(self.record))
