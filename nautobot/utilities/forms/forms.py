import json
import logging
import re

import yaml
from django import forms
from django.forms import formset_factory
from django.urls import reverse

from nautobot.ipam.formfields import IPNetworkFormField
from nautobot.utilities.utils import (
    build_lookup_label,
    get_filterset_parameter_form_field,
)

__all__ = (
    "AddressFieldMixin",
    "BootstrapMixin",
    "BulkEditForm",
    "BulkRenameForm",
    "ConfirmationForm",
    "CSVModelForm",
    "DynamicFilterForm",
    "ImportForm",
    "PrefixFieldMixin",
    "ReturnURLForm",
    "TableConfigForm",
)


logger = logging.getLogger(__name__)


class AddressFieldMixin(forms.ModelForm):
    """
    ModelForm mixin for IPAddress based models.
    """

    address = IPNetworkFormField()

    def __init__(self, *args, **kwargs):

        instance = kwargs.get("instance")
        initial = kwargs.get("initial", {}).copy()

        # If initial already has an `address`, we want to use that `address` as it was passed into
        # the form. If we're editing an object with a `address` field, we need to patch initial
        # to include `address` because it is a computed field.
        if "address" not in initial and instance is not None:
            initial["address"] = instance.address

        kwargs["initial"] = initial

        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        # Need to set instance attribute for `address` to run proper validation on Model.clean()
        self.instance.address = self.cleaned_data.get("address")


