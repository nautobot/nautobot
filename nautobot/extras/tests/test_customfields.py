import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.forms import ChoiceField, IntegerField, NumberInput
from django.urls import reverse
from rest_framework import status
from nautobot.core.forms.widgets import MultiValueCharInput, StaticSelect2

from nautobot.circuits.models import Provider
from nautobot.core.models.fields import slugify_dashes_to_underscores
from nautobot.core.tables import CustomFieldColumn
from nautobot.core.testing import APITestCase, TestCase, TransactionTestCase
from nautobot.core.testing.models import ModelTestCases
from nautobot.core.testing.utils import post_data
from nautobot.dcim.filters import LocationFilterSet
from nautobot.dcim.forms import RackFilterForm
from nautobot.dcim.models import Device, Location, LocationType, Rack
from nautobot.dcim.tables import LocationTable
from nautobot.extras.choices import CustomFieldTypeChoices, CustomFieldFilterLogicChoices
from nautobot.extras.models import ComputedField, CustomField, CustomFieldChoice, Status
from nautobot.users.models import ObjectPermission
from nautobot.virtualization.models import VirtualMachine


# TODO: this needs to be both a BaseModelTestCase (as it tests the model class) and a (views) TestCase,
#       (due to the test_multi_select_field_value_after_bulk_update() test).
#       At some point we should probably split this into separate classes.
class CustomFieldTest(ModelTestCases.BaseModelTestCase, TestCase):
    model = CustomField

    def setUp(self):
        super().setUp()
        location_status = Status.objects.get_for_model(Location).first()
        lt = LocationType.objects.get(name="Campus")
        Location.objects.create(name="Location A", status=location_status, location_type=lt)
        Location.objects.create(name="Location B", status=location_status, location_type=lt)
        Location.objects.create(name="Location C", status=location_status, location_type=lt)

    def test_immutable_fields(self):
        """Some fields may not be changed once set, due to the potential for complex downstream effects."""
        instance = CustomField(
            # 2.0 TODO: #824 remove name field
            label="Custom Field",
            key="custom_field",
            type=CustomFieldTypeChoices.TYPE_TEXT,
        )
        instance.validated_save()

        instance.refresh_from_db()
        instance.key = "custom_field_2"
        with self.assertRaises(ValidationError):
            instance.validated_save()

        instance.refresh_from_db()
        instance.type = CustomFieldTypeChoices.TYPE_SELECT
        with self.assertRaises(ValidationError):
            instance.validated_save()

    def test_simple_fields(self):
        DATA = (
            {
                "field_type": CustomFieldTypeChoices.TYPE_TEXT,
                "field_value": "Foobar!",
                "empty_value": "",
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_INTEGER,
                "field_value": 0,
                "empty_value": None,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_INTEGER,
                "field_value": 42,
                "empty_value": None,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_BOOLEAN,
                "field_value": True,
                "empty_value": None,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_BOOLEAN,
                "field_value": False,
                "empty_value": None,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_DATE,
                "field_value": "2016-06-23",
                "empty_value": None,
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_URL,
                "field_value": "http://example.com/",
                "empty_value": "",
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_JSON,
                "field_value": {"dict_key": "key value"},
                "empty_value": "",
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_JSON,
                "field_value": ["a", "list"],
                "empty_value": "",
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_JSON,
                "field_value": "A string",
                "empty_value": "",
            },
            {
                "field_type": CustomFieldTypeChoices.TYPE_JSON,
                "field_value": None,
                "empty_value": "",
            },
        )

        obj_type = ContentType.objects.get_for_model(Location)

        for data in DATA:
            cf = CustomField(type=data["field_type"], label="My Field", required=False)
            cf.save()  # not validated_save this time, as we're testing backwards-compatibility
            cf.content_types.set([obj_type])
            # Assert that key was auto-populated correctly
            cf.refresh_from_db()
            self.assertEqual(cf.key, slugify_dashes_to_underscores(cf.label))

            # Assign a value to the first Location
            location = Location.objects.get(name="Location A")
            location.cf[cf.key] = data["field_value"]
            location.validated_save()

            # Retrieve the stored value
            location.refresh_from_db()
            self.assertEqual(location.cf[cf.key], data["field_value"])

            # Delete the stored value
            location.cf.pop(cf.key)
            location.save()
            location.refresh_from_db()
            self.assertIsNone(location.cf.get(cf.key))

            # Delete the custom field
            cf.delete()

    def test_select_field(self):
        obj_type = ContentType.objects.get_for_model(Location)

        # Create a custom field
        cf = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            label="My Field",
            required=False,
        )
        cf.save()
        cf.content_types.set([obj_type])

        CustomFieldChoice.objects.create(custom_field=cf, value="Option A")
        CustomFieldChoice.objects.create(custom_field=cf, value="Option B")
        CustomFieldChoice.objects.create(custom_field=cf, value="Option C")

        # Assign a value to the first Location
        location = Location.objects.get(name="Location A")
        location.cf[cf.key] = "Option A"
        location.validated_save()

        # Retrieve the stored value
        location.refresh_from_db()
        self.assertEqual(location.cf[cf.key], "Option A")

        # Delete the stored value
        location.cf.pop(cf.key)
        location.save()
        location.refresh_from_db()
        self.assertIsNone(location.cf.get(cf.key))

        # Delete the custom field
        cf.delete()

    def test_multi_select_field(self):
        obj_type = ContentType.objects.get_for_model(Location)

        # Create a custom field
        cf = CustomField(
            type=CustomFieldTypeChoices.TYPE_MULTISELECT,
            label="My Field",
            required=False,
        )
        cf.save()
        cf.content_types.set([obj_type])

        CustomFieldChoice.objects.create(custom_field=cf, value="Option A")
        CustomFieldChoice.objects.create(custom_field=cf, value="Option B")
        CustomFieldChoice.objects.create(custom_field=cf, value="Option C")

        # Assign a value to the first Location
        location = Location.objects.get(name="Location A")
        location.cf[cf.key] = ["Option A", "Option B"]
        location.validated_save()

        # Retrieve the stored value
        location.refresh_from_db()
        self.assertEqual(location.cf[cf.key], ["Option A", "Option B"])

        # Delete the stored value
        location.cf.pop(cf.key)
        location.save()
        location.refresh_from_db()
        self.assertIsNone(location.cf.get(cf.key))

        # Delete the custom field
        cf.delete()

    def test_multi_select_field_value_after_bulk_update(self):
        obj_type = ContentType.objects.get_for_model(Location)

        # Create a custom field
        cf = CustomField(
            type=CustomFieldTypeChoices.TYPE_MULTISELECT,
            label="My Field",
            required=False,
        )
        cf.save()
        cf.content_types.set([obj_type])
        CustomFieldChoice.objects.create(custom_field=cf, value="Option A")
        CustomFieldChoice.objects.create(custom_field=cf, value="Option B")
        CustomFieldChoice.objects.create(custom_field=cf, value="Option C")
        cf.validated_save()

        # Assign values to all locations
        locations = Location.objects.all()
        for location in locations:
            location.cf[cf.key] = ["Option A", "Option B", "Option C"]
            location.validated_save()

            # Retrieve the stored value
            location.refresh_from_db()
            self.assertEqual(location.cf[cf.key], ["Option A", "Option B", "Option C"])

        pk_list = list(Location.objects.values_list("pk", flat=True))
        data = {
            "pk": pk_list,
            "_apply": True,  # Form button
        }
        # set my_field to [] to emulate form submission when the user does not make any changes to the multiselect cf.
        bulk_edit_data = {
            cf.add_prefix_to_cf_key(): [],
        }
        # Append the form data to the request
        data.update(post_data(bulk_edit_data))
        # Assign model-level permission
        obj_perm = ObjectPermission(
            name="Test permission",
            actions=["view", "change"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Location))

        # Try POST with model-level permission
        bulk_edit_url = reverse("dcim:location_bulk_edit")
        self.assertHttpStatus(self.client.post(bulk_edit_url, data), 302)

        # Assert the values are unchanged after bulk edit
        for location in locations:
            location.refresh_from_db()
            self.assertEqual(location.cf[cf.key], ["Option A", "Option B", "Option C"])

        cf.delete()

    def test_text_field_value(self):
        obj_type = ContentType.objects.get_for_model(Location)

        # Create a custom field
        cf = CustomField(
            type=CustomFieldTypeChoices.TYPE_TEXT,
            label="My Text Field",
            required=False,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Assign a disallowed value (list) to the first Location
        location = Location.objects.get(name="Location A")
        location.cf[cf.key] = ["I", "am", "a", "list"]
        with self.assertRaises(ValidationError) as context:
            location.validated_save()
        self.assertIn("Value must be a string", str(context.exception))

        # Assign another disallowed value (int) to the first Location
        location.cf[cf.key] = 2
        with self.assertRaises(ValidationError) as context:
            location.validated_save()
        self.assertIn("Value must be a string", str(context.exception))

        # Assign another disallowed value (bool) to the first Location
        location.cf[cf.key] = True
        with self.assertRaises(ValidationError) as context:
            location.validated_save()
        self.assertIn("Value must be a string", str(context.exception))

        # Delete the stored value
        location.cf.pop(cf.key)
        location.save()
        location.refresh_from_db()
        self.assertIsNone(location.cf.get(cf.key))

        # Delete the custom field
        cf.delete()

    def test_regex_validation(self):
        obj_type = ContentType.objects.get_for_model(Location)

        for cf_type in CustomFieldTypeChoices.REGEX_TYPES:
            # validation for select and multi-select are performed on the CustomFieldChoice model
            if "select" in cf_type:
                continue

            # Create a custom field
            cf = CustomField(
                type=cf_type,
                label=f"cf_test_{cf_type}",
                required=False,
                validation_regex="A.C[01]x?",
            )
            cf.save()
            cf.content_types.set([obj_type])

            # Assign values to the first Location
            location = Location.objects.first()

            non_matching_values = ["abc1", "AC1", "00AbC", "abc1x", "00abc1x00"]
            error_message = f"Value must match regex '{cf.validation_regex}'"
            for value in non_matching_values:
                with self.subTest(cf_type=cf_type, value=value):
                    with self.assertRaisesMessage(ValidationError, error_message):
                        location.cf[cf.key] = value
                        location.validated_save()

            matching_values = ["ABC1", "00AbC0", "00ABC0x00"]
            for value in matching_values:
                with self.subTest(cf_type=cf_type, value=value):
                    location.cf[cf.key] = value
                    location.validated_save()

            # Delete the custom field
            cf.delete()

    def test_to_filter_field(self):
        with self.subTest("Assert CustomField Select Type renders the correct filter form field and widget"):
            # Assert a Select Choice Field
            ct = ContentType.objects.get_for_model(Device)
            custom_field_select = CustomField(
                type=CustomFieldTypeChoices.TYPE_SELECT,
                label="Select Field",
            )
            custom_field_select.save()
            custom_field_select.content_types.set([ct])
            CustomFieldChoice.objects.create(custom_field=custom_field_select, value="Foo")
            CustomFieldChoice.objects.create(custom_field=custom_field_select, value="Bar")
            CustomFieldChoice.objects.create(custom_field=custom_field_select, value="Baz")
            filter_field = custom_field_select.to_filter_form_field()
            self.assertIsInstance(filter_field, ChoiceField)
            self.assertIsInstance(filter_field.widget, StaticSelect2)
            self.assertEqual(filter_field.widget.choices, [("Bar", "Bar"), ("Baz", "Baz"), ("Foo", "Foo")])
            # Assert Choice Custom Field with lookup-expr other than exact returns a
            filter_field_with_lookup_expr = custom_field_select.to_filter_form_field(lookup_expr="icontains")
            self.assertIsInstance(filter_field_with_lookup_expr, ChoiceField)
            self.assertIsInstance(filter_field_with_lookup_expr.widget, MultiValueCharInput)

        with self.subTest("Assert CustomField Integer Type renders the correct filter form field and widget"):
            custom_field_integer = CustomField(
                type=CustomFieldTypeChoices.TYPE_INTEGER,
                label="integer_field",
            )
            custom_field_integer.save()
            custom_field_integer.content_types.set([ct])
            filter_field = custom_field_integer.to_filter_form_field()
            self.assertIsInstance(filter_field, IntegerField)
            self.assertIsInstance(filter_field.widget, NumberInput)


class CustomFieldManagerTest(TestCase):
    def setUp(self):
        content_type = ContentType.objects.get_for_model(Location)
        custom_field = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, label="Text Field", default="foo")
        custom_field.save()
        custom_field.content_types.set([content_type])

    def test_get_for_model(self):
        self.assertEqual(CustomField.objects.get_for_model(Location).count(), 2)
        self.assertEqual(CustomField.objects.get_for_model(VirtualMachine).count(), 0)


