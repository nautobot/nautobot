from collections.abc import Iterable
import datetime
import json
import logging
import re
from typing import Literal
from urllib.parse import parse_qs, quote_plus

from django import template
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.staticfiles.finders import find
from django.core.exceptions import ObjectDoesNotExist
from django.templatetags.static import static, StaticNode
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, format_html_join, strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import slugify as django_slugify
from django_jinja import library
from markdown import markdown
import yaml

from nautobot.apps.config import get_app_settings_or_config
from nautobot.core import forms
from nautobot.core.constants import PAGINATE_COUNT_DEFAULT
from nautobot.core.utils import color, config, data, deprecation, logging as nautobot_logging, lookup
from nautobot.core.utils.requests import add_nautobot_version_query_param_to_url

HTML_TRUE = mark_safe('<span class="text-success"><i class="mdi mdi-check-bold" title="Yes"></i></span>')
HTML_FALSE = mark_safe('<span class="text-danger"><i class="mdi mdi-close-thick" title="No"></i></span>')
HTML_NONE = mark_safe('<span class="text-muted">&mdash;</span>')

DEFAULT_SUPPORT_MESSAGE = (
    "If further assistance is required, please join the `#nautobot` channel "
    "on [Network to Code's Slack community](https://slack.networktocode.com/) and post your question."
)

register = template.Library()


logger = logging.getLogger(__name__)


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
        value (Union[django.db.models.Model, None]): Instance of a Django model or None.
        field (Optional[str]): Name of the field to use for the display value. Defaults to "display".

    Returns:
        (str): String representation of the value (hyperlinked if it defines get_absolute_url()) or a placeholder.

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
    return _build_hyperlink(value, field)


@library.filter()
@register.filter()
def hyperlinked_email(value):
    """Render an email address as a `mailto:` hyperlink."""
    if not value:
        return placeholder(value)
    return format_html('<a href="mailto:{}">{}</a>', value, value)


@library.filter()
@register.filter()
def hyperlinked_phone_number(value):
    """Render a phone number as a `tel:` hyperlink."""
    if not value:
        return placeholder(value)
    return format_html('<a href="tel:{}">{}</a>', value, value)


@library.filter()
@register.filter()
def placeholder(value):
    """Render a muted placeholder if value is falsey, else render the value.

    Args:
        value (any): Input value, can be any variable.

    Returns:
        (str): Placeholder in HTML, or the string representation of the value.

    Example:
        >>> placeholder("")
        '<span class="text-muted">&mdash;</span>'
        >>> placeholder("hello")
        "hello"
    """
    if value:
        return value
    return HTML_NONE


@library.filter()
@register.filter()
def pre_tag(value):
    """Render a value within `<pre></pre>` tags to enable formatting.

    Args:
        value (any): Input value, can be any variable.

    Returns:
        (str): Value wrapped in `<pre></pre>` tags.

    Example:
        >>> pre_tag("")
        '<pre></pre>'
        >>> pre_tag("hello")
        '<pre>hello</pre>'
    """
    if value is not None:
        return format_html("<pre>{}</pre>", value)
    return HTML_NONE


@library.filter()
@register.filter()
def add_html_id(element_str, id_str):
    """Add an HTML `id="..."` attribute to the given HTML element string.

    Args:
        element_str (str): String describing an HTML element.
        id_str (str): String to add as the `id` attribute of the element_str.

    Returns:
        (str): HTML string with added `id`.

    Example:
        >>> add_html_id("<div></div>", "my-div")
        '<div id="my-div"></div>'
        >>> add_html_id('<a href="..." title="...">Hello!</a>', "my-a")
        '<a id="my-a" href="..." title="...">Hello!</a>'
    """
    match = re.match(r"^(.*?<\w+) ?(.*)$", element_str, flags=re.DOTALL)
    if not match:
        return element_str
    return mark_safe(match.group(1) + format_html(' id="{}" ', id_str) + match.group(2))  # noqa: S308  # suspicious-mark-safe-usage


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
        (str): HTML
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
        return HTML_NONE
    if bool(value):
        return HTML_TRUE
    return HTML_FALSE


