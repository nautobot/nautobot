import csv
import json
import re
from io import StringIO

import django_filters
from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.forms import SimpleArrayField
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from django.db.models import Count, Q
from django.forms.fields import BoundField, JSONField as _JSONField, InvalidJSONInput
from django.urls import reverse

from nautobot.extras.utils import FeatureQuery
from nautobot.utilities.choices import unpack_grouped_choices
from nautobot.utilities.utils import get_route_for_model, is_uuid
from nautobot.utilities.validators import EnhancedURLValidator
from . import widgets
from .constants import ALPHANUMERIC_EXPANSION_PATTERN, IP4_EXPANSION_PATTERN, IP6_EXPANSION_PATTERN
from .utils import expand_alphanumeric_pattern, expand_ipaddress_pattern, parse_numeric_range, parse_csv, validate_csv

__all__ = (
    "CommentField",
    "CSVChoiceField",
    "CSVContentTypeField",
    "CSVDataField",
    "CSVFileField",
    "CSVModelChoiceField",
    "CSVMultipleChoiceField",
    "CSVMultipleContentTypeField",
    "DynamicModelChoiceField",
    "DynamicModelMultipleChoiceField",
    "ExpandableIPAddressField",
    "ExpandableNameField",
    "JSONField",
    "JSONArrayFormField",
    "LaxURLField",
    "MultipleContentTypeField",
    "MultiMatchModelMultipleChoiceField",
    "NumericArrayField",
    "SlugField",
    "TagFilterField",
)


class CSVDataField(forms.CharField):
    """
    A CharField (rendered as a Textarea) which accepts CSV-formatted data. It returns data as a two-tuple: The first
    item is a dictionary of column headers, mapping field names to the attribute by which they match a related object
    (where applicable). The second item is a list of dictionaries, each representing a discrete row of CSV data.

    :param from_form: The form from which the field derives its validation rules.
    """

    widget = forms.Textarea

    def __init__(self, from_form, *args, **kwargs):

        form = from_form()
        self.model = form.Meta.model
        self.fields = form.fields
        self.required_fields = [name for name, field in form.fields.items() if field.required]

        super().__init__(*args, **kwargs)

        self.strip = False
        if not self.label:
            self.label = ""
        if not self.initial:
            self.initial = ",".join(self.required_fields) + "\n"
        if not self.help_text:
            self.help_text = (
                "Enter the list of column headers followed by one line per record to be imported, using "
                "commas to separate values. Multi-line data and values containing commas may be wrapped "
                "in double quotes."
            )

    def to_python(self, value):
        if value is None:
            return None
        reader = csv.reader(StringIO(value.strip()))
        return parse_csv(reader)

    def validate(self, value):
        if value is None:
            return None
        headers, _records = value
        validate_csv(headers, self.fields, self.required_fields)

        return value


class CSVFileField(forms.FileField):
    """
    A FileField (rendered as a ClearableFileInput) which accepts a file containing CSV-formatted data. It returns
    data as a two-tuple: The first item is a dictionary of column headers, mapping field names to the attribute
    by which they match a related object (where applicable). The second item is a list of dictionaries, each
    representing a discrete row of CSV data.

    :param from_form: The form from which the field derives its validation rules.
    """

    def __init__(self, from_form, *args, **kwargs):

        form = from_form()
        self.model = form.Meta.model
        self.fields = form.fields
        self.required_fields = [name for name, field in form.fields.items() if field.required]

        super().__init__(*args, **kwargs)

        if not self.label:
            self.label = "CSV File"
        if not self.help_text:
            self.help_text = (
                "Select a CSV file to upload. It should contain column headers in the first row and use commas "
                "to separate values. Multi-line data and values containing commas may be wrapped "
                "in double quotes."
            )

    def to_python(self, file):
        if file is None:
            return None

        file = super().to_python(file)
        csv_str = file.read().decode("utf-8-sig").strip()
        # Check if there is only one column of input
        # If so a delimiter cannot be determined and it will raise an exception.
        # In that case we will use csv.excel class
        # Which defines the usual properties of an Excel-generated CSV file.
        try:
            dialect = csv.Sniffer().sniff(csv_str, delimiters=",")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(csv_str.splitlines(), dialect)
        headers, records = parse_csv(reader)

        return headers, records

    def validate(self, value):
        if value is None:
            return None

        headers, _records = value
        validate_csv(headers, self.fields, self.required_fields)

        return value