class BootstrapMixin(forms.BaseForm):
    """
    Add the base Bootstrap CSS classes to form elements.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        exempt_widgets = [
            forms.CheckboxInput,
            forms.ClearableFileInput,
            forms.FileInput,
            forms.RadioSelect,
        ]

        for field in self.fields.values():
            if field.widget.__class__ not in exempt_widgets:
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = " ".join([css, "form-control"]).strip()
            if field.required and not isinstance(field.widget, forms.FileInput):
                field.widget.attrs["required"] = "required"
            if "placeholder" not in field.widget.attrs:
                field.widget.attrs["placeholder"] = field.label


class ReturnURLForm(forms.Form):
    """
    Provides a hidden return URL field to control where the user is directed after the form is submitted.
    """

    return_url = forms.CharField(required=False, widget=forms.HiddenInput())


class ConfirmationForm(BootstrapMixin, ReturnURLForm):
    """
    A generic confirmation form. The form is not valid unless the confirm field is checked.
    """

    confirm = forms.BooleanField(required=True, widget=forms.HiddenInput(), initial=True)


class BulkEditForm(forms.Form):
    """
    Base form for editing multiple objects in bulk.

    Note that for models supporting custom fields and relationships, nautobot.extras.forms.NautobotBulkEditForm is
    a more powerful subclass and should be used instead of directly inheriting from this class.
    """

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.nullable_fields = []

        # Copy any nullable fields defined in Meta
        if hasattr(self.Meta, "nullable_fields"):
            self.nullable_fields = self.Meta.nullable_fields


class BulkRenameForm(forms.Form):
    """
    An extendable form to be used for renaming objects in bulk.
    """

    find = forms.CharField()
    replace = forms.CharField()
    use_regex = forms.BooleanField(required=False, initial=True, label="Use regular expressions")

    def clean(self):
        super().clean()

        # Validate regular expression in "find" field
        if self.cleaned_data["use_regex"]:
            try:
                re.compile(self.cleaned_data["find"])
            except re.error:
                raise forms.ValidationError({"find": "Invalid regular expression"})


class CSVModelForm(forms.ModelForm):
    """
    ModelForm used for the import of objects in CSV format.
    """

    def __init__(self, *args, headers=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Modify the model form to accommodate any customized to_field_name properties
        if headers:
            for field, to_field in headers.items():
                if to_field is not None:
                    self.fields[field].to_field_name = to_field


class PrefixFieldMixin(forms.ModelForm):
    """
    ModelForm mixin for IPNetwork based models.
    """

    prefix = IPNetworkFormField()

    def __init__(self, *args, **kwargs):

        instance = kwargs.get("instance")
        initial = kwargs.get("initial", {}).copy()

        # If initial already has a `prefix`, we want to use that `prefix` as it was passed into
        # the form. If we're editing an object with a `prefix` field, we need to patch initial
        # to include `prefix` because it is a computed field.
        if "prefix" not in initial and instance is not None:
            initial["prefix"] = instance.prefix

        kwargs["initial"] = initial

        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        # Need to set instance attribute for `prefix` to run proper validation on Model.clean()
        self.instance.prefix = self.cleaned_data.get("prefix")


class ImportForm(BootstrapMixin, forms.Form):
    """
    Generic form for creating an object from JSON/YAML data
    """

    data = forms.CharField(
        widget=forms.Textarea,
        help_text="Enter object data in JSON or YAML format. Note: Only a single object/document is supported.",
        label="",
    )
    format = forms.ChoiceField(choices=(("json", "JSON"), ("yaml", "YAML")), initial="yaml")

    def clean(self):
        super().clean()

        data = self.cleaned_data["data"]
        format_ = self.cleaned_data["format"]

        # Process JSON/YAML data
        if format_ == "json":
            try:
                self.cleaned_data["data"] = json.loads(data)
                # Check for multiple JSON objects
                if not isinstance(self.cleaned_data["data"], dict):
                    raise forms.ValidationError({"data": "Import is limited to one object at a time."})
            except json.decoder.JSONDecodeError as err:
                raise forms.ValidationError({"data": f"Invalid JSON data: {err}"})
        else:
            # Check for multiple YAML documents
            if "\n---" in data:
                raise forms.ValidationError({"data": "Import is limited to one object at a time."})
            try:
                self.cleaned_data["data"] = yaml.load(data, Loader=yaml.SafeLoader)
            except yaml.error.YAMLError as err:
                raise forms.ValidationError({"data": f"Invalid YAML data: {err}"})


class TableConfigForm(BootstrapMixin, forms.Form):
    """
    Form for configuring user's table preferences.
    """

    columns = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
        help_text="Use the buttons below to arrange columns in the desired order, then select all columns to display.",
    )

    def __init__(self, table, *args, **kwargs):
        self.table = table

        super().__init__(*args, **kwargs)

        # Initialize columns field based on table attributes
        self.fields["columns"].choices = table.configurable_columns
        self.fields["columns"].initial = table.visible_columns

    @property
    def table_name(self):
        return self.table.__class__.__name__


class DynamicFilterForm(BootstrapMixin, forms.Form):
    """
    Form for dynamically inputting filter values for an object list.
    """

    lookup_field = forms.ChoiceField(
        choices=[],
        required=False,
        label="Field",
    )
    lookup_type = forms.ChoiceField(
        choices=[],
        required=False,
    )
    lookup_value = forms.CharField(
        required=False,
        label="Value",
    )

    def __init__(self, *args, filterset_class=None, **kwargs):
        super().__init__(*args, **kwargs)
        from nautobot.utilities.forms import add_blank_choice  # Avoid circular import

        # cls.model is set at `dynamic_formset_factory()`
        self.filterset_class = filterset_class or getattr(self, "filterset_class", None)

        # Raise exception if `cls.filterset_class` not set and `filterset_class` not passed
        if self.filterset_class is None:
            raise AttributeError("'DynamicFilterForm' object requires `filterset_class` attribute")

        model = self.filterset_class._meta.model

        if self.filterset_class is not None:
            filterset_class = self.filterset_class()
            self.filterset_filters = filterset_class.filters
            contenttype = model._meta.app_label + "." + model._meta.model_name

            # Configure fields: Add css class and set choices for lookup_field
            self.fields["lookup_field"].choices = add_blank_choice(self._get_lookup_field_choices())
            self.fields["lookup_field"].widget.attrs["class"] = "nautobot-select2-static lookup_field-select"

            # Update lookup_type and lookup_value fields to match expected field types derived from data
            # e.g status expects a ChoiceField with APISelectMultiple widget, while name expects a CharField etc.
            if "data" in kwargs and "prefix" in kwargs:
                data = kwargs["data"]
                prefix = kwargs["prefix"]
                lookup_type = data.get(prefix + "-lookup_type")
                lookup_value = data.getlist(prefix + "-lookup_value")

                if lookup_type and lookup_value and lookup_type in self.filterset_filters:
                    verbose_name = self.filterset_filters[lookup_type].lookup_expr
                    label = build_lookup_label(lookup_type, verbose_name)
                    self.fields["lookup_type"].choices = [(lookup_type, label)]
                    self.fields["lookup_value"] = get_filterset_parameter_form_field(model, lookup_type)
                elif lookup_type and lookup_type not in self.filterset_filters:
                    logger.warning(f"{lookup_type} is not a valid {filterset_class.__class__.__name__} field")

            self.fields["lookup_type"].widget.attrs["data-query-param-field_name"] = json.dumps(["$lookup_field"])
            self.fields["lookup_type"].widget.attrs["data-contenttype"] = contenttype
            self.fields["lookup_type"].widget.attrs["data-url"] = reverse("core-api:filtersetfield-list-lookupchoices")
            self.fields["lookup_type"].widget.attrs["class"] = "nautobot-select2-api lookup_type-select"

            lookup_value_css = self.fields["lookup_value"].widget.attrs.get("class") or ""
            self.fields["lookup_value"].widget.attrs["class"] = " ".join(
                [lookup_value_css, "lookup_value-input form-control"]
            )
        else:
            logger.warning(f"FilterSet for {model.__class__} not found.")

    @staticmethod
    def capitalize(field):
        field = field.replace("_custom_field_data__", "")
        split_field = field.split("__") if "__" in field else field.split("_")
        words = " ".join(split_field)
        return words[0].upper() + words[1:]

    def _get_lookup_field_choices(self):
        """Get choices for lookup_fields i.e filterset parameters without a lookup expr"""
        filterset_without_lookup = (
            (name, field.label or self.capitalize(field.field_name))
            for name, field in self.filterset_filters.items()
            if "__" not in name and name != "q"
        )
        return sorted(filterset_without_lookup)


def dynamic_formset_factory(filterset_class, data=None, **kwargs):
    filter_form = DynamicFilterForm
    filter_form.filterset_class = filterset_class

    params = {
        "can_delete_extra": True,
        "can_delete": True,
        "extra": 3,
    }
    kwargs.update(params)
    form = formset_factory(form=filter_form, **kwargs)
    if data:
        form = form(data=data)

    return form


DynamicFilterFormSet = dynamic_formset_factory
