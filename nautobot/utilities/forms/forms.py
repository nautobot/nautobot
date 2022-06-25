import json
import re

import yaml
from django import forms
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db.models import fields, ManyToOneRel, ManyToManyRel
from django.db.models.fields import related
from django.forms import inlineformset_factory, formset_factory, BaseFormSet
from django.urls import reverse
from taggit.managers import TaggableManager

from nautobot.ipam.formfields import IPNetworkFormField

__all__ = (
    "AddressFieldMixin",
    "BaseFilterForm",
    "BootstrapMixin",
    "BulkEditForm",
    "BulkRenameForm",
    "ConfirmationForm",
    "CSVModelForm",
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


class SelectWidgetWithConfigurableOptions(forms.Select):
    def __init__(self, *args, model=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.attrs["class"] = "nautobot-select2-static"

    def get_field_data_type(self, field_name):
        """
        Get model field value data type

        Args:
            field_name: model field name

        Returns:
            A dict of field-type and/or field url(if field-type is a choice field)

        """
        field = {"data-field-type": "text"}
        field_extension = None
        if "__" in field_name:
            field_values = field_name.split("__")
            field_name = field_values[0]
            field_extension = field_values[1]

        try:
            field_instance = self.model._meta.get_field(field_name)
            if isinstance(field_instance, (ManyToOneRel, fields.related.ForeignKey, ManyToManyRel, TaggableManager)):
                if field_extension is not None and field_extension != "slug":
                    # get the extension related_model
                    # e.g. if field is tenant__group,
                    # tenant has a foreign key field "group" so we get group related_model instead of tenant model
                    field_model = field_instance.related_model._meta.get_field(field_extension).related_model
                else:
                    field_model = field_instance.related_model

                app_label = field_model._meta.app_label
                model_name = field_model._meta.model_name
                if app_label in settings.PLUGINS:
                    data_url = reverse(f"plugins-api:{app_label}-api:{model_name}-list")
                else:
                    data_url = reverse(f"{app_label}-api:{model_name}-list")

                parent_app_label = self.model._meta.app_label
                parent_model_name = self.model._meta.model_name

                content_types_included_in_filterset = (
                    "content_types" in get_filterset_for_model(field_model).get_fields()
                )

                field = {
                    "data-field-type": "select",
                    "data-field-data-url": data_url,
                }
                if content_types_included_in_filterset is True:
                    field["data-query-param-content_types"] = f'["{parent_app_label.strip()}.{parent_model_name}"]'

        except FieldDoesNotExist:
            pass

        return field

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        data = super().create_option(name, value, label, selected, index, subindex, attrs)
        data["attrs"].update(self.get_field_data_type(value))

        return data


class LookUpFilterForm(BootstrapMixin, forms.Form):
    """
    Form for configuring user's filter form preferences.
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
    value = forms.CharField(required=False)
    advance_filter = forms.JSONField()

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Initialize columns field based on table attributes
        lookup_field_choices = self.get_lookup_expr_choices()

        self.fields["lookup_field"].widget = SelectWidgetWithConfigurableOptions(model=self.model)
        lookup_field_css = self.fields["lookup_field"].widget.attrs.get("class")
        self.fields["lookup_field"].widget.attrs["class"] = " ".join([lookup_field_css, "lookup_field-select"])
        self.fields["lookup_field"].choices = [(None, None)] + [(item, item) for item in lookup_field_choices.keys()]

        self.fields["lookup_type"].widget.attrs["class"] = "nautobot-select2-static lookup_type-select"
        self.fields["lookup_type"].choices = [(None, None)] + [
            (item["name"], item["lookup_label"]) for item in lookup_field_choices["contact_name"]
        ]

        self.fields["value"].widget.attrs["class"] = "value-input form-control"

        self.fields["advance_filter"].widget.attrs["rows"] = 1
        self.fields["advance_filter"].widget.attrs["disabled"] = "true"
        from django.forms import HiddenInput
        self.fields["advance_filter"].widget = HiddenInput()

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


def lookup_formset_factory(model, **kwargs):
    modelform = LookUpFilterForm
    modelform.model = model

    params = {
        "can_delete_extra": False,
        "can_delete": False,
        "extra": 3,
    }

    kwargs.update(params)
    form = formset_factory(form=LookUpFilterForm, **kwargs)

    return form


LookupFilterFormSet = lookup_formset_factory