class CSVChoiceField(forms.ChoiceField):
    """
    Invert the provided set of choices to take the human-friendly label as input, and return the database value.
    """

    STATIC_CHOICES = True

    def __init__(self, *, choices=(), **kwargs):
        super().__init__(choices=choices, **kwargs)
        self.choices = unpack_grouped_choices(choices)


class CSVMultipleChoiceField(CSVChoiceField):
    """
    A version of CSVChoiceField that supports and emits a list of choice values
    """

    def to_python(self, value):
        """Return a list of strings."""
        if value in self.empty_values:
            return ""
        return [v.strip() for v in str(value).split(",")]

    def validate(self, value):
        """Validate that each of the input values is in self.choices."""
        for v in value:
            super().validate(v)


class CSVModelChoiceField(forms.ModelChoiceField):
    """
    Provides additional validation for model choices entered as CSV data.
    """

    default_error_messages = {
        "invalid_choice": "Object not found.",
    }

    def to_python(self, value):
        try:
            return super().to_python(value)
        except MultipleObjectsReturned:
            raise forms.ValidationError(f'"{value}" is not a unique value for this field; multiple objects were found')


class CSVContentTypeField(CSVModelChoiceField):
    """
    Reference a ContentType in the form `{app_label}.{model}`.
    """

    STATIC_CHOICES = True

    def prepare_value(self, value):
        """
        Allow this field to support `{app_label}.{model}` style, null values, or PK-based lookups
        depending on how the field is used.
        """
        if value is None:
            return ""

        # Only pass through strings if they aren't numeric. Otherwise cast to `int`.
        if isinstance(value, str):
            if not value.isdigit():
                return value
            else:
                value = int(value)

        # Integers are PKs
        if isinstance(value, int):
            value = self.queryset.get(pk=value)

        return f"{value.app_label}.{value.model}"

    def to_python(self, value):
        value = self.prepare_value(value)
        try:
            app_label, model = value.split(".")
        except ValueError:
            raise forms.ValidationError('Object type must be specified as "<app_label>.<model>"')
        try:
            return self.queryset.get(app_label=app_label, model=model)
        except ObjectDoesNotExist:
            raise forms.ValidationError("Invalid object type")


class MultipleContentTypeField(forms.ModelMultipleChoiceField):
    """
    Field for choosing any number of `ContentType` objects.

    Optionally can restrict the available ContentTypes to those supporting a particular feature only.
    Optionally can pass the selection through as a list of `{app_label}.{model}` strings instead of PK values.
    """

    STATIC_CHOICES = True

    def __init__(self, *args, feature=None, choices_as_strings=False, **kwargs):
        """
        Construct a MultipleContentTypeField.

        Args:
            feature (str): Feature name to use in constructing a FeatureQuery to restrict the available ContentTypes.
            choices_as_strings (bool): If True, render selection as a list of `"{app_label}.{model}"` strings.
        """
        if "queryset" not in kwargs:
            if feature is not None:
                kwargs["queryset"] = ContentType.objects.filter(FeatureQuery(feature).get_query()).order_by(
                    "app_label", "model"
                )
            else:
                kwargs["queryset"] = ContentType.objects.order_by("app_label", "model")
        if "widget" not in kwargs:
            kwargs["widget"] = widgets.StaticSelect2Multiple()

        super().__init__(*args, **kwargs)

        if choices_as_strings:
            self.choices = self._string_choices_from_queryset

    def _string_choices_from_queryset(self):
        """Overload choices to return `{app_label}.{model}` instead of PKs."""
        return [(f"{m.app_label}.{m.model}", m.app_labeled_name) for m in self.queryset.all()]


