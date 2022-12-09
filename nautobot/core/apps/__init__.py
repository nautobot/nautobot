import logging
import os

from abc import ABC, abstractmethod
from collections import OrderedDict

from django.apps import AppConfig, apps as global_apps
from django.db.models import JSONField, BigIntegerField, BinaryField
from django.db.models.signals import post_migrate
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from constance.apps import ConstanceConfig
from graphene.types import generic, String

from nautobot.core.signals import nautobot_database_ready
from nautobot.extras.plugins.utils import import_object
from nautobot.extras.registry import registry
from nautobot.utilities.choices import ButtonActionColorChoices, ButtonActionIconChoices


logger = logging.getLogger("nautobot.core.apps")
registry["nav_menu"] = {"tabs": {}}
registry["homepage_layout"] = {"panels": {}}


class NautobotConfig(AppConfig):
    """
    Custom AppConfig for Nautobot applications.

    All core apps should inherit from this class instead of using AppConfig directly.

    Adds functionality to generate the HTML navigation menu and homepage content using `navigation.py`
    and `homepage.py` files from installed Nautobot applications and plugins.
    """

    homepage_layout = "homepage.layout"
    menu_tabs = "navigation.menu_items"

    def ready(self):
        """
        Ready function initiates the import application.
        """
        homepage_layout = import_object(f"{self.name}.{self.homepage_layout}")
        if homepage_layout is not None:
            register_homepage_panels(self.path, self.label, homepage_layout)

        menu_items = import_object(f"{self.name}.{self.menu_tabs}")
        if menu_items is not None:
            register_menu_items(menu_items)


def create_or_check_entry(grouping, record, key, path):
    if key not in grouping:
        grouping[key] = record.initial_dict
    else:
        for attr, value in record.fixed_fields:
            if grouping[key][attr]:
                logger.error("Unable to redefine %s on %s from %s to %s", attr, path, grouping[key][attr], value)


def register_menu_items(tab_list):
    """
    Using the imported object a dictionary is either created or updated with objects to create
    the navbar.

    The dictionary is built from four key objects, NavMenuTab, NavMenuGroup, NavMenuItem and
    NavMenuButton. The Django template then uses this dictionary to generate the navbar HTML.
    """
    for nav_tab in tab_list:
        if isinstance(nav_tab, NavMenuTab):
            create_or_check_entry(registry["nav_menu"]["tabs"], nav_tab, nav_tab.name, f"{nav_tab.name}")

            tab_perms = set()
            registry_groups = registry["nav_menu"]["tabs"][nav_tab.name]["groups"]
            for group in nav_tab.groups:
                create_or_check_entry(registry_groups, group, group.name, f"{nav_tab.name} -> {group.name}")

                group_perms = set()
                for item in group.items:

                    # Instead of passing the reverse url strings, we pass in the url itself initialized with args and kwargs.
                    try:
                        item.link = reverse(item.link, args=item.args, kwargs=item.kwargs)
                    except NoReverseMatch as e:
                        # Catch the invalid link here and render the link name as an error message in the template
                        logger.debug("%s", e)
                        item.name = "ERROR: Invalid link!"

                    create_or_check_entry(
                        registry_groups[group.name]["items"],
                        item,
                        item.link,
                        f"{nav_tab.name} -> {group.name} -> {item.link}",
                    )

                    registry_buttons = registry_groups[group.name]["items"][item.link]["buttons"]
                    for button in item.buttons:
                        create_or_check_entry(
                            registry_buttons,
                            button,
                            button.title,
                            f"{nav_tab.name} -> {group.name} -> {item.link} -> {button.title}",
                        )

                    # Add sorted buttons to group registry dict
                    registry_groups[group.name]["items"][item.link]["buttons"] = OrderedDict(
                        sorted(registry_buttons.items(), key=lambda kv_pair: kv_pair[1]["weight"])
                    )

                    group_perms |= set(perms for perms in item.permissions)

                # Add sorted items to group registry dict
                registry_groups[group.name]["items"] = OrderedDict(
                    sorted(registry_groups[group.name]["items"].items(), key=lambda kv_pair: kv_pair[1]["weight"])
                )
                # Add collected permissions to group
                registry_groups[group.name]["permissions"] = group_perms
                # Add collected permissions to tab
                tab_perms |= group_perms

            # Add sorted groups to tab dict
            registry["nav_menu"]["tabs"][nav_tab.name]["groups"] = OrderedDict(
                sorted(registry_groups.items(), key=lambda kv_pair: kv_pair[1]["weight"])
            )
            # Add collected permissions to tab dict
            registry["nav_menu"]["tabs"][nav_tab.name]["permissions"] |= tab_perms
        else:
            raise TypeError(f"Top level objects need to be an instance of NavMenuTab: {nav_tab}")

        # Order all tabs in dict
        registry["nav_menu"]["tabs"] = OrderedDict(
            sorted(registry["nav_menu"]["tabs"].items(), key=lambda kv_pair: kv_pair[1]["weight"])
        )


