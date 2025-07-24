import copy
from dataclasses import dataclass
import logging
from typing import Any, Callable, Literal, Optional, Protocol, Type, Union
from urllib.parse import urlencode

from django.db.models import Model
from django.template import Context
from django.urls import NoReverseMatch, reverse

from nautobot.core.templatetags import helpers
from nautobot.core.ui.utils import get_absolute_url, render_component_template
from nautobot.core.utils import lookup
from nautobot.core.utils.lookup import get_model_from_name

logger = logging.getLogger(__name__)


class WithStr(Protocol):
    def __str__(self) -> str: ...


ViewNameType = Union[str, Callable[[Context], str], None]
ModelLabelType = Literal["plural", "singular"]
ModelType = Union[str, Model, Type[Model], None]
LabelType = Union[Callable[[Context], str], WithStr, None]
BreadcrumbItemsType = dict[str, list["BaseBreadcrumbItem"]]
ReverseParams = Union[dict[str, Any], Callable[[Context], dict[str, Any]], None]


@dataclass
class BaseBreadcrumbItem:
    """
    Base interface for breadcrumb items.

    Attributes:
        should_render (Callable[[Context], bool]): Callable to decide whether this item should be rendered or not.
        label (Union[Callable[[Context], str], WithStr, None]): Optional override for the display label in the breadcrumb.
        label_key (Optional[str]): Optional key to take label from the context.
    """

    should_render: Callable[[Context], bool] = lambda context: True
    label: LabelType = None
    label_key: Optional[str] = None

    def get_url(self, context: Context) -> Optional[str]:
        """
        Get the URL for the breadcrumb item.
        """
        raise NotImplementedError

    def get_label(self, context: Context) -> str:
        """
        Get the label (display text) for the breadcrumb.
        """

        if self.label:
            return str(self.label(context)) if callable(self.label) else str(self.label)
        if self.label_key:
            return str(context.get(self.label_key, ""))
        return ""

    def reverse_view_name(
        self,
        view_name: str,
        context: Context,
        reverse_kwargs: ReverseParams = None,
        reverse_query_params: ReverseParams = None,
    ) -> Optional[str]:
        if view_name == "":
            return None

        try:
            url = reverse(view_name, kwargs=self.resolve_reverse_params(reverse_kwargs, context))
            if query_params := self.resolve_reverse_params(reverse_query_params, context):
                # TODO: refactor after Django 5.2 upgrade
                return f"{url}?{urlencode(query_params)}"
            return url
        except NoReverseMatch as err:
            logger.error('No reverse match for: "%s". Exc: %s', view_name, err)
            return None

    @staticmethod
    def resolve_reverse_params(params: ReverseParams, context: Context) -> dict[str, Any]:
        if callable(params):
            return params(context)
        if params:
            return params
        return {}

    def as_pair(self, context: Context) -> tuple[str, str]:
        """
        Construct the (URL, label) pair for the breadcrumb.

        Combines `get_url()` and `get_label()` and applies title casing to the label.

        Args:
            context (Context): Context object used to resolve the breadcrumb parts.

        Returns:
            tuple[str, Optional[str]]: A tuple of (URL, label), where URL may be an empty string
            if unresolved, and label is title-cased.
        """
        url = self.get_url(context) or ""
        label = helpers.bettertitle(self.get_label(context))
        return url, label


@dataclass
class ViewNameBreadcrumbItem(BaseBreadcrumbItem):
    """
    Breadcrumb via raw view name and optional params.

    From raw viewname string that will be passed to the reverse method. You can pass reverse kwargs or query params.
    Label won't be generated automatically.

    Attributes:
        view_name (Union[str, Callable[[Context], str], None]): Django view name to reverse or callable taking context.
            Can be used as fallback if `view_name_key` won't be found in the context.
        view_name_key: (Optional[str]): Key to get the `view_name` from the context.
        reverse_kwargs (Union[dict[str, Any], Callable[[Context], dict[str, Any]], None]): Keyword arguments passed to `reverse()`.
        reverse_query_params (Union[dict[str, Any], Callable[[Context], dict[str, Any]], None]): Keyword arguments added to the url.
        should_render (Callable[[Context], bool]): Callable to decide whether this item should be rendered or not.
        label (Union[Callable[[Context], str], WithStr, None]): Optional override for the display label in the breadcrumb.
        label_key (Optional[str]): Optional key to take label from the context.

    Examples:
        >>> ViewNameBreadcrumbItem(view_name="dcim:device_list")
        ("/dcim/devices/", "")  # No label automatically generated
        >>> ViewNameBreadcrumbItem(view_name="dcim:device_list", reverse_query_params={"filter": "some_value"}, label="Link")
        ("/dcim/devices/?filter=some_value", "Link")
    """

    view_name: ViewNameType = None
    view_name_key: Optional[str] = None
    reverse_kwargs: ReverseParams = None
    reverse_query_params: ReverseParams = None

    def get_url(self, context: Context) -> Optional[str]:
        """
        Get the URL for the breadcrumb item based on the configuration: view name, context, reverse kwargs, query params.
        """
        view_name = self.view_name
        if self.view_name_key:
            view_name = context.get(self.view_name_key, self.view_name)
        if not view_name:
            return None

        return self.reverse_view_name(self.view_name, context, self.reverse_kwargs, self.reverse_query_params)