class MultiValueCharField(forms.CharField):
    """
    CharField that takes multiple user character inputs and render them as tags in the form field.
    Press enter to complete an input.
    """

    widget = widgets.MultiValueCharInput()

    def get_bound_field(self, form, field_name):
        bound_field = BoundField(form, self, field_name)
        value = bound_field.value()
        widget = bound_field.field.widget
        # Save the selected choices in the widget even after the filterform is submitted
        if value is not None:
            widget.choices = [(v, v) for v in value]

        return bound_field

    def to_python(self, value):
        self.field_class = forms.CharField
        if not value:
            return []

        # Make it a list if it's a string.
        if isinstance(value, str):
            value = [value]

        return [
            # Only append non-empty values (this avoids e.g. trying to cast '' as an integer)
            super(self.field_class, self).to_python(v)  # pylint: disable=bad-super-call
            for v in value
            if v
        ]


class CSVMultipleContentTypeField(MultipleContentTypeField):
    """
    Reference a list of `ContentType` objects in the form `{app_label}.{model}'.
    """

    def prepare_value(self, value):
        """Parse a comma-separated string of model names into a list of PKs."""
        # "".split(",") yields [""] rather than [], which we don't want!
        if isinstance(value, str) and value:
            value = value.split(",")

        # For each model name, retrieve the model object and extract its
        # content-type PK.
        pk_list = []
        if isinstance(value, (list, tuple)):
            for v in value:
                try:
                    model = apps.get_model(v)
                except (ValueError, LookupError):
                    raise forms.ValidationError(
                        self.error_messages["invalid_choice"],
                        code="invalid_choice",
                        params={"value": v},
                    )
                ct = self.queryset.model.objects.get_for_model(model)
                pk_list.append(ct.pk)

        return super().prepare_value(pk_list)


class ExpandableNameField(forms.CharField):
    """
    A field which allows for numeric range expansion
      Example: 'Gi0/[1-3]' => ['Gi0/1', 'Gi0/2', 'Gi0/3']
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.help_text:
            self.help_text = """
                Alphanumeric ranges are supported for bulk creation. Mixed cases and types within a single range
                are not supported. Examples:
                <ul>
                    <li><code>[ge,xe]-0/0/[0-9]</code></li>
                    <li><code>e[0-3][a-d,f]</code></li>
                </ul>
                """

    def to_python(self, value):
        if not value:
            return ""
        if re.search(ALPHANUMERIC_EXPANSION_PATTERN, value):
            return list(expand_alphanumeric_pattern(value))
        return [value]


class ExpandableIPAddressField(forms.CharField):
    """
    A field which allows for expansion of IP address ranges
      Example: '192.0.2.[1-254]/24' => ['192.0.2.1/24', '192.0.2.2/24', '192.0.2.3/24' ... '192.0.2.254/24']
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.help_text:
            self.help_text = (
                "Specify a numeric range to create multiple IPs.<br />Example: <code>192.0.2.[1,5,100-254]/24</code>"
            )

    def to_python(self, value):
        # Hackish address family detection but it's all we have to work with
        if "." in value and re.search(IP4_EXPANSION_PATTERN, value):
            return list(expand_ipaddress_pattern(value, 4))
        elif ":" in value and re.search(IP6_EXPANSION_PATTERN, value):
            return list(expand_ipaddress_pattern(value, 6))
        return [value]


