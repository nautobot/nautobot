from collections import namedtuple, OrderedDict
from decimal import Decimal
import re
import uuid

from django.core import validators
from django.template import engines

from nautobot.dcim import choices  # TODO move dcim.choices.CableLengthUnitChoices into core

# Setup UtilizationData named tuple for use by multiple methods
UtilizationData = namedtuple("UtilizationData", ["numerator", "denominator"])


def deepmerge(original, new):
    """
    Deep merge two dictionaries (new into original) and return a new dict
    """
    merged = OrderedDict(original)
    for key, val in new.items():
        if key in original and isinstance(original[key], dict) and isinstance(val, dict):
            merged[key] = deepmerge(original[key], val)
        else:
            merged[key] = val
    return merged


def flatten_dict(d, prefix="", separator="."):
    """
    Flatten nested dictionaries into a single level by joining key names with a separator.

    Args:
        d (dict): The dictionary to be flattened
        prefix (str): Initial prefix (if any)
        separator (str): The character to use when concatenating key names
    """
    ret = {}
    for k, v in d.items():
        key = separator.join([prefix, k]) if prefix else k
        if isinstance(v, dict):
            ret.update(flatten_dict(v, prefix=key))
        else:
            ret[key] = v
    return ret


def flatten_iterable(iterable):
    """
    Flatten a nested iterable such as a list of lists, keeping strings intact.

    Args:
        iterable (Iterable): The iterable to be flattened

    Yields: str
    """
    for i in iterable:
        if hasattr(i, "__iter__") and not isinstance(i, str):
            yield from flatten_iterable(i)
        else:
            yield i


def is_uuid(value):
    try:
        if isinstance(value, uuid.UUID) or uuid.UUID(value):
            return True
    except (ValueError, TypeError, AttributeError):
        pass
    return False


def is_url(value):
    """
    Validate whether a value is a URL.

    Args:
        value (str): String to validate.

    Returns:
        (bool): True if the value is a valid URL, False otherwise.
    """
    try:
        return validators.URLValidator()(value) is None
    except validators.ValidationError:
        return False


def merge_dicts_without_collision(d1, d2):
    """
    Merge two dicts into a new dict, but raise a ValueError if any key exists with differing values across both dicts.
    """
    intersection = d1.keys() & d2.keys()
    for k in intersection:
        if d1[k] != d2[k]:
            raise ValueError(f'Conflicting values for key "{k}": ({d1[k]!r}, {d2[k]!r})')
    return {**d1, **d2}


def validate_jinja2(template_code):
    """
    Parse a Jinja2 template to validate its syntax. Returns True if the template is valid.

    Raises:
        jinja2.TemplateSyntaxError: If the template is syntactically invalid.
    """
    rendering_engine = engines["jinja"]
    rendering_engine.env.parse(template_code)

    return True


def render_jinja2(template_code, context):
    """
    Render a Jinja2 template with the provided context. Return the rendered content.
    """
    rendering_engine = engines["jinja"]
    template = rendering_engine.from_string(template_code)
    # For reasons unknown to me, django-jinja2 `template.render()` implicitly calls `mark_safe()` on the rendered text.
    # This is a security risk in general, especially so in our case because we're often using this function to render
    # a user-provided template and don't want to open ourselves up to script injection or similar issues.
    # There's no `mark_unsafe()` function, but concatenating a SafeString to an ordinary string (even "") suffices.
    return "" + template.render(context=context)


def _escape_regex_metacharacters(value):
    """Jinja2 `finalize` hook that renders an interpolated value as a regex literal."""
    # Jinja passes the raw value, which may be an int, None or Undefined, so coerce before escaping.
    return re.escape(str(value))


def _get_regex_jinja2_environment():
    """Jinja2 environment used to render a user-authored template into a regular expression.

    An overlay of the standard environment, so the sandbox, filters and globals are all preserved,
    differing in three ways:

    - `finalize` passes every `{{ ... }}` interpolation through `re.escape()`, so an interpolated
      value can only ever contribute literal characters to the pattern. Literal template text is not
      finalized, so the template author's own regex syntax survives untouched.
    - `autoescape` is off, because HTML escaping is meaningless in a regular expression and would
      otherwise interpolate a value containing `&` as `&amp;`.
    - `loader` is unset, as including a Nautobot HTML template cannot produce a useful pattern.
    """
    parent = engines["jinja"].env
    # Cached on the parent environment so that reconfiguring the template engine, as
    # `override_settings` does in tests, yields a fresh overlay rather than a stale one.
    overlay = getattr(parent, "_nautobot_regex_overlay", None)
    if overlay is None:
        overlay = parent.overlay(autoescape=False, finalize=_escape_regex_metacharacters, loader=None)
        parent._nautobot_regex_overlay = overlay
    return overlay


def render_jinja2_for_regex(template_code, context):
    """
    Render a Jinja2 template whose result is to be used as a regular expression. Return the rendered content.

    Values interpolated from `context` are regex-escaped and treated as literal text, so that data
    being validated cannot alter the structure of the resulting pattern. There is no opt-out.
    """
    # The raw jinja2 Template is used here rather than django_jinja's wrapper, so the context must be
    # passed positionally; `render(context=context)` would bind a variable literally named "context".
    return _get_regex_jinja2_environment().from_string(template_code).render(context)


def shallow_compare_dict(source_dict, destination_dict, exclude=None):
    """
    Return a new dictionary of the different keys. The values of `destination_dict` are returned. Only the equality of
    the first layer of keys/values is checked. `exclude` is a list or tuple of keys to be ignored.
    """
    difference = {}

    for key in destination_dict:
        if source_dict.get(key) != destination_dict[key]:
            if isinstance(exclude, (list, tuple)) and key in exclude:
                continue
            difference[key] = destination_dict[key]

    return difference


def to_meters(length, unit):
    """
    Convert the given length to meters.
    """
    length = int(length)
    if length < 0:
        raise ValueError("Length must be a positive integer")

    valid_units = choices.CableLengthUnitChoices.values()
    if unit not in valid_units:
        raise ValueError(f"Unknown unit {unit}. Must be one of the following: {', '.join(valid_units)}")

    if unit == choices.CableLengthUnitChoices.UNIT_KILOMETER:
        return length * 1000
    if unit == choices.CableLengthUnitChoices.UNIT_METER:
        return length
    if unit == choices.CableLengthUnitChoices.UNIT_CENTIMETER:
        return length / 100
    if unit == choices.CableLengthUnitChoices.UNIT_MILE:
        return length * Decimal("1609.344")
    if unit == choices.CableLengthUnitChoices.UNIT_FOOT:
        return length * Decimal("0.3048")
    if unit == choices.CableLengthUnitChoices.UNIT_INCH:
        return length * Decimal("0.3048") * 12
    raise ValueError(f"Unknown unit {unit}. Must be 'km', 'm', 'cm', 'mi', 'ft', or 'in'.")
