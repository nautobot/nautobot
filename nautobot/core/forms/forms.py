import contextlib
import json
import logging
import re

from django import forms
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.models.fields.related import ManyToManyField
from django.forms import BaseInlineFormSet, formset_factory
from django.urls import reverse
from django.utils.text import capfirst
import yaml

from nautobot.core.forms import widgets as nautobot_widgets
from nautobot.core.utils.filtering import build_lookup_label, get_filter_field_label, get_filterset_parameter_form_field
from nautobot.ipam import formfields

__all__ = (
    "AddressFieldMixin",
    "BootstrapMixin",
    "BulkEditForm",
    "BulkRenameForm",
    "CSVModelForm",
    "ConfirmationForm",
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


class BootstrapMixin(forms.BaseForm):
    """
    Add the base Bootstrap CSS classes to form elements.

    Note that this only applies to form fields that are:

    1. statically defined on the form class at declaration time, or
    2. dynamically added to the form at init time by a class **later in the MRO than this mixin**.

    If a class earlier in the MRO adds its own fields, it will have to ensure that the widgets are correctly configured.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        exempt_widgets = [
            forms.CheckboxInput,
            forms.FileInput,
            forms.RadioSelect,
            nautobot_widgets.ClearableFileInput,
        ]

        for field in self.fields.values():
            if field.widget.__class__ not in exempt_widgets:
                css_classes = field.widget.attrs.get("class", "")
                if "form-control" not in css_classes:
                    field.widget.attrs["class"] = " ".join([css_classes, "form-control"]).strip()
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

    def __init__(self, model, *args, edit_all=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.nullable_fields = []

        # Copy any nullable fields defined in Meta
        if hasattr(self.Meta, "nullable_fields"):
            self.nullable_fields = self.Meta.nullable_fields

        if edit_all:
            self.fields["pk"].required = False
            self.fields["_all"] = forms.BooleanField(widget=forms.HiddenInput(), required=False, initial=True)

    def _save_m2m_fields(self, obj):
        """Save M2M fields"""
        from nautobot.core.models.fields import TagsField  # Avoid circular dependency

        m2m_field_names = []
        # Handle M2M Save
        for key in self.cleaned_data.keys():
            if key.startswith(("add_", "remove_")):
                if key.startswith("add_"):
                    field_name = key.lstrip("add_")
                else:
                    field_name = key.lstrip("remove_")
                if field_name in m2m_field_names:
                    continue
                with contextlib.suppress(FieldDoesNotExist):
                    field = obj._meta.get_field(field_name)
                    is_m2m_field = isinstance(field, (ManyToManyField, TagsField))
                    if is_m2m_field:
                        m2m_field_names.append(field_name)

        for field_name in m2m_field_names:
            m2m_field = getattr(obj, field_name)
            if self.cleaned_data.get(f"add_{field_name}", None):
                m2m_field.add(*self.cleaned_data[f"add_{field_name}"])
            if self.cleaned_data.get(f"remove_{field_name}", None):
                m2m_field.remove(*self.cleaned_data[f"remove_{field_name}"])

    def post_save(self, obj):
        """Post save action"""
        self._save_m2m_fields(obj)


class BulkRenameForm(forms.Form):
    """
    An extendable form to be used for renaming objects in bulk.
    """

    find = forms.CharField()
    replace = forms.CharField(required=False, strip=False)
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


class PrefetchInlineFormSet(BaseInlineFormSet):
    def prepare_queryset(self, queryset):
        if self.instance.pk:
            rel_name = self.fk.remote_field.get_accessor_name(model=self.model)  # pylint: disable=no-member
            queryset = getattr(self.instance, rel_name).get_queryset()
            # breakpoint()
            if queryset is not None:
                return queryset
        if queryset is None:
            queryset = self.model._default_manager
        if self.instance.pk is not None:
            return queryset.filter(**{self.fk.name: self.instance})  # pylint: disable=no-member
        return queryset.none()

    def get_instance_by_queryset_index(self, i):
        # Use list() to evaluate the lazy queryset now
        return list(self.get_queryset())[i]

    def __init__(
        self,
        data=None,
        files=None,
        instance=None,
        save_as_new=False,
        prefix=None,
        queryset=None,
        **kwargs,
    ):  # pylint: disable=super-init-not-called
        # Copied from https://github.com/django/django/blob/8293b0f52d086410bb480b7d6a79e614c8184761/django/forms/models.py#L1074
        # Only changed part resposible for prepering qs variable(L431-L437) based on changes from this PR: https://github.com/django/django/pull/17818/files
        if instance is None:
            self.instance = self.fk.remote_field.model()  # pylint: disable=no-member
        else:
            self.instance = instance
        self.save_as_new = save_as_new
        qs = self.prepare_queryset(queryset)
        # if queryset is None:
        #     queryset = self.model._default_manager
        # if self.instance._is_pk_set():
        #     qs = queryset.filter(**{self.fk.name: self.instance})
        # else:
        #     qs = queryset.none()
        self.unique_fields = {self.fk.name}  # pylint: disable=no-member
        forms.BaseModelFormSet.__init__(self, data, files, prefix=prefix, queryset=qs, **kwargs)  # pylint: disable=non-parent-init-called

        # Add the generated field to form._meta.fields if it's defined to make
        # sure validation isn't skipped on that field.
        if self.form._meta.fields and self.fk.name not in self.form._meta.fields:  # pylint: disable=no-member
            if isinstance(self.form._meta.fields, tuple):  # pylint: disable=no-member
                self.form._meta.fields = list(self.form._meta.fields)  # pylint: disable=no-member
            self.form._meta.fields.append(self.fk.name)  # pylint: disable=no-member

    def _construct_form(self, i, **kwargs):
        # Copied from BaseModelFormSet
        # <--------->
        pk_required = i < self.initial_form_count()
        if pk_required:
            if self.is_bound:
                pk_key = "%s-%s" % (self.add_prefix(i), self.model._meta.pk.name)  # pylint: disable=consider-using-f-string
                try:
                    pk = self.data[pk_key]
                except KeyError:
                    # The primary key is missing. The user may have tampered
                    # with POST data.
                    pass
                else:
                    to_python = self._get_to_python(self.model._meta.pk)
                    try:
                        pk = to_python(pk)
                    except ValidationError:
                        # The primary key exists but is an invalid value. The
                        # user may have tampered with POST data.
                        pass
                    else:
                        kwargs["instance"] = self._existing_object(pk)
            else:
                kwargs["instance"] = self.get_instance_by_queryset_index(
                    i
                )  # <---- this line was changes based on this PR: https://github.com/django/django/pull/17818/files
        elif self.initial_extra:
            # Set initial values for extra forms
            try:
                kwargs["initial"] = self.initial_extra[i - self.initial_form_count()]
            except IndexError:
                pass
        form = forms.BaseFormSet._construct_form(self, i, **kwargs)
        if pk_required:
            form.fields[self.model._meta.pk.name].required = True
        # <--------->
        # Copied from BaseInlineFormset
        if self.save_as_new:
            mutable = getattr(form.data, "_mutable", None)
            # Allow modifying an immutable QueryDict.
            if mutable is not None:
                form.data._mutable = True
            # Remove the primary key from the form's data, we are only
            # creating new instances
            form.data[form.add_prefix(self._pk_field.name)] = None
            # Remove the foreign key from the form's data
            form.data[form.add_prefix(self.fk.name)] = None  # pylint: disable=no-member
            if mutable is not None:
                form.data._mutable = mutable

        # Set the fk value here so that the form can do its validation.
        fk_value = self.instance.pk
        if self.fk.remote_field.field_name != self.fk.remote_field.model._meta.pk.name:  # pylint: disable=no-member
            fk_value = getattr(self.instance, self.fk.remote_field.field_name)  # pylint: disable=no-member
            fk_value = getattr(fk_value, "pk", fk_value)
        setattr(form.instance, self.fk.get_attname(), fk_value)  # pylint: disable=no-member
        return form

    def add_fields(self, form, index):
        """Add a hidden field for the object's primary key."""
        from django.db.models import AutoField, ForeignKey, OneToOneField

        # Copied from BaseModelFormSet (https://github.com/django/django/blob/8293b0f52d086410bb480b7d6a79e614c8184761/django/forms/models.py#L949)
        # Changes in line L540 based on PR
        # Changes in lines L552-L556 and L558 needed for widgets
        self._pk_field = pk = self.model._meta.pk
        # If a pk isn't editable, then it won't be on the form, so we need to
        # add it here so we can tell which object is which when we get the
        # data back. Generally, pk.editable should be false, but for some
        # reason, auto_created pk fields and AutoField's editable attribute is
        # True, so check for that as well.

        def pk_is_not_editable(pk):
            return (
                (not pk.editable)
                or (pk.auto_created or isinstance(pk, AutoField))
                or (
                    pk.remote_field
                    and pk.remote_field.parent_link
                    and pk_is_not_editable(pk.remote_field.model._meta.pk)
                )
            )

        if pk_is_not_editable(pk) or pk.name not in form.fields:
            if form.is_bound:
                # If we're adding the related instance, ignore its primary key
                # as it could be an auto-generated default which isn't actually
                # in the database.
                pk_value = None if form.instance._state.adding else form.instance.pk
            else:
                try:
                    if index is not None:
                        pk_value = self.get_instance_by_queryset_index(
                            index
                        ).pk  # <---- this line was changes based on this PR: https://github.com/django/django/pull/17818/files
                    else:
                        pk_value = None
                except IndexError:
                    pk_value = None
            if isinstance(pk, (ForeignKey, OneToOneField)):
                qs = pk.remote_field.model._default_manager.get_queryset()
                # rel_name = pk.remote_field.get_accessor_name(model=self.model)
                # queryset = getattr(self.instance, rel_name).get_queryset()
                # qs = queryset
            else:
                if self.instance.pk:
                    rel_name = self.fk.remote_field.get_accessor_name(model=self.model)  # pylint: disable=no-member
                    qs = getattr(self.instance, rel_name).get_queryset()
                if qs is None:
                    qs = self.model._default_manager.get_queryset()
            qs = qs.using(form.instance._state.db)

            if form._meta.widgets:
                widget = form._meta.widgets.get(self._pk_field.name, forms.HiddenInput)
            else:
                widget = forms.HiddenInput
            form.fields[self._pk_field.name] = forms.ModelChoiceField(
                qs, initial=pk_value, required=False, widget=widget
            )
        forms.BaseFormSet.add_fields(self, form, index)

        # Copied from BaseInlineFormSet (https://github.com/django/django/blob/8293b0f52d086410bb480b7d6a79e614c8184761/django/forms/models.py#L1144)
        if self._pk_field == self.fk:  # pylint: disable=no-member
            name = self._pk_field.name
            kwargs = {"pk_field": True}
        else:
            # The foreign key field might not be on the form, so we poke at the
            # Model field to get the label, since we need that for error messages.
            name = self.fk.name  # pylint: disable=no-member
            kwargs = {"label": getattr(form.fields.get(name), "label", capfirst(self.fk.verbose_name))}  # pylint: disable=no-member

        # The InlineForeignKeyField assumes that the foreign key relation is
        # based on the parent model's pk. If this isn't the case, set to_field
        # to correctly resolve the initial form value.
        if self.fk.remote_field.field_name != self.fk.remote_field.model._meta.pk.name:  # pylint: disable=no-member
            kwargs["to_field"] = self.fk.remote_field.field_name  # pylint: disable=no-member

        # If we're adding a new object, ignore a parent's auto-generated key
        # as it will be regenerated on the save request.
        if self.instance._state.adding:
            if kwargs.get("to_field") is not None:
                to_field = self.instance._meta.get_field(kwargs["to_field"])
            else:
                to_field = self.instance._meta.pk
            if to_field.has_default():
                setattr(self.instance, to_field.attname, None)

        form.fields[name] = forms.models.InlineForeignKeyField(self.instance, **kwargs)
