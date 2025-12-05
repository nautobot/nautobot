from dataclasses import dataclass
from itertools import chain
import logging
from operator import attrgetter
from typing import Any, Callable, Iterator, Literal, Optional, Protocol, Type, Union
from urllib.parse import urlencode

from django.db.models import Model
from django.template import Context
from django.urls import NoReverseMatch, reverse

from nautobot.core.models.tree_queries import TreeModel
from nautobot.core.templatetags import helpers
from nautobot.core.ui.utils import get_absolute_url, render_component_template
from nautobot.core.utils import deprecation, lookup
from nautobot.core.utils.lookup import get_model_for_view_name, get_model_from_name
from nautobot.core.views.utils import get_obj_from_context

logger = logging.getLogger(__name__)


class WithStr(Protocol):
    def __str__(self) -> str: ...


ViewNameType = Union[str, Callable[[Context], str], None]
ModelLabelType = Literal["plural", "singular"]
ModelType = Union[str, Model, Type[Model], None]
LabelType = Union[Callable[[Context], str], WithStr, None]
BreadcrumbItemsType = dict[str, list["BaseBreadcrumbItem"]]
ReverseParams = Union[dict[str, Any], Callable[[Context], dict[str, Any]], None]


def context_object_attr(attr_path: str, context_key: str = "object"):
    """
    Helper function that creates callable to fetch the object from context and then nested attributes.

    Useful for composing breadcrumbs. For example:
    ```
    context = Context({"object": Device.objects.first()})
    breadcrumbs = Breadcrumbs(items={"detail": [
        InstanceBreadcrumbItem(instance=context_object_attr("location.location_type")),
        InstanceBreadcrumbItem(instance=context_object_attr("location")),
    ]})
    ```
    Will render:
    - url to the device.location.location_type detail page
    - url to the device.location detail page

    Examples:
        >>> context_object_attr("location.name")
        lambda context: context['object'].location.name
        >>> context_object_attr("location.name", context_key="device")
        lambda context: context['device'].location.name

    """
    return lambda context: attrgetter(attr_path)(context[context_key]) if context.get(context_key) else None


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

        Args:
            context (Context): The current template context.

        Returns:
            Optional[str]: The URL as a string, or None.
        """
        return None

    def get_label(self, context: Context) -> str:
        """
        Get the label (display text) for the breadcrumb.

        Args:
            context (Context): The current template context.

        Returns:
            str: Label as a string.
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
        """
        Reverse a Django view name into a URL, optionally adding query parameters.

        Args:
            view_name (str): Django view name to reverse.
            context (Context): Template context, used to resolve params if needed.
            reverse_kwargs (ReverseParams): URL kwargs for reversing.
            reverse_query_params (ReverseParams): Query parameters to append.

        Returns:
            Optional[str]: The resolved URL as a string, or None if reversing fails.
        """
        if view_name == "":
            return None

        try:
            # TODO: refactor after Django 5.2 upgrade
            # query params can be passed directly to the `reverse` function instead of merging two strings
            # reverse(view_name, query=query_params, kwargs=...)
            # https://docs.djangoproject.com/en/5.2/ref/urlresolvers/#reverse
            url = reverse(view_name, kwargs=self.resolve_reverse_params(reverse_kwargs, context))
            if query_params := self.resolve_reverse_params(reverse_query_params, context):
                return f"{url}?{urlencode(query_params)}"
            return url
        except NoReverseMatch as err:
            logger.error('No reverse match for: "%s". Exc: %s', view_name, err)
            return None

    @staticmethod
    def resolve_reverse_params(params: ReverseParams, context: Context) -> dict[str, Any]:
        """
        Resolves parameters for URL reversing, calling if callable, or returning as-is.

        Args:
            params (ReverseParams): Dict or callable to resolve.
            context (Context): Context for callables.

        Returns:
            dict[str, Any]: Dictionary of parameters for URL reversing.
        """
        if callable(params):
            return params(context)
        if params:
            return params
        return {}

    def as_pair(self, context: Context) -> Iterator[tuple[str, str]]:
        """
        Construct the (URL, label) pair for the breadcrumb.

        Combines `get_url()` and `get_label()` and applies formatting to the label.

        Args:
            context (Context): Context object used to resolve the breadcrumb parts.

        Returns:
            Iterator[tuple[str, Optional[str]]]: A tuple of (URL, label), where URL may be an empty string
            if unresolved, and label.
        """
        url = self.get_url(context) or ""
        label = self.get_label(context)
        yield url, label


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
        label_from_view_name (bool): Try to resolve given view name and get the label from assosiacted model.

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
    label_from_view_name: bool = False

    def get_url(self, context: Context) -> Optional[str]:
        """
        Get the URL for the breadcrumb item based on the configuration: view name, context, reverse kwargs, query params.

        Args:
            context (Context): The current template context.

        Returns:
            Optional[str]: The URL as a string, or None.
        """
        view_name = self.get_view_name(context)
        if not view_name:
            return None

        return self.reverse_view_name(view_name, context, self.reverse_kwargs, self.reverse_query_params)

    def get_label(self, context: Context) -> str:
        if self.label_from_view_name:
            try:
                model = get_model_for_view_name(self.get_view_name(context))
                if model is not None:
                    return helpers.bettertitle(model._meta.verbose_name_plural)
            except ValueError:
                # `get_model_for_view_name` is not working properly with some proper paths like "home"
                # and because by default we're trying to resolve label by using `list_url` this error may occur in some apps
                pass
        return super().get_label(context)

    def get_view_name(self, context: Context) -> Optional[str]:
        if self.view_name_key:
            return context.get(self.view_name_key, self.view_name)
        if callable(self.view_name):
            return self.view_name(context)

        return self.view_name


