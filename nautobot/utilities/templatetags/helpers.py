import datetime
import json
import re

import yaml
from django import template
from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.templatetags.static import static, StaticNode
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, strip_tags
from django.utils.safestring import mark_safe
from markdown import markdown
from django_jinja import library

from nautobot.utilities.config import get_settings_or_config
from nautobot.utilities.forms import TableConfigForm
from nautobot.utilities.utils import foreground_color, get_route_for_model, UtilizationData

HTML_TRUE = '<span class="text-success"><i class="mdi mdi-check-bold" title="Yes"></i></span>'
HTML_FALSE = '<span class="text-danger"><i class="mdi mdi-close-thick" title="No"></i></span>'
HTML_NONE = '<span class="text-muted">&mdash;</span>'

register = template.Library()


#
# Filters
#


@library.filter()
@register.filter()
def hyperlinked_object(value, field="display"):
    """Render and link to a Django model instance, if any, or render a placeholder if not.

    Uses the specified object field if available, otherwise uses the string representation of the object.
    If the object defines `get_absolute_url()` this will be used to hyperlink the displayed object;
    additionally if there is an `object.description` this will be used as the title of the hyperlink.

    Args:
        value (django.db.models.Model, None)

    Returns:
        str: String representation of the value (hyperlinked if it defines get_absolute_url()) or a placeholder.

    Examples:
        >>> hyperlinked_object(device)
        '<a href="/dcim/devices/3faafe8c-bdd6-4317-88dc-f791e6988caa/">Device 1</a>'
        >>> hyperlinked_object(device_role)
        '<a href="/dcim/device-roles/router/" title="Devices that are routers, not switches">Router</a>'
        >>> hyperlinked_object(None)
        '<span class="text-muted">&mdash;</span>'
        >>> hyperlinked_object("Hello")
        'Hello'
        >>> hyperlinked_object(location)
        '<a href="/dcim/locations/leaf/">Root → Intermediate → Leaf</a>'
        >>> hyperlinked_object(location, "name")
        '<a href="/dcim/locations/leaf/">Leaf</a>'
    """
    if value is None:
        return placeholder(value)
    display = getattr(value, field) if hasattr(value, field) else str(value)
    if hasattr(value, "get_absolute_url"):
        if hasattr(value, "description") and value.description:
            return format_html('<a href="{}" title="{}">{}</a>', value.get_absolute_url(), value.description, display)
        return format_html('<a href="{}">{}</a>', value.get_absolute_url(), display)
    return format_html("{}", display)


@library.filter()
@register.filter()
def placeholder(value):
    """Render a muted placeholder if value is falsey, else render the value.

    Args:
        value (any): Input value, can be any variable.

    Returns:
        str: Placeholder in HTML, or the string representation of the value.

    Example:
        >>> placeholder("")
        '<span class="text-muted">&mdash;</span>'
        >>> placeholder("hello")
        "hello"
    """
    if value:
        return value
    return mark_safe(HTML_NONE)


@library.filter()
@register.filter()
def add_html_id(element_str, id_str):
    """Add an HTML `id="..."` attribute to the given HTML element string.

    Args:
        element_str (str): String describing an HTML element.
        id_str (str): String to add as the `id` attribute of the element_str.

    Returns:
        str: HTML string with added `id`.

    Example:
        >>> add_html_id("<div></div>", "my-div")
        '<div id="my-div"></div>'
        >>> add_html_id('<a href="..." title="...">Hello!</a>', "my-a")
        '<a id="my-a" href="..." title="...">Hello!</a>'
    """
    match = re.match(r"^(.*?<\w+) ?(.*)$", element_str, flags=re.DOTALL)
    if not match:
        return element_str
    return mark_safe(match.group(1) + format_html(' id="{}" ', id_str) + match.group(2))


@library.filter()
@register.filter()
def render_boolean(value):
    """Render HTML from a computed boolean value.

    Args:
        value (any): Input value, can be any variable.
        A truthy value (for example non-empty string / True / non-zero number) is considered True.
        A falsey value other than None (for example "" or 0 or False) is considered False.
        A value of None is considered neither True nor False.

    Returns:
        str: HTML
        '<span class="text-success"><i class="mdi mdi-check-bold" title="Yes"></i></span>' if True value
        - or -
        '<span class="text-muted">&mdash;</span>' if None value
        - or -
        '<span class="text-danger"><i class="mdi mdi-close-thick" title="No"></i></span>' if False value

    Examples:
        >>> render_boolean(None)
        '<span class="text-muted">&mdash;</span>'
        >>> render_boolean(True or "arbitrary string" or 1)
        '<span class="text-success"><i class="mdi mdi-check-bold" title="Yes"></i></span>'
        >>> render_boolean(False or "" or 0)
        '<span class="text-danger"><i class="mdi mdi-close-thick" title="No"></i></span>'
    """
    if value is None:
        return mark_safe(HTML_NONE)
    if bool(value):
        return mark_safe(HTML_TRUE)
    return mark_safe(HTML_FALSE)


