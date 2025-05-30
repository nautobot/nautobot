import collections
from functools import partial
from importlib import import_module
import inspect
from logging import getLogger

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.loader import get_template
from django.urls import get_resolver, URLPattern
from packaging import version

from nautobot.core.apps import (
    NautobotConfig,
    NavMenuTab,
    register_homepage_panels,
    register_menu_items,
)
from nautobot.core.signals import nautobot_database_ready
from nautobot.core.utils.deprecation import class_deprecated_in_favor_of
from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins.exceptions import PluginImproperlyConfigured
from nautobot.extras.plugins.utils import import_object
from nautobot.extras.registry import register_datasource_contents, registry
from nautobot.extras.secrets import register_secrets_provider

logger = getLogger(__name__)

# Initialize plugin registry stores
# registry["datasource_content"], registry["secrets_providers"] are not plugin-exclusive; initialized in extras.registry
registry["plugin_banners"] = []
registry["plugin_custom_validators"] = collections.defaultdict(list)
registry["plugin_graphql_types"] = []
registry["plugin_template_extensions"] = collections.defaultdict(list)
registry["app_metrics"] = []


#
# Plugin AppConfig class
#


class NautobotAppConfig(NautobotConfig):
    """
    Subclass of Django's built-in AppConfig class, to be used for Nautobot plugins.
    """

    default = True

    # Plugin metadata
    author = ""
    author_email = ""
    description = ""
    version = ""

    # Root URL path under /plugins. If not set, the plugin's label will be used.
    base_url = None

    # Minimum/maximum compatible versions of Nautobot
    min_version = None
    max_version = None

    # Default configuration parameters
    default_settings = {}

    # Mandatory configuration parameters
    required_settings = []

    # Middleware classes provided by the plugin
    middleware = []

    # Extra installed apps provided or required by the plugin. These will be registered
    # along with the plugin.
    installed_apps = []

    # Default constance configuration parameters
    constance_config = {}

    # URL reverse lookup names, a la "plugins:myplugin:home", "plugins:myplugin:configure", "plugins:myplugin:docs"
    home_view_name = None
    config_view_name = None
    docs_view_name = None

    # Default integration paths. Plugin authors can override these to customize the paths to
    # integrated components.
    banner_function = "banner.banner"
    custom_validators = "custom_validators.custom_validators"
    datasource_contents = "datasources.datasource_contents"
    filter_extensions = "filter_extensions.filter_extensions"
    graphql_types = "graphql.types.graphql_types"
    homepage_layout = "homepage.layout"
    jinja_filters = "jinja_filters"
    jobs = "jobs.jobs"
    metrics = "metrics.metrics"
    menu_items = "navigation.menu_items"
    secrets_providers = "secrets.secrets_providers"
    table_extensions = "table_extensions.table_extensions"
    template_extensions = "template_content.template_extensions"
    override_views = "views.override_views"

    def ready(self):
        """Callback after plugin app is loaded."""
        # We don't call super().ready here because we don't need or use the on-ready behavior of a core Nautobot app

        # Introspect URL patterns and models to make available to the installed-plugins detail UI view.
        urlpatterns = import_object(f"{self.__module__}.urls.urlpatterns")
        api_urlpatterns = import_object(f"{self.__module__}.api.urls.urlpatterns")

        self.features = {
            "api_urlpatterns": sorted(
                (urlp for urlp in (api_urlpatterns or []) if isinstance(urlp, URLPattern)),
                key=lambda urlp: (urlp.name, str(urlp.pattern)),
            ),
            "models": sorted(model._meta.verbose_name for model in self.get_models()),
            "urlpatterns": sorted(
                (urlp for urlp in (urlpatterns or []) if isinstance(urlp, URLPattern)),
                key=lambda urlp: (urlp.name, str(urlp.pattern)),
            ),
            "constance_config": self.constance_config,
        }

        # Register banner function (if defined)
        banner_function = import_object(f"{self.__module__}.{self.banner_function}")
        if banner_function is not None:
            register_banner_function(banner_function)
            self.features["banner"] = True

        # Register model validators (if defined)
        validators = import_object(f"{self.__module__}.{self.custom_validators}")
        if validators is not None:
            register_custom_validators(validators)
            self.features["custom_validators"] = sorted(set(validator.model for validator in validators))

        # Register datasource contents (if defined)
        datasource_contents = import_object(f"{self.__module__}.{self.datasource_contents}")
        if datasource_contents is not None:
            register_datasource_contents(datasource_contents)
            self.features["datasource_contents"] = datasource_contents

        # Register GraphQL types (if defined)
        graphql_types = import_object(f"{self.__module__}.{self.graphql_types}")
        if graphql_types is not None:
            register_graphql_types(graphql_types)

        # Import jobs (if present)
        # Note that we do *not* auto-call `register_jobs()` - the App is responsible for doing so when imported.
        jobs = import_object(f"{self.__module__}.{self.jobs}")
        if jobs is not None:
            self.features["jobs"] = jobs

        # Import metrics (if present)
        metrics = import_object(f"{self.__module__}.{self.metrics}")
        if metrics is not None and self.name not in settings.METRICS_DISABLED_APPS:
            register_metrics(metrics)
            self.features["metrics"] = []  # Initialize as empty, to be filled by the signal handler
            # Inject the metrics to discover into the signal handler.
            signal_callback = partial(discover_metrics, metrics=metrics)
            nautobot_database_ready.connect(signal_callback, sender=self)

        # Register plugin navigation menu items (if defined)
        menu_items = import_object(f"{self.__module__}.{self.menu_items}")
        if menu_items is not None:
            register_plugin_menu_items(self.verbose_name, menu_items)
            self.features["nav_menu"] = menu_items

        homepage_layout = import_object(f"{self.__module__}.{self.homepage_layout}")
        if homepage_layout is not None:
            register_homepage_panels(self.path, self.label, homepage_layout)
            self.features["home_page"] = homepage_layout

        # Register template content (if defined)
        template_extensions = import_object(f"{self.__module__}.{self.template_extensions}")
        if template_extensions is not None:
            register_template_extensions(template_extensions)
            self.features["template_extensions"] = sorted(set(extension.model for extension in template_extensions))

        # Register custom jinja filters
        try:
            import_module(f"{self.__module__}.{self.jinja_filters}")
            self.features["jinja_filters"] = True
        except ModuleNotFoundError:
            pass

        # Register secrets providers (if any)
        secrets_providers = import_object(f"{self.__module__}.{self.secrets_providers}")
        if secrets_providers is not None:
            for secrets_provider in secrets_providers:
                register_secrets_provider(secrets_provider)
            self.features["secrets_providers"] = secrets_providers

        # Register custom filters (if any)
        filter_extensions = import_object(f"{self.__module__}.{self.filter_extensions}")
        if filter_extensions is not None:
            register_filter_extensions(filter_extensions, self.name)
            self.features["filter_extensions"] = {"filterset_fields": [], "filterform_fields": []}
            for filter_extension in filter_extensions:
                for filterset_field_name in filter_extension.filterset_fields.keys():
                    self.features["filter_extensions"]["filterset_fields"].append(
                        f"{filter_extension.model} -> {filterset_field_name}"
                    )
                for filterform_field_name in filter_extension.filterform_fields.keys():
                    self.features["filter_extensions"]["filterform_fields"].append(
                        f"{filter_extension.model} -> {filterform_field_name}"
                    )

        # Register override view (if any)
        override_views = import_object(f"{self.__module__}.{self.override_views}")
        if override_views is not None:
            for qualified_view_name, view in override_views.items():
                view_class_name = view.view_class.__name__ if hasattr(view, "view_class") else view.cls.__name__
                self.features.setdefault("overridden_views", []).append(
                    (qualified_view_name, f"{view.__module__}.{view_class_name}")
                )
            register_override_views(override_views, self.name)

        # Register tables extensions (if any).
        self._register_table_extensions()

    @classmethod
    def validate(cls, user_config, nautobot_version):
        """Validate the user_config for baseline correctness."""

        plugin_name = cls.__module__

        # Enforce version constraints
        current_version = version.parse(nautobot_version)
        if cls.min_version is not None:
            min_version = version.parse(cls.min_version)
            if current_version < min_version:
                raise PluginImproperlyConfigured(
                    f"Plugin {plugin_name} requires Nautobot minimum version {cls.min_version}"
                )
        if cls.max_version is not None:
            max_version = version.parse(cls.max_version)
            if current_version > max_version:
                raise PluginImproperlyConfigured(
                    f"Plugin {plugin_name} requires Nautobot maximum version {cls.max_version}"
                )

        # Mapping of {setting_name: setting_type} used to validate user configs
        # TODO(jathan): This is fine for now, but as we expand the functionality
        # of plugins, we'll need to consider something like pydantic or attrs.
        setting_validations = {
            "default_settings": dict,
            "installed_apps": list,
            "middleware": list,
            "required_settings": list,
        }

        # Validate user settings
        for setting_name, setting_type in setting_validations.items():
            if not isinstance(getattr(cls, setting_name), setting_type):
                raise PluginImproperlyConfigured(f"Plugin {plugin_name} {setting_name} must be a {setting_type}")

        # Validate the required_settings
        for setting in cls.required_settings:
            if setting not in user_config:
                raise PluginImproperlyConfigured(
                    f"Plugin {plugin_name} requires '{setting}' to be present in "
                    f"the PLUGINS_CONFIG['{plugin_name}'] section of your settings."
                )

        # Apply default configuration values
        for setting, value in cls.default_settings.items():
            # user_config and constance_config take precedence
            # this is to support legacy apps that supply default_settings and constance_config
            if setting not in user_config and setting not in cls.constance_config:
                user_config[setting] = value

    def _register_table_extensions(self):
        """Register tables extensions (if any)."""
        table_extensions = import_object(f"{self.__module__}.{self.table_extensions}")
        if table_extensions is not None:
            register_table_extensions(table_extensions, self.name)
            self.features["table_extensions"] = get_table_extension_features(table_extensions)