@library.filter()
@register.filter(is_safe=True)
def render_markdown(value):
    """
    Render text as Markdown

    Example:
        {{ text | render_markdown }}
    """
    # Render Markdown
    html = markdown(value, extensions=["fenced_code", "tables"])

    # Sanitize rendered HTML
    html = nautobot_logging.clean_html(html)

    return mark_safe(html)  # noqa: S308  # suspicious-mark-safe-usage, OK here since we sanitized the string earlier


@library.filter()
@register.filter()
def render_json(value, syntax_highlight=True, pretty_print=False):
    """
    Render a dictionary as formatted JSON.

    Unless `syntax_highlight=False` is specified, the returned string will be wrapped in a
    `<code class="language-json>` HTML tag to flag it for syntax highlighting by highlight.js.

    Args:
        value (any): Input value, can be any variable.
        syntax_highlight (bool): Whether to highlight the JSON syntax or not.
        pretty_print (bool): Wraps rendered and highlighted JSON in <pre> tag for better code display.

    Returns:
        (str): HTML
            '<code class="language-json">{"json_key": "json_value"}</code>' if only syntax_highlight is True
            - or -
            '<pre><code class="language-json">{"json_key": "json_value"}</code></pre>' if both syntax_highlight and pretty_print are True
            - or -
            '{"json_key": "json_value"}' if only pretty_print is True (both syntax_highlight and pretty_print must be True for pretty print)

    Examples:
        >>> render_json({"key": "value"})
        '<code class="language-json">{"key": "value"}</code>'
        >>> render_json({"key": "value"}, syntax_highlight=False)
        '{"key": "value"}'
        >>> render_json({"key": "value"}, pretty_print=True)
        '<pre><code class="language-json">{"key": "value"}</code></pre>'
        >>> render_json({"key": "value"}, syntax_highlight=False, pretty_print=True)
        '{"key": "value"}'
    """
    rendered_json = json.dumps(value, indent=4, sort_keys=True, ensure_ascii=False)
    if syntax_highlight:
        html_string = '<code class="language-json">{}</code>'
        if pretty_print:
            html_string = "<pre>" + html_string + "</pre>"
        return format_html(html_string, rendered_json)

    return rendered_json


@library.filter()
@register.filter()
def render_yaml(value, syntax_highlight=True):
    """
    Render a dictionary as formatted YAML.

    Unless `syntax_highlight=False` is specified, the returned string will be wrapped in a
    `<code class="language-yaml>` HTML tag to flag it for syntax highlighting by highlight.js.
    """
    rendered_yaml = yaml.dump(json.loads(json.dumps(value, ensure_ascii=False)), allow_unicode=True)
    if syntax_highlight:
        return format_html('<code class="language-yaml">{}</code>', rendered_yaml)
    return rendered_yaml


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
        (any): return the value of the attribute
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
        (str): return the name of the view for the model/action provided.
    Examples:
        >>> viewname(Device, "list")
        "dcim:device_list"
    """
    return lookup.get_route_for_model(model, action)


@library.filter()
@register.filter()
def validated_viewname(model, action):
    """
    Return the view name for the given model and action if valid, or None if invalid.

    Args:
        model (models.Model): Class or Instance of a Django Model
        action (str): name of the action in the viewname

    Returns:
        (Union[str, None]): return the name of the view for the model/action provided if valid, or None if invalid.
    """
    viewname_str = lookup.get_route_for_model(model, action)

    try:
        # Validate and return the view name. We don't return the actual URL yet because many of the templates
        # are written to pass a name to {% url %}.
        reverse(viewname_str)
        return viewname_str
    except NoReverseMatch:
        return None


@library.filter()
@register.filter()
def validated_api_viewname(model, action):
    """
    Return the API view name for the given model and action if valid, or None if invalid.

    Args:
        model (models.Model): Class or Instance of a Django Model
        action (str): name of the action in the viewname

    Returns:
        (Union[str, None]): return the name of the API view for the model/action provided if valid, or None if invalid.
    """
    viewname_str = lookup.get_route_for_model(model, action, api=True)

    try:
        # Validate and return the view name. We don't return the actual URL yet because many of the templates
        # are written to pass a name to {% url %}.
        if action == "detail":
            # Detail views require an argument, so we'll pass a dummy value just for validation
            reverse(viewname_str, args=["00000000-0000-0000-0000-000000000000"])
        else:
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
        (str): string in Title format

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
        (str): ideal foreground color, either black (#000000) or white (#ffffff)

    Example:
        >>> fgcolor("#999999")
        "#ffffff"
    """
    value = value.lower().strip("#")
    if not re.match("^[0-9a-f]{6}$", value):
        return ""
    return f"#{color.foreground_color(value)}"