class CommentField(forms.CharField):
    """
    A textarea with support for Markdown rendering. Exists mostly just to add a standard help_text.
    """

    widget = forms.Textarea
    default_label = ""
    # TODO: Port Markdown cheat sheet to internal documentation
    default_helptext = (
        '<i class="mdi mdi-information-outline"></i> '
        '<a href="https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet" target="_blank">'
        "Markdown</a> syntax is supported"
    )

    def __init__(self, *args, **kwargs):
        required = kwargs.pop("required", False)
        label = kwargs.pop("label", self.default_label)
        help_text = kwargs.pop("help_text", self.default_helptext)
        super().__init__(required=required, label=label, help_text=help_text, *args, **kwargs)


class NullableDateField(forms.DateField):
    def to_python(self, value):
        if not value:
            return None
        elif value == "null":
            return value
        return super().to_python(value)


class SlugField(forms.SlugField):
    """
    Extend the built-in SlugField to automatically populate from a field called `name` unless otherwise specified.
    """

    def __init__(self, slug_source="name", *args, **kwargs):
        """
        Instantiate a SlugField.

        Args:
            slug_source (str, tuple): Name of the field (or a list of field names) that will be used to suggest a slug.
        """
        kwargs.setdefault("label", "Slug")
        kwargs.setdefault("help_text", "URL-friendly unique shorthand")
        kwargs.setdefault("widget", widgets.SlugWidget)
        super().__init__(*args, **kwargs)
        if isinstance(slug_source, (tuple, list)):
            slug_source = " ".join(slug_source)
        self.widget.attrs["slug-source"] = slug_source


class TagFilterField(forms.MultipleChoiceField):
    """
    A filter field for the tags of a model. Only the tags used by a model are displayed.

    :param model: The model of the filter
    """

    widget = widgets.StaticSelect2Multiple

    def __init__(self, model, *args, **kwargs):
        def get_choices():
            tags = model.tags.annotate(count=Count("extras_taggeditem_items")).order_by("name")
            return [(str(tag.slug), f"{tag.name} ({tag.count})") for tag in tags]

        # Choices are fetched each time the form is initialized
        super().__init__(label="Tags", choices=get_choices, required=False, *args, **kwargs)


class DynamicModelChoiceMixin:
    """
    :param display_field: The name of the attribute of an API response object to display in the selection list
    :param query_params: A dictionary of additional key/value pairs to attach to the API request
    :param initial_params: A dictionary of child field references to use for selecting a parent field's initial value
    :param null_option: The string used to represent a null selection (if any)
    :param disabled_indicator: The name of the field which, if populated, will disable selection of the
        choice (optional)
    :param brief_mode: Use the "brief" format (?brief=true) when making API requests (default)
    """

    filter = django_filters.ModelChoiceFilter  # TODO can we change this? pylint: disable=redefined-builtin
    widget = widgets.APISelect

    def __init__(
        self,
        display_field="display",
        query_params=None,
        initial_params=None,
        null_option=None,
        disabled_indicator=None,
        brief_mode=True,
        *args,
        **kwargs,
    ):
        self.display_field = display_field
        self.query_params = query_params or {}
        self.initial_params = initial_params or {}
        self.null_option = null_option
        self.disabled_indicator = disabled_indicator
        self.brief_mode = brief_mode

        # to_field_name is set by ModelChoiceField.__init__(), but we need to set it early for reference
        # by widget_attrs()
        self.to_field_name = kwargs.get("to_field_name")

        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        attrs = {
            "display-field": self.display_field,
        }

        # Set value-field attribute if the field specifies to_field_name
        if self.to_field_name:
            attrs["value-field"] = self.to_field_name

        # Set the string used to represent a null option
        if self.null_option is not None:
            attrs["data-null-option"] = self.null_option

        # Set the disabled indicator, if any
        if self.disabled_indicator is not None:
            attrs["disabled-indicator"] = self.disabled_indicator

        # Toggle brief mode
        if not self.brief_mode:
            attrs["data-full"] = "true"

        # Attach any static query parameters
        for key, value in self.query_params.items():
            widget.add_query_param(key, value)

        return attrs

    def get_bound_field(self, form, field_name):
        bound_field = BoundField(form, self, field_name)

        # Set initial value based on prescribed child fields (if not already set)
        if not self.initial and self.initial_params:
            filter_kwargs = {}
            for kwarg, child_field in self.initial_params.items():
                value = form.initial.get(child_field.lstrip("$"))
                if value:
                    filter_kwargs[kwarg] = value
            if filter_kwargs:
                self.initial = self.queryset.filter(**filter_kwargs).first()

        # Modify the QuerySet of the field before we return it. Limit choices to any data already bound: Options
        # will be populated on-demand via the APISelect widget.
        data = bound_field.value()
        if data:
            field_name = getattr(self, "to_field_name") or "pk"
            filter_ = self.filter(field_name=field_name)
            try:
                self.queryset = filter_.filter(self.queryset, data)
            except TypeError:
                # Catch any error caused by invalid initial data passed from the user
                self.queryset = self.queryset.none()
        else:
            self.queryset = self.queryset.none()

        # Set the data URL on the APISelect widget (if not already set)
        widget = bound_field.field.widget
        if not widget.attrs.get("data-url"):
            route = get_route_for_model(self.queryset.model, "list", api=True)
            data_url = reverse(route)
            widget.attrs["data-url"] = data_url

        return bound_field