@class_deprecated_in_favor_of(NautobotAppConfig)
class PluginConfig(NautobotAppConfig):
    pass


#
# Template content injection
#


class TemplateExtension:
    """
    This class is used to register App content to be injected into core Nautobot templates.

    It contains methods and attributes that may be overridden by App authors to return template content.

    The `model` attribute on the class defines the which model detail/list pages this class renders content for.
    It should be set as a string in the form `<app_label>.<model_name>`.
    """

    model: str = None
    """The model (as a string in the form `<app_label>.<model>`) that this TemplateExtension subclass applies to."""
    object_detail_buttons = None
    """List of Button instances to add to the specified model's detail view."""
    object_detail_tabs = None
    """List of Tab instances to add to the specified model's detail view."""
    object_detail_panels = None
    """List of Panel instances to add to the specified model's detail view."""

    def __init__(self, context):
        """
        Called automatically to instantiate a TemplateExtension with render context before calling `left_page()`, etc.

        The provided context typically includes the following keys:

        * object - The object being viewed
        * request - The current request
        * settings - Global Nautobot settings
        * config - App-specific configuration parameters
        """
        self.context = context

    def render(self, template_name, extra_context=None):
        """
        Convenience method for rendering the specified Django template using the default context data. An additional
        context dictionary may be passed as `extra_context`.
        """
        if extra_context is None:
            extra_context = {}
        elif not isinstance(extra_context, dict):
            raise TypeError("extra_context must be a dictionary")

        return get_template(template_name).render({**self.context, **extra_context})

    def left_page(self):
        """
        (Deprecated) Provide content that will be rendered on the left of the detail page view.

        In Nautobot v2.4.0 and later, Apps can (should) instead register `Panel` instances in `object_detail_panels`,
        instead of implementing a `.left_page()` method.

        Content should be returned as an HTML string.
        Note that content does not need to be marked as safe because this is automatically handled.
        """
        raise NotImplementedError

    def right_page(self):
        """
        (Deprecated) Provide content that will be rendered on the right of the detail page view.

        In Nautobot v2.4.0 and later, Apps can (should) instead register `Panel` instances in `object_detail_panels`,
        instead of implementing a `.right_page()` method.

        Content should be returned as an HTML string.
        Note that content does not need to be marked as safe because this is automatically handled.
        """
        raise NotImplementedError

    def full_width_page(self):
        """
        (Deprecated) Provide content that will be rendered within the full width of the detail page view.

        In Nautobot v2.4.0 and later, Apps can (should) instead register `Panel` instances in `object_detail_panels`,
        instead of implementing a `.full_width_page()` method.

        Content should be returned as an HTML string.
        Note that content does not need to be marked as safe because this is automatically handled.
        """
        raise NotImplementedError

    def buttons(self):
        """
        (Deprecated) Provide content that will be added to the existing list of buttons on the detail page view.

        In Nautobot v2.4.0 and later, Apps can (should) instead register `Button` instances in `object_detail_buttons`,
        instead of implementing a `.buttons()` method.

        Content should be returned as an HTML string.
        Note that content does not need to be marked as safe because this is automatically handled.
        """
        raise NotImplementedError

    def list_buttons(self):
        """
        Buttons that will be rendered and added to the existing list of buttons on the list page view. Content
        should be returned as an HTML string. Note that content does not need to be marked as safe because this is
        automatically handled.
        """
        raise NotImplementedError

    def detail_tabs(self):
        """
        (Deprecated) Provide a dict of tabs and associated views that will be added to the detail page view.

        In Nautobot v2.4.0 and later, Apps can (should) instead implement the `object_detail_tabs` attribute instead.

        Tabs will be ordered by their position in the list.

        Content should be returned as a list of dicts in the following format:
        ```
        [
            {
                "title": "<title>",
                "url": "<url for the tab link>",
            },
            {
                "title": "<title>",
                "url": "<url for the tab link>",
            },
        ]
        ```
        """
        raise NotImplementedError