class CustomFieldDataAPITest(APITestCase):
    """
    Check that object representations in the REST API include their custom field data.

    For tests of the api/extras/custom-fields/ REST API endpoint itself, see test_api.py.
    """

    @classmethod
    def setUpTestData(cls):
        content_type = ContentType.objects.get_for_model(Location)

        # Text custom field
        cls.cf_text = CustomField(
            type=CustomFieldTypeChoices.TYPE_TEXT, label="Text Field", key="text_cf", default="foo"
        )
        cls.cf_text.save()
        cls.cf_text.content_types.set([content_type])

        # Integer custom field
        cls.cf_integer = CustomField(
            type=CustomFieldTypeChoices.TYPE_INTEGER, label="Number Field", key="number_cf", default=123
        )
        cls.cf_integer.save()
        cls.cf_integer.content_types.set([content_type])

        # Boolean custom field
        cls.cf_boolean = CustomField(
            type=CustomFieldTypeChoices.TYPE_BOOLEAN,
            label="Boolean Field",
            key="boolean_cf",
            default=False,
        )
        cls.cf_boolean.save()
        cls.cf_boolean.content_types.set([content_type])

        # Date custom field
        cls.cf_date = CustomField(
            type=CustomFieldTypeChoices.TYPE_DATE,
            label="Date Field",
            key="date_cf",
            default="2020-01-01",
        )
        cls.cf_date.save()
        cls.cf_date.content_types.set([content_type])

        # URL custom field
        cls.cf_url = CustomField(
            type=CustomFieldTypeChoices.TYPE_URL,
            label="URL Field",
            key="url_cf",
            default="http://example.com/1",
        )
        cls.cf_url.save()
        cls.cf_url.content_types.set([content_type])

        # Select custom field
        cls.cf_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            label="Choice Field",
            key="choice_cf",
        )
        cls.cf_select.save()
        cls.cf_select.content_types.set([content_type])
        CustomFieldChoice.objects.create(custom_field=cls.cf_select, value="Foo")
        CustomFieldChoice.objects.create(custom_field=cls.cf_select, value="Bar")
        CustomFieldChoice.objects.create(custom_field=cls.cf_select, value="Baz")
        cls.cf_select.default = "Foo"
        cls.cf_select.save()

        # Multi-select custom field
        cls.cf_multi_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_MULTISELECT,
            label="Multiple Choice Field",
            key="multi_choice_cf",
        )
        cls.cf_multi_select.save()
        cls.cf_multi_select.content_types.set([content_type])
        CustomFieldChoice.objects.create(custom_field=cls.cf_multi_select, value="Foo")
        CustomFieldChoice.objects.create(custom_field=cls.cf_multi_select, value="Bar")
        CustomFieldChoice.objects.create(custom_field=cls.cf_multi_select, value="Baz")
        cls.cf_multi_select.default = ["Foo", "Bar"]
        cls.cf_multi_select.save()

        if "example_plugin" in settings.PLUGINS:
            cls.cf_plugin_field = CustomField.objects.get(key="example_plugin_auto_custom_field")

        cls.statuses = Status.objects.get_for_model(Location)

        # Create some locations
        cls.lt = LocationType.objects.get(name="Campus")
        cls.locations = (
            Location.objects.create(name="Location 1", status=cls.statuses[0], location_type=cls.lt),
            Location.objects.create(name="Location 2", status=cls.statuses[0], location_type=cls.lt),
        )

        # Assign custom field values for location 2
        cls.locations[1]._custom_field_data = {
            cls.cf_text.key: "bar",
            cls.cf_integer.key: 456,
            cls.cf_boolean.key: True,
            cls.cf_date.key: "2020-01-02",
            cls.cf_url.key: "http://example.com/2",
            cls.cf_select.key: "Bar",
            cls.cf_multi_select.key: ["Bar", "Baz"],
        }
        if "example_plugin" in settings.PLUGINS:
            cls.locations[1]._custom_field_data[cls.cf_plugin_field.key] = "Custom value"
        cls.locations[1].save()

    def test_get_single_object_without_custom_field_data(self):
        """
        Validate that custom fields are present on an object even if it has no values defined.
        """
        url = reverse("dcim-api:location-detail", kwargs={"pk": self.locations[0].pk})
        self.add_permissions("dcim.view_location")

        response = self.client.get(url, **self.header)
        self.assertEqual(response.data["name"], self.locations[0].name)
        # A model directly instantiated via the ORM does NOT automatically receive custom field default values.
        # This is arguably a bug. See https://github.com/nautobot/nautobot/issues/3312 for details.
        expected_data = {
            "text_cf": None,
            "number_cf": None,
            "boolean_cf": None,
            "date_cf": None,
            "url_cf": None,
            "choice_cf": None,
            "multi_choice_cf": None,
        }
        if "example_plugin" in settings.PLUGINS:
            expected_data["example_plugin_auto_custom_field"] = None
        self.assertEqual(response.data["custom_fields"], expected_data)

    def test_get_single_object_with_custom_field_data(self):
        """
        Validate that custom fields are present and correctly set for an object with values defined.
        """
        location2_cfvs = self.locations[1].cf
        url = reverse("dcim-api:location-detail", kwargs={"pk": self.locations[1].pk})
        self.add_permissions("dcim.view_location")

        response = self.client.get(url, **self.header)
        self.assertEqual(response.data["name"], self.locations[1].name)
        self.assertEqual(response.data["custom_fields"]["text_cf"], location2_cfvs["text_cf"])
        self.assertEqual(response.data["custom_fields"]["number_cf"], location2_cfvs["number_cf"])
        self.assertEqual(response.data["custom_fields"]["boolean_cf"], location2_cfvs["boolean_cf"])
        self.assertEqual(response.data["custom_fields"]["date_cf"], location2_cfvs["date_cf"])
        self.assertEqual(response.data["custom_fields"]["url_cf"], location2_cfvs["url_cf"])
        self.assertEqual(response.data["custom_fields"]["choice_cf"], location2_cfvs["choice_cf"])
        self.assertEqual(response.data["custom_fields"]["multi_choice_cf"], location2_cfvs["multi_choice_cf"])

    def test_create_single_object_with_defaults(self):
        """
        Create a new location with no specified custom field values and check that it received the default values.
        """
        data = {
            "name": "Location 3",
            "location_type": self.lt.pk,
            "status": self.statuses[0].pk,
        }
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        # Validate response data
        response_cf = response.data["custom_fields"]
        self.assertEqual(response_cf["text_cf"], self.cf_text.default)
        self.assertEqual(response_cf["number_cf"], self.cf_integer.default)
        self.assertEqual(response_cf["boolean_cf"], self.cf_boolean.default)
        self.assertEqual(response_cf["date_cf"], self.cf_date.default)
        self.assertEqual(response_cf["url_cf"], self.cf_url.default)
        self.assertEqual(response_cf["choice_cf"], self.cf_select.default)
        self.assertEqual(response_cf["multi_choice_cf"], self.cf_multi_select.default)
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(response_cf["example_plugin_auto_custom_field"], self.cf_plugin_field.default)

        # Validate database data
        location = Location.objects.get(pk=response.data["id"])
        self.assertEqual(location.cf["text_cf"], self.cf_text.default)
        self.assertEqual(location.cf["number_cf"], self.cf_integer.default)
        self.assertEqual(location.cf["boolean_cf"], self.cf_boolean.default)
        self.assertEqual(str(location.cf["date_cf"]), self.cf_date.default)
        self.assertEqual(location.cf["url_cf"], self.cf_url.default)
        self.assertEqual(location.cf["choice_cf"], self.cf_select.default)
        self.assertEqual(location.cf["multi_choice_cf"], self.cf_multi_select.default)
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(location.cf["example_plugin_auto_custom_field"], self.cf_plugin_field.default)

    def test_create_single_object_with_values(self):
        """
        Create a single new location with a value for each type of custom field.
        """
        data = {
            "name": "Location 3",
            "status": self.statuses[0].pk,
            "location_type": self.lt.pk,
            "custom_fields": {
                "text_cf": "bar",
                "number_cf": 456,
                "boolean_cf": True,
                "date_cf": "2020-01-02",
                "url_cf": "http://example.com/2",
                "choice_cf": "Bar",
                "multi_choice_cf": ["Baz"],
            },
        }
        if "example_plugin" in settings.PLUGINS:
            data["custom_fields"]["example_plugin_auto_custom_field"] = "Custom value"
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        # Validate response data
        response_cf = response.data["custom_fields"]
        data_cf = data["custom_fields"]
        self.assertEqual(response_cf["text_cf"], data_cf["text_cf"])
        self.assertEqual(response_cf["number_cf"], data_cf["number_cf"])
        self.assertEqual(response_cf["boolean_cf"], data_cf["boolean_cf"])
        self.assertEqual(response_cf["date_cf"], data_cf["date_cf"])
        self.assertEqual(response_cf["url_cf"], data_cf["url_cf"])
        self.assertEqual(response_cf["choice_cf"], data_cf["choice_cf"])
        self.assertEqual(response_cf["multi_choice_cf"], data_cf["multi_choice_cf"])
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(
                response_cf["example_plugin_auto_custom_field"], data_cf["example_plugin_auto_custom_field"]
            )

        # Validate database data
        location = Location.objects.get(pk=response.data["id"])
        self.assertEqual(location.cf["text_cf"], data_cf["text_cf"])
        self.assertEqual(location.cf["number_cf"], data_cf["number_cf"])
        self.assertEqual(location.cf["boolean_cf"], data_cf["boolean_cf"])
        self.assertEqual(str(location.cf["date_cf"]), data_cf["date_cf"])
        self.assertEqual(location.cf["url_cf"], data_cf["url_cf"])
        self.assertEqual(location.cf["choice_cf"], data_cf["choice_cf"])
        self.assertEqual(location.cf["multi_choice_cf"], data_cf["multi_choice_cf"])
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(
                location.cf["example_plugin_auto_custom_field"], data_cf["example_plugin_auto_custom_field"]
            )

    def test_create_multiple_objects_with_defaults(self):
        """
        Create three news locations with no specified custom field values and check that each received
        the default custom field values.
        """
        data = (
            {
                "name": "Location 3",
                "location_type": self.lt.pk,
                "status": self.statuses[0].pk,
            },
            {
                "name": "Location 4",
                "location_type": self.lt.pk,
                "status": self.statuses[0].pk,
            },
            {
                "name": "Location 5",
                "location_type": self.lt.pk,
                "status": self.statuses[0].pk,
            },
        )
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), len(data))

        for i, _obj in enumerate(data):
            # Validate response data
            response_cf = response.data[i]["custom_fields"]
            self.assertEqual(response_cf["text_cf"], self.cf_text.default)
            self.assertEqual(response_cf["number_cf"], self.cf_integer.default)
            self.assertEqual(response_cf["boolean_cf"], self.cf_boolean.default)
            self.assertEqual(response_cf["date_cf"], self.cf_date.default)
            self.assertEqual(response_cf["url_cf"], self.cf_url.default)
            self.assertEqual(response_cf["choice_cf"], self.cf_select.default)
            self.assertEqual(response_cf["multi_choice_cf"], self.cf_multi_select.default)
            if "example_plugin" in settings.PLUGINS:
                self.assertEqual(response_cf["example_plugin_auto_custom_field"], self.cf_plugin_field.default)

            # Validate database data
            location = Location.objects.get(pk=response.data[i]["id"])
            self.assertEqual(location.cf["text_cf"], self.cf_text.default)
            self.assertEqual(location.cf["number_cf"], self.cf_integer.default)
            self.assertEqual(location.cf["boolean_cf"], self.cf_boolean.default)
            self.assertEqual(str(location.cf["date_cf"]), self.cf_date.default)
            self.assertEqual(location.cf["url_cf"], self.cf_url.default)
            self.assertEqual(location.cf["choice_cf"], self.cf_select.default)
            self.assertEqual(location.cf["multi_choice_cf"], self.cf_multi_select.default)
            if "example_plugin" in settings.PLUGINS:
                self.assertEqual(location.cf["example_plugin_auto_custom_field"], self.cf_plugin_field.default)

    def test_create_multiple_objects_with_values(self):
        """
        Create a three new locations, each with custom fields defined.
        """
        custom_field_data = {
            "text_cf": "bar",
            "number_cf": 456,
            "boolean_cf": True,
            "date_cf": "2020-01-02",
            "url_cf": "http://example.com/2",
            "choice_cf": "Bar",
            "multi_choice_cf": ["Foo", "Bar"],
        }
        if "example_plugin" in settings.PLUGINS:
            custom_field_data["example_plugin_auto_custom_field"] = "Custom value"
        data = (
            {
                "name": "Location 3",
                "status": self.statuses.first().pk,
                "location_type": self.lt.pk,
                "custom_fields": custom_field_data,
            },
            {
                "name": "Location 4",
                "status": self.statuses.first().pk,
                "location_type": self.lt.pk,
                "custom_fields": custom_field_data,
            },
            {
                "name": "Location 5",
                "status": self.statuses.first().pk,
                "location_type": self.lt.pk,
                "custom_fields": custom_field_data,
            },
        )
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), len(data))

        for i, _obj in enumerate(data):
            # Validate response data
            response_cf = response.data[i]["custom_fields"]
            self.assertEqual(response_cf["text_cf"], custom_field_data["text_cf"])
            self.assertEqual(response_cf["number_cf"], custom_field_data["number_cf"])
            self.assertEqual(response_cf["boolean_cf"], custom_field_data["boolean_cf"])
            self.assertEqual(response_cf["date_cf"], custom_field_data["date_cf"])
            self.assertEqual(response_cf["url_cf"], custom_field_data["url_cf"])
            self.assertEqual(response_cf["choice_cf"], custom_field_data["choice_cf"])
            self.assertEqual(response_cf["multi_choice_cf"], custom_field_data["multi_choice_cf"])
            if "example_plugin" in settings.PLUGINS:
                self.assertEqual(
                    response_cf["example_plugin_auto_custom_field"],
                    custom_field_data["example_plugin_auto_custom_field"],
                )

            # Validate database data
            location = Location.objects.get(pk=response.data[i]["id"])
            self.assertEqual(location.cf["text_cf"], custom_field_data["text_cf"])
            self.assertEqual(location.cf["number_cf"], custom_field_data["number_cf"])
            self.assertEqual(location.cf["boolean_cf"], custom_field_data["boolean_cf"])
            self.assertEqual(str(location.cf["date_cf"]), custom_field_data["date_cf"])
            self.assertEqual(location.cf["url_cf"], custom_field_data["url_cf"])
            self.assertEqual(location.cf["choice_cf"], custom_field_data["choice_cf"])
            self.assertEqual(location.cf["multi_choice_cf"], custom_field_data["multi_choice_cf"])
            if "example_plugin" in settings.PLUGINS:
                self.assertEqual(
                    location.cf["example_plugin_auto_custom_field"],
                    custom_field_data["example_plugin_auto_custom_field"],
                )

    def test_update_single_object_with_values(self):
        """
        Update an object with existing custom field values. Ensure that only the updated custom field values are
        modified.
        """
        location = self.locations[1]
        original_cfvs = {**location.cf}
        data = {
            "custom_fields": {
                "text_cf": "ABCD",
                "number_cf": 1234,
            },
        }
        url = reverse("dcim-api:location-detail", kwargs={"pk": self.locations[1].pk})
        self.add_permissions("dcim.change_location")

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        # Validate response data
        response_cf = response.data["custom_fields"]
        self.assertEqual(response_cf["text_cf"], data["custom_fields"]["text_cf"])
        self.assertEqual(response_cf["number_cf"], data["custom_fields"]["number_cf"])
        self.assertEqual(response_cf["boolean_cf"], original_cfvs["boolean_cf"])
        self.assertEqual(response_cf["date_cf"], original_cfvs["date_cf"])
        self.assertEqual(response_cf["url_cf"], original_cfvs["url_cf"])
        self.assertEqual(response_cf["choice_cf"], original_cfvs["choice_cf"])
        self.assertEqual(response_cf["multi_choice_cf"], original_cfvs["multi_choice_cf"])
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(
                response_cf["example_plugin_auto_custom_field"], original_cfvs["example_plugin_auto_custom_field"]
            )

        # Validate database data
        location.refresh_from_db()
        self.assertEqual(location.cf["text_cf"], data["custom_fields"]["text_cf"])
        self.assertEqual(
            location.cf["number_cf"],
            data["custom_fields"]["number_cf"],
        )
        self.assertEqual(location.cf["boolean_cf"], original_cfvs["boolean_cf"])
        self.assertEqual(location.cf["date_cf"], original_cfvs["date_cf"])
        self.assertEqual(location.cf["url_cf"], original_cfvs["url_cf"])
        self.assertEqual(location.cf["choice_cf"], original_cfvs["choice_cf"])
        self.assertEqual(location.cf["multi_choice_cf"], original_cfvs["multi_choice_cf"])
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(
                location.cf["example_plugin_auto_custom_field"], original_cfvs["example_plugin_auto_custom_field"]
            )

    def test_minimum_maximum_values_validation(self):
        url = reverse("dcim-api:location-detail", kwargs={"pk": self.locations[1].pk})
        self.add_permissions("dcim.change_location")

        self.cf_integer.validation_minimum = 10
        self.cf_integer.validation_maximum = 20
        self.cf_integer.save()

        data = {"custom_fields": {"number_cf": 9}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

        data = {"custom_fields": {"number_cf": 21}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

        data = {"custom_fields": {"number_cf": 15}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_bigint_values_of_custom_field_maximum_attribute(self):
        url = reverse("dcim-api:location-detail", kwargs={"pk": self.locations[1].pk})
        self.add_permissions("dcim.change_location")

        self.cf_integer.validation_maximum = 5000000000
        self.cf_integer.save()

        data = {"custom_fields": {"number_cf": 4294967294}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        data = {"custom_fields": {"number_cf": 5000000001}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_bigint_values_of_custom_field_minimum_attribute(self):
        url = reverse("dcim-api:location-detail", kwargs={"pk": self.locations[1].pk})
        self.add_permissions("dcim.change_location")

        self.cf_integer.validation_minimum = -5000000000
        self.cf_integer.save()

        data = {"custom_fields": {"number_cf": -4294967294}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        data = {"custom_fields": {"number_cf": -5000000001}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_regex_validation(self):
        url = reverse("dcim-api:location-detail", kwargs={"pk": self.locations[1].pk})
        self.add_permissions("dcim.change_location")

        self.cf_text.validation_regex = r"^[A-Z]{3}$"  # Three uppercase letters
        self.cf_text.save()

        data = {"custom_fields": {"text_cf": "ABC123"}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

        data = {"custom_fields": {"text_cf": "abc"}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

        data = {"custom_fields": {"text_cf": "ABC"}}
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_select_regex_validation(self):
        url = reverse("extras-api:customfieldchoice-list")
        self.add_permissions("extras.add_customfieldchoice")

        self.cf_select.validation_regex = r"^[A-Z]{3}$"  # Three uppercase letters
        self.cf_select.save()

        data = {"custom_field": self.cf_select.id, "value": "1234", "weight": 100}
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

        data = {"custom_field": self.cf_select.id, "value": "abc", "weight": 100}
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

        data = {"custom_field": self.cf_select.id, "value": "ABC", "weight": 100}
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

    def test_text_type_with_invalid_values(self):
        """
        Try and create a new location with an invalid value for a text type.
        """
        data = {
            "name": "Location 4",
            "status": self.statuses[0].pk,
            "location_type": self.lt.pk,
            "custom_fields": {
                "text_cf": ["I", "am", "a", "disallowed", "type"],
            },
        }
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Value must be a string", str(response.content))

        data["custom_fields"].update({"text_cf": 2})
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Value must be a string", str(response.content))

        data["custom_fields"].update({"text_cf": True})
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Value must be a string", str(response.content))

    def test_create_without_required_field(self):
        self.cf_text.default = None
        self.cf_text.required = True
        self.cf_text.save()

        data = {
            "name": "Location N",
            "location_type": self.lt.pk,
            "status": self.statuses[0].pk,
        }
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location")
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Required field cannot be empty", str(response.content))

        # Try in CSV format too
        csvdata = "\n".join(
            [
                "name,location_type,status",
                f"Location N,{self.lt.composite_key},{self.statuses[0].name}",
            ]
        )
        response = self.client.post(url, csvdata, content_type="text/csv", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Required field cannot be empty", str(response.content))

    def test_create_invalid_select_choice(self):
        data = {
            "name": "Location N",
            "location_type": self.lt.pk,
            "status": self.statuses[0].pk,
            "custom_fields": {
                "choice_cf": "Frobozz",
            },
        }
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location")
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid choice", str(response.content))

        # Try in CSV format too
        csvdata = "\n".join(
            [
                "name,location_type,status,cf_choice_cf",
                f"Location N,{self.lt.composite_key},{self.statuses[0].name},Frobozz",
            ]
        )
        response = self.client.post(url, csvdata, content_type="text/csv", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid choice", str(response.content))


class CustomFieldImportTest(TestCase):
    """
    Test importing object custom field data along with the object itself.
    """

    user_permissions = (
        "dcim.add_location",
        "dcim.view_location",
        "dcim.change_location",
        "dcim.add_locationtype",
        "dcim.change_locationtype",
        "dcim.view_locationtype",
        "extras.view_status",
    )

    @classmethod
    def setUpTestData(cls):
        custom_fields = (
            CustomField(label="Text", type=CustomFieldTypeChoices.TYPE_TEXT),
            CustomField(label="Integer", type=CustomFieldTypeChoices.TYPE_INTEGER),
            CustomField(label="Boolean", type=CustomFieldTypeChoices.TYPE_BOOLEAN),
            CustomField(label="Date", type=CustomFieldTypeChoices.TYPE_DATE),
            CustomField(label="URL", type=CustomFieldTypeChoices.TYPE_URL),
            CustomField(
                label="Select",
                type=CustomFieldTypeChoices.TYPE_SELECT,
            ),
            CustomField(
                label="Multiselect",
                type=CustomFieldTypeChoices.TYPE_MULTISELECT,
            ),
        )
        for cf in custom_fields:
            cf.validated_save()
            cf.content_types.set([ContentType.objects.get_for_model(Location)])

        CustomFieldChoice.objects.create(custom_field=CustomField.objects.get(label="Select"), value="Choice A")
        CustomFieldChoice.objects.create(custom_field=CustomField.objects.get(label="Select"), value="Choice B")
        CustomFieldChoice.objects.create(custom_field=CustomField.objects.get(label="Select"), value="Choice C")
        CustomFieldChoice.objects.create(custom_field=CustomField.objects.get(label="Multiselect"), value="Choice A")
        CustomFieldChoice.objects.create(custom_field=CustomField.objects.get(label="Multiselect"), value="Choice B")
        CustomFieldChoice.objects.create(custom_field=CustomField.objects.get(label="Multiselect"), value="Choice C")

    def test_import(self):
        """
        Import a Location in CSV format, including a value for each CustomField.
        """
        LocationType.objects.create(name="Test Root")
        location_status = Status.objects.get_for_model(Location).first()
        data = (
            [
                "name",
                "location_type",
                "status",
                "cf_text",
                "cf_integer",
                "cf_boolean",
                "cf_date",
                "cf_url",
                "cf_select",
                "cf_multiselect",
            ],
            [
                "Location 1",
                "Test Root",
                location_status.name,
                "ABC",
                "123",
                "True",
                "2020-01-01",
                "http://example.com/1",
                "Choice A",
                "Choice A",
            ],
            [
                "Location 2",
                "Test Root",
                location_status.name,
                "DEF",
                "456",
                "False",
                "2020-01-02",
                "http://example.com/2",
                "Choice B",
                '"Choice A,Choice B"',
            ],
            ["Location 3", "Test Root", location_status.name, "", "", "", "", "", "", ""],
        )
        if "example_plugin" in settings.PLUGINS:
            data[0].append("cf_example_plugin_auto_custom_field")
            data[1].append("Custom value")
            data[2].append("Another custom value")
            data[3].append("")
        csv_data = "\n".join(",".join(row) for row in data)
        response = self.client.post(reverse("dcim:location_import"), {"csv_data": csv_data})
        self.assertEqual(response.status_code, 200)

        # Validate data for location 1
        try:
            location1 = Location.objects.get(name="Location 1")
        except Location.DoesNotExist:
            self.fail(str(response.content))
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(len(location1.cf), 8)
        else:
            self.assertEqual(len(location1.cf), 7)
        self.assertEqual(location1.cf["text"], "ABC")
        self.assertEqual(location1.cf["integer"], 123)
        self.assertEqual(location1.cf["boolean"], True)
        self.assertEqual(location1.cf["date"], "2020-01-01")
        self.assertEqual(location1.cf["url"], "http://example.com/1")
        self.assertEqual(location1.cf["select"], "Choice A")
        self.assertEqual(location1.cf["multiselect"], ["Choice A"])
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(location1.cf["example_plugin_auto_custom_field"], "Custom value")

        # Validate data for location 2
        location2 = Location.objects.get(name="Location 2")
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(len(location2.cf), 8)
        else:
            self.assertEqual(len(location2.cf), 7)
        self.assertEqual(location2.cf["text"], "DEF")
        self.assertEqual(location2.cf["integer"], 456)
        self.assertEqual(location2.cf["boolean"], False)
        self.assertEqual(location2.cf["date"], "2020-01-02")
        self.assertEqual(location2.cf["url"], "http://example.com/2")
        self.assertEqual(location2.cf["select"], "Choice B")
        self.assertEqual(location2.cf["multiselect"], ["Choice A", "Choice B"])
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(location2.cf["example_plugin_auto_custom_field"], "Another custom value")

        # No custom field data should be set for location 3
        location3 = Location.objects.get(name="Location 3")
        self.assertFalse(any(location3.cf.values()))


class CustomFieldModelTest(TestCase):
    """
    Test behavior of models that inherit from CustomFieldModel.
    """

    @classmethod
    def setUpTestData(cls):
        cf1 = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, label="Foo")
        cf1.save()
        cf1.content_types.set([ContentType.objects.get_for_model(Location)])

        cf2 = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, label="Bar")
        cf2.save()
        cf2.content_types.set([ContentType.objects.get_for_model(Rack)])
        cls.lt = LocationType.objects.get(name="Campus")

        cls.location_status = Status.objects.get_for_model(Location).first()
        cls.location1 = Location.objects.create(name="NYC", location_type=cls.lt, status=cls.location_status)
        cls.computed_field_one = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Location),
            key="computed_field_one",
            label="Computed Field One",
            template="{{ obj.name }} is the name of this location.",
            fallback_value="An error occurred while rendering this template.",
            weight=100,
        )
        # Field whose template will raise a TemplateError
        cls.bad_computed_field = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Location),
            key="bad_computed_field",
            label="Bad Computed Field",
            template="{{ something_that_throws_an_err | not_a_real_filter }} bad data",
            fallback_value="This template has errored",
            weight=100,
        )
        # Field whose template will raise a TypeError
        cls.worse_computed_field = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Location),
            key="worse_computed_field",
            label="Worse Computed Field",
            template="{{ obj.images | list }}",
            fallback_value="Another template error",
            weight=200,
        )
        cls.non_location_computed_field = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Device),
            key="device_computed_field",
            label="Device Computed Field",
            template="Hello, world.",
            fallback_value="This template has errored",
            weight=100,
        )
        # Field whose template will return None, with fallback_value defaulting to empty string
        cls.bad_attribute_computed_field = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Location),
            key="bad_attribute_computed_field",
            label="Bad Attribute Computed Field",
            template="{{ obj.location }}",
            weight=200,
        )

    def test_custom_field_dict_population(self):
        """Test that custom_field_data is properly populated when no data is passed in."""
        label = "Custom Field"
        custom_field = CustomField.objects.create(
            label=label,
            key="custom_field",
            default="Default Value",
            type=CustomFieldTypeChoices.TYPE_TEXT,
        )
        custom_field.validated_save()
        custom_field.content_types.set([ContentType.objects.get_for_model(Provider)])

        provider = Provider.objects.create(name="Test")
        provider.validated_save()

        self.assertIn(
            "custom_field",
            provider._custom_field_data.keys(),
            "Custom fields aren't being set properly on a model on save.",
        )

    def test_custom_field_dict_population_null(self):
        """Test that custom_field_data is not populated when the default value is None."""
        label = "Custom Field"
        custom_field = CustomField.objects.create(
            label=label,
            key="custom_field",
            default=None,
            type=CustomFieldTypeChoices.TYPE_TEXT,
        )
        custom_field.validated_save()
        custom_field.content_types.set([ContentType.objects.get_for_model(Provider)])

        provider = Provider.objects.create(name="Test")
        provider.validated_save()

        self.assertNotIn(
            "custom_field",
            provider._custom_field_data.keys(),
            "Custom fields aren't being set properly on a model on save.",
        )

    def test_custom_field_required(self):
        """Test that omitting required custom fields raises a ValidationError."""
        label = "Custom Field"
        custom_field = CustomField.objects.create(
            # 2.0 TODO: #824 remove name field
            label=label,
            key="custom_field",
            type=CustomFieldTypeChoices.TYPE_TEXT,
            required=True,
        )
        custom_field.validated_save()
        custom_field.content_types.set([ContentType.objects.get_for_model(Provider)])

        provider = Provider.objects.create(name="Test")
        with self.assertRaises(ValidationError):
            provider.validated_save()

    def test_custom_field_required_on_update(self):
        """Test that removing required custom fields and then updating an object raises a ValidationError."""
        label = "Custom Field"
        custom_field = CustomField.objects.create(
            # 2.0 TODO: #824 remove name field
            label=label,
            key="custom_field",
            type=CustomFieldTypeChoices.TYPE_TEXT,
            required=True,
        )
        custom_field.validated_save()
        custom_field.content_types.set([ContentType.objects.get_for_model(Provider)])

        provider = Provider.objects.create(name="Test", _custom_field_data={"custom_field": "Value"})
        provider.validated_save()
        provider._custom_field_data.pop("custom_field")
        with self.assertRaises(ValidationError):
            provider.validated_save()

    def test_update_removed_custom_field(self):
        """Test that missing custom field keys are added on save."""
        label = "Custom Field"
        custom_field = CustomField.objects.create(
            label=label,
            key="custom_field",
            default="Default Value",
            type=CustomFieldTypeChoices.TYPE_TEXT,
        )
        custom_field.validated_save()
        custom_field.content_types.set([ContentType.objects.get_for_model(Provider)])

        # Explicitly there is no `validated_save` so the custom field is not populated
        provider = Provider.objects.create(name="Test")

        self.assertEqual(
            {}, provider._custom_field_data, "Custom field data was not empty despite clean not being called."
        )

        provider.validated_save()

        self.assertIn("custom_field", provider._custom_field_data.keys())

    def test_cf_data(self):
        """
        Check that custom field data is present on the instance immediately after being set and after being fetched
        from the database.
        """
        location = Location(name="Test Location", status=self.location_status, location_type=self.lt)

        # Check custom field data on new instance
        location.cf["foo"] = "abc"
        self.assertEqual(location.cf["foo"], "abc")

        # Check custom field data from database
        location.validated_save()
        location = Location.objects.get(name="Test Location")
        self.assertEqual(location.cf["foo"], "abc")

    def test_invalid_data(self):
        """
        Setting custom field data for a non-applicable (or non-existent) CustomField should log a warning.
        """
        location = Location(name="Test Location", location_type=self.lt)

        # Set custom field data
        location.cf["foo"] = "abc"
        location.cf["bar"] = "def"
        with self.assertLogs(level=logging.WARNING):
            location.clean()

        del location.cf["bar"]
        location.clean()

    def test_missing_required_field(self):
        """
        Check that a ValidationError is raised if any required custom fields are not present.
        """
        cf3 = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, label="Baz", required=True)
        cf3.save()
        cf3.content_types.set([ContentType.objects.get_for_model(Location)])

        location = Location(name="Test Location", location_type=self.lt)

        # Set custom field data with a required field omitted
        location.cf["foo"] = "abc"
        with self.assertRaises(ValidationError):
            location.clean()

        location.cf["baz"] = "def"
        location.clean()

    #
    # test computed field components
    #

    def test_get_computed_field_method(self):
        self.assertEqual(
            self.location1.get_computed_field("computed_field_one"),
            f"{self.location1.name} is the name of this location.",
        )

    def test_get_computed_field_method_render_false(self):
        self.assertEqual(
            self.location1.get_computed_field("computed_field_one", render=False), self.computed_field_one.template
        )

    def test_get_computed_fields_method(self):
        expected_renderings = {
            "computed_field_one": f"{self.location1.name} is the name of this location.",
            "bad_computed_field": self.bad_computed_field.fallback_value,
            "worse_computed_field": self.worse_computed_field.fallback_value,
            "bad_attribute_computed_field": "",
        }
        self.assertDictEqual(self.location1.get_computed_fields(), expected_renderings)

    def test_get_computed_fields_method_label_as_key(self):
        expected_renderings = {
            "Computed Field One": f"{self.location1.name} is the name of this location.",
            "Bad Computed Field": self.bad_computed_field.fallback_value,
            "Worse Computed Field": self.worse_computed_field.fallback_value,
            "Bad Attribute Computed Field": "",
        }
        self.assertDictEqual(self.location1.get_computed_fields(label_as_key=True), expected_renderings)

    def test_get_computed_fields_only_returns_fields_for_content_type(self):
        self.assertTrue(self.non_location_computed_field.key not in self.location1.get_computed_fields())

    def test_check_if_key_is_graphql_safe(self):
        """
        Check the GraphQL validation method on CustomField Key Attribute.
        """
        # Check if it catches the cf.key starting with a digit.
        cf1 = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, label="Test 1", key="12_test_1")
        with self.assertRaises(ValidationError) as error:
            cf1.validated_save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )
        # Check if it catches the cf.key with whitespace.
        cf1.key = "test 1"
        with self.assertRaises(ValidationError) as error:
            cf1.validated_save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )
        # Check if it catches the cf.key with hyphens.
        cf1.key = "test-1-custom-field"
        with self.assertRaises(ValidationError) as error:
            cf1.validated_save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )
        # Check if it catches the cf.key with special characters
        cf1.key = "test_1_custom_f)(&d"
        with self.assertRaises(ValidationError) as error:
            cf1.validated_save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )


