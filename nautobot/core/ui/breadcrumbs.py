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
ModelType = Union[str, Model, Type[Model], None]


@dataclass
class BreadcrumbItem:
    """
    Dataclass responsible for generating an breadcrumb item. You can define items in multiple ways.

    This class provides 3 different modes of generating breadcrumbs:
    1. Viewname
    From raw viewname string that will be passed to the reverse method. You can pass reverse args or kwargs.
    In this mode you need to pass a label.

    2. Model
    Based on model class, content type or dotted model name passed directly or taken automatically from context.
    It will generate label based on model `verbose_name` or `verbose_name_plural` depending on `model_label_type`.
    You can still override it by passing a label.

    3. Instance
    Detail url for object instance taken from context. This is the default mode and instance will be get
    from `context["object"]`
    In this mode label will be generated from object, but you can still override it.

    Attributes:
        viewname_str (Optional[str]): Django view name to reverse. Used in raw viewname mode.
        reverse_kwargs (Optional[dict[str, Any]]): Keyword arguments passed to `reverse()`.
        reverse_args (Optional[dict[str, Any]]): Positional arguments passed to `reverse()`.
        instance_key (Optional[str]): Context key to fetch a Django model instance for building the breadcrumb.
        model (Union[str, Type[Model], None]): Django model class, instance, or dotted path string.
        model_key (Optional[str]): Context key to fetch a model class, instance or dotted path string.
        model_url_action (str): Action to use when resolving a model-based route (default: "list").
        model_label_type (Literal["singular", "plural"]): Whether to use `verbose_name` or `verbose_name_plural`.
        label (Optional[str]): Optional override for the display label in the breadcrumb.

    Examples:
        >>> BreadcrumbItem(model=Device)
        ("/dcim/devices/", "Devices")
        >>> BreadcrumbItem(instance_key="obj")

        >>> BreadcrumbItem(viewname_str="dcim:device_list")
        >>> BreadcrumbItem(viewname_str="dcim:device_list", viewname_kwargs={"filter": "some_value"}, label="Link")
    """

    # 1. Raw viewname mode
    viewname_str: Optional[str] = None
    reverse_kwargs: Optional[dict[str, Any]] = None
    reverse_args: Optional[dict[str, Any]] = None
    # 2. Object instance from context mode
    instance_key: Optional[str] = "object"
    # 3. Model/dotted model name passed directly or taken from context
    model: ModelType = None
    model_key: Optional[str] = None
    model_url_action: str = "list"
    model_label_type: ModelLabelType = "plural"
    # Option to override label
    label: Optional[WithStr] = None

    def get_url(self, context: Context) -> Optional[str]:
        """
        Resolve the URL for the breadcrumb item based on the configuration.

        The resolution strategy depends on the mode:
        - If `viewname_str` is provided, it uses `reverse()` with optional args/kwargs.
        - If `model` or `model_key` is set, it attempts to reverse a model-based view.
        - If `instance_key` is used, it generates a detail URL for that object using `get_object_link()`.

        Args:
            context (Context): The view or template context, used for resolving keys or models.

        Returns:
            Optional[str]: The resolved URL, or `None` if the resolution fails.
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
        Determine the label (display text) for the breadcrumb.

        Resolution priority:
        - If `label` is set explicitly, it's returned as-is.
        - If `model` or `model_key` is provided, it uses the model's `verbose_name` or `verbose_name_plural`.
        - If `instance_key` is provided, the object's `display` property or its string representation is used.

        Args:
            context (Context): The context used to fetch the instance or model.

        Returns:
            str: The label text to display for the breadcrumb item.
        """
        if self.label:
            return str(self.label)
        if self.model:
            return self._label_from_model(self.model)
        if self.model_key:
            model = context.get(self.model_key)
            return self._label_from_model(model)
        if self.instance_key:
            instance = context.get(self.instance_key)
            if hasattr(instance, "display"):
                return instance.display
            return str(instance)

        return ""

    def _label_from_model(self, model: ModelType) -> str:
        """
        Get the display name from the model's metadata.

        Depending on the `model_label_type`, either the `verbose_name` or `verbose_name_plural`
        will be returned. Accepts model class or dotted path string.

        Args:
            model (Union[str, Type[Model]]): A Django model class or dotted model name.
            name_arg (str): Optional override for metadata attribute to fetch.
                            Defaults to 'verbose_name_plural'.

        Returns:
            str: The verbose name of the model class for use as a label.
        """
        name_arg = "verbose_name" if self.model_label_type == "singular" else "verbose_name_plural"
        if not model:
            return ""
        if isinstance(model, str):
            model = get_model_from_name(model)
            return getattr(model._meta, name_arg)
        return getattr(model._meta, name_arg)

    def as_pair(self, context) -> tuple[str, Optional[str]]:
        """
        Construct the (URL, label) pair for the breadcrumb.

        Combines `get_url()` and `get_label()` and applies title casing to the label.

        Args:
            context (Context): Context object used to resolve the breadcrumb parts.

        Returns:
            tuple[str, Optional[str]]: A tuple of (URL, label), where URL may be an empty string
            if unresolved, and label is title-cased.
        """
        return self.get_url(context) or "", bettertitle(self.get_label(context))


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