class DynamicModelChoiceField(DynamicModelChoiceMixin, forms.ModelChoiceField):
    """
    Override get_bound_field() to avoid pre-populating field choices with a SQL query. The field will be
    rendered only with choices set via bound data. Choices are populated on-demand via the APISelect widget.
    """

    def clean(self, value):
        """
        When null option is enabled and "None" is sent as part of a form to be submitted, it is sent as the
        string 'null'.  This will check for that condition and gracefully handle the conversion to a NoneType.
        """
        if self.null_option is not None and value == settings.FILTERS_NULL_CHOICE_VALUE:
            return None
        return super().clean(value)


class DynamicModelMultipleChoiceField(DynamicModelChoiceMixin, forms.ModelMultipleChoiceField):
    """
    A multiple-choice version of DynamicModelChoiceField.
    """

    filter = django_filters.ModelMultipleChoiceFilter
    widget = widgets.APISelectMultiple

    def prepare_value(self, value):
        """
        Ensure that a single string value (i.e. UUID) is accurately represented as a list of one item.

        This is necessary because otherwise the superclass will split the string into individual characters,
        resulting in an error (https://github.com/nautobot/nautobot/issues/512).

        Note that prepare_value() can also be called with an object instance or list of instances; in that case,
        we do *not* want to convert a single instance to a list of one entry.
        """
        if isinstance(value, str):
            value = [value]
        return super().prepare_value(value)


class LaxURLField(forms.URLField):
    """
    Modifies Django's built-in URLField to remove the requirement for fully-qualified domain names
    (e.g. http://myserver/ is valid)
    """

    default_validators = [EnhancedURLValidator()]


