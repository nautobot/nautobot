import collections
import inspect
from importlib import import_module
from logging import getLogger

from packaging import version

from django.core.exceptions import ValidationError
from django.template.loader import get_template
from django.urls import get_resolver, URLPattern

from nautobot.core.apps import (
    NautobotConfig,
    NavMenuButton,
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
    register_menu_items,
    register_homepage_panels,
)
from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.registry import registry, register_datasource_contents
from nautobot.extras.plugins.exceptions import PluginImproperlyConfigured
from nautobot.extras.plugins.utils import import_object
from nautobot.extras.secrets import register_secrets_provider
from nautobot.utilities.choices import ButtonColorChoices
from nautobot.utilities.deprecation import class_deprecated_in_favor_of

logger = getLogger(__name__)

# Initialize plugin registry stores
# registry["datasource_content"], registry["secrets_providers"] are not plugin-exclusive; initialized in extras.registry
registry["plugin_banners"] = []
registry["plugin_custom_validators"] = collections.defaultdict(list)
registry["plugin_graphql_types"] = []
registry["plugin_jobs"] = []
registry["plugin_template_extensions"] = collections.defaultdict(list)


#
# Plugin AppConfig class
#


class NautobotAppConfig(NautobotConfig):
    """
    Subclass of Django's built-in AppConfig class, to be used for Nautobot plugins.
    """

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

    # Cacheops configuration. Cache all operations by default.
    caching_config = {
        "*": {"ops": "all"},
    }

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
    menu_items = "navigation.menu_items"
    secrets_providers = "secrets.secrets_providers"
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
        jobs = import_object(f"{self.__module__}.{self.jobs}")
        if jobs is not None:
            register_jobs(jobs)
            self.features["jobs"] = jobs

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
                self.features.setdefault("overridden_views", []).append(
                    (qualified_view_name, f"{view.__module__}.{view.__name__}")
                )
            register_override_views(override_views, self.name)

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
            "caching_config": dict,
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
            if setting not in user_config:
                user_config[setting] = value


@class_deprecated_in_favor_of(NautobotAppConfig)
class PluginConfig(NautobotAppConfig):
    pass


#
# Template content injection
#


class TemplateExtension:
    """
    This class is used to register plugin content to be injected into core Nautobot templates. It contains methods
    that are overridden by plugin authors to return template content.

    The `model` attribute on the class defines the which model detail page this class renders content for. It
    should be set as a string in the form `<app_label>.<model_name>`. `render()` provides the following context data:

    * object - The object being viewed
    * request - The current request
    * settings - Global Nautobot settings
    * config - Plugin-specific configuration parameters
    """

    model = None

    def __init__(self, context):
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
        Content that will be rendered on the left of the detail page view. Content should be returned as an
        HTML string. Note that content does not need to be marked as safe because this is automatically handled.
        """
        raise NotImplementedError

    def right_page(self):
        """
        Content that will be rendered on the right of the detail page view. Content should be returned as an
        HTML string. Note that content does not need to be marked as safe because this is automatically handled.
        """
        raise NotImplementedError

    def full_width_page(self):
        """
        Content that will be rendered within the full width of the detail page view. Content should be returned as an
        HTML string. Note that content does not need to be marked as safe because this is automatically handled.
        """
        raise NotImplementedError

    def buttons(self):
        """
        Buttons that will be rendered and added to the existing list of buttons on the detail page view. Content
        should be returned as an HTML string. Note that content does not need to be marked as safe because this is
        automatically handled.
        """
        raise NotImplementedError

    def detail_tabs(self):
        """
        Tabs that will be rendered and added to the existing list of tabs on the detail page view.
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


def register_jobs(class_list):
    """
    Register a list of Job classes
    """
    from nautobot.extras.jobs import Job

    for job in class_list:
        if not inspect.isclass(job):
            raise TypeError(f"Job class {job} was passed as an instance!")
        if not issubclass(job, Job):
            raise TypeError(f"{job} is not a subclass of extras.jobs.Job!")

        registry["plugin_jobs"].append(job)

    # Note that we do not (and cannot) update the Job records in the Nautobot database at this time.
    # That is done in response to the `nautobot_database_ready` signal, see nautobot.extras.signals.refresh_job_models


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
    from nautobot.utilities.utils import get_filterset_for_model, get_form_for_model
    from nautobot.utilities.forms.utils import add_field_to_filter_form_class

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
# Navigation menu links
#


