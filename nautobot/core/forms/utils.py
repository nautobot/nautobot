from itertools import groupby
import re

from django import forms as django_forms
from django.forms.models import fields_for_model

from nautobot.core import forms
from nautobot.core.models import querysets

__all__ = (
    "add_blank_choice",
    "add_field_to_filter_form_class",
    "expand_alphanumeric_pattern",
    "expand_ipaddress_pattern",
    "form_from_model",
    "parse_alphanumeric_range",
    "parse_numeric_range",
    "restrict_form_fields",
)


def parse_numeric_range(input_string, base=10):
    """
    Expand a numeric range (continuous or not) into a sorted decimal or
    hexadecimal list, as specified by the base parameter
      '0-3,5' => [0, 1, 2, 3, 5]
      '2,8-b,d,f' => [2, 8, 9, a, b, d, f]
    """
    if base not in [10, 16]:
        raise TypeError("Invalid base value.")

    if not isinstance(input_string, str) or not input_string:
        raise TypeError("Input value must be a string using a range format.")

    values = []

    for dash_range in input_string.split(","):
        try:
            begin, end = dash_range.split("-")
            if begin == "" or end == "":
                raise TypeError("Input value must be a string using a range format.")
        except ValueError:
            begin, end = dash_range, dash_range

        begin, end = int(begin.strip(), base=base), int(end.strip(), base=base) + 1
        values.extend(range(begin, end))
    # Remove duplicates and sort
    return sorted(set(values))


def parse_alphanumeric_range(string):
    """
    Expand an alphanumeric range (continuous or not) into a list.
    'a-d,f' => [a, b, c, d, f]
    '0-3,a-d' => [0, 1, 2, 3, a, b, c, d]
    """
    values = []
    for dash_range in string.split(","):
        try:
            begin, end = dash_range.split("-")
            vals = begin + end
            # Break out of loop if there's an invalid pattern to return an error
            if (not (vals.isdigit() or vals.isalpha())) or (vals.isalpha() and not (vals.isupper() or vals.islower())):
                return []
        except ValueError:
            begin, end = dash_range, dash_range
        if begin.isdigit() and end.isdigit():
            for n in list(range(int(begin), int(end) + 1)):
                values.append(n)
        else:
            # Value-based
            if begin == end:
                values.append(begin)
            # Range-based
            else:
                # Not a valid range (more than a single character)
                if not len(begin) == len(end) == 1:
                    raise django_forms.ValidationError(f'Range "{dash_range}" is invalid.')
                for n in list(range(ord(begin), ord(end) + 1)):
                    values.append(chr(n))
    return values


def expand_alphanumeric_pattern(string):
    """
    Expand an alphabetic pattern into a list of strings.
    """
    lead, pattern, remnant = re.split(forms.ALPHANUMERIC_EXPANSION_PATTERN, string, maxsplit=1)
    parsed_range = parse_alphanumeric_range(pattern)
    for i in parsed_range:
        if re.search(forms.ALPHANUMERIC_EXPANSION_PATTERN, remnant):
            for string2 in expand_alphanumeric_pattern(remnant):
                yield f"{lead}{i}{string2}"
        else:
            yield f"{lead}{i}{remnant}"


def expand_ipaddress_pattern(string, ip_version):
    """
    Expand an IP address pattern into a list of strings. Examples:
      '192.0.2.[1,2,100-250]/24' => ['192.0.2.1/24', '192.0.2.2/24', '192.0.2.100/24' ... '192.0.2.250/24']
      '2001:db8:0:[0,fd-ff]::/64' => ['2001:db8:0:0::/64', '2001:db8:0:fd::/64', ... '2001:db8:0:ff::/64']
    """
    if ip_version not in [4, 6]:
        raise ValueError(f"Invalid IP address version: {ip_version}")
    if ip_version == 4:
        regex = forms.IP4_EXPANSION_PATTERN
        base = 10
    else:
        regex = forms.IP6_EXPANSION_PATTERN
        base = 16
    lead, pattern, remnant = re.split(regex, string, maxsplit=1)
    parsed_range = parse_numeric_range(pattern, base)
    for i in parsed_range:
        if re.search(regex, remnant):
            for string2 in expand_ipaddress_pattern(remnant, ip_version):
                yield "".join([lead, format(i, "x" if ip_version == 6 else "d"), string2])
        else:
            yield "".join([lead, format(i, "x" if ip_version == 6 else "d"), remnant])


def add_blank_choice(choices):
    """
    Add a blank choice to the beginning of a choices list.
    """
    return ((None, "---------"), *tuple(choices))


def form_from_model(model, fields):
    """
    Return a Form class with the specified fields derived from a model. This is useful when we need a form to be used
    for creating objects, but want to avoid the model's validation (e.g. for bulk create/edit functions). All fields
    are marked as not required.
    """
    form_fields = fields_for_model(model, fields=fields)
    for field in form_fields.values():
        field.required = False

    return type("FormFromModel", (django_forms.Form,), form_fields)


def restrict_form_fields(form, user, action="view"):
    """
    Restrict all form fields which reference a RestrictedQuerySet. This ensures that users see only permitted objects
    as available choices.
    """
    for field in form.fields.values():
        if hasattr(field, "queryset") and issubclass(field.queryset.__class__, querysets.RestrictedQuerySet):
            field.queryset = field.queryset.restrict(user, action)


def add_field_to_filter_form_class(form_class, field_name, field_obj):
    """
    Attach a field to an existing filter form class.
    """
    if not isinstance(field_obj, django_forms.Field):
        raise TypeError(f"Custom form field `{field_name}` is not an instance of django.forms.Field.")
    if field_name in form_class.base_fields:
        raise AttributeError(
            f"There was a conflict with filter form field `{field_name}`, the custom filter form field was ignored."
        )
    form_class.base_fields[field_name] = field_obj


def compress_range(iterable):
    """
    Generates compressed range from an un-sorted expanded range.
    For example:
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100, 101, 102, 103, 104, 105, 1000, 1100, 1101, 1102, 1103, 1104, 1105, 1106]
        =>
        iter1: (1, 10)
        iter2: (100, 105)
        iter3: (1000, 1000)
        iter4: (1100, 1106)
    """
    iterable = sorted(set(iterable))
    for _, grp in groupby(enumerate(iterable), lambda t: t[1] - t[0]):
        grp = list(grp)
        yield grp[0][1], grp[-1][1]
