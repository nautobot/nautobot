"""
Model test cases
"""

import re
from unittest import TestCase

from django.contrib.contenttypes.models import ContentType
from django.core.validators import ValidationError
from django.db.utils import IntegrityError

from nautobot.core.testing.models import ModelTestCases
from nautobot.data_validation.models import (
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)
from nautobot.data_validation.tests import ValidationRuleTestCaseMixin
from nautobot.dcim.models import Cable, Device, Location, PowerFeed
from nautobot.extras.models import Job


class ValidationRuleModelTestCases:
    class ValidationRuleModelTestCase(ValidationRuleTestCaseMixin, ModelTestCases.BaseModelTestCase):
        def test_get_for_model_caching_and_cache_invalidation(self):
            """Test that the cache is used and is properly invalidated when rules are created or deleted."""
            # Assert that the cache is used when calling get_for_model or get_enabled_for_model a second time
            self.model.objects.get_for_model("dcim.device")
            with self.assertNumQueries(0):
                self.model.objects.get_for_model("dcim.device")
            self.model.objects.get_enabled_for_model("dcim.device")
            with self.assertNumQueries(0):
                self.model.objects.get_enabled_for_model("dcim.device")

            # Assert the cache is invalidated on rule save
            self.model.objects.get_for_model("dcim.device").first().save()
            with self.assertNumQueries(1):
                self.model.objects.get_for_model("dcim.device")
            with self.assertNumQueries(1):
                self.model.objects.get_enabled_for_model("dcim.device")

            # Assert the cache is invalidated on rule delete
            self.model.objects.get_for_model("dcim.device").first().delete()
            with self.assertNumQueries(1):
                self.model.objects.get_for_model("dcim.device")
            with self.assertNumQueries(1):
                self.model.objects.get_enabled_for_model("dcim.device")


class RegularExpressionValidationRuleModelTestCase(ValidationRuleModelTestCases.ValidationRuleModelTestCase):
    """
    Test cases related to the RegularExpressionValidationRule model
    """

    model = RegularExpressionValidationRule

    def setUp(self):
        RegularExpressionValidationRule.objects.create(
            name="Regex rule 0",
            content_type=ContentType.objects.get_for_model(Device),
            field="description",
            regular_expression="^.*$",
        )
        super().setUp()

    def test_invalid_field_name(self):
        """Test that a non-existent model field is rejected."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="afieldthatdoesnotexist",
            regular_expression="^.*$",
        )

        with self.assertRaisesRegex(ValidationError, "Not a valid field for content type dcim.device."):
            rule.clean()

    def test_private_fields_cannot_be_used(self):
        """Test that a private model field is rejected."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="_name",  # _name is a private field
            regular_expression="^.*$",
        )

        with self.assertRaisesRegex(
            ValidationError, "This field's type does not support regular expression validation."
        ):
            rule.clean()

    def test_non_editable_fields_cannot_be_used(self):
        """Test that a non-editable model field is rejected."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="created",  # created has auto_now_add=True, making it editable=False
            regular_expression="^.*$",
        )

        with self.assertRaisesRegex(
            ValidationError, "This field's type does not support regular expression validation."
        ):
            rule.clean()

    def test_blacklisted_fields_cannot_be_used(self):
        """Test that a blacklisted model field is rejected."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="id",  # id is a uuid field which is blacklisted
            regular_expression="^.*$",
        )

        with self.assertRaisesRegex(
            ValidationError, "This field's type does not support regular expression validation."
        ):
            rule.clean()

    def test_invalid_regex_fails_validation(self):
        """Test that an invalid regex string fails validation."""
        rule = RegularExpressionValidationRule.objects.create(
            name="Regex rule 1",
            content_type=ContentType.objects.get_for_model(Device),
            field="name",
            regular_expression="[",  # this is an invalid regex pattern
        )

        escaped_regex = re.escape(rule.regular_expression)
        with self.assertRaisesRegex(ValidationError, f"{escaped_regex} is not a valid regular expression."):
            rule.full_clean()

    def test_regex_is_only_validataed_if_context_processing_is_disabled(self):
        """Test regular expression is only validated if context processing is disabled."""
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


