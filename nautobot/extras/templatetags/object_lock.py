"""Assignment template tags exposing per-object Object Lock state to detail templates.

Each call performs one query, delegated to ``lock_state_for_objects``.
"""

from django import template
from django.utils.html import format_html, format_html_join
from django_jinja import library

from nautobot.core.templatetags.buttons import action_url
from nautobot.core.templatetags.helpers import bettertitle
from nautobot.core.templatetags.perms import can_add
from nautobot.core.utils import lookup
from nautobot.core.views import utils as views_utils
from nautobot.extras.object_lock_ui import LOCK_PROTECTION_BLURB, lock_state_for_objects

register = template.Library()


@library.global_function(name="object_lock_state")
@register.simple_tag
def object_lock_state(obj):
    """Return the aggregated :class:`LockState` for ``obj``, or ``None`` if it has no active lock.

    Intended for assignment use in templates, e.g.::

        {% load object_lock %}
        {% object_lock_state object as object_lock %}
        {% if object_lock %} ... {% endif %}

    Returns ``None`` for a missing object or one lacking a primary key, so the template's ``{% if %}``
    guard renders the unlocked branch.

    Args:
        obj: A model instance, or ``None``.

    Returns:
        LockState | None: The lock state when the object currently has one or more active locks, else
        ``None``.
    """
    if obj is None or not hasattr(obj, "pk") or obj.pk is None:
        return None
    return lock_state_for_objects([obj]).get(obj.pk)


@library.global_function(name="object_lock_blurb")
@register.simple_tag
def object_lock_blurb():
    """Return the calibrated Object Lock protection blurb for use in template copy.

    Returns:
        str: ``LOCK_PROTECTION_BLURB`` (e.g. "protected against accidental deletion/edits ...").
    """
    return LOCK_PROTECTION_BLURB


@register.simple_tag(takes_context=True)
def object_lock_extra_detail_buttons(context):
    """Render the Clone + model-registered extra action buttons for a locked object's detail view.

    The locked branch of the detail template renders its own lock-aware Edit/Delete affordances instead
    of ``consolidate_detail_view_action_buttons``, which would otherwise also drop Clone and any
    model-specific extra action buttons (e.g. a device type's "Add Components"). This restores exactly
    those, so locking an object never hides unrelated, safe actions.
    """
    instance = context["object"]
    user = context["user"]
    rendered = []
    clone_url = action_url(instance, "add")
    if clone_url and hasattr(instance, "clone_fields") and can_add(user, instance):
        params = views_utils.prepare_cloned_fields(instance)
        if params:
            clone_url = f"{clone_url}?{params}"
        rendered.append(
            format_html(
                '<a href="{}" id="clone-button" class="btn btn-default">'
                '<span class="mdi mdi-plus-thick" aria-hidden="true"></span> Clone {}</a>',
                clone_url,
                bettertitle(context.get("verbose_name") or instance._meta.verbose_name),
            )
        )
    for extra_button in lookup.get_extra_detail_view_action_buttons_for_model(instance._meta.model):
        markup = extra_button.render(context)
        if markup:
            rendered.append(markup)
    return format_html_join("\n", "{}", ((button,) for button in rendered))