@library.filter()
@register.filter(is_safe=True)
def render_markdown(value):
    """
    Render text as Markdown

    Example:
        {{ text | render_markdown }}
    """
    # Strip HTML tags
    value = strip_tags(value)

    # Sanitize Markdown links
    schemes = "|".join(settings.ALLOWED_URL_SCHEMES)
    pattern = rf"\[(.+)\]\((?!({schemes})).*:(.+)\)"
    value = re.sub(pattern, "[\\1](\\3)", value, flags=re.IGNORECASE)

    # Render Markdown
    html = markdown(value, extensions=["fenced_code", "tables"])

    return mark_safe(html)


@library.filter()
@register.filter()
def render_json(value):
    """
    Render a dictionary as formatted JSON.
    """
    return json.dumps(value, indent=4, sort_keys=True, ensure_ascii=False)


@library.filter()
@register.filter()
def render_yaml(value):
    """
    Render a dictionary as formatted YAML.
    """
    return yaml.dump(json.loads(json.dumps(value, ensure_ascii=False)), allow_unicode=True)


@library.filter()
@register.filter()
def meta(obj, attr):
    """
    Return the specified Meta attribute of a model. This is needed because Django does not permit templates
    to access attributes which begin with an underscore (e.g. _meta).

    Args:
        obj (models.Model): Class or Instance of a Django Model
        attr (str): name of the attribute to access

    Returns:
        any: return the value of the attribute
    """
    return getattr(obj._meta, attr, "")


@library.filter()
@register.filter()
def viewname(model, action):
    """
    Return the view name for the given model and action. Does not perform any validation.

    Args:
        model (models.Model): Class or Instance of a Django Model
        action (str): name of the action in the viewname

    Returns:
        str: return the name of the view for the model/action provided.
    Examples:
        >>> viewname(Device, "list")
        "dcim:device_list"
    """
    return get_route_for_model(model, action)


@library.filter()
@register.filter()
def validated_viewname(model, action):
    """
    Return the view name for the given model and action if valid, or None if invalid.

    Args:
        model (models.Model): Class or Instance of a Django Model
        action (str): name of the action in the viewname

    Returns:
        str or None: return the name of the view for the model/action provided if valid, or None if invalid.
    """
    viewname_str = get_route_for_model(model, action)

    try:
        # Validate and return the view name. We don't return the actual URL yet because many of the templates
        # are written to pass a name to {% url %}.
        reverse(viewname_str)
        return viewname_str
    except NoReverseMatch:
        return None


@library.filter()
@register.filter()
def bettertitle(value):
    """
    Alternative to the builtin title(); capitalizes words without replacing letters that are already uppercase.

    Args:
        value (str): string to convert to Title Case

    Returns:
        str: string in Title format

    Example:
        >>> bettertitle("IP address")
        "IP Address"
    """
    return " ".join([w[0].upper() + w[1:] for w in value.split()])


@library.filter()
@register.filter()
def humanize_speed(speed):
    """
    Humanize speeds given in Kbps. Examples:

        1544 => "1.544 Mbps"
        100000 => "100 Mbps"
        10000000 => "10 Gbps"
    """
    if not speed:
        return ""
    if speed >= 1000000000 and speed % 1000000000 == 0:
        return f"{int(speed / 1000000000)} Tbps"
    elif speed >= 1000000 and speed % 1000000 == 0:
        return f"{int(speed / 1000000)} Gbps"
    elif speed >= 1000 and speed % 1000 == 0:
        return f"{int(speed / 1000)} Mbps"
    elif speed >= 1000:
        return f"{float(speed) / 1000} Mbps"
    else:
        return f"{speed} Kbps"


@library.filter()
@register.filter()
def tzoffset(value):
    """
    Returns the hour offset of a given time zone using the current time.
    """
    return datetime.datetime.now(value).strftime("%z")


@library.filter()
@register.filter()
def fgcolor(value):
    """
    Return the ideal foreground color (block or white) given an arbitrary background color in RRGGBB format.

    Args:
        value (str): Color in RRGGBB format, with or without #

    Returns:
        str: ideal foreground color, either black (#000000) or white (#ffffff)

    Example:
        >>> fgcolor("#999999")
        "#ffffff"
    """
    value = value.lower().strip("#")
    if not re.match("^[0-9a-f]{6}$", value):
        return ""
    return f"#{foreground_color(value)}"


