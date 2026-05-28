from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nautobot.dcim import models as dcim_models
from nautobot.dcim.forms import LocationForm
from nautobot.dcim.models import Location
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.forms import CustomFieldModelFormMixin
from nautobot.extras.models import CustomField


class CustomFieldModelFormMixinTestCase(TestCase):
    def setUp(self):
        ct = ContentType.objects.get_for_model(Location)
        cf = CustomField(
            type=CustomFieldTypeChoices.TYPE_TEXT,
            label="My Field",
            key="my_field",
            required=False,
            default="my_field_default",
        )
        cf.validated_save()
        cf.content_types.set([ct])

        self.my_custom_field = cf

    def test_custom_field_data_removed_in_all(self):
        """Asserts that when `__all__` is set on a CustomFieldModelFormMixin, _custom_field_data is stripped."""

        class TestForm(CustomFieldModelFormMixin):
            class Meta:
                model = dcim_models.InterfaceRedundancyGroup
                fields = "__all__"

        custom_field_form = TestForm()
        self.assertNotIn("_custom_field_data", custom_field_form.fields)

    def test_custom_field_data_kept_if_explicit(self):
        """Asserts that _custom_field_data will still show up if explicitly set."""

        class TestForm(CustomFieldModelFormMixin):
            class Meta:
                model = dcim_models.InterfaceRedundancyGroup
                fields = ["_custom_field_data"]

        custom_field_form = TestForm()
        self.assertIn("_custom_field_data", custom_field_form.fields)

    def test_custom_field_is_added_on_create_form(self):
        """
        Test that a custom field is added to the form on a creation form.
        """
        form = LocationForm()

        self.assertIn("cf_my_field", form.fields)
        self.assertIn("cf_my_field", form.custom_fields)
        self.assertEqual(form.fields["cf_my_field"].initial, "my_field_default")

    def test_custom_field_is_added_on_edit_form(self):
        """
        Test that a custom field is added to the form on an edit form.
        """
        instance = Location.objects.first()
        form = LocationForm(instance=instance)

        self.assertIn("cf_my_field", form.fields)
        self.assertIn("cf_my_field", form.custom_fields)
        self.assertEqual(form.fields["cf_my_field"].initial, None)

        instance.cf["my_field"] = "my_field_value"
        instance.save()

        form = LocationForm(instance=instance)

        self.assertIn("cf_my_field", form.fields)
        self.assertIn("cf_my_field", form.custom_fields)
        self.assertEqual(form.fields["cf_my_field"].initial, "my_field_value")

    def test_scoped_custom_field_is_added_on_edit_form_when_in_scope(self):
        """
        Test that a custom field is added to the form when it is in a scope filter.
        """
        instance = Location.objects.first()

        self.my_custom_field.scope_filter = {"name": instance.name}
        self.my_custom_field.save()

        form = LocationForm(instance=instance)

        self.assertIn("cf_my_field", form.fields)
        self.assertIn("cf_my_field", form.custom_fields)
        self.assertEqual(form.fields["cf_my_field"].initial, None)

    def test_scoped_custom_field_is_not_added_when_out_of_scope(self):
        """
        Test that a custom field is not added to the form when it is not in a scope filter.
        """
        self.my_custom_field.scope_filter = {"name": "My location"}
        self.my_custom_field.save()

        instance = Location.objects.first()
        form = LocationForm(instance=instance)

        self.assertNotIn("cf_my_field", form.fields)
        self.assertNotIn("cf_my_field", form.custom_fields)

    def test_scoped_custom_field_is_added_on_create_form(self):
        """
        Test that a custom field is added to the form when it is a create form, even if out of scope.
        """
        self.my_custom_field.scope_filter = {"name": "My location"}
        self.my_custom_field.save()

        form = LocationForm()

        self.assertIn("cf_my_field", form.fields)
        self.assertIn("cf_my_field", form.custom_fields)
        self.assertEqual(form.fields["cf_my_field"].initial, "my_field_default")