@class_deprecated_in_favor_of(TemplateExtension)
class PluginTemplateExtension(TemplateExtension):
    pass


def register_template_extensions(class_list):
    """
    Register a list of TemplateExtension classes
    """
    # Validation
    for template_extension in class_list:
        if not inspect.isclass(template_extension):
            raise TypeError(f"TemplateExtension class {template_extension} was passed as an instance!")
        if not issubclass(template_extension, TemplateExtension):
            raise TypeError(f"{template_extension} is not a subclass of nautobot.apps.ui.TemplateExtension!")
        if template_extension.model is None:
            raise TypeError(f"TemplateExtension class {template_extension} does not define a valid model!")

        registry["plugin_template_extensions"][template_extension.model].append(template_extension)


class Banner:
    """Class that may be returned by a registered plugin_banners function."""

    def __init__(self, content, banner_class=BannerClassChoices.CLASS_INFO):
        self.content = content
        if banner_class not in BannerClassChoices.values():
            raise ValueError("Banner class must be a choice within BannerClassChoices.")
        self.banner_class = banner_class


@class_deprecated_in_favor_of(Banner)
class PluginBanner(Banner):
    pass


def register_banner_function(function):
    """
    Register a function that may return a Banner object.
    """
    registry["plugin_banners"].append(function)