@dataclass
class ModelBreadcrumbItem(BaseBreadcrumbItem):
    """
    Breadcrumb via model class / instance / name.

    Based on model class, content type or dotted model name passed directly or taken automatically from context.
    It will generate label based on model `verbose_name` or `verbose_name_plural` depending on `model_label_type`.
    If `label` is set explicitly, it's returned as-is or called if callable.

    Attributes:
        model (Union[str, Type[Model], None]): Django model class, instance, or dotted path string.
        model_key (Optional[str]): Context key to fetch a model class, instance or dotted path string.
        action (str): Action to use when resolving a model-based route (default: "list").
        label_type (Literal["singular", "plural"]): Whether to use `verbose_name` or `verbose_name_plural`.
        reverse_kwargs (nion[dict[str, Any], Callable[[Context], dict[str, Any]], None]): Keyword arguments passed to `reverse()`.
        reverse_query_params (nion[dict[str, Any], Callable[[Context], dict[str, Any]], None]): Keyword arguments added to the url.
        should_render (Callable[[Context], bool]): Callable to decide whether this item should be rendered or not.
        label (Union[Callable[[Context], str], WithStr, None]): Optional override for the display label in the breadcrumb.
        label_key (Optional[str]): Optional key to take label from the context.

    Examples:
        >>> ModelBreadcrumbItem(model=Device)
        ("/dcim/devices/", "Devices")
        >>> ModelBreadcrumbItem(model="dcim.device")
        ("/dcim/devices/", "Devices")
        >>> ModelBreadcrumbItem(model="dcim.device", label_type="singular", action="add")
        ("/dcim/devices/add", "Device")
    """

    model: ModelType = None
    model_key: Optional[str] = None
    action: str = "list"
    label_type: ModelLabelType = "plural"
    reverse_kwargs: ReverseParams = None
    reverse_query_params: ReverseParams = None

    def get_url(self, context: Context) -> Optional[str]:
        """
        Get the URL for the breadcrumb item based on the configuration: model, action, reverse kwargs, query params.
        """
        model_obj = self.model or context.get(self.model_key)
        if not model_obj:
            return None
        view_name = lookup.get_route_for_model(model_obj, self.action)
        return self.reverse_view_name(view_name, context, self.reverse_kwargs, self.reverse_query_params)

    def get_label(self, context: Context) -> str:
        """
        Get the display name from the model's metadata.

        Depending on the `model_label_type`, either the `verbose_name` or `verbose_name_plural`
        will be returned. Accepts model class, instance or dotted path string.

        Returns:
            str: The verbose name of the model class for use as a label.
        """
        if self.label or self.label_key:
            return super().get_label(context)

        model_obj = self.model or context.get(self.model_key)
        name_attr = "verbose_name" if self.label_type == "singular" else "verbose_name_plural"

        if model_obj is not None:
            if isinstance(model_obj, str):
                model_cls = get_model_from_name(model_obj)
                return getattr(model_cls._meta, name_attr)
            return getattr(model_obj._meta, name_attr)
        return ""


