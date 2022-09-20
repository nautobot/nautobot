import json
from collections.abc import Iterable
from urllib.parse import urljoin

from django import forms
from django.forms.models import ModelChoiceIterator
from django.urls import get_script_prefix

from nautobot.utilities.choices import ColorChoices
from .utils import add_blank_choice

__all__ = (
    "APISelect",
    "APISelectMultiple",
    "BulkEditNullBooleanSelect",
    "ColorSelect",
    "ContentTypeSelect",
    "DatePicker",
    "DateTimePicker",
    "SelectWithDisabled",
    "SelectWithPK",
    "SlugWidget",
    "SmallTextarea",
    "StaticSelect2",
    "StaticSelect2Multiple",
    "TimePicker",
)


class SmallTextarea(forms.Textarea):
    """
    Subclass used for rendering a smaller textarea element.
    """


class SlugWidget(forms.TextInput):
    """
    Subclass TextInput and add a slug regeneration button next to the form field.
    """

    template_name = "widgets/sluginput.html"


class ColorSelect(forms.Select):
    """
    Extends the built-in Select widget to colorize each <option>.
    """

    option_template_name = "widgets/colorselect_option.html"

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = add_blank_choice(ColorChoices)
        super().__init__(*args, **kwargs)
        self.attrs["class"] = "nautobot-select2-color-picker"


class BulkEditNullBooleanSelect(forms.NullBooleanSelect):
    """
    A Select widget for NullBooleanFields
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Override the built-in choice labels
        self.choices = (
            ("1", "---------"),
            ("2", "Yes"),
            ("3", "No"),
        )
        self.attrs["class"] = "nautobot-select2-static"


class SelectWithDisabled(forms.Select):
    """
    Modified the stock Select widget to accept choices using a dict() for a label. The dict for each option must include
    'label' (string) and 'disabled' (boolean).
    """

    option_template_name = "widgets/selectwithdisabled_option.html"


class StaticSelect2(SelectWithDisabled):
    """
    A static <select> form widget using the Select2 library.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.attrs["class"] = "nautobot-select2-static"


class StaticSelect2Multiple(StaticSelect2, forms.SelectMultiple):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.attrs["data-multiple"] = 1


class SelectWithPK(StaticSelect2):
    """
    Include the primary key of each option in the option label (e.g. "Router7 (4721)").
    """

    option_template_name = "widgets/select_option_with_pk.html"


class ContentTypeSelect(StaticSelect2):
    """
    Appends an `api-value` attribute equal to the slugified model name for each ContentType. For example:
        <option value="37" api-value="console-server-port">console server port</option>
    This attribute can be used to reference the relevant API endpoint for a particular ContentType.
    """

    option_template_name = "widgets/select_contenttype.html"


class APISelect(SelectWithDisabled):
    """
    A select widget populated via an API call

    Args:
        api_url: API endpoint URL. Required if not set automatically by the parent field.
        api_version: API version.
    """

    def __init__(self, api_url=None, full=False, api_version=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.attrs["class"] = "nautobot-select2-api"

        if api_version:
            # Set Request Accept Header api-version e.g Accept: application/json; version=1.2
            self.attrs["data-api-version"] = api_version

        if api_url:
            # Prefix the URL w/ the script prefix (e.g. `/nautobot`)
            self.attrs["data-url"] = urljoin(get_script_prefix(), api_url.lstrip("/"))

    def add_query_param(self, name, value):
        """
        Add details for an additional query param in the form of a data-* JSON-encoded list attribute.

        :param name: The name of the query param
        :param value: The value of the query param
        """
        key = f"data-query-param-{name}"

        values = json.loads(self.attrs.get(key, "[]"))
        if isinstance(value, (list, tuple)):
            values.extend([str(v) for v in value])
        else:
            values.append(str(value))

        self.attrs[key] = json.dumps(values, ensure_ascii=False)

    def get_context(self, name, value, attrs):

        # This adds null options to DynamicModelMultipleChoiceField selected choices
        # example <select ..>
        #           <option .. selected value="null">None</option>
        #           <option .. selected value="1234-455...">Rack 001</option>
        #           <option .. value="1234-455...">Rack 002</option>
        #          </select>
        # Prepend null choice to self.choices if
        # 1. form field allow null_option e.g. DynamicModelMultipleChoiceField(..., null_option="None"..)
        # 2. if null is part of url query parameter for name(field_name) i.e. http://.../?rack_id=null
        # 3. if both value and choices are iterable
        if (
            self.attrs.get("data-null-option")
            and isinstance(value, (list, tuple))
            and "null" in value
            and isinstance(self.choices, Iterable)
        ):

            class ModelChoiceIteratorWithNullOption(ModelChoiceIterator):
                def __init__(self, *args, **kwargs):
                    self.null_options = kwargs.pop("null_option", None)
                    super().__init__(*args, **kwargs)

                def __iter__(self):
                    # ModelChoiceIterator.__iter__() yields a tuple of (value, label)
                    # using this approach first yield a tuple of (null(value), null_option(label))
                    yield "null", self.null_options
                    for item in super().__iter__():
                        yield item

            null_option = self.attrs.get("data-null-option")
            choices = ModelChoiceIteratorWithNullOption(field=self.choices.field, null_option=null_option)
            self.choices = choices

        return super().get_context(name, value, attrs)


class APISelectMultiple(APISelect, forms.SelectMultiple):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.attrs["data-multiple"] = 1


class DatePicker(forms.TextInput):
    """
    Date picker using Flatpickr.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["class"] = "date-picker"
        self.attrs["placeholder"] = "YYYY-MM-DD"


class DateTimePicker(forms.TextInput):
    """
    DateTime picker using Flatpickr.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["class"] = "datetime-picker"
        self.attrs["placeholder"] = "YYYY-MM-DD hh:mm:ss"


class TimePicker(forms.TextInput):
    """
    Time picker using Flatpickr.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["class"] = "time-picker"
        self.attrs["placeholder"] = "hh:mm:ss"


class MultiValueCharInput(StaticSelect2Multiple):
    """
    Manual text input with tagging enabled.
    Press enter to create a new entry.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["class"] = "nautobot-select2-multi-value-char"
