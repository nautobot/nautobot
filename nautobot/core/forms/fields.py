import json
import logging
import re

from django import forms as django_forms
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.forms import SimpleArrayField
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from django.db.models import Q
from django.forms.fields import BoundField, CallableChoiceIterator, InvalidJSONInput, JSONField as _JSONField
from django.templatetags.static import static
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.html import format_html
import django_filters
from netaddr import EUI
from netaddr.core import AddrFormatError

from nautobot.core import choices as core_choices, forms
from nautobot.core.forms import widgets
from nautobot.core.models import validators
from nautobot.core.utils import data as data_utils, lookup

logger = logging.getLogger(__name__)

__all__ = (
    "CSVChoiceField",
    "CSVContentTypeField",
    "CSVDataField",
    "CSVFileField",
    "CSVModelChoiceField",
    "CSVMultipleChoiceField",
    "CSVMultipleContentTypeField",
    "CommentField",
    "DynamicModelChoiceField",
    "DynamicModelMultipleChoiceField",
    "ExpandableIPAddressField",
    "ExpandableNameField",
    "JSONArrayFormField",
    "JSONField",
    "LaxURLField",
    "MACAddressField",
    "MultiMatchModelMultipleChoiceField",
    "MultipleContentTypeField",
    "NumericArrayField",
    "SlugField",
    "TagFilterField",
)


class CSVDataField(django_forms.CharField):
    """
    A CharField (rendered as a Textarea) which expects CSV-formatted data.

    Initial value is a list of headers corresponding to the required fields for the given serializer class.

    This no longer actually does any CSV parsing or validation on its own,
    as that is now handled by the NautobotCSVParser class and the REST API serializers.

    Args:
        required_field_names (list[str]): List of field names representing required fields for this import.
    """

    widget = django_forms.Textarea

    def __init__(self, *args, required_field_names="", **kwargs):
        self.required_field_names = required_field_names
        kwargs.setdefault("required", False)

        super().__init__(*args, **kwargs)

        self.strip = False
        if not self.label:
            self.label = ""
        if not self.initial:
            self.initial = ",".join(self.required_field_names) + "\n"
        if not self.help_text:
            self.help_text = (
                "Enter the list of column headers followed by one line per record to be imported, using "
                "commas to separate values. Multi-line data and values containing commas may be wrapped "
                "in double quotes."
            )


class CSVFileField(django_forms.FileField):
    """
    A FileField (rendered as a ClearableFileInput) which expects a file containing CSV-formatted data.

    This no longer actually does any CSV parsing or validation on its own,
    as that is now handled by the NautobotCSVParser class and the REST API serializers.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)

        super().__init__(*args, **kwargs)

        if not self.label:
            self.label = "CSV File"
        if not self.help_text:
            self.help_text = (
                "Select a CSV file to upload. It should contain column headers in the first row and use commas "
                "to separate values. Multi-line data and values containing commas may be wrapped "
                "in double quotes."
            )

    def to_python(self, data):
        """For parity with CSVDataField, this returns the CSV text rather than an UploadedFile object."""
        if data is None:
            return None

        data = super().to_python(data)
        return data.read().decode("utf-8-sig").strip()


class CSVChoiceField(django_forms.ChoiceField):
    """
    Invert the provided set of choices to take the human-friendly label as input, and return the database value.

    Despite the name, this is no longer used in CSV imports since 2.0, but *is* used in JSON/YAML import of DeviceTypes.
    """

    STATIC_CHOICES = True

    def __init__(self, *, choices=(), **kwargs):
        super().__init__(choices=choices, **kwargs)
        self.choices = core_choices.unpack_grouped_choices(choices)


class CSVMultipleChoiceField(CSVChoiceField):
    """
    A version of CSVChoiceField that supports and emits a list of choice values.

    As with CSVChoiceField, the name is misleading, as this is no longer used for CSV imports, but is used for
    JSON/YAML import of DeviceTypes still.
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


class CSVModelChoiceField(django_forms.ModelChoiceField):
    """
    Provides additional validation for model choices entered as CSV data.

    Note: class name is misleading; the subclass CSVContentTypeField (below) is also used in FilterSets, where it has
    nothing to do with CSV data.
    """

    default_error_messages = {
        "invalid_choice": "Object not found.",
    }

    def to_python(self, value):
        try:
            return super().to_python(value)
        except MultipleObjectsReturned:
            raise ValidationError(f'"{value}" is not a unique value for this field; multiple objects were found')