def register_graphql_types(class_list):
    """
    Register a list of DjangoObjectType classes
    """
    # Validation
    from graphene_django import DjangoObjectType

    for item in class_list:
        if not inspect.isclass(item):
            raise TypeError(f"DjangoObjectType class {item} was passed as an instance!")
        if not issubclass(item, DjangoObjectType):
            raise TypeError(f"{item} is not a subclass of graphene_django.DjangoObjectType!")
        if item._meta.model is None:
            raise TypeError(f"DjangoObjectType class {item} does not define a valid model!")

        registry["plugin_graphql_types"].append(item)


def register_metrics(function_list):
    """
    Register a list of metric functions
    """
    for metric in function_list:
        if not callable(metric):
            raise TypeError(f"{metric} is not a callable.")
        registry["app_metrics"].append(metric)


class FilterExtension:
    """Class that may be returned by a registered Filter Extension function."""

    model = None

    filterset_fields = {}

    filterform_fields = {}


@class_deprecated_in_favor_of(FilterExtension)
class PluginFilterExtension(FilterExtension):
    pass


def register_filter_extensions(filter_extensions, plugin_name):
    """
    Register a list of FilterExtension classes
    """
    from nautobot.core.forms.utils import add_field_to_filter_form_class
    from nautobot.core.utils.lookup import get_filterset_for_model, get_form_for_model

    for filter_extension in filter_extensions:
        if not issubclass(filter_extension, FilterExtension):
            raise TypeError(f"{filter_extension} is not a subclass of nautobot.apps.filters.FilterExtension!")
        if filter_extension.model is None:
            raise TypeError(f"FilterExtension class {filter_extension} does not define a valid model!")

        model_filterset_class = get_filterset_for_model(filter_extension.model)
        model_filterform_class = get_form_for_model(filter_extension.model, "Filter")

        for new_filterset_field_name, new_filterset_field in filter_extension.filterset_fields.items():
            if not new_filterset_field_name.startswith(f"{plugin_name}_"):
                raise ValueError(
                    f"Attempted to create a custom filter `{new_filterset_field_name}` that did not start with `{plugin_name}`"
                )

            try:
                model_filterset_class.add_filter(new_filterset_field_name, new_filterset_field)
            except AttributeError:
                logger.error(
                    f"There was a conflict with filter set field `{new_filterset_field_name}`, the custom filter set field was ignored."
                )

        for new_filterform_field_name, new_filterform_field in filter_extension.filterform_fields.items():
            try:
                add_field_to_filter_form_class(
                    form_class=model_filterform_class,
                    field_name=new_filterform_field_name,
                    field_obj=new_filterform_field,
                )
            except AttributeError:
                logger.error(
                    f"There was a conflict with filter form field `{new_filterform_field_name}`, the custom filter form field was ignored."
                )


