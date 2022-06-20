import json
import re

import yaml
from django import forms
from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields import related

from nautobot.ipam.formfields import IPNetworkFormField

__all__ = (
    "AddressFieldMixin",
    "BaseFilterForm",
    "BootstrapMixin",
    "BulkEditForm",
    "BulkRenameForm",
    "ConfirmationForm",
    "CSVModelForm",
    "FilterConfigForm",
    "ImportForm",
    "LookUpFilterForm",
    "PrefixFieldMixin",
    "ReturnURLForm",
    "TableConfigForm",
)

from nautobot.utilities.forms import DynamicModelMultipleChoiceField
from nautobot.utilities.utils import get_filterset_for_model


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

        for field_name, field in self.fields.items():
            if field.widget.__class__ not in exempt_widgets:
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = " ".join([css, "form-control"]).strip()
            if field.required and not isinstance(field.widget, forms.FileInput):
                field.widget.attrs["required"] = "required"
            if "placeholder" not in field.widget.attrs:
                field.widget.attrs["placeholder"] = field.label


class BaseFilterForm(forms.BaseForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Defaults
        self.selected_fields = [field.name for field in self.visible_fields()]
        self.columns_sequence = [
            (field.name, field.label) for field in self.visible_fields()
        ] + self.get_filterset_fields_name_and_label(self.selected_fields)

        if user is not None and user.is_authenticated:
            user_config = f"filter_form.{self.__class__.__name__}"
            columns = user.get_config(user_config + ".columns")
            lookup_expr = user.get_config(user_config + ".lookup_expr")
            fields_to_remove = []

            if columns:
                self.selected_fields = columns
                self.fields.update(
                    self.get_filterset_fields(
                        default_visible_fields=[field.name for field in self.visible_fields()],
                        selected_fields=columns,
                    )
                )
                fields_to_remove = [field for field in self.fields.keys() if field not in columns]

            for field in fields_to_remove:
                self.fields.pop(field)

        self.order_fields(self.selected_fields)
        self.order_columns_sequence(self.selected_fields)

    def get_filterset_fields_name_and_label(self, default_visible_fields):
        filters = get_filterset_for_model(self.model).get_filters()
        filters_fields = []
        for name, item in filters.items():
            if name not in default_visible_fields and "__" not in name:
                filters_fields.append((name, name))

        return filters_fields

    def get_filterset_fields(self, default_visible_fields, selected_fields):
        filters = get_filterset_for_model(self.model).get_filters()
        fields = {}

        for name, item in filters.items():
            if name not in default_visible_fields and name in selected_fields and "__" not in name:
                fields[name] = self.get_form_field(name)
                if "__" in name:
                    field_name = item.field_name[0].upper() + item.field_name[1:]
                    fields[name].label = f"{field_name} {item.lookup_expr}"
                else:
                    fields[name].label = item.label
        return fields

    def order_columns_sequence(self, field_order=None):
        """
        Rearrange the columns_sequence according to field_order.

        Args:
            field_order (list): A list of field names specifying the order.
        """
        ordered_fields = {}
        fields = dict(self.columns_sequence)

        for key in field_order:
            if key in fields:
                ordered_fields[key] = fields.pop(key)

        ordered_fields.update(fields)
        self.columns_sequence = ordered_fields.items()

    def get_form_field(self, name):
        """
        Return the appropriate form field(e.g CharField, DynamicModelMultipleChoiceField, BooleanField) for model field`

        Args:
            name (str): Model field name
        """
        form = forms.CharField(required=False)

        if "__" not in name:
            try:
                field_instance = self.model._meta.get_field(name)
                if isinstance(field_instance, (related.ForeignKey, related.ManyToManyField)):
                    related_model = getattr(field_instance, "related_model", None)
                    form = DynamicModelMultipleChoiceField(queryset=related_model.objects.all(), required=False)
                # TODO: Add check for other types eg Integer, boolean etc
            except FieldDoesNotExist:
                pass
        else:
            ...

        return form


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
    Base form for editing multiple objects in bulk
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
        format = self.cleaned_data["format"]

        # Process JSON/YAML data
        if format == "json":
            try:
                self.cleaned_data["data"] = json.loads(data)
                # Check for multiple JSON objects
                if not isinstance(self.cleaned_data["data"], dict):
                    raise forms.ValidationError({"data": "Import is limited to one object at a time."})
            except json.decoder.JSONDecodeError as err:
                raise forms.ValidationError({"data": "Invalid JSON data: {}".format(err)})
        else:
            # Check for multiple YAML documents
            if "\n---" in data:
                raise forms.ValidationError({"data": "Import is limited to one object at a time."})
            try:
                self.cleaned_data["data"] = yaml.load(data, Loader=yaml.SafeLoader)
            except yaml.error.YAMLError as err:
                raise forms.ValidationError({"data": "Invalid YAML data: {}".format(err)})


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


class FilterConfigForm(BootstrapMixin, forms.Form):
    """
    Form for configuring user's filter form preferences.
    """

    columns = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
        help_text="Use the buttons below to arrange columns in the desired order, then select all columns to display.",
    )

    def __init__(self, form, *args, **kwargs):
        self.form = form

        super().__init__(*args, **kwargs)

        # Initialize columns field based on table attributes
        self.fields["columns"].choices = form.columns_sequence
        self.fields["columns"].initial = form.selected_fields

    @property
    def form_name(self):
        return self.form.__class__.__name__


class LookUpFilterForm(BootstrapMixin, forms.Form):
    """
    Form for configuring user's filter form preferences.
    """

    lookup_field = forms.ChoiceField(
        choices=[],
        required=False,
    )
    lookup_type = forms.ChoiceField(
        choices=[],
        required=False,
    )
    lookup_value = forms.CharField(
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop("model", None)

        super().__init__(*args, **kwargs)

        # Initialize columns field based on table attributes
        lookup_field_choices = self.get_lookup_expr_choices()

        self.fields["lookup_field"].choices = [(item, item) for item in lookup_field_choices.keys()]
        self.fields["lookup_field"].widget.attrs["data-lookup-expr"] = json.dumps(lookup_field_choices)

    def get_lookup_expr_choices(self):
        filters = get_filterset_for_model(self.model).get_filters()
        lookup_fields = {}
        for name, item in filters.items():
            if "__" in name:
                data = {
                    "name": name,
                    "lookup_field": item.field_name,
                    "lookup_type": item.lookup_expr,
                    "lookup_label": name.split("__")[-1] + " - " + item.lookup_expr,
                }
                lookup_fields.setdefault(item.field_name, []).append(data)
        return dict(sorted(lookup_fields.items(), key=lambda d: d[0]))
