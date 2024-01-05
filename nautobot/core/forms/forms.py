import json
import logging
import re

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.forms import formset_factory
from django.urls import reverse
import yaml

from nautobot.core.utils.filtering import build_lookup_label, get_filterset_parameter_form_field, get_filter_field_label
from nautobot.ipam import formfields

__all__ = (
    "AddressFieldMixin",
    "BaseInlineGFKFormSet",
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
    "inline_gfk_formset_factory",
)


logger = logging.getLogger(__name__)


class AddressFieldMixin(forms.ModelForm):
    """
    ModelForm mixin for IPAddress based models.
    """

    address = formfields.IPNetworkFormField()

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


class BaseInlineGFKFormSet(forms.BaseModelFormSet):
    """
    Like forms.BaseInlineFormSet, but for child objects related to a parent by GenericForeignKey rather than ForeignKey.
    """

    def __init__(self, data=None, files=None, instance=None, save_as_new=False, prefix=None, queryset=None, **kwargs):
        if instance is None:
            self.instance = self.ct_field.content_type.model()  # TODO
        else:
            self.instance = instance
        self.save_as_new = save_as_new
        if queryset is None:
            queryset = self.model._default_manager
        if self.instance.present_in_database:
            qs = queryset.filter(
                **{
                    self.ct_field.name: ContentType.objects.get_for_model(self.instance),
                    self.fk_field.name: self.instance.pk,
                }
            )
        else:
            qs = queryset.none()
        self.unique_fields = {self.ct_field.name, self.fk_field.name}
        super().__init__(data, files, prefix=prefix, queryset=qs, **kwargs)

        # Add the generated fields to form._meta.fields if it's defined to make
        # sure validation isn't skipped on those fields.
        if self.form._meta.fields and self.ct_field.name not in self.form._meta.fields:
            if isinstance(self.form._meta.fields, tuple):
                self.form._meta.fields = list(self.form._meta.fields)
            self.form._meta.fields.append(self.ct_field.name)
        if self.form._meta.fields and self.fk_field.name not in self.form._meta.fields:
            if isinstance(self.form._meta.fields, tuple):
                self.form._meta.fields = list(self.form._meta.fields)
            self.form._meta.fields.append(self.fk_field.name)

    def _construct_form(self, i, **kwargs):
        form = super()._construct_form(i, **kwargs)
        if self.save_as_new:
            mutable = getattr(form.data, "_mutable", None)
            # Allow modifying an immutable QueryDict
            if mutable is not None:
                form.data._mutable = True
            # Remove the primary key from the form's data, we are only creating new instances
            form.data[form.add_prefix(self._pk_field.name)] = None
            # Remove the foreign key from the form's data
            form.data[form.add_prefix(self.ct_field.name)] = None
            form.data[form.add_prefix(self.fk_field.name)] = None
            if mutable is not None:
                form.data._mutable = mutable

        # Set the GFK value here so that the form can do its validation.
        setattr(form.instance, self.fk_field.get_attname(), self.instance.pk)
        setattr(form.instance, self.ct_field.get_attname(), ContentType.objects.get_for_model(self.instance).pk)
        return form


def inline_gfk_formset_factory(
    parent_model,
    model,
    ct_field_name,
    fk_field_name,
    form=forms.ModelForm,
    formset=BaseInlineGFKFormSet,
    fields=None,
    exclude=None,
    extra=3,
    can_order=False,
    can_delete=True,
    max_num=None,
    formfield_callback=None,
    widgets=None,
    validate_max=False,
    localized_fields=None,
    labels=None,
    help_texts=None,
    error_messages=None,
    min_num=None,
    validate_min=False,
    field_classes=None,
    absolute_max=None,
    can_delete_extra=True,
):
    """Like django.forms.inlineformset_factory, but for GenericForeignKeys instead of ForeignKeys."""
    ct_field = [field for field in model._meta.fields if field.name == ct_field_name][0]
    fk_field = [field for field in model._meta.fields if field.name == fk_field_name][0]
    kwargs = {
        "form": form,
        "formfield_callback": formfield_callback,
        "formset": formset,
        "extra": extra,
        "can_delete": can_delete,
        "can_order": can_order,
        "fields": fields,
        "exclude": exclude,
        "min_num": min_num,
        "max_num": max_num,
        "widgets": widgets,
        "validate_min": validate_min,
        "validate_max": validate_max,
        "localized_fields": localized_fields,
        "labels": labels,
        "help_texts": help_texts,
        "error_messages": error_messages,
        "field_classes": field_classes,
        "absolute_max": absolute_max,
        "can_delete_extra": can_delete_extra,
    }
    FormSet = forms.modelformset_factory(model, **kwargs)
    FormSet.ct_field = ct_field
    FormSet.fk_field = fk_field
    return FormSet


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
    ModelForm used for the import of objects.

    Note: the name is misleading as since 2.0 this is no longer used for CSV imports; however it *is* still used for
    JSON/YAML imports of DeviceTypes and their component templates.
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

    prefix = formfields.IPNetworkFormField()

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

    def __init__(self, *args, filterset=None, **kwargs):
        super().__init__(*args, **kwargs)
        from nautobot.core.forms import add_blank_choice  # Avoid circular import

        # cls.model is set at `dynamic_formset_factory()`
        self.filterset = filterset or getattr(self, "filterset", None)

        # Raise exception if `cls.filterset` not set and `filterset` not passed
        if self.filterset is None:
            raise AttributeError("'DynamicFilterForm' object requires `filterset` attribute")

        model = self.filterset._meta.model

        if self.filterset is not None:
            self.filterset_filters = self.filterset.filters
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
                    self.fields["lookup_value"] = get_filterset_parameter_form_field(
                        model, lookup_type, filterset=self.filterset
                    )
                elif lookup_type and lookup_type not in self.filterset_filters:
                    logger.warning(f"{lookup_type} is not a valid {self.filterset.__class__.__name__} field")

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

    def _get_lookup_field_choices(self):
        """Get choices for lookup_fields i.e filterset parameters without a lookup expr"""
        from nautobot.extras.filters.mixins import RelationshipFilter  # Avoid circular import

        filterset_without_lookup = (
            (
                name,
                get_filter_field_label(filter_field),
            )
            for name, filter_field in self.filterset_filters.items()
            if isinstance(filter_field, RelationshipFilter) or ("__" not in name and name != "q")
        )
        return sorted(filterset_without_lookup, key=lambda x: x[1])


def dynamic_formset_factory(filterset, data=None, **kwargs):
    filter_form = DynamicFilterForm
    filter_form.filterset = filterset

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