@library.filter()
@register.filter()
def divide(x, y):
    """Return x/y (rounded).

    Args:
        x (int or float): dividend number
        y (int or float): divisor number

    Returns:
        (int): x/y (rounded)

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
        (int): x/y as a percentage

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
    """Return the likely static documentation path for the specified model, if it can be found/predicted.

    - Core models, as of 2.0, are usually at `docs/user-guide/core-data-model/{app_label}/{model_name}.html`.
        - Models in the `extras` app are usually at `docs/user-guide/platform-functionality/{model_name}.html`.
    - Apps (plugins) are generally expected to be documented at `{app_label}/docs/models/{model_name}.html`.

    Any model can define a `documentation_static_path` class attribute if it needs to override the above expectations.

    If a file doesn't exist at the expected static path, this will return None.

    Args:
        model (models.Model): Instance of a Django model

    Returns:
        (Union[str, None]): static URL for the documentation of the object or None if not found.

    Example:
        >>> get_docs_url(location_instance)
        "static/docs/models/dcim/location.html"
    """
    if hasattr(model, "documentation_static_path"):
        path = model.documentation_static_path
    elif model._meta.app_label in settings.PLUGINS:
        path = f"{model._meta.app_label}/docs/models/{model._meta.model_name}.html"
    elif model._meta.app_label == "extras":
        path = f"docs/user-guide/platform-functionality/{model._meta.model_name}.html"
    else:
        path = f"docs/user-guide/core-data-model/{model._meta.app_label}/{model._meta.model_name}.html"

    # Check to see if documentation exists in any of the static paths.
    if find(path):
        return static(path)
    logger.debug("No documentation found for %s (expected to find it at %s)", type(model), path)
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
        (list[str]): List of string, if the separator wasn't found, list of 1
    """
    return string.split(sep)


@library.filter()
@register.filter()
def as_range(n):
    """Return a range of n items.

    Args:
        n (int, str): Number of element in the range

    Returns:
        (Union[list, Range]): range function from o to the value provided. Returns an empty list if n is not valid.

    Example:
        {% for i in record.ancestors.count|as_range %}
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
        (float): Value in feet
    """
    return float(n) * 3.28084


@library.filter()
@register.filter()
def get_item(d, key):
    """Access a specific item/key in a dictionary

    Args:
        d (dict): dictionary containing the data to access
        key (str): name of the item/key to access

    Returns:
        (any): Value of the item in the dictionary provided

    Example:
        >>> get_item(data, key)
        "value"
    """
    return d.get(key)


@library.filter()
@register.filter()
def settings_or_config(key, app_name=None):
    """Get a value from Django settings (if specified there) or Constance configuration (otherwise)."""
    if app_name:
        return get_app_settings_or_config(app_name, key)
    return config.get_settings_or_config(key)