#
# Table Extensions
#


class TableExtension:
    """Template class for extending Tables.

    An app can override the default columns for a table by either:
    - Extending the original default columns to include custom columns.
        - add_to_default_columns = ("my_app_name_new_column",)
    - Removing native columns from the default columns.
        - remove_from_default_columns = ("tenant",)
    """

    model = None
    suffix = None
    table_columns = {}
    add_to_default_columns = ()
    remove_from_default_columns = ()

    @classmethod
    def alter_queryset(cls, queryset):
        """Alter the View class QuerySet.

        This is a good place to add `prefetch_related` to the view queryset.
        example:
            return queryset.prefetch_related("my_model_set")
        """
        return queryset

    @classmethod
    def _get_table_columns_registrations(cls):
        """Return a list of register labels fro each column."""
        if not cls.table_columns:
            return []
        return [f"{cls.model} -> {column_name}" for column_name in cls.table_columns]

    @classmethod
    def _get_add_to_default_columns_registrations(cls):
        """Return a list of register labels for each column added to defaults."""
        if not cls.add_to_default_columns:
            return []
        return [f"{cls.model} -> {cls.add_to_default_columns}"]

    @classmethod
    def _get_remove_from_default_columns_registrations(cls):
        """Return a list of register labels for each column removed from defaults."""
        if not cls.remove_from_default_columns:
            return []
        return [f"{cls.model} -> {cls.remove_from_default_columns}"]


def get_table_extension_features(table_extensions):
    """Return a dictionary of TableExtension features for the App detail view."""
    return {
        "columns": [
            label
            for table_extension in table_extensions
            for label in table_extension._get_table_columns_registrations()
        ],
        "add_to_default_columns": [
            label
            for table_extension in table_extensions
            for label in table_extension._get_add_to_default_columns_registrations()
        ],
        "remove_from_default_columns": [
            label
            for table_extension in table_extensions
            for label in table_extension._get_remove_from_default_columns_registrations()
        ],
    }


def register_table_extensions(table_extensions, app_name):
    """Register a list of TableExtension classes."""
    for table_extension in table_extensions:
        _validate_is_subclass_of_table_extension(table_extension)
        _add_columns_into_model_table(table_extension, app_name)
        _modify_default_table_columns(table_extension, app_name)
        _alter_table_view_queryset(table_extension, app_name)


