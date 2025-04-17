"""
Model test cases
"""

import re

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from nautobot.core.testing.mixins import NautobotTestCaseMixin
from nautobot.data_validation.models import (
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)
from nautobot.data_validation.tests import ValidationRuleTestCaseMixin
from nautobot.dcim.models import Location, LocationType, Rack
from nautobot.extras.models import Status


class CustomValidatorTestCases:
    class CustomValidatorTestCase(ValidationRuleTestCaseMixin, NautobotTestCaseMixin, TestCase):
        def setUp(self):
            super().setUp()
            self.location_type = LocationType.objects.get(name="Root")
            self.status = Status.objects.get_for_model(Location).first()


class RegularExpressionValidationRuleCustomValidatorTestCase(CustomValidatorTestCases.CustomValidatorTestCase):
    model = RegularExpressionValidationRule

    def test_invalid_regex_matches_raise_validation_error(self):
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="name",
            regular_expression="^ABC$",
        )

        location = Location(name="does not match the regex", location_type=self.location_type, status=self.status)
        escaped_regex = re.escape(rule.regular_expression)
        with self.assertRaisesRegex(ValidationError, f"Value does not conform to regex: {escaped_regex}"):
            location.clean()

    def test_valid_regex_matches_do_not_raise_validation_error(self):
        RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="name",
            regular_expression="^ABC$",
        )

        location = Location(name="ABC", location_type=self.location_type, status=self.status)

        try:
            location.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")

    def test_empty_field_values_coerced_to_empty_string(self):
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
            regular_expression="^ABC$",
        )

        location = Location(
            name="Location 1",
            location_type=self.location_type,
            status=self.status,
            description="",  # empty value not allowed by the regex
        )

        escaped_regex = re.escape(rule.regular_expression)
        with self.assertRaisesRegex(ValidationError, f"Value does not conform to regex: {escaped_regex}"):
            location.clean()

    def test_context_processing_happy_path(self):
        RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
            regular_expression="{{ object.name[0:3] }}.*",
            context_processing=True,
        )

        location = Location(
            name="AMS-195",
            location_type=self.location_type,
            status=self.status,
            description="AMS-195 is really cool",  # This should match `AMS.*`
        )

        try:
            location.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")

    def test_context_processing_sad_path(self):
        RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
            regular_expression="{{ object.name[0:3] }}.*",
            context_processing=True,
        )

        location = Location(
            name="AMS-195",
            location_type=self.location_type,
            status=self.status,
            description="I don't like AMS-195",  # This should *not* match `AMS.*`
        )

        with self.assertRaisesRegex(ValidationError, "Value does not conform to regex: AMS.*"):
            location.clean()

    def test_context_processing_invalid_regex_fails_validation(self):
        RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
            regular_expression="[{{ object.name[0:3] }}.*",  # once processed, this is an invalid regex
            context_processing=True,
        )

        location = Location(name="AMS-195", location_type=self.location_type, status=self.status)

        with self.assertRaisesRegex(
            ValidationError,
            "There was an error rendering the regular expression in the data validation rule 'Regex rule 1'. Either fix the validation rule or disable it in order to save this data.",
        ):
            location.clean()