@library.filter()
@register.filter()
def quote_string(value):
    """Add literal quote characters around the provided value if it's a string."""
    if isinstance(value, str):
        return f'"{value}"'
    return value


@library.filter()
def slugify(value):
    """Return a slugified version of the value."""
    return django_slugify(value)


@library.filter()
@register.filter()
def render_uptime(seconds):
    """Format a value in seconds to a human readable value.

    Example:
        >>> render_uptime(1024768)
        "11 days 20 hours 39 minutes"
    """
    try:
        seconds = int(seconds)
    except ValueError:
        return placeholder(seconds)
    delta = datetime.timedelta(seconds=seconds)
    uptime_hours = delta.seconds // 3600
    uptime_minutes = delta.seconds // 60 % 60
    return format_html(
        "{} {} {} {} {} {}",
        delta.days,
        "days" if delta.days != 1 else "day",
        uptime_hours,
        "hours" if uptime_hours != 1 else "hour",
        uptime_minutes,
        "minutes" if uptime_minutes != 1 else "minute",
    )


@library.filter()
@register.filter()
def dbm(value):
    """Display value as dBm."""
    return f"{value} dBm" if value else placeholder(value)


@library.filter()
@register.filter()
def hyperlinked_field(value, hyperlink=None):
    """Render a value as a hyperlink."""
    if not value:
        return placeholder(value)
    hyperlink = hyperlink or value
    return format_html('<a href="{}">{}</a>', hyperlink, value)


@library.filter()
@register.filter()
def render_content_types(value):
    """Render sorted by model and app_label ContentTypes value"""
    if not value.exists():
        return HTML_NONE
    output = format_html("<ul>")
    sorted_value = value.order_by("app_label", "model")
    for content_type in sorted_value:
        output += format_html("<li>{content_type}</li>", content_type=content_type)
    output += format_html("</ul>")

    return output


@library.filter()
@register.filter()
def render_ancestor_hierarchy(value):
    """Renders a nested HTML list representing the hierarchy of ancestors for a given object, with an optional location type."""

    if not value or not hasattr(value, "ancestors"):
        return HTML_NONE

    result = format_html('<ul class="tree-hierarchy">')
    append_to_result = format_html("</ul>")

    for ancestor in value.ancestors():
        nestable_tag = format_html('<span title="nestable">↺</span>' if getattr(ancestor, "nestable", False) else "")

        if getattr(ancestor, "location_type", None):
            location_type = hyperlinked_object(ancestor.location_type, "name")
            location_type = format_html("({})", location_type) if location_type else ""
            result += format_html(
                "<li>{value} {location_type} {nestable_tag}<ul>",
                value=hyperlinked_object(ancestor, "name"),
                location_type=location_type,
                nestable_tag=nestable_tag,
            )
        else:
            result += format_html(
                "<li>{value} {nestable_tag} <ul>",
                value=hyperlinked_object(ancestor, "name"),
                nestable_tag=nestable_tag,
            )
        append_to_result += format_html("</ul></li>")

    nestable_tag = format_html('<span title="nestable">↺</span>') if getattr(value, "nestable", False) else ""

    if getattr(value, "location_type", None):
        location_type = hyperlinked_object(value.location_type, "name")
        location_type = format_html("({})", location_type) if location_type else ""
        result += format_html(
            "<li><strong>{value} {location_type} {nestable_tag}</strong></li>",
            value=hyperlinked_object(value, "name"),
            location_type=location_type,
            nestable_tag=nestable_tag,
        )

    else:
        result += format_html(
            "<li><strong>{value} {nestable_tag}</strong></li>",
            value=hyperlinked_object(value, "name"),
            nestable_tag=nestable_tag,
        )
    result += append_to_result

    return result