@dataclass
class InstanceBreadcrumbItem(BaseBreadcrumbItem):
    """
    Breadcrumb via object instance from context.

    Detail url for object instance taken from context. By default, `instance_key` is set to `object`.
    Label will be generated from object, but you can still override it.

    Attributes:
        instance_key (Optional[str]): Context key to fetch a Django model instance for building the breadcrumb.
        should_render (Callable[[Context], bool]): Callable to decide whether this item should be rendered or not.
        label (Union[Callable[[Context], str], WithStr, None]): Optional override for the display label in the breadcrumb.
        label_key (Optional[str]): Optional key to take label from the context.

    Examples:
        >>> InstanceBreadcrumbItem()
        ("/dcim/devices/1234", "My Device")  # Assuming that under "object" there is a Device instance
        >>> InstanceBreadcrumbItem(label="Custom Device Label")
        ("/dcim/devices/1234", "Custom Device Label")  # Assuming that under "object" there is a Device instance
    """

    instance_key: str = "object"
    label: Union[Callable[[Context], str], WithStr, None] = None

    def get_url(self, context: Context) -> Optional[str]:
        """
        Resolve the URL for the breadcrumb item based on the instance.
        """
        instance = context.get(self.instance_key)
        return get_absolute_url(instance) if instance else None

    def get_label(self, context: Context) -> str:
        """
        Get the label (display text) for the breadcrumb from instance.
        """
        if self.label or self.label_key:
            return super().get_label(context)
        instance = context.get(self.instance_key)
        if not instance:
            return ""
        return getattr(instance, "display", str(instance))


DEFAULT_MODEL_BREADCRUMBS = [
    ViewNameBreadcrumbItem(
        view_name_key="list_url", label_key="title", should_render=lambda context: context.get("list_url") is not None
    ),  # Default breadcrumb if view defines `list_url` in the Context
    ModelBreadcrumbItem(model_key="model", should_render=lambda context: context.get("list_url") is None),
    # Fallback if there is no `list_url` in the Context
]
DEFAULT_INSTANCE_BREADCRUMBS = DEFAULT_MODEL_BREADCRUMBS + [InstanceBreadcrumbItem()]

DEFAULT_BREADCRUMBS = {
    "list": DEFAULT_MODEL_BREADCRUMBS,
    "detail": DEFAULT_INSTANCE_BREADCRUMBS,
}


class Breadcrumbs:
    """
    Base class responsible for generating and rendering breadcrumbs for a page.

    This class supports flexible breadcrumb configuration through:
    - `items`: Default breadcrumb items per view action.
    - `prepend_items`: Items to prepend before the defaults.
    - `append_items`: Items to append after the defaults.

    You can override all or parts of the breadcrumb trail by passing appropriate
    `BreadcrumbItem` objects grouped by view action (e.g., "list", "add", "edit").

    `detail` action is special case, used when there is no dedicated action for given request.
    In such case breadcrumbs logic will be using `context['detail']: bool` to determine whether to show
    `list` version of breadcrumbs or `detail`.

    For example if you want to use standard `detail` breadcrumbs for almost all actions but change it only for
    `approve` action you can use this class as following: `Breadcrumbs(append_items={"approve": [...]})`

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
        self.items: BreadcrumbItemsType = copy.deepcopy(DEFAULT_BREADCRUMBS)
        if items:
            self.items.update(items)
        # TODO: after breadcrumbs implementation verify if we need append/prepend feature
        self.prepend_items: BreadcrumbItemsType = prepend_items or {}
        self.append_items: BreadcrumbItemsType = append_items or {}

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
            (list[tuple[str, str]]): A list of (url, label) tuples representing breadcrumb entries.
        """
        action = context.get("view_action", "list")
        detail = context.get("detail", False)
        items = self.get_items_for_action(self.items, action, detail)
        prepend_items = self.get_items_for_action(self.prepend_items, action, detail)
        append_items = self.get_items_for_action(self.append_items, action, detail)
        all_items = prepend_items + items + append_items
        return [item.as_pair(context) for item in all_items if item.should_render(context)]

    @staticmethod
    def get_items_for_action(items: BreadcrumbItemsType, action: str, detail: bool) -> list[BaseBreadcrumbItem]:
        breadcrumbs_list = items.get(action, [])
        if breadcrumbs_list:
            return breadcrumbs_list

        if detail:
            return items.get("detail", [])

        return []

    def render(self, context):
        """
        Render the breadcrumbs HTML.

        This method updates the context with the generated breadcrumb items and any additional context from `get_extra_context`.

        Args:
            context (Context): The current rendering context.

        Returns:
            (str): Rendered HTML for the breadcrumb component.
        """
        with context.update(
            {
                **self.get_extra_context(context),
            }
        ):
            breadcrumbs_items = self.get_breadcrumbs_items(context)
            return render_component_template(self.template, context, breadcrumbs_items=breadcrumbs_items)

    def get_extra_context(self, context: Context):
        """
        Provide additional data to include in the rendering context, based on the configuration of this component.

        Context updated here will be applied to resolving url and labels.
        Please ote that you can't override `breadcrumb_items` here because items are generated after this method call.

        Args:
            context (Context): The current context passed to `render()`.

        Returns:
            (dict): A dictionary of extra context variables.
        """
        return {}