def register_homepage_panels(path, label, homepage_layout):
    """
    Register homepage panels using `homepage.py`.

    Each app can now register a `homepage.py` file which holds objects defining the layout of the
    home page. `HomePagePanel`, `HomePageGroup` and `HomePageItem` can be used to
    define different parts of the layout.

    These objects are converted into a dictionary to be stored inside of the Nautobot registry.

    Args:
        path (str): Absolute filesystem path to the app which defines the homepage layout;
                    typically this will be an `AppConfig.path` property
        label (str): Label of the app which defines the homepage layout, for example `dcim` or `my_nautobot_plugin`
        homepage_layout (list): A list of HomePagePanel instances to contribute to the homepage layout.
    """
    template_path = f"{path}/templates/{label}/inc/"
    registry_panels = registry["homepage_layout"]["panels"]
    for panel in homepage_layout:
        panel_perms = registry_panels[panel.name]["permissions"] if registry_panels.get(panel.name) else set()
        if panel.permissions:
            panel_perms |= set(panel.permissions)
        panel.template_path = template_path
        if isinstance(panel, HomePagePanel):
            create_or_check_entry(registry_panels, panel, panel.name, f"{panel.name}")
            registry_items = registry_panels[panel.name]["items"]

            if panel.custom_template:
                if not os.path.isfile(f"{template_path}{panel.custom_template}"):
                    raise ValueError(f"Unable to load {template_path}{panel.custom_template}")

            for item in panel.items:
                if isinstance(item, HomePageItem):
                    item.template_path = template_path
                    create_or_check_entry(registry_items, item, item.name, f"{panel.name} -> {item.name}")

                    if item.custom_template:
                        if not os.path.isfile(f"{template_path}{item.custom_template}"):
                            raise ValueError(f"Unable to load {template_path}{item.custom_template}")

                    panel_perms |= set(item.permissions)

                elif isinstance(item, HomePageGroup):
                    item.template_path = template_path
                    create_or_check_entry(registry_items, item, item.name, f"{panel.name} -> {item.name}")
                    for group_item in item.items:
                        if isinstance(group_item, HomePageItem):
                            group_item.template_path = template_path
                            create_or_check_entry(
                                registry_items[item.name]["items"],
                                group_item,
                                group_item.name,
                                f"{panel.name} -> {item.name} -> {group_item.name}",
                            )
                        else:
                            raise TypeError(f"Third level objects need to be an instance of HomePageItem: {group_item}")
                        panel_perms |= set(group_item.permissions)
                    registry_items[item.name]["items"] = OrderedDict(
                        sorted(registry_items[item.name]["items"].items(), key=lambda kv_pair: kv_pair[1]["weight"])
                    )
                else:
                    raise TypeError(
                        f"Second level objects need to be an instance of HomePageGroup or HomePageItem: {item}"
                    )

            registry_panels[panel.name]["items"] = OrderedDict(
                sorted(registry_items.items(), key=lambda kv_pair: kv_pair[1]["weight"])
            )
        else:
            raise TypeError(f"Top level objects need to be an instance of HomePagePanel: {panel}")
        registry_panels[panel.name]["permissions"] = panel_perms

    registry["homepage_layout"]["panels"] = OrderedDict(
        sorted(registry_panels.items(), key=lambda kv_pair: kv_pair[1]["weight"])
    )


class HomePageBase(ABC):
    """Base class for homepage layout classes."""

    @property
    @abstractmethod
    def initial_dict(self):  # to be implemented by each subclass
        return {}

    @property
    @abstractmethod
    def fixed_fields(self):  # to be implemented by subclass
        return ()