@library.filter()
@register.filter()
def render_address(address):
    if address:
        map_link = format_html(
            '<a href="https://maps.google.com/?q={}" target="_blank" class="btn btn-primary btn-xs">'
            '<i class="mdi mdi-map-marker"></i> Map it</a>',
            quote_plus(address),
        )
        address = format_html_join("", "{}<br>", ((line,) for line in address.split("\n")))
        return format_html('<div class="pull-right noprint">{}</div>{}', map_link, address)
    return HTML_NONE


@register.filter()
def render_m2m(queryset, full_listing_link, verbose_name_plural, max_visible=5):
    total_count = queryset.count()
    display_count = min(total_count, max_visible)
    if not display_count:
        return HTML_NONE

    items = [hyperlinked_object(record) for record in queryset[:display_count]]

    remaining = total_count - display_count
    if remaining > 0:
        link = format_html('<a href="{}">... View {} more {}</a>', full_listing_link, remaining, verbose_name_plural)
        items.append(link)

    return format_html_join("", "<div>{}</div>", ((item,) for item in items)) if items else HTML_NONE


@library.filter()
@register.filter()
def render_button_class(value):
    """
    Render a string as a styled HTML button using Bootstrap classes.

    Args:
        value (str): A string representing the button class (e.g., 'primary').

    Returns:
        str: HTML string for a button with the given class.

    Example:
        >>> render_button_class("primary")
        '<button class="btn btn-primary">primary</button>'
    """
    if value:
        base = value.split()[0]
        return format_html('<button class="btn btn-{}">{}</button>', base.lower(), base.capitalize())
    return ""


def render_job_run_link(value):
    """
    Render the job as a hyperlink to its 'run' view using the class_path.

    Args:
        value (Job): The job object.

    Returns:
        str: HTML anchor tag linking to the job's run view.
    """
    if hasattr(value, "class_path"):
        url = reverse("extras:job_run_by_class_path", kwargs={"class_path": value.class_path})
        return format_html('<a href="{}">{}</a>', url, value)
    return str(value)


@library.filter()
@register.filter()
def label_list(value, suffix=""):
    """Render a list of values with optional suffix (like 'MHz') as span labels."""
    if not value:
        return HTML_NONE
    return format_html_join(
        " ",
        '<span class="label label-default">{0}{1}</span>',
        ((item, suffix) for item in value),
    )


#
# Tags
#


@register.simple_tag()
def get_attr(obj, attr, default=None):
    return getattr(obj, attr, default)


def _base_querystring(request, **kwargs):
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


# TODO: Remove this tag in Nautobot 3.0.


@register.simple_tag()
@deprecation.method_deprecated(
    "Leverage `legacy_querystring` instead of `querystring` if this templatetag is required. In Nautobot 3.0, "
    "`querystring` will be removed in preparation for Django 5.2 in which there is a built-in querystring tag "
    "that operates differently. You may find that `django_querystring` is more appropriate for your use case "
    "and is a replica of Django 5.2's `querystring` templatetag."
)
def querystring(request, **kwargs):
    return _base_querystring(request, **kwargs)


@register.simple_tag()
def legacy_querystring(request, **kwargs):
    return _base_querystring(request, **kwargs)


# Note: This is vendored from Django 5.2
@register.simple_tag(name="django_querystring", takes_context=True)
def django_querystring(context, query_dict=None, **kwargs):
    """
    Add, remove, and change parameters of a ``QueryDict`` and return the result
    as a query string. If the ``query_dict`` argument is not provided, default
    to ``request.GET``.

    For example::

        {% django_querystring foo=3 %}

    To remove a key::

        {% django_querystring foo=None %}

    To use with pagination::

        {% django_querystring page=page_obj.next_page_number %}

    A custom ``QueryDict`` can also be used::

        {% django_querystring my_query_dict foo=3 %}
    """
    if query_dict is None:
        query_dict = context.request.GET
    params = query_dict.copy()
    for key, value in kwargs.items():
        if value is None:
            if key in params:
                del params[key]
        elif isinstance(value, Iterable) and not isinstance(value, str):
            params.setlist(key, value)
        else:
            params[key] = value
    if not params and not query_dict:
        return ""
    query_string = params.urlencode()
    return f"?{query_string}"