@library.filter()
@register.filter()
def divide(x, y):
    """Return x/y (rounded).

    Args:
        x (int or float): dividend number
        y (int or float): divisor number

    Returns:
        int: x/y (rounded)

    Examples:
        >>> divide(10, 3)
        3
    """
    if x is None or y is None:
        return None
    return round(x / y)


@library.filter()
@register.filter()
def percentage(x, y):
    """Return x/y as a percentage.

    Args:
        x (int or float): dividend number
        y (int or float): divisor number

    Returns:
        int: x/y as a percentage

    Examples:
        >>> percentage(2, 10)
        20

    """
    if x is None or y is None:
        return None
    return round(x / y * 100)


@library.filter()
@register.filter()
def get_docs_url(model):
    """Return the documentation URL for the specified model.

    Nautobot Core models have a path like docs/models/{app_label}/{model_name}
    while plugins will have {app_label}/docs/models/{model_name}. If the html file
    does not exist, this function will return None.

    Args:
        model (models.Model): Instance of a Django model

    Returns:
        str: static URL for the documentation of the object.
        or
        None

    Example:
        >>> get_docs_url(obj)
        "static/docs/models/dcim/site.html"
    """
    path = f"docs/models/{model._meta.app_label}/{model._meta.model_name}.html"
    if model._meta.app_label in settings.PLUGINS:
        path = f"{model._meta.app_label}/docs/models/{model._meta.model_name}.html"

    # Check to see if documentation exists in any of the static paths.
    if find(path):
        return static(path)
    return None


@library.filter()
@register.filter()
def has_perms(user, permissions_list):
    """
    Return True if the user has *all* permissions in the list.
    """
    return user.has_perms(permissions_list)


@library.filter()
@register.filter()
def has_one_or_more_perms(user, permissions_list):
    """
    Return True if the user has *at least one* permissions in the list.
    """

    for permission in permissions_list:
        if user.has_perm(permission):
            return True
    return False


@library.filter()
@register.filter()
def split(string, sep=","):
    """Split a string by the given value (default: comma)

    Args:
        string (str): string to split into a list
        sep (str default=,): separator to look for in the string

    Returns:
        [list]: List of string, if the separator wasn't found, list of 1
    """
    return string.split(sep)


@library.filter()
@register.filter()
def as_range(n):
    """Return a range of n items.

    Args:
        n (int, str): Number of element in the range

    Returns:
        [list, Range]: range function from o to the value provided. Returns an empty list if n is not valid.

    Example:
        {% for i in record.parents|as_range %}
            <i class="mdi mdi-circle-small"></i>
        {% endfor %}
    """
    try:
        int(n)
    except (TypeError, ValueError):
        return []
    return range(int(n))


@library.filter()
@register.filter()
def meters_to_feet(n):
    """Convert a length from meters to feet.

    Args:
        n (int, float, str): Number of meters to convert

    Returns:
        [float]: Value in feet
    """
    return float(n) * 3.28084


@library.filter()
@register.filter()
def get_item(d, key):
    """Access a specific item/key in a dictionary

    Args:
        d (dict): dictionary containing the data to access
        key (str]): name of the item/key to access

    Returns:
        [any]: Value of the item in the dictionary provided

    Example:
        >>> get_items(data, key)
        "value"
    """
    return d.get(key)


@library.filter()
@register.filter()
def settings_or_config(key):
    """Get a value from Django settings (if specified there) or Constance configuration (otherwise)."""
    return get_settings_or_config(key)


@library.filter()
@register.filter()
def quote_string(value):
    """Add literal quote characters around the provided value if it's a string."""
    if isinstance(value, str):
        return f'"{value}"'
    return value


#
# Tags
#


@register.simple_tag()
def get_attr(obj, attr, default=None):
    return getattr(obj, attr, default)


@register.simple_tag()
def querystring(request, **kwargs):
    """
    Append or update the page number in a querystring.
    """
    querydict = request.GET.copy()
    for k, v in kwargs.items():
        if v is not None:
            querydict[k] = str(v)
        elif k in querydict:
            querydict.pop(k)
    query_string = querydict.urlencode(safe="/")
    if query_string:
        return "?" + query_string
    else:
        return ""