class NavMenuBase(ABC):  # replaces PermissionsMixin
    """Base class for navigation classes."""

    @property
    @abstractmethod
    def initial_dict(self):  # to be implemented by each subclass
        return {}

    @property
    @abstractmethod
    def fixed_fields(self):  # to be implemented by subclass
        return ()


class PermissionsMixin:
    """Ensure permissions through init."""

    def __init__(self, permissions=None):
        """Ensure permissions."""
        if permissions is not None and not isinstance(permissions, (list, tuple)):
            raise TypeError("Permissions must be passed as a tuple or list.")
        self.permissions = permissions


class HomePagePanel(HomePageBase, PermissionsMixin):
    """Defines properties that can be used for a panel."""

    permissions = []
    items = []
    template_path = None

    @property
    def initial_dict(self):
        return {
            "custom_template": self.custom_template,
            "custom_data": self.custom_data,
            "weight": self.weight,
            "items": {},
            "permissions": self.permissions,
            "template_path": self.template_path,
        }

    @property
    def fixed_fields(self):
        return ()

    def __init__(self, name, permissions=None, custom_data=None, custom_template=None, items=None, weight=1000):
        """
        Ensure panel properties.

        Args:
            name (str): The name of the panel.
            permissions (list): The permissions required to view this panel.
            custom_data (dict): Custom data to be passed to the custom template.
            custom_template (str): Name of custom template.
            items (list): List of items to be rendered in this panel.
            weight (int): The weight of this panel.
        """
        if permissions is None:
            permissions = []
        super().__init__(permissions)
        self.custom_data = custom_data
        self.custom_template = custom_template
        self.name = name
        self.permissions = permissions
        self.weight = weight

        if items is not None and custom_template is not None:
            raise ValueError("Cannot specify items and custom_template at the same time.")
        if items is not None:
            if not isinstance(items, (list, tuple)):
                raise TypeError("Items must be passed as a tuple or list.")
            elif not all(isinstance(item, (HomePageGroup, HomePageItem)) for item in items):
                raise TypeError("All items defined in a panel must be an instance of HomePageGroup or HomePageItem")
            self.items = items


class HomePageGroup(HomePageBase, PermissionsMixin):
    """Defines properties that can be used for a panel group."""

    permissions = []
    items = []

    @property
    def initial_dict(self):
        return {
            "items": {},
            "permissions": set(),
            "weight": self.weight,
        }

    @property
    def fixed_fields(self):
        return ()

    def __init__(self, name, permissions=None, items=None, weight=1000):
        """
        Ensure group properties.

        Args:
            name (str): The name of the group.
            permissions (list): The permissions required to view this group.
            items (list): List of items to be rendered in this group.
            weight (int): The weight of this group.
        """
        if permissions is None:
            permissions = []
        super().__init__(permissions)
        self.name = name
        self.weight = weight

        if items is not None:
            if not isinstance(items, (list, tuple)):
                raise TypeError("Items must be passed as a tuple or list.")
            elif not all(isinstance(item, HomePageItem) for item in items):
                raise TypeError("All items defined in a group must be an instance of HomePageItem")
            self.items = items


class HomePageItem(HomePageBase, PermissionsMixin):
    """Defines properties that can be used for a panel item."""

    permissions = []
    items = []
    template_path = None

    @property
    def initial_dict(self):
        return {
            "custom_template": self.custom_template,
            "custom_data": self.custom_data,
            "description": self.description,
            "link": self.link,
            "model": self.model,
            "permissions": self.permissions,
            "template_path": self.template_path,
            "weight": self.weight,
        }

    @property
    def fixed_fields(self):
        return ()

    def __init__(
        self,
        name,
        link=None,
        model=None,
        custom_template=None,
        custom_data=None,
        description=None,
        permissions=None,
        weight=1000,
    ):
        """
        Ensure item properties.

        Args:
            name (str): The name of the item.
            link (str): The link to be used for this item.
            model (str): The model to being used for this item to calculate the total count of objects.
            custom_template (str): Name of custom template.
            custom_data (dict): Custom data to be passed to the custom template.
        """
        super().__init__(permissions)

        self.name = name
        self.custom_template = custom_template
        self.custom_data = custom_data
        self.description = description
        self.link = link
        self.model = model
        self.weight = weight

        if model is not None and custom_template is not None:
            raise ValueError("Cannot specify model and custom_template at the same time.")