class CSVContentTypeField(CSVModelChoiceField):
    """
    Reference a ContentType in the form `{app_label}.{model}`.

    Note: class name is misleading; this field is also used in numerous FilterSets where it has nothing to do with CSV.
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
            raise ValidationError('Object type must be specified as "<app_label>.<model>"')
        try:
            return self.queryset.get(app_label=app_label, model=model)
        except ObjectDoesNotExist:
            raise ValidationError("Invalid object type")


class MultipleContentTypeField(django_forms.ModelMultipleChoiceField):
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
        from nautobot.extras import utils as extras_utils

        if "queryset" not in kwargs:
            if feature is not None:
                from nautobot.extras.registry import registry

                if feature not in registry["model_features"]:
                    raise KeyError
                kwargs["queryset"] = ContentType.objects.filter(
                    extras_utils.FeatureQuery(feature).get_query()
                ).order_by("app_label", "model")
            else:
                kwargs["queryset"] = ContentType.objects.order_by("app_label", "model")
        if "widget" not in kwargs:
            kwargs["widget"] = forms.StaticSelect2Multiple()

        super().__init__(*args, **kwargs)

        if choices_as_strings:
            self.choices = self._string_choices_from_queryset

    def _string_choices_from_queryset(self):
        """Overload choices to return `{app_label}.{model}` instead of PKs."""
        return [(f"{m.app_label}.{m.model}", m.app_labeled_name) for m in self.queryset.all()]


class MultiValueCharField(django_forms.CharField):
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
        self.field_class = django_forms.CharField
        if not value:
            return []

        # Make it a list if it's a string.
        if isinstance(value, str):
            value = [value]

        return [
            # Only append non-empty values (this avoids e.g. trying to cast '' as an integer)
            self.field_class.to_python(self, v)
            for v in value
            if v
        ]


class CSVMultipleContentTypeField(MultipleContentTypeField):
    """
    Reference a list of `ContentType` objects in the form `{app_label}.{model}'.

    Note: This is unused in Nautobot core at this time, but some apps (data-validation-engine) use this for non-CSV
    purposes, similar to CSVContentTypeField above.
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
                    raise ValidationError(
                        self.error_messages["invalid_choice"],
                        code="invalid_choice",
                        params={"value": v},
                    )
                ct = self.queryset.model.objects.get_for_model(model)
                pk_list.append(ct.pk)

        return super().prepare_value(pk_list)


class ExpandableNameField(django_forms.CharField):
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
        if re.search(forms.ALPHANUMERIC_EXPANSION_PATTERN, value):
            return list(forms.expand_alphanumeric_pattern(value))
        return [value]


class ExpandableIPAddressField(django_forms.CharField):
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
        # Ensure that a subnet mask has been specified. This prevents IPs from defaulting to a /32 or /128.
        if len(value.split("/")) != 2:
            raise ValidationError("CIDR mask (e.g. /24) is required.")

        # Hackish address version detection but it's all we have to work with
        if "." in value and re.search(forms.IP4_EXPANSION_PATTERN, value):
            return list(forms.expand_ipaddress_pattern(value, 4))
        elif ":" in value and re.search(forms.IP6_EXPANSION_PATTERN, value):
            return list(forms.expand_ipaddress_pattern(value, 6))

        return [value]


class CommentField(django_forms.CharField):
    """
    A textarea with support for Markdown rendering. Exists mostly just to add a standard help_text.
    """

    widget = django_forms.Textarea
    default_label = ""

    @property
    def default_helptext(self):
        # TODO: Port Markdown cheat sheet to internal documentation
        return format_html(
            '<i class="mdi mdi-information-outline"></i> '
            '<a href="https://www.markdownguide.org/cheat-sheet/#basic-syntax" rel="noopener noreferrer">Markdown</a> '
            'syntax is supported, as well as <a href="{}#render_markdown">a limited subset of HTML</a>.',
            static("docs/user-guide/platform-functionality/template-filters.html"),
        )

    def __init__(self, *args, **kwargs):
        required = kwargs.pop("required", False)
        label = kwargs.pop("label", self.default_label)
        help_text = kwargs.pop("help_text", self.default_helptext)
        super().__init__(required=required, label=label, help_text=help_text, *args, **kwargs)


class MACAddressField(django_forms.Field):
    widget = django_forms.CharField
    default_error_messages = {
        "invalid": "MAC address must be in EUI-48 format",
    }

    def to_python(self, value):
        value = super().to_python(value)

        # Validate MAC address format
        try:
            value = EUI(value.strip())
        except AddrFormatError:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

        return value


class NullableDateField(django_forms.DateField):
    def to_python(self, value):
        if not value:
            return None
        elif value == "null":
            return value
        return super().to_python(value)


class SlugField(django_forms.SlugField):
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
        kwargs.setdefault("widget", forms.SlugWidget)
        super().__init__(*args, **kwargs)
        if isinstance(slug_source, (tuple, list)):
            slug_source = " ".join(slug_source)
        self.widget.attrs["slug-source"] = slug_source


class AutoPositionField(django_forms.CharField):
    def __init__(self, source="name", *args, **kwargs):
        """
        Instantiate a AutoPositionField.

        Args:
            source (str, tuple): Name of the field (or a list of field names) that will be used to suggest a position.
        """
        kwargs.setdefault("label", "Position")
        kwargs.setdefault("widget", forms.AutoPopulateWidget)
        super().__init__(*args, **kwargs)
        if isinstance(source, (tuple, list)):
            source = " ".join(source)
        self.widget.attrs["source"] = source


class AutoPositionPatternField(ExpandableNameField):
    def __init__(self, source="name_pattern", *args, **kwargs):
        """
        Instantiate a AutoPositionPatternField.

        Args:
            source (str, tuple): Name pattern of the field (or a list of field names) that will be used to suggest a position pattern.
        """
        kwargs.setdefault("label", "Position")
        kwargs.setdefault("widget", forms.AutoPopulateWidget(attrs={"title": "Regenerate position"}))
        super().__init__(*args, **kwargs)
        if isinstance(source, (tuple, list)):
            source = " ".join(source)
        self.widget.attrs["source"] = source


class DynamicModelChoiceMixin:
    """
    :param display_field: The name of the attribute of an API response object to display in the selection list
    :param query_params: A dictionary of additional key/value pairs to attach to the API request
    :param initial_params: A dictionary of child field references to use for selecting a parent field's initial value
    :param null_option: The string used to represent a null selection (if any)
    :param disabled_indicator: The name of the field which, if populated, will disable selection of the
        choice (optional)
    :param depth: Nested serialization depth when making API requests (default: `0` or a flat representation)
    """

    filter = django_filters.ModelChoiceFilter  # 2.0 TODO(Glenn): can we rename this? pylint: disable=redefined-builtin
    widget = widgets.APISelect
    iterator = widgets.MinimalModelChoiceIterator

    def __init__(
        self,
        display_field="display",
        query_params=None,
        initial_params=None,
        null_option=None,
        disabled_indicator=None,
        depth=0,
        *args,
        **kwargs,
    ):
        self.display_field = display_field
        self.query_params = query_params or {}
        # Default to "exclude_m2m=true" for improved performance, if not otherwise specified
        self.query_params.setdefault("exclude_m2m", "true")
        self.initial_params = initial_params or {}
        self.null_option = null_option
        self.disabled_indicator = disabled_indicator
        self.depth = depth

        # to_field_name is set by ModelChoiceField.__init__(), but we need to set it early for reference
        # by widget_attrs()
        self.to_field_name = kwargs.get("to_field_name")
        self.data_queryset = kwargs.get("queryset")  # may be updated in get_bound_field()

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

        # Toggle depth
        attrs["data-depth"] = self.depth

        # Attach any static query parameters if supported
        if isinstance(widget, widgets.APISelect) or hasattr(widget, "add_query_param"):
            for key, value in self.query_params.items():
                widget.add_query_param(key, value)

        return attrs

    def prepare_value(self, value):
        """
        Augment the behavior of forms.ModelChoiceField.prepare_value().

        Specifically, if `value` is a PK, but we have `to_field_name` set, we need to look up the model instance
        from the given PK, so that the base class will get the appropriate field value rather than just keeping the PK,
        because the rendered form field needs this in order to correctly prepopulate a default selection.
        """
        if self.to_field_name and data_utils.is_uuid(value):
            try:
                value = self.queryset.get(pk=value)
            except ObjectDoesNotExist:
                pass
        return super().prepare_value(value)

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
                self.data_queryset = filter_.filter(self.queryset, data)
            except (TypeError, ValueError, ValidationError):
                # Catch any error caused by invalid initial data passed from the user
                self.data_queryset = self.queryset.none()
        else:
            self.data_queryset = self.queryset.none()

        # Set the data URL on the APISelect widget (if not already set)
        widget = bound_field.field.widget
        if not widget.attrs.get("data-url"):
            route = lookup.get_route_for_model(self.queryset.model, "list", api=True)
            try:
                data_url = reverse(route)
                widget.attrs["data-url"] = data_url
            except NoReverseMatch:
                logger.error(
                    'API route lookup "%s" failed for model %s, form field "%s" will not work properly',
                    route,
                    self.queryset.model.__name__,
                    bound_field.name,
                )

        return bound_field


class DynamicModelChoiceField(DynamicModelChoiceMixin, django_forms.ModelChoiceField):
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


class DynamicModelMultipleChoiceField(DynamicModelChoiceMixin, django_forms.ModelMultipleChoiceField):
    """
    A multiple-choice version of DynamicModelChoiceField.
    """

    filter = django_filters.ModelMultipleChoiceFilter
    widget = widgets.APISelectMultiple


class LaxURLField(django_forms.URLField):
    """
    Modifies Django's built-in URLField to remove the requirement for fully-qualified domain names
    (e.g. http://myserver/ is valid)
    """

    default_validators = [validators.EnhancedURLValidator()]


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


class JSONArrayFormField(django_forms.JSONField):
    """
    A FormField counterpart to JSONArrayField.
    Replicates ArrayFormField's base field validation: Field values are validated as JSON Arrays,
    and each Array element is validated by `base_field` validators.
    """

    def __init__(self, base_field, *, choices=None, delimiter=",", **kwargs):
        self.has_choices = False
        if choices:
            self.choices = choices
            self.widget = widgets.StaticSelect2Multiple(choices=choices)
            self.has_choices = True
        self.base_field = base_field
        self.delimiter = delimiter
        super().__init__(**kwargs)

    # TODO: change this when we upgrade to Django 5, it uses a getter/setter for choices
    def _get_choices(self):
        return getattr(self, "_choices", None)

    def _set_choices(self, value):
        if callable(value):
            value = CallableChoiceIterator(value)
        else:
            value = list(value)
        self._choices = self.widget.choices = value

    choices = property(_get_choices, _set_choices)

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
        if self.has_choices:
            if isinstance(value, list):
                return value
            return [value]
        elif isinstance(value, list):
            return self.delimiter.join(str(self.base_field.prepare_value(v)) for v in value)
        return value

    def bound_data(self, data, initial):
        if data is None:
            return None
        if isinstance(data, list):
            data = json.dumps(data)
        return super().bound_data(data, initial)

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
            if self.has_choices and not self.valid_value(item):
                errors.append(ValidationError(f"{item} is not a valid choice"))
        if errors:
            raise ValidationError(errors)

    def valid_value(self, value):
        """Check to see if the provided value is a valid choice."""
        text_value = str(value)
        for k, v in self.choices:
            if isinstance(v, (list, tuple)):
                # This is an optgroup, so look inside the group for options
                for k2, _ in v:
                    if value == k2 or text_value == str(k2):
                        return True
            else:
                if value == k or text_value == str(k):
                    return True
        return False

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
            if not value:
                return []

            if isinstance(value, list):
                value = ",".join([str(n) for n in value])

            value = ",".join([str(n) for n in forms.parse_numeric_range(value)])

        except (TypeError, ValueError) as error:
            raise ValidationError(error)
        return super().to_python(value)


class MultiMatchModelMultipleChoiceField(DynamicModelChoiceMixin, django_filters.fields.ModelMultipleChoiceField):
    """
    Filter field to support matching on the PK *or* `to_field_name` fields (defaulting to `slug` if not specified).

    Raises ValidationError if none of the fields match the requested value.
    """

    filter = django_filters.ModelMultipleChoiceFilter
    widget = widgets.APISelectMultiple

    def __init__(self, *args, **kwargs):
        self.natural_key = kwargs.setdefault("to_field_name", "slug")
        super().__init__(*args, **kwargs)

    def _check_values(self, values):  # pylint:disable=arguments-renamed
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
            if data_utils.is_uuid(item):
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


class TagFilterField(DynamicModelMultipleChoiceField):
    """
    A filter field for the tags of a model. Only the tags used by a model are displayed.

    :param model: The model of the filter
    """

    def __init__(self, model, *args, query_params=None, queryset=None, **kwargs):
        from nautobot.extras.models import Tag

        if queryset is None:
            queryset = Tag.objects.get_for_model(model)
        query_params = query_params or {}
        query_params.update({"content_types": model._meta.label_lower})
        super().__init__(
            label="Tags",
            query_params=query_params,
            queryset=queryset,
            required=False,
            to_field_name="name",
            *args,
            **kwargs,
        )
