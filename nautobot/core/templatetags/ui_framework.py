from functools import partial
import logging

from django import template
from django.template.loader import render_to_string
from django.utils.html import format_html_join, strip_spaces_between_tags

from nautobot.core.ui.breadcrumbs import Breadcrumbs
from nautobot.core.ui.titles import Titles
from nautobot.core.ui.utils import render_component_template
from nautobot.core.utils.lookup import get_view_for_model
from nautobot.core.views.utils import get_obj_from_context

logger = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag(takes_context=True)
def render_tabs_labels(context, tabs):
    """Render the tab labels for each Tab in the given `tabs` with the given `context`."""
    if tabs is not None:
        return format_html_join("\n", "{}", ([tab.render_label_wrapper(context)] for tab in tabs))
    return ""


@register.simple_tag(takes_context=True)
def render_component(context, component):
    """Render a single component to HTML."""
    return component.render(context)


@register.simple_tag(takes_context=True)
def render_components(context, components):
    """Render each component in the given `components` with the given `context`."""
    if components is not None:
        return format_html_join("\n", "{}", ([component.render(context)] for component in components))
    return ""


@register.simple_tag(takes_context=True)
def render_table_config_forms(context, tabs):
    """
    Render all table config forms for the given tabs, filtering out duplicates when same table is used multiple times.
    """
    if tabs is not None:
        table_config_form_contexts = [
            panel.get_table_config_form_context(context)
            for tab in tabs
            if tab.should_render_content(context)
            for panel in tab.panels
            if hasattr(panel, "render_table_config_form")
        ]
        filtered_table_config_form_contexts = []
        for form_context in table_config_form_contexts:
            if not form_context:
                # Non-rendered table
                continue
            if form_context["table_name"] in [ffc["table_name"] for ffc in filtered_table_config_form_contexts]:
                # Duplicate entry
                continue
            filtered_table_config_form_contexts.append(form_context)

        return format_html_join(
            "\n",
            "{}",
            (
                [render_to_string("utilities/templatetags/table_config_form.html", form_context)]
                for form_context in filtered_table_config_form_contexts
            ),
        )
    return ""


@register.simple_tag(takes_context=True)
def render_title(context, mode="plain"):
    """
    Render the title passed in the context. Due to backwards compatibility in most of the Generic views,
    we're either passing `title` to the template or render `title` defined in `view_titles`.

    But in some newer views we want to have simple way to render title, only by defining `view_titles` within a view class.
    """
    if title := context.get("title"):
        return title

    title_obj = context.get("view_titles")
    if title_obj is not None and isinstance(title_obj, Titles):
        return title_obj.render(context, mode=mode)

    return ""


@register.simple_tag(takes_context=True)
def render_breadcrumbs(context, legacy_default_breadcrumbs=None, legacy_block_breadcrumbs=None):
    """
    Renders the breadcrumbs using the UI Component Framework or legacy template-defined breadcrumbs.

    Function checks if breadcrumbs from UI Component Framework are available and render them but only
    when there is no other changes coming from legacy template-defined breadcrumbs.

    Examples:
    - UI Component Framework breadcrumbs are defined in the view. But in the template, {% block breadcrumbs %} is being used,
    to override breadcrumbs or `{% block extra_breadcrumbs %}`. Output: template breadcrumbs will be rendered.
    - There is no UI Component Framework breadcrumbs and no other block overrides. Output: default breadcrumbs will be rendered.
    - UI Component Framework breadcrumbs are defined in the view. No breadcrumbs block overrides. Output: UI Component Framework breadcrumbs will be rendered.
    """
    render_template = partial(
        render_component_template,
        "components/breadcrumbs.html",
        context,
    )

    if (
        legacy_block_breadcrumbs
        and strip_spaces_between_tags(legacy_default_breadcrumbs).strip()
        != strip_spaces_between_tags(legacy_block_breadcrumbs).strip()
    ):
        return render_template(legacy_breadcrumbs=legacy_block_breadcrumbs)

    breadcrumbs_obj = context.get("breadcrumbs")
    if breadcrumbs_obj is not None and isinstance(breadcrumbs_obj, Breadcrumbs):
        return breadcrumbs_obj.render(context)

    return render_template(legacy_breadcrumbs=legacy_default_breadcrumbs)


@register.simple_tag(takes_context=True)
def render_detail_view_extra_buttons(context, tab_id=None):
    """
    Render the "extra_buttons" from the context's object_detail_content, or as fallback, from the base detail view.

    This makes it possible for "extra" tabs (such as Changelog and Notes, and any added by App TemplateExtensions)
    to automatically still render any `extra_buttons` defined by the base detail view, without the tab-specific views
    needing to explicitly inherit from the base view.
    """
    object_detail_content = context.get("object_detail_content")
    if object_detail_content is None:
        obj = get_obj_from_context(context)
        if obj is None:
            logger.error("No 'obj' or 'object' found in the render context!")
            return ""
        base_detail_view = get_view_for_model(obj)
        if base_detail_view is None:
            logger.warning(
                "Unable to identify the base detail view - check that it has a valid name, i.e. %sUIViewSet or %sView",
                type(obj).__name__,
                type(obj).__name__,
            )
            return ""
        object_detail_content = getattr(base_detail_view, "object_detail_content", None)
    if object_detail_content is not None and object_detail_content.extra_buttons:
        extra_buttons_on_current_tab = [
            extra_button
            for extra_button in object_detail_content.extra_buttons
            if tab_id is None  # `tab_id` *should* be given, but keep `is None` condition for backward compatibility
            or extra_button.render_on_tab_id == "__all__"
            or (isinstance(extra_button.render_on_tab_id, str) and tab_id == extra_button.render_on_tab_id)
            or (isinstance(extra_button.render_on_tab_id, (list, tuple)) and tab_id in extra_button.render_on_tab_id)
        ]
        return render_components(context, extra_buttons_on_current_tab)
    return ""


@register.simple_tag(takes_context=True)
def render_default_panels_for_object(context, obj):
    """
    Render the object_detail_content main-tab panels for the given object.

    Used for example in `extras/inc/jobresult.html` to render the details of a JobResult in a tab under the detail
    view of a different object (such as a GitRepository).
    """
    if obj is None:
        return ""
    base_detail_view = get_view_for_model(obj)
    if base_detail_view is None:
        logger.warning(
            "Unable to identify the base detail view - check that it has a valid name, i.e. %sUIViewSet or %sView",
            type(obj).__name__,
            type(obj).__name__,
        )
        return ""
    object_detail_content = getattr(base_detail_view, "object_detail_content", None)
    if object_detail_content is None:
        logger.warning("No object_detail_content defined on %s", base_detail_view.__name__)
        return ""
    with context.update({"obj": obj, "object": obj, "object_detail_content": object_detail_content}):
        return render_components(context, object_detail_content.tabs[0].panels)