@dataclass
class ModelBreadcrumbItem(BaseBreadcrumbItem):
    """
    Breadcrumb via model class / instance / name.

    Based on model class, content type or dotted model name passed directly or taken automatically from context.
    It will generate label based on model `verbose_name` or `verbose_name_plural` depending on `model_label_type`.
    If `label` is set explicitly, it's returned as-is or called if callable.

    Attributes:
        model (Union[str, Type[Model], None, Callable[[Context], Union[str, Type[Model], None]]): Django model class, instance, or dotted path string or callable that returns one of this.
        model_key (Optional[str]): Context key to fetch a model class, instance or dotted path string. By default: "object".
        action (str): Action to use when resolving a model-based route (default: "list").
        label_type (Literal["singular", "plural"]): Whether to use `verbose_name` or `verbose_name_plural`.
        reverse_kwargs (Union[dict[str, Any], Callable[[Context], dict[str, Any]], None]): Keyword arguments passed to `reverse()`.
        reverse_query_params (Union[dict[str, Any], Callable[[Context], dict[str, Any]], None]): Keyword arguments added to the url.
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

    model: Union[ModelType, Callable[[Context], ModelType]] = None
    model_key: Optional[str] = "object"
    action: str = "list"
    label_type: ModelLabelType = "plural"
    reverse_kwargs: ReverseParams = None
    reverse_query_params: ReverseParams = None

    def get_url(self, context: Context) -> Optional[str]:
        """
        Get the URL for the breadcrumb item based on the configuration: model, action, reverse kwargs, query params.

        Args:
            context (Context): The current template context.

        Returns:
            Optional[str]: The URL as a string, or None.
        """
        model_obj = self.get_model(context)
        if not model_obj:
            return None
        view_name = lookup.get_route_for_model(model_obj, self.action)
        return self.reverse_view_name(view_name, context, self.reverse_kwargs, self.reverse_query_params)

    def get_label(self, context: Context) -> str:
        """
        Get the display name from the model's metadata.

        Depending on the `model_label_type`, either the `verbose_name` or `verbose_name_plural`
        will be returned. Accepts model class, instance or dotted path string.

        Args:
            context (Context): The current template context.

        Returns:
            str: The verbose name of the model class for use as a label.
        """
        if self.label or self.label_key:
            return super().get_label(context)

        model_obj = self.get_model(context)
        name_attr = "verbose_name" if self.label_type == "singular" else "verbose_name_plural"
        label = ""

        if model_obj is not None:
            if isinstance(model_obj, str):
                model_cls = get_model_from_name(model_obj)
                label = getattr(model_cls._meta, name_attr)
            else:
                label = getattr(model_obj._meta, name_attr)

        return helpers.bettertitle(label)

    def get_model(self, context: Context) -> ModelType:
        if self.model:
            if callable(self.model):
                return self.model(context)
            return self.model

        if self.model_key:
            return context.get(self.model_key)

        return None


@dataclass
class InstanceBreadcrumbItem(BaseBreadcrumbItem):
    """
    Breadcrumb via object instance from context.

    Detail url for object instance taken from context. By default, `instance_key` is set to `object`.
    Label will be generated from object, but you can still override it.

    Attributes:
        instance_key (Optional[str]): Context key to fetch a Django model instance for building the breadcrumb. Default: "object".
        instance (Union[Callable[[Context], Optional[Model]], Model, None]): Callable to fetch the instance from context. If
        should_render (Callable[[Context], bool]): Callable to decide whether this item should be rendered or not.
        label (Union[Callable[[Context], str], WithStr, None]): Optional override for the display label in the breadcrumb.
        label_key (Optional[str]): Optional key to take label from the context.

    Examples:
        >>> InstanceBreadcrumbItem()
        ("/dcim/devices/1234", "My Device")  # Assuming that under "object" there is a Device instance
        >>> InstanceBreadcrumbItem(label="Custom Device Label")
        ("/dcim/devices/1234", "Custom Device Label")  # Assuming that under "object" there is a Device instance
    """

    instance_key: Optional[str] = "object"
    instance: Union[Callable[[Context], Optional[Model]], Model, None] = None
    label: Union[Callable[[Context], str], WithStr, None] = None

    def get_url(self, context: Context) -> Optional[str]:
        """
        Resolve the URL for the breadcrumb item based on the instance.

        Args:
            context (Context): The current template context.

        Returns:
            Optional[str]: The URL as a string, or None.
        """
        instance = self.get_instance(context)
        return get_absolute_url(instance) if instance else None

    def get_label(self, context: Context) -> str:
        """
        Get the label (display text) for the breadcrumb from instance.

        Args:
            context (Context): The current template context.

        Returns:
            str: Label as a string.
        """
        if self.label or self.label_key:
            return super().get_label(context)
        instance = self.get_instance(context)
        if not instance:
            return ""
        return getattr(instance, "page_title", str(instance))

    def get_instance(self, context: Context) -> Optional[Model]:
        """
        Get the instance depending on the settings.

        Args:
            context (Context): The current template context.

        Returns:
            Optional[Model]: Instance from context.
        """
        if self.instance:
            if callable(self.instance):
                return self.instance(context)
            return self.instance

        if self.instance_key:
            return context.get(self.instance_key)

        return None


@dataclass
class InstanceParentBreadcrumbItem(InstanceBreadcrumbItem):
    """
    Breadcrumb item prepared to be "parent" or "group" of given model.

    It will create a breadcrumb item to the object list but will try to filter it by given parent.

    Attributes:
        parent_key (str): Instance attribute to get the parent instance. Default: "parent".
        parent (Optional[Model]): Instance or related object (parent).
        parent_query_param (Optional[str]): Query param name under which parent lookup key will be added into breadcrumb url. If None, will be the same as `parent_key`.
        parent_lookup_key (Optional[str]): Parent attribute which will be used to build the url and filter the instance list url. Can be set to None to use parent as key.

    Examples:
        >>> InstanceParentBreadcrumbItem()
        ("/dcim/devices?parent=<parent.pk>", "Parent")  # Assuming that under "object" there is a Device instance and has "parent"
        >>> InstanceParentBreadcrumbItem(parent_key="group", parent_lookup_key="name")
        ("/dcim/devices?group=<group_name>", "Group")  # Assuming that under "object" there is a Device instance and has "group"
    """

    parent_key: str = "parent"
    parent: Optional[Model] = None
    parent_query_param: Optional[str] = None
    parent_lookup_key: Optional[str] = "pk"

    def __post_init__(self):
        """
        Set `parent_query_param` if not filled.
        """
        if self.parent_query_param is None:
            self.parent_query_param = self.parent_key

    def get_url(self, context: Context) -> Optional[str]:
        """
        Resolve the URL for the breadcrumb item based on the instance and provided parent.

        Args:
            context (Context): The current template context.

        Returns:
            Optional[str]: The URL as a string, or None.
        """
        instance = self.get_instance(context)
        related_object = self.get_related_object(instance)
        if not instance or not related_object:
            return None

        view_name = lookup.get_route_for_model(instance, "list")
        return self.reverse_view_name(
            view_name, context, reverse_query_params=self.get_reverse_query_params(related_object)
        )

    def get_label(self, context: Context) -> str:
        """
        Get the label (display text) for the breadcrumb from instance and provided parent.

        Args:
            context (Context): The current template context.

        Returns:
            str: Label as a string.
        """
        if self.label or self.label_key:
            return super().get_label(context)
        instance = self.get_instance(context)
        related_object = self.get_related_object(instance)
        if not instance or not related_object:
            return ""
        return getattr(related_object, "page_title", str(related_object))

    def get_reverse_query_params(self, parent: Model) -> Optional[dict]:
        if self.parent_lookup_key is None:
            return {self.parent_query_param: parent}

        if hasattr(parent, self.parent_lookup_key):
            if query_param := getattr(parent, self.parent_lookup_key):
                return {self.parent_query_param: query_param}
        return {}

    def get_related_object(self, instance: Model) -> Optional[Model]:
        if self.parent:
            return self.parent

        if hasattr(instance, self.parent_key):
            return getattr(instance, self.parent_key) or None

        return None


@dataclass
class AncestorsInstanceBreadcrumbItem(InstanceBreadcrumbItem):
    """
    Item class which can render list of ancestors of given instance.

    By default, it won't include itself.

    Attributes:
        include_self (bool): Whether to include self as last item of ancestors.

    Examples:
        >>> AncestorsInstanceBreadcrumbItem(instance=location)
        ("/dcim/locations/<pk>", "Parent 2"), ("/dcim/locations/<pk>", "Parent 1")
        >>> AncestorsInstanceBreadcrumbItem(instance=location, include_self=True)
        ("/dcim/locations/<pk>", "Parent 2"), ("/dcim/locations/<pk>", "Parent 1"), ("/dcim/locations/<pk>", "Location")
    """

    ancestor_item: Callable[[Model], BaseBreadcrumbItem] = lambda instance: InstanceBreadcrumbItem(instance=instance)
    include_self: bool = False

    def as_pair(self, context: Context) -> Iterator[tuple[str, str]]:
        """
        Construct the (URL, label) pair for the breadcrumb with all the instance ancestors.

        Creates separate `InstanceBreadcrumbItem` with copied data from self.

        Args:
            context (Context): Context object used to resolve the breadcrumb parts.

        Returns:
            Iterator[tuple[str, Optional[str]]]: A tuple of (URL, label), where URL may be an empty string
            if unresolved, and label.
        """
        instance = self.get_instance(context)

        for ancestor in instance.ancestors():
            yield from self.ancestor_item(ancestor).as_pair(context)

        if self.include_self:
            yield from self.ancestor_item(instance).as_pair(context)


class Breadcrumbs:
    """
    Base class responsible for generating and rendering breadcrumbs for a page.

    This class supports flexible breadcrumb configuration through:
    - `items`: Default breadcrumb items per view action.

    You can add more information to the breadcrumbs trail by passing appropriate
    `BreadcrumbItem` objects grouped by view action (e.g., "*", "list", "add", "edit").

    Special breadcrumb item actions:
         - `*` - if no other action was found, items from `*` will be used
         - `detail` action is used when there is no dedicated action for given request
         and there is `context['detail'] = True` set in context

    !!! important
        If you're using custom action other than `list` / `detail` you need to remember to add list view breadcrumb manually
        if you need them in your custom action.

    Attributes:
        template (str): Path to the template used to render the breadcrumb component.
        items (dict[str, list[BreadcrumbItem]]): Default breadcrumb items per view action.
    """

    breadcrumb_items: list[BaseBreadcrumbItem] = [
        # Default breadcrumb if view defines `list_url` in the Context
        ViewNameBreadcrumbItem(
            view_name_key="list_url",
            label_key="title",
            label_from_view_name=True,
            should_render=lambda context: context.get("list_url") is not None,
        ),
        # Fallback if there is no `list_url` in the Context
        ModelBreadcrumbItem(model_key="model", should_render=lambda context: context.get("list_url") is None),
    ]

    def __init__(
        self,
        items: BreadcrumbItemsType = None,
        template: str = "components/breadcrumbs.html",
        detail_item_label: LabelType = None,
    ):
        """
        Initialize the Breadcrumbs configuration.

        Args:
            items (Optional[dict[str, list[BreadcrumbItem]]]): Default breadcrumb items for each action.
            template (str): The template used to render the breadcrumbs.
            detail_item_label (Union[Callable[[Context], str], WithStr, None]): Custom label for last built-in breadcrumb item with link to the object details.
        """
        self.template = template
        self.detail_item_label = detail_item_label

        # Set the default breadcrumbs
        self.items = {
            "list": [],
            "detail": [*self.breadcrumb_items],
        }

        # If custom items are present, merge with defaults
        if items:
            self.items = {**self.items, **items}

    def get_breadcrumbs_items(self, context: Context) -> list[tuple[str, str]]:
        """
        Compute the list of breadcrumb items for the given context.

        Items are determined based on the `view_action` in context.

        Args:
            context (Context): The view or template context that holds `view_action` and related state.

        Returns:
            (list[tuple[str, str]]): A list of (url, label) tuples representing breadcrumb entries.
        """
        action = context.get("view_action", "")
        detail = context.get("detail", False)
        items = self.get_items_for_action(self.items, action, detail, context)
        items_pairs = [item.as_pair(context) for item in items if item.should_render(context)]
        return list(chain.from_iterable(items_pairs))

    def filter_breadcrumbs_items(self, items: list[tuple[str, str]], context: Context) -> list[tuple[str, str]]:
        """
        Filters out all items that both label and url are None or empty str.

        Args:
            items (list[tuple[str, str]]): breadcrumb items pairs.
            context (Context): The view or template context.

        Returns:
            (list[tuple[str, str]]): A list of filtered breadcrumb items pairs.
        """
        return [(url, label) for url, label in items if self.is_label_not_blank(label)]

    @staticmethod
    def is_label_not_blank(label: str) -> bool:
        """
        Check if label is not empty (only whitespace) or None.

        Args:
            label (str): The label to check.

        Returns:
            (bool): True if label is not None or empty (only whitespace), False otherwise.
        """
        return label and label.strip()

    def get_items_for_action(
        self, items: BreadcrumbItemsType, action: str, detail: bool, context: Context
    ) -> list[BaseBreadcrumbItem]:
        """
        Get the breadcrumb items for a specific action, 'detail' or to asterisk (*) if present.

        Args:
            items (BreadcrumbItemsType): Dictionary mapping action names to breadcrumb item lists.
            action (str): Current action name (e.g., "list", "detail").
            detail (bool): Whether this is a detail view (for fallback).
            context (Context): The view or template context.

        Returns:
            list[BaseBreadcrumbItem]: List of breadcrumb items for the action.
        """
        breadcrumbs_list = items.get(action, [])
        if breadcrumbs_list:
            return breadcrumbs_list

        if detail:
            return items.get("detail", [])

        return items.get("*", [])

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
            filtered_items = self.filter_breadcrumbs_items(breadcrumbs_items, context)
            return render_component_template(self.template, context, breadcrumbs_items=filtered_items)

    def get_extra_context(self, context: Context):
        """
        Provide additional data to include in the rendering context, based on the configuration of this component.

        Context updated here will be applied to resolving url and labels.
        Please note that you can't override `breadcrumb_items` here because items are generated after this method call.

        Args:
            context (Context): The current context passed to `render()`.

        Returns:
            (dict): A dictionary of extra context variables.
        """
        return {}


@deprecation.class_deprecated("Functionality of this class was moved to the AncestorsInstanceBreadcrumbItem.")
class AncestorsBreadcrumbs(Breadcrumbs):
    """
    Breadcrumbs class which can render list of ancestors of given instance.

    Default behavior:
    - render breadcrumb item with link to the list view
    - dynamically add list of `InstanceBreadcrumbItem` from `ancestors()`
    """

    def get_items_for_action(
        self, items: BreadcrumbItemsType, action: str, detail: bool, context: Context
    ) -> list[BaseBreadcrumbItem]:
        """
        Get the breadcrumb items for a specific action, 'detail' or to asterisk (*) if present.

        For detail action it calls `self.get_detail_items()` method. For other actions, it calls parent class method.

        Args:
            items (BreadcrumbItemsType): Dictionary mapping action names to breadcrumb item lists.
            action (str): Current action name (e.g., "list", "detail").
            detail (bool): Whether this is a detail view (for fallback).
            context (Context): The view or template context.

        Returns:
            list[BaseBreadcrumbItem]: List of breadcrumb items for the action.
        """
        if not detail:
            return super().get_items_for_action(items, action, detail, context)

        return self.get_detail_items(context)

    def get_detail_items(self, context: Context) -> list[BaseBreadcrumbItem]:
        """
        Build breadcrumb items for a detail view, including the model, its ancestors, and the instance itself.

        Args:
            context (Context): Template or view context containing the current object.

        Returns:
            list[BaseBreadcrumbItem]: Ordered breadcrumb items for the given instance.
        """
        instance = get_obj_from_context(context)
        return [
            ModelBreadcrumbItem(model=instance),
            *self.get_ancestors_items(instance),
        ]

    def get_ancestors_items(self, instance: TreeModel) -> list[BaseBreadcrumbItem]:
        """
        Create breadcrumb items for all ancestor objects of the given instance.

        Args:
            instance (TreeModel): Object from context.

        Returns:
            list[BaseBreadcrumbItem]: Breadcrumb items for each ancestor of the instance.
        """
        return [InstanceBreadcrumbItem(instance=ancestor, label=ancestor.name) for ancestor in instance.ancestors()]