class NavMenuTab(NavMenuBase, PermissionsMixin):
    """
    Ths class represents a navigation menu tab. This is built up from a name and a weight value. The name is
    the display text and the weight defines its position in the navbar.

    Groups are each specified as a list of NavMenuGroup instances.
    """

    permissions = []
    groups = []

    @property
    def initial_dict(self):
        return {
            "weight": self.weight,
            "groups": {},
            "permissions": set(),
        }

    @property
    def fixed_fields(self):
        return ()

    def __init__(self, name, permissions=None, groups=None, weight=1000):
        """
        Ensure tab properties.

        Args:
            name (str): The name of the tab.
            permissions (list): The permissions required to view this tab.
            groups (list): List of groups to be rendered in this tab.
            weight (int): The weight of this tab.
        """
        super().__init__(permissions)
        self.name = name
        self.weight = weight
        if groups is not None:
            if not isinstance(groups, (list, tuple)):
                raise TypeError("Groups must be passed as a tuple or list.")
            elif not all(isinstance(group, NavMenuGroup) for group in groups):
                raise TypeError("All groups defined in a tab must be an instance of NavMenuGroup")
            self.groups = groups


class NavMenuGroup(NavMenuBase, PermissionsMixin):
    """
    Ths class represents a navigation menu group. This is built up from a name and a weight value. The name is
    the display text and the weight defines its position in the navbar.

    Items are each specified as a list of NavMenuItem instances.
    """

    permissions = []
    items = []

    @property
    def initial_dict(self):
        return {
            "weight": self.weight,
            "items": {},
        }

    @property
    def fixed_fields(self):
        return ()

    def __init__(self, name, items=None, weight=1000):
        """
        Ensure group properties.

        Args:
            name (str): The name of the group.
            items (list): List of items to be rendered in this group.
            weight (int): The weight of this group.
        """
        self.name = name
        self.weight = weight

        if items is not None and not isinstance(items, (list, tuple)):
            raise TypeError("Items must be passed as a tuple or list.")
        elif not all(isinstance(item, NavMenuItem) for item in items):
            raise TypeError("All items defined in a group must be an instance of NavMenuItem")
        self.items = items


class NavMenuItem(NavMenuBase, PermissionsMixin):
    """
    This class represents a navigation menu item. This constitutes primary link and its text, but also allows for
    specifying additional link buttons that appear to the right of the item in the nav menu.

    Links are specified as Django reverse URL strings.
    Buttons are each specified as a list of NavMenuButton instances.
    """

    @property
    def initial_dict(self):
        return {
            "name": self.name,
            "weight": self.weight,
            "buttons": {},
            "permissions": self.permissions,
            "args": [],
            "kwargs": {},
        }

    @property
    def fixed_fields(self):
        return (
            ("name", self.name),
            ("permissions", self.permissions),
        )

    permissions = []
    buttons = []
    args = []
    kwargs = {}

    def __init__(self, link, name, args=None, kwargs=None, permissions=None, buttons=(), weight=1000):
        """
        Ensure item properties.

        Args:
            link (str): The link to be used for this item.
            name (str): The name of the item.
            args (list): Arguments that are being passed to the url with reverse() method
            kwargs (dict): Keyword arguments are are being passed to the url with reverse() method
            permissions (list): The permissions required to view this item.
            buttons (list): List of buttons to be rendered in this item.
            weight (int): The weight of this item.
        """
        super().__init__(permissions)
        self.link = link
        self.name = name
        self.weight = weight
        self.args = args
        self.kwargs = kwargs

        if not isinstance(buttons, (list, tuple)):
            raise TypeError("Buttons must be passed as a tuple or list.")
        elif not all(isinstance(button, NavMenuButton) for button in buttons):
            raise TypeError("All buttons defined in an item must be an instance or subclass of NavMenuButton")
        self.buttons = buttons