class JSONField(_JSONField):
    """
    Custom wrapper around Django's built-in JSONField to avoid presenting "null" as the default text.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.help_text:
            self.help_text = 'Enter context data in <a href="https://json.org/">JSON</a> format.'
            self.widget.attrs["placeholder"] = ""

    def prepare_value(self, value):
        if isinstance(value, InvalidJSONInput):
            return value
        if value is None:
            return ""
        return json.dumps(value, sort_keys=True, indent=4, ensure_ascii=False)

    # TODO: remove this when we upgrade to Django 4
    def bound_data(self, data, initial):
        if data is None:
            return None
        return super().bound_data(data, initial)


class JSONArrayFormField(forms.JSONField):
    """
    A FormField counterpart to JSONArrayField.
    Replicates ArrayFormField's base field validation: Field values are validated as JSON Arrays,
    and each Array element is validated by `base_field` validators.
    """

    def __init__(self, base_field, *, delimiter=",", **kwargs):
        self.base_field = base_field
        self.delimiter = delimiter
        super().__init__(**kwargs)

    def clean(self, value):
        """
        Validate `value` and return its "cleaned" value as an appropriate
        Python object. Raise ValidationError for any errors.
        """
        value = super().clean(value)
        return [self.base_field.clean(val) for val in value]

    def prepare_value(self, value):
        """
        Return a string of this value.
        """
        if isinstance(value, list):
            return self.delimiter.join(str(self.base_field.prepare_value(v)) for v in value)
        return value

    def to_python(self, value):
        """
        Convert `value` into JSON, raising django.core.exceptions.ValidationError
        if the data can't be converted. Return the converted value.
        """
        if isinstance(value, list):
            items = value
        elif value:
            try:
                items = value.split(self.delimiter)
            except Exception as e:
                raise ValidationError(e)
        else:
            items = []

        errors = []
        values = []
        for item in items:
            try:
                values.append(self.base_field.to_python(item))
            except ValidationError as error:
                errors.append(error)
        if errors:
            raise ValidationError(errors)
        return values

    def validate(self, value):
        """
        Validate `value` and raise ValidationError if necessary.
        """
        super().validate(value)
        errors = []
        for item in value:
            try:
                self.base_field.validate(item)
            except ValidationError as error:
                errors.append(error)
        if errors:
            raise ValidationError(errors)

    def run_validators(self, value):
        """
        Runs all validators against `value` and raise ValidationError if necessary.
        Some validators can't be created at field initialization time.
        """
        super().run_validators(value)
        errors = []
        for item in value:
            try:
                self.base_field.run_validators(item)
            except ValidationError as error:
                errors.append(error)
        if errors:
            raise ValidationError(errors)

    def has_changed(self, initial, data):
        """
        Return True if `data` differs from `initial`.
        """
        value = self.to_python(data)
        if initial in self.empty_values and value in self.empty_values:
            return False
        return super().has_changed(initial, data)


class NumericArrayField(SimpleArrayField):
    """Basic array field that takes comma-separated or hyphenated ranges."""

    def to_python(self, value):
        try:
            value = ",".join([str(n) for n in parse_numeric_range(value)])
        except ValueError as error:
            raise ValidationError(error)
        return super().to_python(value)


class MultiMatchModelMultipleChoiceField(django_filters.fields.ModelMultipleChoiceField):
    """
    Filter field to support matching on the PK *or* `to_field_name` fields (defaulting to `slug` if not specified).

    Raises ValidationError if none of the fields match the requested value.
    """

    def __init__(self, *args, **kwargs):
        self.natural_key = kwargs.setdefault("to_field_name", "slug")
        super().__init__(*args, **kwargs)

    def _check_values(self, values):
        """
        This method overloads the grandparent method in `django.forms.models.ModelMultipleChoiceField`,
        re-using some of that method's existing logic and adding support for coupling this field with
        multiple model fields.
        """
        null = self.null_label is not None and values and self.null_value in values
        if null:
            values = [v for v in values if v != self.null_value]
        # deduplicate given values to avoid creating many querysets or
        # requiring the database backend deduplicate efficiently.
        try:
            values = frozenset(values)
        except TypeError:
            # list of lists isn't hashable, for example
            raise ValidationError(
                self.error_messages["invalid_list"],
                code="invalid_list",
            )
        pk_values = set()
        natural_key_values = set()
        for item in values:
            query = Q()
            if is_uuid(item):
                pk_values.add(item)
                query |= Q(pk=item)
            else:
                natural_key_values.add(item)
                query |= Q(**{self.natural_key: item})
            qs = self.queryset.filter(query)
            if not qs.exists():
                raise ValidationError(
                    self.error_messages["invalid_choice"],
                    code="invalid_choice",
                    params={"value": item},
                )
        query = Q(pk__in=pk_values) | Q(**{f"{self.natural_key}__in": natural_key_values})
        qs = self.queryset.filter(query)
        result = list(qs)
        if null:
            result += [self.null_value]
        return result