class MinMaxValidationRuleCustomValidatorTestCase(CustomValidatorTestCases.CustomValidatorTestCase):
    model = MinMaxValidationRule

    def test_empty_field_values_raise_validation_error(self):
        MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="latitude",
            min=1,
            max=1,
        )

        location = Location(
            name="Location without a latitude",
            location_type=self.location_type,
            status=self.status,
            latitude=None,  # empty value not allowed by the rule
        )

        with self.assertRaisesRegex(ValidationError, "Value does not conform to mix/max validation: min 1.0, max 1.0"):
            location.clean()

    def test_field_value_type_raise_validation_error(self):
        MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="latitude",
            min=1,
            max=1,
        )

        location = Location(
            name="Location with an invalid latitude",
            location_type=self.location_type,
            status=self.status,
            latitude="foobar",  # wrong type
        )

        with self.assertRaisesRegex(
            ValidationError,
            "Unable to validate against min/max rule Min max rule 1 because the field value is not numeric.",
        ):
            location.clean()

    def test_min_violation_raise_validation_error(self):
        MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="latitude",
            min=5,
            max=10,
        )

        location = Location(
            name="Location with latitude less than min",
            location_type=self.location_type,
            status=self.status,
            latitude=4,  # less than min of 5
        )

        with self.assertRaisesRegex(ValidationError, "Value is less than minimum value: 5.0"):
            location.clean()

    def test_max_violation_raise_validation_error(self):
        MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="latitude",
            min=5,
            max=10,
        )

        location = Location(
            name="Location with a latitude more than max",
            location_type=self.location_type,
            status=self.status,
            latitude=11,  # more than max of 10
        )

        with self.assertRaisesRegex(ValidationError, "Value is more than maximum value: 10.0"):
            location.clean()

    def test_unbounded_min_does_not_raise_validation_error(self):
        MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="latitude",
            min=None,  # unbounded
            max=10,
        )

        location = Location(
            name="Location with a valid latitude",
            location_type=self.location_type,
            status=self.status,
            latitude=-5,
        )

        try:
            location.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")

    def test_unbounded_max_does_not_raise_validation_error(self):
        MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="latitude",
            min=5,
            max=None,  # unbounded
        )

        location = Location(
            name="Location with a valid latitude",
            location_type=self.location_type,
            status=self.status,
            latitude=30,
        )

        try:
            location.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")

    def test_valid_bounded_value_does_not_raise_validation_error(self):
        MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="latitude",
            min=5,
            max=10,
        )

        location = Location(
            name="Location with a valid latitude",
            location_type=self.location_type,
            status=self.status,
            latitude=8,  # within bounds
        )

        try:
            location.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")


class RequiredValidationRuleCustomValidatorTestCase(CustomValidatorTestCases.CustomValidatorTestCase):
    model = RequiredValidationRule

    def test_blank_value_raises_error(self):
        RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
        )

        location = Location(
            name="Location 1 does not have a description", location_type=self.location_type, status=self.status
        )

        with self.assertRaisesRegex(ValidationError, "This field cannot be blank."):
            location.clean()

    def test_provided_values_no_not_raise_error(self):
        RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
        )

        location = Location(
            name="Location 2 does have a description",
            location_type=self.location_type,
            status=self.status,
            description="Location 2",
        )

        try:
            location.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")

    def test_empty_string_field_values_raise_error(self):
        RequiredValidationRule.objects.create(
            name="Required rule 3",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
        )

        location = Location(
            name="Location 3 has an empty string description",
            location_type=self.location_type,
            status=self.status,
            description="",
        )

        with self.assertRaisesRegex(ValidationError, "This field cannot be blank."):
            location.clean()

    def test_falsy_values_do_not_raise_error(self):
        RequiredValidationRule.objects.create(
            name="Required rule 4",
            content_type=ContentType.objects.get_for_model(Rack),
            field="serial",
        )

        location = Location(name="Location 3", location_type=self.location_type, status=self.status)
        location.save()

        rack = Rack(
            name="Rack 1",
            location=location,
            status=Status.objects.get_for_model(Rack).first(),
            serial=0,  # test that zero passes validation
        )

        try:
            rack.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")


class UniqueValidationRuleCustomValidatorTestCase(CustomValidatorTestCases.CustomValidatorTestCase):
    model = UniqueValidationRule

    def test_null_value_does_not_raise_error(self):
        UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="asn",
            max_instances=1,
        )

        location1 = Location(
            name="Location 1",
            location_type=self.location_type,
            status=self.status,
            asn=None,
        )
        location2 = Location(
            name="Location 2",
            location_type=self.location_type,
            status=self.status,
            asn=None,
        )

        location1.validated_save()

        try:
            location2.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")

    def test_max_instances_reached_raises_error(self):
        UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="description",
            max_instances=2,
        )

        location1 = Location(
            name="Location 1",
            location_type=self.location_type,
            status=self.status,
            description="same",
        )
        location2 = Location(
            name="Location 2",
            location_type=self.location_type,
            status=self.status,
            description="same",
        )
        location3 = Location(
            name="Location 3",
            location_type=self.location_type,
            status=self.status,
            description="same",
        )

        location1.validated_save()
        location2.validated_save()

        with self.assertRaisesRegex(ValidationError, "There can only be 2 instances with this value."):
            location3.clean()