# 2.2 TODO: remove in favor of NavMenuItem
@class_deprecated_in_favor_of(NavMenuItem)
class PluginMenuItem:
    """
    This class represents a navigation menu item. This constitutes primary link and its text, but also allows for
    specifying additional link buttons that appear to the right of the item in the van menu.

    Links are specified as Django reverse URL strings.
    Buttons are each specified as a list of PluginMenuButton instances.
    """

    permissions = []
    buttons = []

    def __init__(self, link, link_text, permissions=None, buttons=None):
        self.link = link
        self.link_text = link_text
        if permissions is not None:
            if not isinstance(permissions, (list, tuple)):
                raise TypeError("Permissions must be passed as a tuple or list.")
            self.permissions = permissions
        if buttons is not None:
            if not isinstance(buttons, (list, tuple)):
                raise TypeError("Buttons must be passed as a tuple or list.")
            self.buttons = buttons


# 2.2 TODO: remove in favor of NavMenuButton
@class_deprecated_in_favor_of(NavMenuButton)
class PluginMenuButton:
    """
    This class represents a button within a PluginMenuItem. Note that button colors should come from
    ButtonColorChoices.
    """

    color = ButtonColorChoices.DEFAULT
    permissions = []

    def __init__(self, link, title, icon_class, color=None, permissions=None):
        self.link = link
        self.title = title
        self.icon_class = icon_class
        if permissions is not None:
            if not isinstance(permissions, (list, tuple)):
                raise TypeError("Permissions must be passed as a tuple or list.")
            self.permissions = permissions
        if color is not None:
            if color not in ButtonColorChoices.values():
                raise ValueError("Button color must be a choice within ButtonColorChoices.")
            self.color = color


def register_plugin_menu_items(section_name, menu_items):
    """
    Register a list of PluginMenuItem instances for a given menu section (e.g. plugin name)
    """
    new_menu_items = []
    new_menu_item_weight = 100

    nav_menu_items = set()

    permissions = set()

    for menu_item in menu_items:
        if isinstance(menu_item, PluginMenuItem):
            # translate old-style plugin menu definitions into the new nav-menu items and buttons

            new_menu_button_weight = 100
            new_menu_buttons = []
            for button in menu_item.buttons:
                new_menu_buttons.append(
                    NavMenuButton(
                        link=button.link,
                        title=button.title,
                        icon_class=button.icon_class,
                        button_class=button.color,
                        permissions=button.permissions,
                        weight=new_menu_button_weight,
                    )
                )
                new_menu_button_weight += 100

            new_menu_items.append(
                NavMenuItem(
                    link=menu_item.link,
                    name=menu_item.link_text,
                    permissions=menu_item.permissions,
                    weight=new_menu_item_weight,
                    buttons=new_menu_buttons,
                )
            )
            new_menu_item_weight += 100
            permissions = permissions.union(menu_item.permissions)
        elif isinstance(menu_item, NavMenuTab):
            nav_menu_items.add(menu_item)
        else:
            raise TypeError("Top level objects need to be an instance of NavMenuTab or PluginMenuItem: {menu_tab}")

    if new_menu_items:
        # wrap bare item/button list into the default "Plugins" menu tab and appropriate grouping
        if registry["nav_menu"]["tabs"].get("Plugins"):
            weight = (
                registry["nav_menu"]["tabs"]["Plugins"]["groups"][
                    list(registry["nav_menu"]["tabs"]["Plugins"]["groups"])[-1]
                ]["weight"]
                + 100
            )
        else:
            weight = 100
        nav_menu_items.add(
            NavMenuTab(
                name="Plugins",
                weight=5000,
                # Permissions cast to tuple to match development pattern.
                permissions=tuple(permissions),
                groups=(NavMenuGroup(name=section_name, weight=weight, items=new_menu_items),),
            ),
        )

    register_menu_items(nav_menu_items)


#
# Model Validators
#


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
        self.context = {"object": obj}

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