@register.simple_tag()
def table_config_button(table, table_name=None, extra_classes="", disabled=False):
    if table_name is None:
        table_name = table.__class__.__name__
    html_template = (
        '<button type="button" class="btn btn-default {}'
        '" data-toggle="modal" data-target="#{}_config" {} title="Configure table">'
        '<i class="mdi mdi-cog"></i> Configure</button>'
    )
    return format_html(html_template, extra_classes, table_name, 'disabled="disabled"' if disabled else "")


@register.simple_tag()
def table_config_button_small(table, table_name=None):
    return table_config_button(table, table_name, "btn-xs")


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
        (dict): Dictionary with utilization, warning threshold, danger threshold, utilization count, and total count for
                display
    """
    # See https://github.com/nautobot/nautobot/issues/1169
    # If `get_utilization()` threw an exception, utilization_data will be an empty string
    # rather than a UtilizationData instance. Avoid a potentially confusing exception in that case.
    if not isinstance(utilization_data, data.UtilizationData):
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
        (dict): Dictionary with utilization, warning threshold, danger threshold, utilization count, and total count for
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
        "table_config_form": forms.TableConfigForm(table=table),
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


@register.inclusion_tag("utilities/templatetags/saved_view_modal.html")
def saved_view_modal(
    params,
    view,
    model,
    request,
):
    from nautobot.extras.forms import SavedViewModalForm
    from nautobot.extras.models import SavedView
    from nautobot.extras.utils import fixup_filterset_query_params

    sort_order = []
    per_page = None
    table_changes_pending = False
    all_filters_removed = False
    current_saved_view = None
    current_saved_view_pk = None
    non_filter_params = [
        "all_filters_removed",
        "page",
        "per_page",
        "sort",
        "saved_view",
        "table_changes_pending",
        "clear_view",
    ]
    param_dict = {}
    filters_applied = fixup_filterset_query_params(parse_qs(params), view, non_filter_params)

    view_class = lookup.get_view_for_model(model, "List")
    table_name = None
    if hasattr(view_class, "table"):
        table_name = view_class.table.__name__
    if hasattr(view_class, "table_class"):
        table_name = view_class.table_class.__name__

    for param in non_filter_params:
        if param == "saved_view":
            current_saved_view_pk = filters_applied.pop(param, None)
            if current_saved_view_pk:
                current_saved_view_pk = current_saved_view_pk[0]
                try:
                    # We are not using .restrict(request.user, "view") here
                    # User should be able to see any saved view that he has the list view access to.
                    current_saved_view = SavedView.objects.get(pk=current_saved_view_pk)
                except ObjectDoesNotExist:
                    messages.error(request, f"Saved view {current_saved_view_pk} not found")

        elif param == "table_changes_pending":
            table_changes_pending = filters_applied.pop(param, False)
        elif param == "all_filters_removed":
            all_filters_removed = filters_applied.pop(param, False)
        elif param == "per_page":
            per_page = filters_applied.pop(param, None)
        elif param == "sort":
            sort_order = filters_applied.pop(param, [])
        elif param == "clear_view":
            filters_applied.pop(param, False)

    if filters_applied:
        param_dict["filter_params"] = filters_applied
    else:
        if (current_saved_view is not None and all_filters_removed) or (current_saved_view is None):
            # user removed all the filters in a saved view
            param_dict["filter_params"] = {}
        elif current_saved_view is not None:
            # user did not make any changes to the saved view filter params
            param_dict["filter_params"] = current_saved_view.config.get("filter_params", {})

    if current_saved_view is not None and not table_changes_pending:
        # user did not make any changes to the saved view table config
        view_table_config = current_saved_view.config.get("table_config", {}).get(f"{table_name}", None)
        if view_table_config is not None:
            param_dict["table_config"] = view_table_config.get("columns", [])
    else:
        # display default user display
        if request.user is not None and not isinstance(request.user, AnonymousUser):
            param_dict["table_config"] = request.user.get_config(f"tables.{table_name}.columns")
    # If both are not available, do not display table_config

    if per_page:
        # user made changes to saved view pagination count
        param_dict["per_page"] = per_page
    elif current_saved_view is not None and not per_page:
        # no changes made, display current saved view pagination count
        param_dict["per_page"] = current_saved_view.config.get(
            "pagination_count", config.get_settings_or_config("PAGINATE_COUNT", fallback=PAGINATE_COUNT_DEFAULT)
        )
    else:
        # display default pagination count
        param_dict["per_page"] = config.get_settings_or_config("PAGINATE_COUNT", fallback=PAGINATE_COUNT_DEFAULT)

    if sort_order:
        # user made changes to saved view sort order
        param_dict["sort_order"] = sort_order
    elif current_saved_view is not None and not sort_order:
        # no changes made, display current saved view sort order
        param_dict["sort_order"] = current_saved_view.config.get("sort_order", [])
    else:
        # no sorting applied
        param_dict["sort_order"] = []

    param_dict = json.dumps(param_dict, indent=4, sort_keys=True, ensure_ascii=False)
    return {
        "form": SavedViewModalForm(),
        "params": params,
        "param_dict": param_dict,
        "view": view,
    }


@register.inclusion_tag("utilities/templatetags/dynamic_group_assignment_modal.html")
def dynamic_group_assignment_modal(request, content_type):
    from nautobot.extras.forms import DynamicGroupBulkAssignForm

    return {
        "request": request,
        "form": DynamicGroupBulkAssignForm(model=content_type.model_class()),
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
        (dict): Passed in values used to render HTML.
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
        url = f"{settings.MEDIA_URL}{settings.BRANDING_FILEPATHS.get(branding_asset)}"
    else:
        url = StaticNode.handle_simple(static_asset)
    return add_nautobot_version_query_param_to_url(url)


@register.simple_tag
def support_message():
    """
    Return the configured support message (if any) or else the default.
    """
    try:
        message = config.get_settings_or_config("SUPPORT_MESSAGE")
    except AttributeError:
        message = ""
    if not message:
        message = DEFAULT_SUPPORT_MESSAGE
    return render_markdown(message)


@register.simple_tag
def versioned_static(file_path):
    """Returns a versioned static file URL with a query parameter containing the version number."""
    url = static(file_path)
    return add_nautobot_version_query_param_to_url(url)


@register.simple_tag
def tree_hierarchy_ui_representation(tree_depth, hide_hierarchy_ui, base_depth=0):
    """Generates a visual representation of a tree record hierarchy using dots.

    Args:
        tree_depth (range): A range representing the depth of the tree nodes.
        hide_hierarchy_ui (bool): Indicates whether to hide the hierarchy UI.
        base_depth (int, optional): Starting depth (number of dots to skip rendering).

    Returns:
        str: A string containing dots (representing hierarchy levels) if `hide_hierarchy_ui` is False,
             otherwise an empty string.
    """
    if hide_hierarchy_ui or tree_depth == 0:
        return ""
    if isinstance(base_depth, int):  # may be an empty string
        tree_depth = tree_depth[base_depth:]
    ui_representation = " ".join(['<i class="mdi mdi-circle-small"></i>' for _ in tree_depth])
    return mark_safe(ui_representation)  # noqa: S308 # suspicious-mark-safe-usage, OK here since its just the `i` tag


@library.filter()
@register.filter()
def hyperlinked_object_with_color(obj):
    """Render the display view of an object."""
    if obj:
        content = f'<span class="label" style="color: {fgcolor(obj.color)}; background-color: #{obj.color}">{hyperlinked_object(obj)}</span>'
        return format_html(content)
    return HTML_NONE


@register.filter()
def queryset_to_pks(obj):
    """Return all object UUIDs as a string separated by `,`"""
    result = list(obj.values_list("pk", flat=True)) if obj else []
    result = [str(entry) for entry in result]
    return ",".join(result)


@library.filter()
@register.filter()
def hyperlinked_object_target_new_tab(value, field="display"):
    """Render and link to a Django model instance, if any, or render a placeholder if not.

    Similar to the hyperlinked_object filter, but passes attributes needed to open the link in new tab.

    Uses the specified object field if available, otherwise uses the string representation of the object.
    If the object defines `get_absolute_url()` this will be used to hyperlink the displayed object;
    additionally if there is an `object.description` this will be used as the title of the hyperlink.

    Args:
        value (Union[django.db.models.Model, None]): Instance of a Django model or None.
        field (Optional[str]): Name of the field to use for the display value. Defaults to "display".

    Returns:
        (str): String representation of the value (hyperlinked if it defines get_absolute_url()) or a placeholder.

    Examples:
        >>> hyperlinked_object_target_new_tab(device)
        '<a href="/dcim/devices/3faafe8c-bdd6-4317-88dc-f791e6988caa/" target="_blank" rel="noreferrer">Device 1</a>'
        >>> hyperlinked_object_target_new_tab(device_role)
        '<a href="/dcim/device-roles/router/" title="Devices that are routers, not switches" target="_blank" rel="noreferrer">Router</a>'
        >>> hyperlinked_object_target_new_tab(None)
        '<span class="text-muted">&mdash;</span>'
        >>> hyperlinked_object_target_new_tab("Hello")
        'Hello'
        >>> hyperlinked_object_target_new_tab(location)
        '<a href="/dcim/locations/leaf/" target="_blank" rel="noreferrer">Root → Intermediate → Leaf</a>'
        >>> hyperlinked_object_target_new_tab(location, "name")
        '<a href="/dcim/locations/leaf/" target="_blank" rel="noreferrer">Leaf</a>'
    """
    return _build_hyperlink(value, field, target="_blank", rel="noreferrer")


def _build_hyperlink(value, field="", target="", rel=""):
    """Internal function used by filters to build hyperlinks.

    Args:
        value (Union[django.db.models.Model, None]): Instance of a Django model or None.
        field (Optional[str]): Name of the field to use for the display value. Defaults to "display".
        target (Optional[str]): Location to open the linked document.  Defaults to "" which is _self.
        rel (Optional[str]): Relationship between current document and linked document. Defaults to "".

    Returns:
        (str): String representation of the value (hyperlinked if it defines get_absolute_url()) or a placeholder.
    """
    if value is None:
        return placeholder(value)

    attributes = {}
    display = getattr(value, field) if hasattr(value, field) else str(value)
    if hasattr(value, "get_absolute_url"):
        try:
            attributes["href"] = value.get_absolute_url()
            if hasattr(value, "description") and value.description:
                attributes["title"] = value.description
            if target:
                attributes["target"] = target
            if rel:
                attributes["rel"] = rel
            return format_html("<a {}>{}</a>", format_html_join(" ", '{}="{}"', attributes.items()), display)
        except AttributeError:
            pass
    return format_html("{}", display)


@register.simple_tag(takes_context=True)
def saved_view_title(context, mode: Literal["html", "plain"] = "html"):
    """
    Creates a formatted title that includes saved view information.
    Usage: <h1>{{ title }}{% saved_view_title "html" %}</h1>
    """
    new_changes_not_applied = context.get("new_changes_not_applied", False)
    current_saved_view = context.get("current_saved_view")

    if not current_saved_view:
        return ""

    if new_changes_not_applied:
        title = format_html(' — <i title="Pending changes not saved">{}</i>', current_saved_view.name)
    else:
        title = format_html(" — {}", current_saved_view.name)

    if mode == "plain":
        return strip_tags(title)

    return title