def _add_columns_into_model_table(table_extension, app_name):
    """Inject each new column into the Model Table."""
    from nautobot.core.utils.lookup import get_table_for_model

    if not isinstance(table_extension.table_columns, dict):
        error = f"{app_name} TableExtension: 'table_columns' attribute must be of type 'dict'."
        logger.error(error)
        return

    table = get_table_for_model(table_extension.model, suffix=table_extension.suffix)
    for name, column in table_extension.table_columns.items():
        _validate_table_column_name_is_prefixed_with_app_name(name, app_name)
        _add_column_to_table_base_columns(table, name, column, app_name)


def _add_column_to_table_base_columns(table, column_name, column, app_name):
    """Attach a column to an existing table."""
    import django_tables2

    if not isinstance(column, django_tables2.Column):
        raise TypeError(f"Custom column `{column_name}` is not an instance of django_tables2.Column.")

    if column_name in table.base_columns:
        logger.error(
            f"{app_name}: There was a name conflict with existing table column `{column_name}`, the custom column was ignored."
        )
    else:
        table.base_columns[column_name] = column


def _alter_table_view_queryset(table_extension, app_name):
    """Replace the model view queryset with an optimized queryset from the app."""
    from nautobot.core.utils.lookup import get_view_for_model

    # TODO: Investigate if there is a more targeted way to patch only the list view queryset
    # when targeting a subclass of `NautobotUIViewSet`.
    view = get_view_for_model(table_extension.model, view_type="List")
    view.queryset = table_extension.alter_queryset(view.queryset)


def _modify_default_table_columns(table_extension, app_name):
    """Add or remove columns from the table default columns."""
    from nautobot.core.utils.lookup import get_table_for_model

    table = get_table_for_model(table_extension.model, suffix=table_extension.suffix)
    message = (
        f"{app_name}: Cannot {{action}} column `{{column_name}}` {{preposition}} the default columns for `{table}`."
    )

    for column_name in table_extension.add_to_default_columns:
        if not getattr(table.Meta, "default_columns", None):
            logger.warning(
                f"{app_name}: Table `{table}` does not have a `default_columns` attribute. Cannot add column: {column_name}."
            )
            continue
        if column_name in table.base_columns:
            table.Meta.default_columns = (*table.Meta.default_columns, column_name)
        else:
            logger.debug(message.format(action="add", column_name=column_name, preposition="to"))

    for column_name in table_extension.remove_from_default_columns:
        if not getattr(table.Meta, "default_columns", None):
            logger.warning(
                f"{app_name}: Table `{table}` does not have a `default_columns` attribute. Cannot remove column: {column_name}."
            )
            continue
        if column_name in table.Meta.default_columns:
            table.Meta.default_columns = tuple(name for name in table.Meta.default_columns if name != column_name)
        else:
            logger.debug(message.format(action="remove", column_name=column_name, preposition="from"))


def _validate_is_subclass_of_table_extension(table_extension):
    if not issubclass(table_extension, TableExtension):
        raise TypeError(f"{table_extension} is not a subclass of nautobot.apps.filters.TableExtension!")


def _validate_table_column_name_is_prefixed_with_app_name(name, app_name):
    if not name.startswith(f"{app_name}_"):
        raise ValueError(f"Attempted to create a custom table column `{name}` that did not start with `{app_name}`")


#
# Navigation menu links
#


def register_plugin_menu_items(section_name, menu_items):
    """
    Register a list of NavMenuTab instances for a given menu section (e.g. plugin name)
    """
    nav_menu_items = set()

    for menu_item in menu_items:
        if isinstance(menu_item, NavMenuTab):
            nav_menu_items.add(menu_item)
        else:
            raise TypeError(f"Top level objects need to be an instance of NavMenuTab: {menu_item}")

    register_menu_items(nav_menu_items)


#
# Model Validators
#


class CustomValidatorContext(dict):
    def __init__(self, obj):
        """
        If there is an active change context, meaning we are in a web request context,
        we have access to the current user object. Otherwise, we are likely running inside
        a management command or other non-web or non-Job context, and we should use an AnonymousUser.
        This ensures people's custom validators don't outright break when running in non-web
        contexts, and should generally provide a sane default, given validation based on the
        user is commonly going to be least-privelege based, and thus the AnonymousUser will
        cause such validation logic to fail closed.
        """
        from django.contrib.auth.models import AnonymousUser

        from nautobot.extras.signals import change_context_state

        change_context = change_context_state.get()
        user = None
        if change_context:
            user = change_context.get_user()
        if user is None:
            user = AnonymousUser()

        super().__init__(object=obj, user=user)


