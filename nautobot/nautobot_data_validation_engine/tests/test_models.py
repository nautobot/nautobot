"""
Model test cases
"""

from django.contrib.contenttypes.models import ContentType
from django.core.validators import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from nautobot.dcim.models import Cable, Device, Location, PowerFeed
from nautobot.extras.models import Job

from nautobot.nautobot_data_validation_engine.models import (
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)


class RegularExpressionValidationRuleModelTestCase(TestCase):
    """
    Test cases related to the RegularExpressionValidationRule model
    """

    def test_invalid_field_name(self):
        """Test that a non-existent model field is rejected."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="afieldthatdoesnotexist",
            regular_expression="^.*$",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_private_fields_cannot_be_used(self):
        """Test that a private model field is rejected."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="_name",  # _name is a private field
            regular_expression="^.*$",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_non_editable_fields_cannot_be_used(self):
        """Test that a non-editable model field is rejected."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="created",  # created has auto_now_add=True, making it editable=False
            regular_expression="^.*$",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_blacklisted_fields_cannot_be_used(self):
        """Test that a blacklisted model field is rejected."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="id",  # id is a uuid field which is blacklisted
            regular_expression="^.*$",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_invalid_regex_fails_validation(self):
        """Test that an invalid regex string fails validation."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="name",
            regular_expression="[",  # this is an invalid regex pattern
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_regex_is_only_validataed_if_context_processing_is_disabled(self):
        """Test that an invalid regex string fails validation."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="name",
            regular_expression="[",  # this is an invalid regex pattern
            context_processing=True,
        )

        try:
            rule.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")


class MinMaxValidationRuleModelTestCase(TestCase):
    """
    Test cases related to the MinMaxValidationRule model
    """

    def test_invalid_field_name(self):
        """Test that a non-existent model field is rejected."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="afieldthatdoesnotexist",
            min=1,
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_private_fields_cannot_be_used(self):
        """Test that a private model field is rejected."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Cable),
            field="_abs_length",  # this is a private field used for caching a denormalized value
            min=1,
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_blacklisted_fields_cannot_be_used(self):
        """Test that a blacklisted model field is rejected."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Job),
            field="id",  # Job.id is an AutoField which is blacklisted
            min=1,
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_min_or_max_must_be_set(self):
        """Test that a blacklisted model field is rejected."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="amperage",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_min_must_be_less_than_max(self):
        """Test that a blacklisted model field is rejected."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="amperage",
            min=1,
            max=0,
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_min__and_max_can_be_equal(self):
        """Test that a blacklisted model field is rejected."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="amperage",
            min=1,
            max=1,
        )

        try:
            rule.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")


class RequiredValidationRuleModelTestCase(TestCase):
    """
    Test cases related to the RequiredValidationRule model
    """

    def test_invalid_field_name(self):
        """Test that a non-existent model field is rejected."""
        rule = RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="afieldthatdoesnotexist",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_private_fields_cannot_be_used(self):
        """Test that a private model field is rejected."""
        rule = RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Cable),
            field="_abs_length",  # this is a private field used for caching a denormalized value
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_blacklisted_fields_cannot_be_used(self):
        """Test that a blacklisted model field is rejected."""
        rule = RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Job),
            field="id",  # Job.id is an AutoField which is blacklisted
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_default_required_field_cannot_be_used(self):
        """Test that a field that is already required cannot be used."""
        rule = RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="name",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_null_false_blank_true_can_be_used(self):
        """Test that Field(null=False, blank=True) can be used."""
        rule = RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="physical_address",
        )

        try:
            rule.clean()
        except ValidationError as e:
            self.fail(f"rule.clean() failed validation: {e}")


class UniqueValidationRuleModelTestCase(TestCase):
    """
    Test cases related to the UniqueValidationRule model
    """

    def test_invalid_field_name(self):
        """Test that a non-existent model field is rejected."""
        rule = UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="afieldthatdoesnotexist",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_private_fields_cannot_be_used(self):
        """Test that a private model field is rejected."""
        rule = UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(Cable),
            field="_abs_length",  # this is a private field used for caching a denormalized value
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_blacklisted_fields_cannot_be_used(self):
        """Test that a blacklisted model field is rejected."""
        rule = UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(Job),
            field="id",  # Job.id is an AutoField which is blacklisted
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_default_unique_field_cannot_be_used(self):
        """Test that a field that is already unique cannot be used."""
        UniqueValidationRule.objects.create(
            name="Unique rule existing",
            content_type=ContentType.objects.get_for_model(Location),
            field="name",
        )

        with self.assertRaises(IntegrityError):
            rule = UniqueValidationRule.objects.create(
                name="Unique rule 1",
                content_type=ContentType.objects.get_for_model(Location),
                field="name",
            )

            rule.clean()
