from dataclasses import dataclass
from typing import Any, Literal, Optional, Protocol, Type, Union

from django.db.models import Model
from django.template import Context
from django.urls import NoReverseMatch, reverse

from nautobot.core.templatetags.helpers import bettertitle, get_object_link
from nautobot.core.ui.utils import render_component_template
from nautobot.core.utils import lookup
from nautobot.core.utils.lookup import get_model_from_name


class WithStr(Protocol):
    def __str__(self) -> str: ...


ModelLabelType = Literal["plural", "singular"]


@dataclass
class BreadcrumbItem:
    """
    Dataclass responsible for generating an breadcrumb item. You can define items in multiple ways.

    This class provides 3 different modes of generating breadcrumbs:
    1. From raw viewname string that will be passed to the reverse method. In this mode you need to pass label.
    2. Detail url for object instance taken from context. In this mode label will ba taken from object but you can still override it.
    3. Based on model, dotted model name either passed directly or taken automatically from context.

    Attributes:
        model (models.Model, str): Class, Instance, or dotted string of a Django Model

    Examples:
        >>> BreadcrumbItem(model=Device)
        >>> BreadcrumbItem(instance_key="obj")
        >>> BreadcrumbItem(viewname_str="dcim:device_list")
        >>> BreadcrumbItem(viewname_str="dcim:device_list", viewname_kwargs={"filter": "some_value"}, label="Link")
    """

    # 1. Raw viewname mode
    viewname_str: Optional[str] = None
    reverse_kwargs: Optional[dict[str, Any]] = None
    reverse_args: Optional[dict[str, Any]] = None
    # 2. Object instance from context mode
    instance_key: Optional[str] = None
    # 3. Model/dotted model name passed directly or taken from context
    model: Union[str, Type[Model], None] = None
    model_key: Optional[str] = None
    model_url_action: str = "list"
    model_label_type: ModelLabelType = "plural"
    # Option to override label
    label: Optional[WithStr] = None

    def get_url(self, context: Context) -> Optional[str]:
        """
        Returns a resolved URL or None if resolution fails.
        """
        try:
            if self.viewname_str:
                return reverse(self.viewname_str, args=self.reverse_args or [], kwargs=self.reverse_kwargs or {})
            if self.model:
                viewname = lookup.get_route_for_model(self.model, "list")
                return reverse(viewname, args=self.reverse_args or [], kwargs=self.reverse_kwargs or {})
            if self.model_key:
                model = context.get(self.model_key)
                viewname = lookup.get_route_for_model(model, self.model_url_action)
                return reverse(viewname, args=self.reverse_args or [], kwargs=self.reverse_kwargs or {})
            if self.instance_key:
                instance = context.get(self.instance_key)
                return get_object_link(instance)
        except NoReverseMatch:
            return None

        return None

    def get_label(self, context: Context) -> str:
        """
        Returns the display text for the link. If label is None, try to resolve model or instance as label.
        """
        if self.label:
            return str(self.label)
        if self.model:
            return self._text_from_model(self.model)
        if self.model_key:
            model = context.get(self.model_key)
            return self._text_from_model(model)
        if self.instance_key:
            instance = context.get(self.instance_key)
            if hasattr(instance, "display"):
                return instance.display
            return str(instance)

        return ""

    def _text_from_model(self, model, name_arg="verbose_name_plural") -> str:
        name_arg = "verbose_name" if self.model_label_type == "singular" else "verbose_name_plural"
        if not model:
            return ""
        if isinstance(model, str):
            model = get_model_from_name(model)
            return getattr(model._meta, name_arg)
        return getattr(model._meta, name_arg)

    def as_pair(self, context) -> tuple[str, Optional[str]]:
        """
        Returns (url, label) tuple.
        """
        return (self.get_url(context) or "", bettertitle(self.get_label(context)))


DEFAULT_LIST_BREADCRUMBS = [BreadcrumbItem(model_key="content_type")]
DEFAULT_INSTANCE_BREADCRUMBS = [BreadcrumbItem(model_key="content_type"), BreadcrumbItem(instance_key="object")]

DEFAULT_BREADCRUMBS = {
    "list_action": DEFAULT_LIST_BREADCRUMBS,
    "retrieve_action": [BreadcrumbItem(model_key="content_type"), BreadcrumbItem(instance_key="object")],
    "destroy_action": DEFAULT_INSTANCE_BREADCRUMBS,
    "create_action": DEFAULT_LIST_BREADCRUMBS,
    "update_action": DEFAULT_INSTANCE_BREADCRUMBS,
    "bulk_destroy_action": DEFAULT_LIST_BREADCRUMBS,
    "bulk_rename_action": DEFAULT_LIST_BREADCRUMBS,
    "bulk_update_action": DEFAULT_LIST_BREADCRUMBS,
    "changelog_action": DEFAULT_INSTANCE_BREADCRUMBS,
    "notes_action": DEFAULT_INSTANCE_BREADCRUMBS,
    "approve_action": DEFAULT_INSTANCE_BREADCRUMBS,
    "deny_action": DEFAULT_INSTANCE_BREADCRUMBS,
}


class Breadcrumbs:
    """
    Base class with logic responsible for generating proper breadcrumbs.

    `items` can be used to override the default breadcrumbs behavior.
    `prepend_items` and `append_items` can be used to add some items at the start of end of the breadcrumbs.
    """

    def __init__(self, items=None, prepend_items=None, append_items=None, template="inc/breadcrumbs.html"):
        self.template = template
        self.items = DEFAULT_BREADCRUMBS.copy()
        self.items.update(items)

        self.prepend_items = prepend_items
        self.append_items = append_items

    def get_breadcrumbs_items(self, context: Context):
        action = context.get("view_action", "list_action")
        items = self.items.get(action, [])
        prepend_items = self.prepend_items.get(action, [])
        append_items = self.append_items.get(action, [])
        all_items = prepend_items + items + append_items
        return [item.as_pair(context) for item in all_items]

    def render(self, context):
        with context.update(
            breadcrumbs_items=self.generate_breadcrumbs_items(context),
            **self.get_extra_context(context),
        ):
            return render_component_template(self.template, context)

    def get_extra_context(self, context: Context):
        """
        Provide additional data to include in the rendering context, based on the configuration of this component.

        Returns:
            (dict): Additional context data.
        """
        return {}