class CustomValidator:
    """
    This class is used to register plugin custom model validators which act on specified models. It contains the clean
    method which is overridden by plugin authors to execute custom validation logic. Plugin authors must raise
    ValidationError within this method to trigger validation error messages which are propagated to the user.
    A convenience method `validation_error(<message>)` may be used for this purpose.

    The `model` attribute on the class defines the model to which this validator is registered. It
    should be set as a string in the form `<app_label>.<model_name>`.
    """

    model = None

    def __init__(self, obj):
        self.context = CustomValidatorContext(obj)

    def validation_error(self, message):
        """
        Convenience method for raising `django.core.exceptions.ValidationError` which is required in order to
        trigger validation error messages which are propagated to the user.
        """
        raise ValidationError(message)

    def clean(self):
        """
        Implement custom model validation in the standard Django clean method pattern. The model instance is accessed
        with the `object` key within `self.context`, e.g. `self.context['object']`. ValidationError must be raised to
        prevent saving model instance changes, and propagate messages to the user. For convenience,
        `self.validation_error(<message>)` may be called to raise a ValidationError.
        """
        raise NotImplementedError


@class_deprecated_in_favor_of(CustomValidator)
class PluginCustomValidator(CustomValidator):
    pass


def register_custom_validators(class_list):
    """
    Register a list of CustomValidator classes
    """
    # Validation
    for custom_validator in class_list:
        if not inspect.isclass(custom_validator):
            raise TypeError(f"CustomValidator class {custom_validator} was passed as an instance!")
        if not issubclass(custom_validator, CustomValidator):
            raise TypeError(f"{custom_validator} is not a subclass of nautobot.apps.models.CustomValidator!")
        if custom_validator.model is None:
            raise TypeError(f"CustomValidator class {custom_validator} does not define a valid model!")

        registry["plugin_custom_validators"][custom_validator.model].append(custom_validator)


def register_override_views(override_views, plugin):
    validation_error = (
        "Plugin '{}' tried to override view '{}' but did not contain a valid app name "
        "(e.g. `dcim:device`, `plugins:myplugin:myview`)."
    )

    for qualified_view_name, view in override_views.items():
        resolver = get_resolver()

        try:
            qualified_app_name, view_name = qualified_view_name.rsplit(":", 1)
            app_resolver = resolver
            for app_name in qualified_app_name.split(":"):
                app_resolver_tupl = app_resolver.namespace_dict.get(app_name)
                if app_resolver_tupl is None:
                    # We couldn't find the app, regardless of nesting
                    raise ValidationError(validation_error.format(plugin, qualified_view_name))

                app_resolver = app_resolver_tupl[1]

        except ValueError:
            # This is only thrown when qualified_view_name does not contain ":"
            raise ValidationError(validation_error.format(plugin, qualified_view_name))

        for pattern in app_resolver.url_patterns:
            if isinstance(pattern, URLPattern) and hasattr(pattern, "name") and pattern.name == view_name:
                pattern.callback = view


def discover_metrics(sender, *, apps, metrics, **kwargs):
    """
    Callback to discover metrics.

    This is necessary because we need to actually evaluate the metric generator fully to discover which metrics it
    provides. This allows us to give an accurate overview on the plugin detail page. However, because the metrics might
    import models themselves, they can only be run after migrations have taken place. This is ensured by connecting
    this signal handler to the nautobot_database_ready signal for each app.
    """
    if not metrics:
        return
    for metric in metrics:
        # Iterate over all the metric instances in this metric. This is done because a single callable might
        # return multiple metrics with different names. Note: If a metric is _always_ returned from its
        # callable, there would be inconsistency in the 'features' dict. This would however be a bad practice on
        # the metric definition side, as any metric that _could_ exist _should_ always also exist, even if set
        # to some initial value (ref: https://prometheus.io/docs/practices/instrumentation/#avoid-missing-metrics).
        for metric_instance in metric():
            sender.features["metrics"].append(metric_instance.name)
