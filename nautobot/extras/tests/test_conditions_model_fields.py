"""Tests for `nautobot.extras.conditions.model_fields`."""

from django.contrib.contenttypes.models import ContentType
from django.test import tag

from nautobot.core.models.utils import serialize_object_v2
from nautobot.core.testing import TestCase as NautobotTestCase
from nautobot.dcim.models import CablePath, Device, Location, LocationType
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.conditions.model_fields import _where_values_are_listed, addressable_fields
from nautobot.extras.models import CustomField, CustomFieldChoice, Status


@tag("unit")
class AddressableFieldsTest(NautobotTestCase):
    """What the field picker offers has to be what a change record holds, name for name."""

    @classmethod
    def setUpTestData(cls):
        status_note = CustomField.objects.create(label="Status Note", type=CustomFieldTypeChoices.TYPE_TEXT)
        status_note.content_types.add(ContentType.objects.get_for_model(Status))
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
        """A serializer also declares fields only an annotated queryset fills in, and those never appear.

        A custom field is offered under its own path, so each name folds back to the key the record holds.
        """
        for label, entries, record in (
            ("the record itself", addressable_fields(Location), self.record),
            ("what it nests under a relation", self.entry("status")["subfields"], self.record["status"]),
        ):
            with self.subTest(label):
                self.assertEqual({entry["name"].partition(".")[0] for entry in entries}, set(record))

    def test_a_field_holding_json_is_not_offered(self):
        self.assertNotIn("local_config_context_data", {entry["name"] for entry in addressable_fields(Device)})
        platform = self.entry("platform", Device)
        self.assertNotIn("napalm_args", {sub["name"] for sub in platform["subfields"]})

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

    def test_a_many_valued_relation_says_where_its_objects_can_be_read(self):
        """Only the tags a location can hold, the same narrowing the filter form asks for."""
        self.assertEqual(self.entry("tags")["values_url"], "/api/extras/tags/?content_types=dcim.location")

    def test_a_many_valued_relation_offers_no_sub_field(self):
        """A many-valued relation is compared whole, so `status` keeps its sub-fields and `tags` has none."""
        self.assertNotIn("subfields", self.entry("tags"))
        self.assertIn("subfields", self.entry("status"))

    def test_a_relation_with_no_list_endpoint_says_its_objects_cannot_be_read(self):
        """A picker needs somewhere to call. `CablePath` has no API list route, so there is nowhere."""
        self.assertIsNone(_where_values_are_listed(Location, "status", CablePath, ["dcim.location"]))

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


@tag("unit")
class CustomFieldsOfferedTest(NautobotTestCase):
    """A custom field is offered as a field of its own, named for the path a condition stores."""

    # The kind each type compares as, or None where no operator compares it and the field is left out.
    KIND_BY_TYPE = {
        CustomFieldTypeChoices.TYPE_TEXT: "text",
        CustomFieldTypeChoices.TYPE_URL: "text",
        CustomFieldTypeChoices.TYPE_MARKDOWN: "text",
        CustomFieldTypeChoices.TYPE_SELECT: "text",
        CustomFieldTypeChoices.TYPE_MULTISELECT: "list",
        CustomFieldTypeChoices.TYPE_INTEGER: "number",
        CustomFieldTypeChoices.TYPE_BOOLEAN: "boolean",
        CustomFieldTypeChoices.TYPE_DATE: "date",
        CustomFieldTypeChoices.TYPE_DATETIME: "date",
        CustomFieldTypeChoices.TYPE_JSON: None,
    }

    @classmethod
    def setUpTestData(cls):
        location_content_type = ContentType.objects.get_for_model(Location)
        cls.custom_fields = {}
        for custom_field_type, label in CustomFieldTypeChoices.CHOICES:
            custom_field = CustomField.objects.create(label=f"Offered {label}", type=custom_field_type)
            custom_field.content_types.add(location_content_type)
            cls.custom_fields[custom_field_type] = custom_field
        for custom_field_type in CustomFieldTypeChoices.SELECTION_TYPES:
            CustomFieldChoice.objects.create(custom_field=cls.custom_fields[custom_field_type], value="Chosen")

    def entry(self, custom_field):
        """What the picker offers for that custom field, or None where it offers nothing."""
        name = f"custom_fields.{custom_field.key}"
        return next((entry for entry in addressable_fields(Location) if entry["name"] == name), None)

    def test_each_type_carries_the_kind_and_the_label(self):
        """The table covers every type, because one nobody classified would be offered with every operator
        and a box to type into.
        """
        self.assertEqual(set(self.KIND_BY_TYPE), {value for value, _ in CustomFieldTypeChoices.CHOICES})
        for custom_field_type, kind in self.KIND_BY_TYPE.items():
            with self.subTest(custom_field_type):
                custom_field = self.custom_fields[custom_field_type]
                entry = self.entry(custom_field)
                if kind is None:
                    self.assertIsNone(entry)
                else:
                    self.assertEqual(entry["kind"], kind)
                    self.assertEqual(entry["label"], custom_field.label)

    def test_only_a_type_with_choices_says_where_they_can_be_read(self):
        """A form offers the choices themselves rather than asking somebody to type one exactly."""
        for custom_field_type in (*CustomFieldTypeChoices.SELECTION_TYPES, CustomFieldTypeChoices.TYPE_TEXT):
            with self.subTest(custom_field_type):
                custom_field = self.custom_fields[custom_field_type]
                expected = f"/api/extras/custom-field-choices/?custom_field={custom_field.key}"
                if custom_field_type in CustomFieldTypeChoices.SELECTION_TYPES:
                    self.assertEqual(self.entry(custom_field)["values_url"], expected)
                else:
                    self.assertNotIn("values_url", self.entry(custom_field))