class MinMaxValidationRuleModelTestCase(ValidationRuleModelTestCases.ValidationRuleModelTestCase):
    """
    Test cases related to the MinMaxValidationRule model
    """

    model = MinMaxValidationRule

    def setUp(self):
        MinMaxValidationRule.objects.create(
            name="Min max rule 0",
            content_type=ContentType.objects.get_for_model(Device),
            field="position",
            min=1,
        )
        super().setUp()

    def test_invalid_field_name(self):
        """Test that a non-existent model field is rejected."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="afieldthatdoesnotexist",
            min=1,
        )

        with self.assertRaisesRegex(ValidationError, "Not a valid field for content type dcim.powerfeed."):
            rule.clean()

    def test_private_fields_cannot_be_used(self):
        """Test that a private model field is rejected."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Cable),
            field="_abs_length",  # this is a private field used for caching a denormalized value
            min=1,
        )

        with self.assertRaisesRegex(ValidationError, "This field's type does not support min/max validation."):
            rule.clean()

    def test_blacklisted_fields_cannot_be_used(self):
        """Test that a blacklisted model field is rejected."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(Job),
            field="id",  # Job.id is an AutoField which is blacklisted
            min=1,
        )

        with self.assertRaisesRegex(ValidationError, "This field's type does not support min/max validation."):
            rule.clean()

    def test_min_or_max_must_be_set(self):
        """Test that at least min or max value must be specified."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="amperage",
        )

        with self.assertRaisesRegex(ValidationError, "At least a minimum or maximum value must be specified."):
            rule.clean()

    def test_min_must_be_less_than_max(self):
        """Test that the min value set must be less than the max value."""
        rule = MinMaxValidationRule.objects.create(
            name="Min max rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="amperage",
            min=1,
            max=0,
        )

        with self.assertRaisesRegex(ValidationError, "Minimum value cannot be more than the maximum value."):
            rule.clean()

    def test_min_and_max_can_be_equal(self):
        """Test that min and max values can be equal."""
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


class RequiredValidationRuleModelTestCase(ValidationRuleModelTestCases.ValidationRuleModelTestCase):
    """
    Test cases related to the RequiredValidationRule model
    """

    model = RequiredValidationRule

    def setUp(self):
        RequiredValidationRule.objects.create(
            name="Required rule 0",
            content_type=ContentType.objects.get_for_model(Device),
            field="device_redundancy_group",
        )
        super().setUp()

    def test_invalid_field_name(self):
        """Test that a non-existent model field is rejected."""
        rule = RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="afieldthatdoesnotexist",
        )

        with self.assertRaisesRegex(ValidationError, "Not a valid field for content type dcim.powerfeed."):
            rule.clean()

    def test_private_fields_cannot_be_used(self):
        """Test that a private model field is rejected."""
        rule = RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Cable),
            field="_abs_length",  # this is a private field used for caching a denormalized value
        )

        with self.assertRaisesRegex(ValidationError, "This field's type does not support required validation."):
            rule.clean()

    def test_blacklisted_fields_cannot_be_used(self):
        """Test that a blacklisted model field is rejected."""
        rule = RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Job),
            field="id",  # Job.id is an AutoField which is blacklisted
        )

        with self.assertRaisesRegex(ValidationError, "This field's type does not support required validation."):
            rule.clean()

    def test_default_required_field_cannot_be_used(self):
        """Test that a field that is already required cannot be used."""
        rule = RequiredValidationRule.objects.create(
            name="Required rule 1",
            content_type=ContentType.objects.get_for_model(Location),
            field="name",
        )

        with self.assertRaisesRegex(ValidationError, "This field is already required by default."):
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


class UniqueValidationRuleModelTestCase(ValidationRuleModelTestCases.ValidationRuleModelTestCase):
    """
    Test cases related to the UniqueValidationRule model
    """

    model = UniqueValidationRule

    def setUp(self):
        UniqueValidationRule.objects.create(
            name="Unique rule 0",
            content_type=ContentType.objects.get_for_model(Device),
            field="serial",
            max_instances=1,
        )
        super().setUp()

    def test_invalid_field_name(self):
        """Test that a non-existent model field is rejected."""
        rule = UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(PowerFeed),
            field="afieldthatdoesnotexist",
        )

        with self.assertRaisesRegex(ValidationError, "Not a valid field for content type dcim.powerfeed."):
            rule.clean()

    def test_private_fields_cannot_be_used(self):
        """Test that a private model field is rejected."""
        rule = UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(Cable),
            field="_abs_length",  # this is a private field used for caching a denormalized value
        )

        with self.assertRaisesRegex(ValidationError, "This field's type does not support uniqueness validation."):
            rule.clean()

    def test_blacklisted_fields_cannot_be_used(self):
        """Test that a blacklisted model field is rejected."""
        rule = UniqueValidationRule.objects.create(
            name="Unique rule 1",
            content_type=ContentType.objects.get_for_model(Job),
            field="id",  # Job.id is an AutoField which is blacklisted
        )

        with self.assertRaisesRegex(ValidationError, "This field's type does not support uniqueness validation."):
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


class ValidationRuleModelMixinTestCase(TestCase):
    """
    Validate ValidationRuleModelMixin is working as intended.
    """

    def test_is_data_compliance_model(self):
        """Validate is_data_compliance_model is set correctly on models using ValidationRuleModelMixin."""
        # These models should have is_data_compliance_model = False
        self.assertFalse(MinMaxValidationRule.is_data_compliance_model)
        self.assertFalse(RegularExpressionValidationRule.is_data_compliance_model)
        self.assertFalse(RequiredValidationRule.is_data_compliance_model)
        self.assertFalse(UniqueValidationRule.is_data_compliance_model)