BreadcrumbItemsType = dict[str, list[BreadcrumbItem]]


class Breadcrumbs:
    """
    Base class responsible for generating and rendering breadcrumbs for a page.

    This class supports flexible breadcrumb configuration through:
    - `items`: Default breadcrumb items per view action.
    - `prepend_items`: Items to prepend before the defaults.
    - `append_items`: Items to append after the defaults.

    You can override all or parts of the breadcrumb trail by passing appropriate
    `BreadcrumbItem` objects grouped by view action (e.g., "list", "add", "edit").

    Attributes:
        template (str): Path to the template used to render the breadcrumb component.
        items (dict[str, list[BreadcrumbItem]]): Default breadcrumb items per view action.
        prepend_items (dict[str, list[BreadcrumbItem]]): Items prepended to the breadcrumb trail.
        append_items (dict[str, list[BreadcrumbItem]]): Items appended to the breadcrumb trail.
    """

    def __init__(
        self,
        items: BreadcrumbItemsType = None,
        prepend_items: BreadcrumbItemsType = None,
        append_items: BreadcrumbItemsType = None,
        template: str = "inc/breadcrumbs.html",
    ):
        """
        Initialize the Breadcrumbs configuration.

        Args:
            items (Optional[dict[str, list[BreadcrumbItem]]]): Default breadcrumb items for each action.
            prepend_items (Optional[dict[str, list[BreadcrumbItem]]]): Items to prepend to action's breadcrumbs.
            append_items (Optional[dict[str, list[BreadcrumbItem]]]): Items to append to action's breadcrumbs.
            template (str): The template used to render the breadcrumbs.
        """
        self.template = template
        self.items = DEFAULT_BREADCRUMBS.copy()
        self.items.update(items)

        self.prepend_items = prepend_items
        self.append_items = append_items

    def get_breadcrumbs_items(self, context: Context):
        """
        Compute the list of breadcrumb items for the given context.

        Items are determined based on the `view_action` in context. This includes:
        - Prepend items
        - Default items
        - Append items

        Args:
            context (Context): The view or template context that holds `view_action` and related state.

        Returns:
            list[tuple[str, str]]: A list of (url, label) tuples representing breadcrumb entries.
        """
        action = context.get("view_action", "list_action")
        items = self.items.get(action, [])
        prepend_items = self.prepend_items.get(action, [])
        append_items = self.append_items.get(action, [])
        all_items = prepend_items + items + append_items
        return [item.as_pair(context) for item in all_items]

    def render(self, context):
        """
        Render the breadcrumbs HTML.

        This method updates the context with the generated breadcrumb items and any additional context from `get_extra_context`.

        Args:
            context (Context): The current rendering context.

        Returns:
            str: Rendered HTML for the breadcrumb component.
        """
        with context.update(
            {
                "breadcrumbs_items": self.get_breadcrumbs_items(context),
                **self.get_extra_context(context),
            }
        ):
            return render_component_template(self.template, context)

    def get_extra_context(self, context: Context):
        """
        Provide additional data to include in the rendering context, based on the configuration of this component.

         Args:
            context (Context): The current context passed to `render()`.

        Returns:
            dict: A dictionary of extra context variables.
        """
        return {}