@register.inclusion_tag("utilities/templatetags/utilization_graph.html")
def utilization_graph(utilization_data, warning_threshold=75, danger_threshold=90):
    """Wrapper for a horizontal bar graph indicating a percentage of utilization from a tuple of data.

    Takes the utilization_data that is a namedtuple with numerator and denominator field names and passes them into
    the utilization_graph_raw_data to handle the generation graph data.

    Args:
        utilization_data (UtilizationData): Namedtuple with numerator and denominator keys
        warning_threshold (int, optional): Warning Threshold Value. Defaults to 75.
        danger_threshold (int, optional): Danger Threshold Value. Defaults to 90.

    Returns:
        dict: Dictionary with utilization, warning threshold, danger threshold, utilization count, and total count for
                display
    """
    # See https://github.com/nautobot/nautobot/issues/1169
    # If `get_utilization()` threw an exception, utilization_data will be an empty string
    # rather than a UtilizationData instance. Avoid a potentially confusing exception in that case.
    if not isinstance(utilization_data, UtilizationData):
        return {}
    return utilization_graph_raw_data(
        numerator=utilization_data.numerator,
        denominator=utilization_data.denominator,
        warning_threshold=warning_threshold,
        danger_threshold=danger_threshold,
    )


@register.inclusion_tag("utilities/templatetags/utilization_graph.html")
def utilization_graph_raw_data(numerator, denominator, warning_threshold=75, danger_threshold=90):
    """Display a horizontal bar graph indicating a percentage of utilization.

    Args:
        numerator (int): Numerator for creating a percentage
        denominator (int): Denominator for creating a percentage
        warning_threshold (int, optional): Warning Threshold Value. Defaults to 75.
        danger_threshold (int, optional): Danger Threshold Value. Defaults to 90.

    Returns:
        dict: Dictionary with utilization, warning threshold, danger threshold, utilization count, and total count for
                display
    """
    # Check for possible division by zero error
    if denominator == 0:
        utilization = 0
    else:
        utilization = int(float(numerator) / denominator * 100)

    return {
        "utilization": utilization,
        "warning_threshold": warning_threshold,
        "danger_threshold": danger_threshold,
        "utilization_count": numerator,
        "total_count": denominator,
    }


@register.inclusion_tag("utilities/templatetags/tag.html")
def tag(tag, url_name=None):  # pylint: disable=redefined-outer-name
    """
    Display a tag, optionally linked to a filtered list of objects.
    """
    return {
        "tag": tag,
        "url_name": url_name,
    }


@register.inclusion_tag("utilities/templatetags/badge.html")
def badge(value, show_empty=False):
    """
    Display the specified number as a badge.
    """
    return {
        "value": value,
        "show_empty": show_empty,
    }


@register.inclusion_tag("utilities/templatetags/table_config_form.html")
def table_config_form(table, table_name=None):
    return {
        "table_name": table_name or table.__class__.__name__,
        "table_config_form": TableConfigForm(table=table),
    }


@register.inclusion_tag("utilities/templatetags/filter_form_modal.html")
def filter_form_modal(
    filter_form,
    dynamic_filter_form,
    model_plural_name,
    filter_form_name="FilterForm",
    dynamic_filter_form_name="DynamicFilterForm",
):
    return {
        "model_plural_name": model_plural_name,
        "filter_form": filter_form,
        "filter_form_name": filter_form_name,
        "dynamic_filter_form": dynamic_filter_form,
        "dynamic_filter_form_name": dynamic_filter_form_name,
    }


@register.inclusion_tag("utilities/templatetags/modal_form_as_dialog.html")
def modal_form_as_dialog(form, editing=False, form_name=None, obj=None, obj_type=None):
    """Generate a form in a modal view.

    Create an overlaying modal view which holds a Django form.

    Inside of the template the template tag needs to be used with the correct inputs. A button will
    also need to be create to open and close the modal. See below for an example:

    ```
    {% modal_form_as_dialog form editing=False form_name="CreateDevice" obj=obj obj_type="Device" %}
    <a class="btn btn-primary" data-toggle="modal" data-target="#CreateDevice_form" title="Query Form">Create Device</a>
    ```
    Args:
        form (django.form.Forms): Django form object.
        editing (bool, optional): Is the form creating or editing an object? Defaults to False for create.
        form_name ([type], optional): Name of form. Defaults to None. If None get name from class name.
        obj (django.model.Object, optional): If editing an existing model object, the object needs to be passed in. Defaults to None.
        obj_type (string, optional): Used in title of form to display object type. Defaults to None.

    Returns:
        dict: Passed in values used to render HTML.
    """
    return {
        "editing": editing,
        "form": form,
        "form_action_url": form.get_action_url(),
        "form_name": form_name or form.__class__.__name__,
        "obj": obj,
        "obj_type": obj_type,
    }


@register.simple_tag
def custom_branding_or_static(branding_asset, static_asset):
    """
    This tag attempts to return custom branding assets relative to the MEDIA_ROOT and MEDIA_URL, if such
    branding has been configured in settings, else it returns stock branding via static.
    """
    if settings.BRANDING_FILEPATHS.get(branding_asset):
        return f"{ settings.MEDIA_URL }{ settings.BRANDING_FILEPATHS.get(branding_asset) }"
    return StaticNode.handle_simple(static_asset)