class NavMenuButton(NavMenuBase, PermissionsMixin):
    """
    This class represents a button within a PluginMenuItem. Note that button colors should come from
    ButtonColorChoices.
    """

    @property
    def initial_dict(self):
        return {
            "link": self.link,
            "icon_class": self.icon_class,
            "button_class": self.button_class,
            "weight": self.weight,
            "buttons": {},
            "permissions": self.permissions,
        }

    @property
    def fixed_fields(self):
        return (
            ("button_class", self.button_class),
            ("icon_class", self.icon_class),
            ("link", self.link),
            ("permissions", self.permissions),
        )

    def __init__(
        self,
        link,
        title,
        icon_class,
        button_class=ButtonActionColorChoices.DEFAULT,
        permissions=None,
        weight=1000,
    ):
        """
        Ensure button properties.

        Args:
            link (str): The link to be used for this button.
            title (str): The title of the button.
            icon_class (str): The icon class to be used as the icon for the start of the button.
            button_class (str): The button class defines to be used to define the style of the button.
            permissions (list): The permissions required to view this button.
            weight (int): The weight of this button.
        """
        super().__init__(permissions)
        self.link = link
        self.title = title
        self.icon_class = icon_class
        self.weight = weight
        self.button_class = button_class


class NavMenuAddButton(NavMenuButton):
    """Add button subclass."""

    def __init__(self, *args, **kwargs):
        """Ensure button properties."""
        if "title" not in kwargs:
            kwargs["title"] = "Add"
        if "icon_class" not in kwargs:
            kwargs["icon_class"] = ButtonActionIconChoices.ADD
        if "button_class" not in kwargs:
            kwargs["button_class"] = ButtonActionColorChoices.ADD
        if "weight" not in kwargs:
            kwargs["weight"] = 100
        super().__init__(*args, **kwargs)


class NavMenuImportButton(NavMenuButton):
    """Import button subclass."""

    def __init__(self, *args, **kwargs):
        """Ensure button properties."""
        if "title" not in kwargs:
            kwargs["title"] = "Import"
        if "icon_class" not in kwargs:
            kwargs["icon_class"] = ButtonActionIconChoices.IMPORT
        if "button_class" not in kwargs:
            kwargs["button_class"] = ButtonActionColorChoices.IMPORT
        if "weight" not in kwargs:
            kwargs["weight"] = 200
        super().__init__(*args, **kwargs)


def post_migrate_send_nautobot_database_ready(sender, app_config, signal, **kwargs):
    """
    Send the `nautobot_database_ready` signal to all installed apps and plugins.

    Signal handler for Django's post_migrate() signal.
    """
    kwargs.setdefault("apps", global_apps)
    for app_conf in global_apps.get_app_configs():
        nautobot_database_ready.send(sender=app_conf, app_config=app_conf, **kwargs)


class CoreConfig(NautobotConfig):
    """
    AppConfig for the core of Nautobot.
    """

    name = "nautobot.core"
    verbose_name = "Nautobot Core"

    def ready(self):
        from graphene_django.converter import convert_django_field
        from nautobot.core.graphql import BigInteger

        @convert_django_field.register(JSONField)
        def convert_json(field, registry=None):  # pylint: disable=redefined-outer-name
            """Convert JSONField to GenericScalar."""
            return generic.GenericScalar()

        @convert_django_field.register(BinaryField)
        def convert_binary(field, registry=None):  # pylint: disable=redefined-outer-name
            """Convert BinaryField to String."""
            return String()

        @convert_django_field.register(BigIntegerField)
        def convert_biginteger(field, registry=None):  # pylint: disable=redefined-outer-name
            """Convert BigIntegerField to BigInteger scalar."""
            return BigInteger()

        from django.conf import settings
        from django.contrib.auth.models import update_last_login
        from django.contrib.auth.signals import user_logged_in

        # If maintenance mode is enabled, assume the database is read-only, and disable updating the user's
        # last_login time upon authentication.
        if settings.MAINTENANCE_MODE:
            logger.warning("Maintenance mode enabled: disabling update of most recent login time")
            user_logged_in.disconnect(update_last_login, dispatch_uid="update_last_login")

        post_migrate.connect(post_migrate_send_nautobot_database_ready, sender=self)

        super().ready()

        # Magical monkey-patch TaggableManager to replace the `formfield()` method from our mixin.
        from cacheops.utils import monkey_mix
        from nautobot.extras.models import mixins
        from taggit.managers import TaggableManager

        monkey_mix(TaggableManager, mixins.TaggableManagerMonkeyMixin)


class NautobotConstanceConfig(ConstanceConfig):
    """Override "Constance" app name to "Configuration"."""

    verbose_name = "Configuration"
