import collections
import inspect
from importlib import import_module

from packaging import version

from django.core.exceptions import ValidationError
from django.template.loader import get_template

from nautobot.core.apps import NautobotConfig, NavMenuButton, NavMenuGroup, NavMenuItem, NavMenuTab, register_menu_items
from nautobot.extras.registry import registry, register_datasource_contents
from nautobot.extras.plugins.exceptions import PluginImproperlyConfigured
from nautobot.extras.plugins.utils import import_object
from nautobot.utilities.choices import ButtonColorChoices


# Initialize plugin registry stores
# registry['datasource_content'] is a non-plugin-exclusive registry and is initialized in extras.registry
registry["plugin_custom_validators"] = collections.defaultdict(list)
registry["plugin_graphql_types"] = []
registry["plugin_jobs"] = []
registry["plugin_template_extensions"] = collections.defaultdict(list)


#
# Plugin AppConfig class
#


class PluginConfig(NautobotConfig):
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

    # Default integration paths. Plugin authors can override these to customize the paths to
    # integrated components.
    custom_validators = "custom_validators.custom_validators"
    datasource_contents = "datasources.datasource_contents"
    graphql_types = "graphql.types.graphql_types"
    jobs = "jobs.jobs"
    menu_items = "navigation.menu_items"
    template_extensions = "template_content.template_extensions"
    jinja_filters = "jinja_filters"

    def ready(self):

        # Register model validators (if defined)
        validators = import_object(f"{self.__module__}.{self.custom_validators}")
        if validators is not None:
            register_custom_validators(validators)

        # Register datasource contents (if defined)
        datasource_contents = import_object(f"{self.__module__}.{self.datasource_contents}")
        if datasource_contents is not None:
            register_datasource_contents(datasource_contents)

        # Register GraphQL types (if defined)
        graphql_types = import_object(f"{self.__module__}.{self.graphql_types}")
        if graphql_types is not None:
            register_graphql_types(graphql_types)

        # Import jobs (if present)
        jobs = import_object(f"{self.__module__}.{self.jobs}")
        if jobs is not None:
            register_jobs(jobs)

        # Register plugin navigation menu items (if defined)
        menu_items = import_object(f"{self.__module__}.{self.menu_items}")
        if menu_items is not None:
            register_plugin_menu_items(self.verbose_name, menu_items)

        # Register template content (if defined)
        template_extensions = import_object(f"{self.__module__}.{self.template_extensions}")
        if template_extensions is not None:
            register_template_extensions(template_extensions)

        # Register custom jinja filters
        try:
            import_module(f"{self.__module__}.{self.jinja_filters}")
        except ModuleNotFoundError:
            pass

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


#
# Template content injection
#


class PluginTemplateExtension:
    """
    This class is used to register plugin content to be injected into core Nautobot templates. It contains methods
    that are overridden by plugin authors to return template content.

    The `model` attribute on the class defines the which model detail page this class renders content for. It
    should be set as a string in the form '<app_label>.<model_name>'. render() provides the following context data:

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


def register_template_extensions(class_list):
    """
    Register a list of PluginTemplateExtension classes
    """
    # Validation
    for template_extension in class_list:
        if not inspect.isclass(template_extension):
            raise TypeError(f"PluginTemplateExtension class {template_extension} was passed as an instance!")
        if not issubclass(template_extension, PluginTemplateExtension):
            raise TypeError(f"{template_extension} is not a subclass of extras.plugins.PluginTemplateExtension!")
        if template_extension.model is None:
            raise TypeError(f"PluginTemplateExtension class {template_extension} does not define a valid model!")

        registry["plugin_template_extensions"][template_extension.model].append(template_extension)


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


#
# Navigation menu links
#


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
            if type(permissions) not in (list, tuple):
                raise TypeError("Permissions must be passed as a tuple or list.")
            self.permissions = permissions
        if buttons is not None:
            if type(buttons) not in (list, tuple):
                raise TypeError("Buttons must be passed as a tuple or list.")
            self.buttons = buttons


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
            if type(permissions) not in (list, tuple):
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


class PluginCustomValidator:
    """
    This class is used to register plugin custom model validators which act on specified models. It contains the clean
    method which is overridden by plugin authors to execute custom validation logic. Plugin authors must raise
    ValidationError within this method to trigger validation error messages which are propgated to the user.
    A convenience method `validation_error(<message>)` may be used for this purpose.

    The `model` attribute on the class defines the model to which this validator is registered. It
    should be set as a string in the form '<app_label>.<model_name>'.
    """

    model = None

    def __init__(self, obj):
        self.context = {"object": obj}

    def validation_error(self, message):
        """
        Convenience method for raising `django.core.exceptions.ValidationError` which is required in order to
        trigger validation error messages which are propgated to the user.
        """
        raise ValidationError(message)

    def clean(self):
        """
        Implement custom model validation in the standard Django clean method pattern. The model instance is accessed
        with the `object` key within `self.context`, e.g. `self.context['object']`. ValidationError must be raised to
        prevent saving model instance changes, and propogate messages to the user. For convenience,
        `self.validation_error(<message>)` may be called to raise a ValidationError.
        """
        raise NotImplementedError


def register_custom_validators(class_list):
    """
    Register a list of PluginCustomValidator classes
    """
    # Validation
    for custom_validator in class_list:
        if not inspect.isclass(custom_validator):
            raise TypeError(f"PluginCustomValidator class {custom_validator} was passed as an instance!")
        if not issubclass(custom_validator, PluginCustomValidator):
            raise TypeError(f"{custom_validator} is not a subclass of extras.plugins.PluginCustomValidator!")
        if custom_validator.model is None:
            raise TypeError(f"PluginCustomValidator class {custom_validator} does not define a valid model!")

        registry["plugin_custom_validators"][custom_validator.model].append(custom_validator)
