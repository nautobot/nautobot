import json
import re

import yaml
from django import forms

from nautobot.ipam.formfields import IPNetworkFormField

__all__ = (
    "AddressFieldMixin",
    "BootstrapMixin",
    "BulkEditForm",
    "BulkRenameForm",
    "ConfirmationForm",
    "CSVModelForm",
    "ImportForm",
    "PrefixFieldMixin",
    "ReturnURLForm",
    "TableConfigForm",
)


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


# Form set factories


def meta_class_factory(**kwargs):
    return type("Meta", (), kwargs)


def form_class_factory(class_name, bases, class_attrs, meta_class_attrs):
    try:
        bases = tuple(bases)
    except TypeError:
        bases = tuple([bases])
    meta_class = meta_class_factory(**meta_class_attrs)
    class_attrs["Meta"] = meta_class
    return type(class_name, bases, class_attrs)


# Form sets


class NautobotFormSet:
    """Form set for creating sets of forms dynamically"""

    class Meta:
        fields = None
        model = None

    @classmethod
    def get_form_specific_attrs(cls, prefix):
        """
        Return attributes defined on the FormSet class with names starting with the supplied prefix
        Remove the prefix before returning a mapping of the attributes
        """
        form_specific_attrs = {}
        for key, value in cls.__dict__.items():
            if key.startswith(f"{prefix}_"):
                key_without_prefix = key.removeprefix(f"{prefix}_")
                form_specific_attrs[key_without_prefix] = value
        return form_specific_attrs

    @classmethod
    def get_form_specific_fields(cls, prefix):
        """
        Return form fields defined on the FormSet class with names starting with the supplied prefix
        Fields must be an instance of django.forms.Field. Remove the prefix before returning a mapping of the fields
        """
        attrs = cls.get_form_specific_attrs(prefix)
        form_specific_fields = {k: v for k, v in attrs.items() if isinstance(v, forms.Field)}
        return form_specific_fields


class NautobotFormSetEditFormMixin:
    """
    Mixin for NautobotFormSet to create a new object edit form class.
    The class will be named {formset name}EditForm
    The FormSet Meta class must have these attributes set:
    model: The class of the database model

    Optional Meta attributes:
    edit_form_fields: set as the new form's Meta.fields attribute
    edit_form_widgets: set as the new form's Meta.widgets attribute
    fields: set as the new form's Meta.fields attribute, only used if edit_form_fields is not set

    Static field definitions may be created similar to django's built-in ModelForm by declaring
    them on the FormSet class, but each field name must be prefixed with `edit_form_`
    Example for a field named description:
    edit_form_description = forms.CharField(max_length=200, blank=True)
    """

    @classmethod
    def object_edit_form(cls, *args, **kwargs):
        """Return a dynamically generated object edit form class"""
        if not hasattr(cls, "_edit_form"):
            meta_class_attrs = cls._get_edit_form_meta_class_attrs()
            bases = cls._get_edit_form_bases()
            form_class_name = f"{cls.__name__}EditForm"
            class_attrs = cls.get_form_specific_fields("edit_form")
            cls._edit_form = form_class_factory(form_class_name, bases, class_attrs, meta_class_attrs)

        return cls._edit_form

    @classmethod
    def _get_edit_form_meta_class_attrs(cls):
        """Return mapping of attributes for the form's Meta class"""
        meta_class_attrs = {
            "model": cls.Meta.model,
        }
        fields = cls._get_edit_form_meta_fields()
        if fields is not None:
            meta_class_attrs["fields"] = fields
        widgets = getattr(cls.Meta, "edit_form_widgets", None)
        if widgets is not None:
            meta_class_attrs["widgets"] = widgets
        return meta_class_attrs

    @classmethod
    def _get_edit_form_bases(cls):
        """Return list of base classes for the form by inspecting the base classes of the model"""
        #  prevent circular imports
        from nautobot.extras.forms import CustomFieldModelFormMixin, RelationshipModelFormMixin
        from nautobot.extras.forms.mixins import NoteModelFormMixin
        from nautobot.extras.models import CustomFieldModel, RelationshipModel
        from nautobot.extras.models.mixins import NotesMixin

        model_form_mapping = {
            CustomFieldModel: CustomFieldModelFormMixin,
            RelationshipModel: RelationshipModelFormMixin,
            NotesMixin: NoteModelFormMixin,
        }
        bases = [BootstrapMixin]
        for base_model, form in model_form_mapping.items():
            if issubclass(cls.Meta.model, base_model):
                bases.append(form)
        bases.append(forms.ModelForm)
        return bases

    @classmethod
    def _get_edit_form_meta_fields(cls):
        """Retrieve Meta.fields for the form from the FormSet.Meta class"""
        if hasattr(cls.Meta, "edit_form_fields"):
            return cls.Meta.edit_form_fields
        else:
            return getattr(cls.Meta, "fields", None)


class NautobotFormSetCSVFormMixin:
    """
    Mixin for NautobotFormSet to create a new csv import form class.
    The class will be named {formset name}CSVForm
    The FormSet Meta class must have these attributes set:
    model: The class of the database model

    Optional Meta attributes:
    csv_form_fields: set as the new form's Meta.fields attribute, overriding the default model.csv_headers

    Static field definitions may be created similar to django's built-in ModelForm by declaring
    them on the FormSet class, but each field name must be prefixed with `csv_form_`
    Example for a field named description:
    csv_form_description = forms.CharField(max_length=200, blank=True)
    """

    @classmethod
    def csv_form(cls, *args, **kwargs):
        """Return a dynamically generated csv import form class"""
        if not hasattr(cls, "_csv_form"):
            meta_class_attrs = cls._get_csv_form_meta_class_attrs()
            bases = cls._get_csv_form_bases()
            form_class_name = f"{cls.__name__}CSVForm"
            class_attrs = cls.get_form_specific_fields("csv_form")
            cls._csv_form = form_class_factory(form_class_name, bases, class_attrs, meta_class_attrs)

        return cls._csv_form

    @classmethod
    def _get_csv_form_meta_class_attrs(cls):
        """Return mapping of attributes for the form's Meta class"""
        meta_class_attrs = {
            "model": cls.Meta.model,
            "fields": cls._get_csv_form_meta_fields(),
        }
        return meta_class_attrs

    @classmethod
    def _get_csv_form_bases(cls):
        """Return list of base classes for the form by inspecting the base classes of the model"""
        #  prevent circular imports
        from nautobot.extras.forms import CustomFieldModelCSVForm, StatusModelCSVFormMixin
        from nautobot.extras.models import CustomFieldModel, StatusModel

        csv_model_form_mapping = {
            CustomFieldModel: CustomFieldModelCSVForm,
            StatusModel: StatusModelCSVFormMixin,
        }
        bases = []
        for base_model, form in csv_model_form_mapping.items():
            if issubclass(cls.Meta.model, base_model):
                bases.append(form)
        bases.append(CSVModelForm)
        return bases

    @classmethod
    def _get_csv_form_meta_fields(cls):
        """Retrieve Meta.fields for the form from the FormSet.Meta class if set, otherwise use the model's csv_headers"""
        if hasattr(cls.Meta, "csv_form_fields"):
            return cls.Meta.edit_form_fields
        else:
            return cls.Meta.model.csv_headers
