from collections import OrderedDict
import logging
import os

from constance.apps import ConstanceConfig
from django.apps import AppConfig, apps as global_apps
from django.db.models import BigIntegerField, BinaryField, JSONField
from django.db.models.signals import post_migrate
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.http import urlencode
from django.utils.module_loading import import_string
from graphene.types import generic, String

from nautobot.core.signals import nautobot_database_ready
from nautobot.core.ui.base import PermissionsMixin  # noqa: F401

from nautobot.core.ui.homepage import (  # isort: skip  # noqa: F401
    HomePageBase,
    HomePageGroup,
    HomePageItem,
    HomePagePanel,
)
from nautobot.core.ui.nav import (  # isort: skip  # noqa: F401
    NavMenuAddButton,
    NavMenuBase,
    NavMenuButton,
    NavMenuGroup,
    NavMenuImportButton,
    NavMenuItem,
    NavMenuTab,
    NAV_CONTEXT_NAMES,
)

from nautobot.extras.registry import registry

logger = logging.getLogger(__name__)
registry["nav_menu"] = {"tabs": {}}
registry["homepage_layout"] = {"panels": {}}


class NautobotConfig(AppConfig):
    """
    Custom AppConfig for Nautobot applications.

    All core apps should inherit from this class instead of using AppConfig directly.

    Adds functionality to generate the HTML navigation menu and homepage content using `navigation.py`
    and `homepage.py` files from installed Nautobot core applications and Apps.
    """

    default = False  # abstract base class, all subclasses must set this to True
    homepage_layout = "homepage.layout"
    menu_tabs = "navigation.menu_items"
    # New UI Navigation
    navigation = "navigation.navigation"
    searchable_models = []  # models included in global search; list of ["modelname", "modelname", "modelname"...]

    def ready(self):
        """
        Ready function initiates the import application.
        """
        try:
            homepage_layout = import_string(f"{self.name}.{self.homepage_layout}")
            register_homepage_panels(self.path, self.label, homepage_layout)
        except ImportError:
            pass

        try:
            menu_items = import_string(f"{self.name}.{self.menu_tabs}")
            register_menu_items(menu_items)
        except ImportError:
            pass


def create_or_check_entry(grouping, record, key, path):
    """
    Helper function for adding and/or validating nested data in a provided dict based on a provided record.

    Used in constructing the nav tab/group/item/buttons hierarchy as well as the homepage panel/group/item hierarchy.

    If `key` does not exist in `grouping`, it will be populated with the `initial_dict` of the provided `record`.
    Else, if any of the `fixed_fields` of the provided `record` conflict with the existing data in `grouping["key"]`,
    an error message will be logged.

    Args:
        grouping (dict): The dictionary to populate or validate (e.g. the contents of `registry["nav_menu"]["tabs"]`).
        record (HomePageBase, NavMenuBase): An object with `initial_dict` and `fixed_fields` attributes/properties.
        key (str): The key within `grouping` to populate or validate the contents of.
        path (str): String included in log messages for diagnosis and debugging.
    """
    if key not in grouping:
        grouping[key] = record.initial_dict
    else:
        for attr, value in record.fixed_fields:
            if grouping[key][attr] != value:
                logger.error("Unable to redefine %s on %s from %s to %s", attr, path, grouping[key][attr], value)