class CustomFieldFilterTest(TestCase):
    """
    Test object filtering by custom field values.
    """

    queryset = Location.objects.all()
    filterset = LocationFilterSet

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Location)

        # Integer filtering
        cf = CustomField(label="CF1", type=CustomFieldTypeChoices.TYPE_INTEGER)
        cf.save()
        cf.content_types.set([obj_type])

        # Boolean filtering
        cf = CustomField(label="CF2", type=CustomFieldTypeChoices.TYPE_BOOLEAN)
        cf.save()
        cf.content_types.set([obj_type])

        # Exact text filtering
        cf = CustomField(
            label="CF3",
            type=CustomFieldTypeChoices.TYPE_TEXT,
            filter_logic=CustomFieldFilterLogicChoices.FILTER_EXACT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Loose text filtering
        cf = CustomField(
            label="CF4",
            type=CustomFieldTypeChoices.TYPE_TEXT,
            filter_logic=CustomFieldFilterLogicChoices.FILTER_LOOSE,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Date filtering
        cf = CustomField(label="CF5", type=CustomFieldTypeChoices.TYPE_DATE)
        cf.save()
        cf.content_types.set([obj_type])

        # Exact URL filtering
        cf = CustomField(
            label="CF6",
            type=CustomFieldTypeChoices.TYPE_URL,
            filter_logic=CustomFieldFilterLogicChoices.FILTER_EXACT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Loose URL filtering
        cf = CustomField(
            label="CF7",
            type=CustomFieldTypeChoices.TYPE_URL,
            filter_logic=CustomFieldFilterLogicChoices.FILTER_LOOSE,
        )
        cf.save()
        cf.content_types.set([obj_type])

        # Selection filtering
        cf = CustomField(
            label="CF8",
            type=CustomFieldTypeChoices.TYPE_SELECT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        CustomFieldChoice.objects.create(custom_field=cf, value="Foo")
        CustomFieldChoice.objects.create(custom_field=cf, value="Bar")

        # Multi-select filtering
        cf = CustomField(
            label="CF9",
            type=CustomFieldTypeChoices.TYPE_MULTISELECT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        CustomFieldChoice.objects.create(custom_field=cf, value="Foo")
        CustomFieldChoice.objects.create(custom_field=cf, value="Bar")
        cls.location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        Location.objects.create(
            name="Location 1",
            location_type=cls.location_type,
            status=location_status,
            _custom_field_data={
                "cf1": 100,
                "cf2": True,
                "cf3": "foo",
                "cf4": "foo",
                "cf5": "2016-06-26",
                "cf6": "http://foo.example.com/",
                "cf7": "http://foo.example.com/",
                "cf8": "Foo",
                "cf9": [],
            },
        )
        Location.objects.create(
            name="Location 2",
            location_type=cls.location_type,
            status=location_status,
            _custom_field_data={
                "cf1": 200,
                "cf2": False,
                "cf3": "foobar",
                "cf4": "foobar",
                "cf5": "2016-06-27",
                "cf6": "http://bar.example.com/",
                "cf7": "http://bar.example.com/",
                "cf8": "Bar",
                "cf9": ["Foo"],
            },
        )
        Location.objects.create(
            name="Location 3",
            location_type=cls.location_type,
            status=location_status,
            _custom_field_data={"cf9": ["Foo", "Bar"]},
        )
        Location.objects.create(
            name="Location 4",
            location_type=cls.location_type,
            status=location_status,
            _custom_field_data={},
        )

    def test_filter_integer(self):
        self.assertQuerysetEqual(
            self.filterset({"cf_cf1": 100}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf1=100),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf1__n": [100]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf1=100)
            | self.queryset.filter(_custom_field_data__cf1__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf1__lte": [101]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf1__lte=100),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf1__lt": [101]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf1__lt=101),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf1__gte": [199]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf1__gte=199),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf1__gt": [199]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf1__gt=199),
        )

    def test_filter_boolean(self):
        self.assertQuerysetEqual(
            self.filterset({"cf_cf2": True}, self.queryset).qs, self.queryset.filter(_custom_field_data__cf2=True)
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf2": False}, self.queryset).qs, self.queryset.filter(_custom_field_data__cf2=False)
        )

    def test_filter_text(self):
        self.assertQuerysetEqual(
            self.filterset({"cf_cf3": "foo"}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf3__contains="foo"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4": "foo"}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf4__icontains="foo"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__n": ["foo"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf4="foo")
            | self.queryset.filter(_custom_field_data__cf4__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__ic": ["OOB"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf4__icontains="OOB"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__nic": ["OOB"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf4__icontains="OOB")
            | self.queryset.filter(_custom_field_data__cf4__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__iew": ["Bar"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf4__iendswith="Bar"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__niew": ["Bar"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf4__iendswith="Bar")
            | self.queryset.filter(_custom_field_data__cf4__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__isw": ["Foob"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf4__istartswith="Foob"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__nisw": ["Foob"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf4__istartswith="Foob")
            | self.queryset.filter(_custom_field_data__cf4__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__ie": ["Foo"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf4__iexact="Foo"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__nie": ["Foo"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf4__iexact="Foo")
            | self.queryset.filter(_custom_field_data__cf4__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__re": ["f.*b"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf4__regex="f.*b"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__nre": ["f.*b"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf4__regex="f.*b")
            | self.queryset.filter(_custom_field_data__cf4__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__ire": ["F.*b"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf4__iregex="F.*b"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf4__nire": ["F.*b"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf4__iregex="F.*b")
            | self.queryset.filter(_custom_field_data__cf4__isnull=True),
        )

    def test_filter_date(self):
        self.assertQuerysetEqual(
            self.filterset({"cf_cf5": "2016-06-26"}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf5="2016-06-26"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf5__n": "2016-06-26"}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf5="2016-06-26")
            | self.queryset.filter(_custom_field_data__cf4__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf5__lte": ["2016-06-28"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf5__lte="2016-06-28"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf5__lte": ["2016-06-27"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf5__lte="2016-06-27"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf5__lte": ["2016-06-26"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf5__lte="2016-06-26"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf5__lte": ["2016-06-25"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__lte="2016-06-25"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf5__gte": ["2016-06-25"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf5__gte="2016-06-25"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf5__gte": ["2016-06-26"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf5__gte="2016-06-26"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf5__gte": ["2016-06-27"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf5__gte="2016-06-27"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf5__gte": ["2016-06-28"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf5__gte="2016-06-28"),
        )
        params = {"cf_cf5__gte": ["2016-06-25"], "cf_cf5__lt": ["2016-06-27"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf5__gte="2016-06-25", _custom_field_data__cf5__lt="2016-06-27"),
        )

    def test_filter_url(self):
        params = {"cf_cf6": "http://foo.example.com/"}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf6="http://foo.example.com/"),
        )
        params = {"cf_cf6__n": ["http://foo.example.com/"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf6="http://foo.example.com/")
            | self.queryset.filter(_custom_field_data__cf6__isnull=True),
        )
        params = {"cf_cf7": "example.com"}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf7__icontains="example.com"),
        )
        params = {"cf_cf7__n": ["http://foo.example.com/"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf7="http://foo.example.com/")
            | self.queryset.filter(_custom_field_data__cf7__isnull=True),
        )
        params = {"cf_cf6__ic": ["FOO.example.COM"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf6__icontains="FOO.example.COM"),
        )
        params = {"cf_cf6__nic": ["FOO.example.COM"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf6__icontains="FOO.example.COM")
            | self.queryset.filter(_custom_field_data__cf6__isnull=True),
        )
        params = {"cf_cf6__iew": ["FOO.example.COM/"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf6__iendswith="FOO.example.COM/"),
        )
        params = {"cf_cf6__niew": ["FOO.example.COM/"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf6__iendswith="FOO.example.COM/")
            | self.queryset.filter(_custom_field_data__cf6__isnull=True),
        )
        params = {"cf_cf6__isw": ["HTTP://FOO"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf6__istartswith="HTTP://FOO"),
        )
        params = {"cf_cf6__nisw": ["HTTP://FOO"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf6__istartswith="HTTP://FOO")
            | self.queryset.filter(_custom_field_data__cf6__isnull=True),
        )
        params = {"cf_cf6__ie": ["http://FOO.example.COM/"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf6__iexact="http://FOO.example.COM/"),
        )
        params = {"cf_cf6__nie": ["http://FOO.example.COM/"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf6__iexact="http://FOO.example.COM/")
            | self.queryset.filter(_custom_field_data__cf6__isnull=True),
        )
        params = {"cf_cf6__re": ["foo.*com"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf6__regex="foo.*com"),
        )
        params = {"cf_cf6__nre": ["foo.*com"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf6__regex="foo.*com")
            | self.queryset.filter(_custom_field_data__cf6__isnull=True),
        )
        params = {"cf_cf6__ire": ["FOO.*COM"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf6__iregex="FOO.*COM"),
        )
        params = {"cf_cf6__nire": ["FOO.*COM"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf6__iregex="FOO.*COM")
            | self.queryset.filter(_custom_field_data__cf6__isnull=True),
        )

    def test_filter_select(self):
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8": ["Foo", "AR"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf8__in=["Foo", "AR"]),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__n": ["Foo"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf8="Foo")
            | self.queryset.filter(_custom_field_data__cf8__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__ic": ["FOO"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf8__icontains="FOO"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__nic": ["FOO"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf8__icontains="FOO")
            | self.queryset.filter(_custom_field_data__cf8__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__iew": ["AR"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf8__iendswith="AR"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__niew": ["AR"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf8__iendswith="AR")
            | self.queryset.filter(_custom_field_data__cf8__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__isw": ["FO"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf8__istartswith="FO"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__nisw": ["FO"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf8__istartswith="FO")
            | self.queryset.filter(_custom_field_data__cf8__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__ie": ["foo"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf8__iexact="foo"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__nie": ["foo"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf8__istartswith="FO")
            | self.queryset.filter(_custom_field_data__cf8__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__re": ["F.o"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf8__regex="F.o"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__nre": ["F.o"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf8__regex="F.o")
            | self.queryset.filter(_custom_field_data__cf8__isnull=True),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__ire": ["F.O"]}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf8__iregex="F.o"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf8__nire": ["F.O"]}, self.queryset).qs,
            self.queryset.exclude(_custom_field_data__cf8__iregex="F.o")
            | self.queryset.filter(_custom_field_data__cf8__isnull=True),
        )

    def test_filter_multi_select(self):
        self.assertQuerysetEqual(
            self.filterset({"cf_cf9": "Foo"}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf9__contains="Foo"),
        )
        self.assertQuerysetEqual(
            self.filterset({"cf_cf9": "Bar"}, self.queryset).qs,
            self.queryset.filter(_custom_field_data__cf9__contains="Bar"),
        )


class CustomFieldChoiceTest(ModelTestCases.BaseModelTestCase):
    model = CustomFieldChoice

    def setUp(self):
        obj_type = ContentType.objects.get_for_model(Location)
        self.cf = CustomField(
            label="CF1",
            type=CustomFieldTypeChoices.TYPE_SELECT,
        )
        self.cf.save()
        self.cf.content_types.set([obj_type])

        self.choice = CustomFieldChoice(custom_field=self.cf, value="Foo")
        self.choice.save()

        location_status = Status.objects.get_for_model(Location).first()
        self.location_type = LocationType.objects.get(name="Campus")
        self.location = Location(
            name="Location 1",
            location_type=self.location_type,
            _custom_field_data={
                "cf1": "Foo",
            },
            status=location_status,
        )
        self.location.validated_save()

    def test_default_value_must_be_valid_choice_sad_path(self):
        self.cf.default = "invalid value"
        with self.assertRaises(ValidationError):
            self.cf.full_clean()

    def test_default_value_must_be_valid_choice_happy_path(self):
        self.cf.default = "Foo"
        self.cf.full_clean()
        self.cf.save()
        self.assertEqual(self.cf.default, "Foo")

    def test_active_choice_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.choice.delete()

    def test_custom_choice_deleted_with_field(self):
        self.cf.delete()
        if "example_plugin" in settings.PLUGINS:
            self.assertEqual(CustomField.objects.count(), 1)  # custom field automatically added by the plugin
        else:
            self.assertEqual(CustomField.objects.count(), 0)
        self.assertEqual(CustomFieldChoice.objects.count(), 0)

    def test_regex_validation(self):
        obj_type = ContentType.objects.get_for_model(Location)

        for cf_type in CustomFieldTypeChoices.REGEX_TYPES:
            # only validation for select and multi-select are performed on the CustomFieldChoice model
            if "select" not in cf_type:
                continue

            # Create a custom field
            cf = CustomField(
                type=cf_type,
                label=f"cf_test_{cf_type}",
                required=False,
                validation_regex="A.C[01]x?",
            )
            cf.save()
            cf.content_types.set([obj_type])

            non_matching_values = ["abc1", "AC1", "00AbC", "abc1x", "00abc1x00"]
            for value in non_matching_values:
                error_message = f"Value must match regex {cf.validation_regex} got {value}."
                with self.subTest(cf_type=cf_type, value=value):
                    with self.assertRaisesMessage(ValidationError, error_message):
                        cfc = CustomFieldChoice.objects.create(custom_field=cf, value=value)
                        cfc.validated_save()

            CustomFieldChoice.objects.all().delete()

            matching_values = ["ABC1", "00AbC0", "00ABC0x00"]
            for value in matching_values:
                with self.subTest(cf_type=cf_type, value=value):
                    cfc = CustomFieldChoice.objects.create(custom_field=cf, value=value)
                    cfc.validated_save()

            # Delete the custom field
            cf.delete()


class CustomFieldBackgroundTasks(TransactionTestCase):
    def test_provision_field_task(self):
        location_type = LocationType.objects.create(name="Root Type 1")
        location_status = Status.objects.get_for_model(Location).first()
        location = Location(name="Location 1", location_type=location_type, status=location_status)
        location.save()

        obj_type = ContentType.objects.get_for_model(Location)
        cf = CustomField(label="CF1", type=CustomFieldTypeChoices.TYPE_TEXT, default="Foo")
        cf.save()
        cf.content_types.set([obj_type])

        location.refresh_from_db()

        self.assertEqual(location.cf["cf1"], "Foo")

    def test_delete_custom_field_data_task(self):
        obj_type = ContentType.objects.get_for_model(Location)
        cf = CustomField(
            label="CF1",
            type=CustomFieldTypeChoices.TYPE_TEXT,
        )
        cf.save()
        cf.content_types.set([obj_type])
        location_type = LocationType.objects.create(name="Root Type 2")
        location_status = Status.objects.get_for_model(Location).first()
        location = Location(
            name="Location 1",
            location_type=location_type,
            status=location_status,
            _custom_field_data={"cf1": "foo"},
        )
        location.save()

        cf.delete()

        location.refresh_from_db()

        self.assertTrue("cf1" not in location.cf)

    def test_update_custom_field_choice_data_task(self):
        obj_type = ContentType.objects.get_for_model(Location)
        cf = CustomField(
            label="CF1",
            type=CustomFieldTypeChoices.TYPE_SELECT,
        )
        cf.save()
        cf.content_types.set([obj_type])

        choice = CustomFieldChoice(custom_field=cf, value="Foo")
        choice.save()
        location_type = LocationType.objects.create(name="Root Type 3")
        location_status = Status.objects.get_for_model(Location).first()
        location = Location(
            name="Location 1",
            location_type=location_type,
            status=location_status,
            _custom_field_data={"cf1": "Foo"},
        )
        location.save()

        choice.value = "Bar"
        choice.save()

        location.refresh_from_db()

        self.assertEqual(location.cf["cf1"], "Bar")


class CustomFieldTableTest(TestCase):
    """
    Test inclusion of custom fields in object table views.
    """

    def setUp(self):
        content_type = ContentType.objects.get_for_model(Location)

        # Text custom field
        cf_text = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, label="Text Field", default="foo")
        cf_text.validated_save()
        cf_text.content_types.set([content_type])

        # Integer custom field
        cf_integer = CustomField(type=CustomFieldTypeChoices.TYPE_INTEGER, label="Number Field", default=123)
        cf_integer.validated_save()
        cf_integer.content_types.set([content_type])

        # Boolean custom field
        cf_boolean = CustomField(
            type=CustomFieldTypeChoices.TYPE_BOOLEAN,
            label="Boolean Field",
            default=False,
        )
        cf_boolean.validated_save()
        cf_boolean.content_types.set([content_type])

        # Date custom field
        cf_date = CustomField(
            type=CustomFieldTypeChoices.TYPE_DATE,
            label="Date Field",
            default="2020-01-01",
        )
        cf_date.validated_save()
        cf_date.content_types.set([content_type])

        # URL custom field
        cf_url = CustomField(
            type=CustomFieldTypeChoices.TYPE_URL,
            label="URL Field",
            default="http://example.com/1",
        )
        cf_url.validated_save()
        cf_url.content_types.set([content_type])

        # Select custom field
        cf_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            label="Choice Field",
        )
        cf_select.validated_save()
        cf_select.content_types.set([content_type])
        CustomFieldChoice.objects.create(custom_field=cf_select, value="Foo")
        CustomFieldChoice.objects.create(custom_field=cf_select, value="Bar")
        CustomFieldChoice.objects.create(custom_field=cf_select, value="Baz")
        cf_select.default = "Foo"
        cf_select.validated_save()

        # Multi-select custom field
        cf_multi_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_MULTISELECT,
            label="Multi Choice Field",
        )
        cf_multi_select.validated_save()
        cf_multi_select.content_types.set([content_type])
        CustomFieldChoice.objects.create(custom_field=cf_multi_select, value="Foo")
        CustomFieldChoice.objects.create(custom_field=cf_multi_select, value="Bar")
        CustomFieldChoice.objects.create(custom_field=cf_multi_select, value="Baz")
        cf_multi_select.default = ["Foo", "Bar"]
        cf_multi_select.validated_save()

        statuses = Status.objects.get_for_model(Location)

        # Create a location
        location_type = LocationType.objects.create(name="Root Type 4")
        self.location = Location.objects.create(
            name="Location Custom", status=statuses.first(), location_type=location_type
        )

        # Assign custom field values for location 2
        self.location._custom_field_data = {
            cf_text.key: "bar",
            cf_integer.key: 456,
            cf_boolean.key: True,
            cf_date.key: "2020-01-02",
            cf_url.key: "http://example.com/2",
            cf_select.key: "Bar",
            cf_multi_select.key: ["Bar", "Baz"],
        }
        self.location.validated_save()

    def test_custom_field_table_render(self):
        queryset = Location.objects.filter(name=self.location.name)
        location_table = LocationTable(queryset)

        custom_column_expected = {
            "text_field": "bar",
            "number_field": "456",
            "boolean_field": '<span class="text-success"><i class="mdi mdi-check-bold" title="Yes"></i></span>',
            "date_field": "2020-01-02",
            "url_field": '<a href="http://example.com/2">http://example.com/2</a>',
            "choice_field": '<span class="label label-default">Bar</span>',
            "multi_choice_field": (
                '<span class="label label-default">Bar</span> <span class="label label-default">Baz</span> '
            ),
        }

        bound_row = location_table.rows[0]

        for col_name, col_expected_value in custom_column_expected.items():
            internal_col_name = "cf_" + col_name
            custom_column = location_table.base_columns.get(internal_col_name)
            self.assertIsNotNone(custom_column)
            self.assertIsInstance(custom_column, CustomFieldColumn)

            rendered_value = bound_row.get_cell(internal_col_name)
            self.assertEqual(rendered_value, col_expected_value)


class CustomFieldFilterFormTest(TestCase):
    def test_custom_filter_form(self):
        """Assert CustomField renders the appropriate filter form field"""
        rack_ct = ContentType.objects.get_for_model(Rack)
        ct_field = CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_SELECT, label="Select Field")
        ct_field.content_types.set([rack_ct])
        CustomFieldChoice.objects.create(custom_field=ct_field, value="Foo")
        CustomFieldChoice.objects.create(custom_field=ct_field, value="Bar")
        CustomFieldChoice.objects.create(custom_field=ct_field, value="Baz")
        filterform = RackFilterForm()
        self.assertIsInstance(filterform["cf_select_field"].field, ChoiceField)
        self.assertIsInstance(filterform["cf_select_field"].field.widget, StaticSelect2)
