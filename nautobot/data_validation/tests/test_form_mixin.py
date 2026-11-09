from django import forms
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nautobot.core.testing.mixins import NautobotTestCaseMixin
from nautobot.data_validation.form_mixin import DataValidationModelFormMixin
from nautobot.data_validation.models import RequiredValidationRule
from nautobot.data_validation.tests import ValidationRuleTestCaseMixin
from nautobot.dcim.models import Location


class DataValidationFormMixinTestCase(ValidationRuleTestCaseMixin, NautobotTestCaseMixin, TestCase):
    model = RequiredValidationRule

    @classmethod
    def setUpTestData(cls):
        cls.content_type = ContentType.objects.get_for_model(Location)
        cls.TestModel = Location
        cls.facility_required = RequiredValidationRule.objects.create(
            content_type=cls.content_type,
            field="facility",
            enabled=True,
            name="Facility required",
        )

    def test_mixin_sets_required_field_with_rule(self):
        """Test that fields become required when rules exist."""

        class TestModelForm(DataValidationModelFormMixin, forms.ModelForm):
            class Meta:
                model = self.TestModel
                fields = ["name", "facility", "description"]

        form = TestModelForm()
        self.assertTrue(form.fields["name"].required)  # Required by default
        self.assertTrue(form.fields["facility"].required)
        self.assertFalse(form.fields["description"].required)

    def test_mixin_sets_all_required_field_with_rule(self):
        """Test that all needed fields become required when rules exist."""
        RequiredValidationRule.objects.create(
            content_type=self.content_type,
            field="description",
            enabled=True,
            name="Description required",
        )

        class TestModelForm(DataValidationModelFormMixin, forms.ModelForm):
            class Meta:
                model = self.TestModel
                fields = ["name", "facility", "description"]

        form = TestModelForm()
        self.assertTrue(form.fields["name"].required)  # Required by default
        self.assertTrue(form.fields["facility"].required)
        self.assertTrue(form.fields["description"].required)

    def test_mixin_works_with_enabled_rules_only(self):
        """Test that all needed fields become required when rules are enabled."""
        RequiredValidationRule.objects.get_or_create(
            content_type=self.content_type,
            field="time_zone",
            enabled=False,
        )

        class TestModelForm(DataValidationModelFormMixin, forms.ModelForm):
            class Meta:
                model = self.TestModel
                fields = ["facility", "time_zone"]

        form = TestModelForm()
        self.assertTrue(form.fields["facility"].required)
        self.assertFalse(form.fields["time_zone"].required)

    def test_custom_error_message_applied(self):
        """Test custom error messages populate widget attributes."""
        error_msg = "<div>Custom error message</div>"

        RequiredValidationRule.objects.get_or_create(
            content_type=self.content_type,
            field="asn",
            enabled=True,
            name="ASN required",
            error_message=error_msg,
        )

        class TestModelForm(DataValidationModelFormMixin, forms.ModelForm):
            class Meta:
                model = self.TestModel
                fields = ["asn"]

        form = TestModelForm()
        widget_attrs = form.fields["asn"].widget.attrs
        self.assertEqual(widget_attrs["data-nb-required-message"], "Custom error message")
        self.assertNotIn("oninvalid", widget_attrs)

    def test_custom_error_message_is_not_rendered_as_script(self):
        """Test custom error messages render only as escaped data, never inside an event handler."""
        RequiredValidationRule.objects.create(
            content_type=self.content_type,
            field="asn",
            enabled=True,
            name="ASN required",
            error_message='It\'s "required" & needed',
        )

        class TestModelForm(DataValidationModelFormMixin, forms.ModelForm):
            class Meta:
                model = self.TestModel
                fields = ["asn"]

        rendered = str(TestModelForm()["asn"])
        self.assertNotRegex(rendered, r"\son\w+=")
        self.assertIn('data-nb-required-message="It&#x27;s &quot;required&quot; &amp; needed"', rendered)

    def test_form_without_error_message_has_no_data_attribute(self):
        """Test rules without a custom error message add no message attribute."""

        class TestModelForm(DataValidationModelFormMixin, forms.ModelForm):
            class Meta:
                model = self.TestModel
                fields = ["facility"]

        form = TestModelForm()
        self.assertTrue(form.fields["facility"].required)
        self.assertNotIn("data-nb-required-message", form.fields["facility"].widget.attrs)

    def test_no_changes_in_form_if_no_rules(self):
        """Test fields remain unmodified without rules."""

        class TestModelForm(DataValidationModelFormMixin, forms.ModelForm):
            class Meta:
                model = self.TestModel
                fields = ["name", "description"]

        form = TestModelForm()
        self.assertTrue(form.fields["name"].required)
        self.assertFalse(form.fields["description"].required)

    def test_non_model_form_ignored(self):
        """Test mixin skips processing for non-ModelForms."""

        class TestModelForm(DataValidationModelFormMixin, forms.Form):
            facility = forms.CharField(required=False)

        with self.assertRaises(TypeError):
            TestModelForm()