def register_menu_items(tab_list):
    """
    Based on the tab_list, the `registry["nav_menu"]` dictionary is created/updated to define the navbar.

    The dictionary is built from four key objects, NavMenuTab, NavMenuGroup, NavMenuItem and NavMenuButton.
    The Django template then uses this dictionary to generate the navbar HTML.

    The dictionary takes the form:

    ```
    registry = {
        ...
        "nav_menu": {
            "tabs": {
                <NavMenuTab.name>: {
                    "weight": <NavMenuTab.weight>,
                    "groups": {
                        <NavMenuGroup.name>: {
                            "weight": <NavMenuGroup.weight>,
                            "items": {
                                reverse(<NavMenuItem.link>): {
                                    "name": <NavMenuItem.name>,
                                    "weight": <NavMenuItem.weight>",
                                    "buttons": {
                                        <NavMenuButton.name>: {
                                            "link": <NavMenuButton.link>,
                                            "icon_class": <NavMenuButton.icon_class>,
                                            "button_class": <NavMenuButton.button_class>,
                                            "weight": <NavMenuButton.weight>,
                                            "permissions": <NavMenuButton.permissions>,
                                        },
                                        ...
                                    },
                                    "permissions": <NavMenuItem.permissions>,
                                },
                                ...
                            },
                            "permissions": <set of permissions constructed from all contained NavMenuItems, or None>,
                        },
                        ...
                    },
                    "permissions": <set of permissions constructed from all contained NavMenuGroups, or None>,
                },
                ...
            },
        },
        ...
    }
    ```

    This is almost certainly overcomplicated and could do with significant refactoring at some point.
    """
    for nav_tab in tab_list:
        if isinstance(nav_tab, NavMenuTab):
            # Handle Apps that haven't been updated yet
            if nav_tab.name == "Plugins":
                nav_tab.name = "Apps"
            create_or_check_entry(registry["nav_menu"]["tabs"], nav_tab, nav_tab.name, nav_tab.name)

            tab_perms = registry["nav_menu"]["tabs"][nav_tab.name]["permissions"]
            registry_groups = registry["nav_menu"]["tabs"][nav_tab.name]["groups"]
            for group in nav_tab.groups:
                create_or_check_entry(registry_groups, group, group.name, f"{nav_tab.name} -> {group.name}")

                group_perms = registry["nav_menu"]["tabs"][nav_tab.name]["groups"][group.name]["permissions"]
                for item in group.items:
                    # Instead of passing the reverse url strings, we pass in the url itself initialized with args and kwargs.
                    try:
                        item.link = reverse(item.link, args=item.args, kwargs=item.kwargs)
                        if item.query_params:
                            item.link += f"?{urlencode(item.query_params)}"
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

                    # If any item has "no" permissions required, then the group behaves likewise
                    if group_perms is None or not item.permissions:
                        group_perms = None
                    else:
                        group_perms |= set(perms for perms in item.permissions)

                # Add sorted items to group registry dict
                registry_groups[group.name]["items"] = OrderedDict(
                    sorted(registry_groups[group.name]["items"].items(), key=lambda kv_pair: kv_pair[1]["weight"])
                )
                # Add collected permissions to group
                registry_groups[group.name]["permissions"] = group_perms

                # If any group has "no" permissions required, then the tab performs likewise
                if tab_perms is None or not group_perms:
                    tab_perms = None
                else:
                    tab_perms |= group_perms

            # Add sorted groups to tab dict
            registry["nav_menu"]["tabs"][nav_tab.name]["groups"] = OrderedDict(
                sorted(registry_groups.items(), key=lambda kv_pair: kv_pair[1]["weight"])
            )
            # Add collected permissions to tab dict
            registry["nav_menu"]["tabs"][nav_tab.name]["permissions"] = tab_perms
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
        label (str): Label of the app which defines the homepage layout, for example `dcim` or `my_nautobot_app`
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


def post_migrate_send_nautobot_database_ready(sender, app_config, signal, **kwargs):
    """
    Send the `nautobot_database_ready` signal to all installed core apps and Apps.

    Signal handler for Django's post_migrate() signal.
    """
    kwargs.setdefault("apps", global_apps)
    for app_conf in global_apps.get_app_configs():
        nautobot_database_ready.send(sender=app_conf, app_config=app_conf, **kwargs)


class CoreConfig(NautobotConfig):
    """
    AppConfig for the core of Nautobot.
    """

    default = True
    name = "nautobot.core"
    verbose_name = "Nautobot Core"

    def ready(self):
        # Register netutils jinja2 filters in django_jinja
        from django_jinja import library
        from netutils.utils import jinja2_convenience_function

        for name, func in jinja2_convenience_function().items():
            # Register in django_jinja
            library.filter(name=name, fn=func)

        from graphene_django.converter import convert_django_field

        from nautobot.core.graphql import BigInteger
        import nautobot.core.jobs  # noqa: F401  # unused-import -- but this import registers the system jobs

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


class NautobotConstanceConfig(ConstanceConfig):
    """Override "Constance" app name to "Configuration"."""

    verbose_name = "Configuration"
