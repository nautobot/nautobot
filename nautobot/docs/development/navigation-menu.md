# Navigation Menu Tabs

Core applications and plugins can modify the existing navigation bar layout by defining `menu_items` inside of `navigation.py`. Using the key and weight system, a developer can integrate the plugin amongst existing menu tabs, groups, items and buttons and/or create entirely new menus as desired.

## Adding a new tab

The code below shows how to add a new tab to the navbar. A tab is defined by a `NavMenuTab` object. Similarly a group is defined using `NavMenuGroup`. Both of these objects are used as containers for actual items.

The position in the navigation menu is defined by the weight. The lower the weight the closer to the start of the menus the object will be. All core objects have weights in multiples of 100, meaning there is plenty of space around the objects for plugins to customize.

Below you can see `Dummy Tab` has a weight value of `150`. This means the tab will appear between `Organization` and `Devices`.

``` python
from nautobot.core.apps import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuImportButton, NavMenuTab

menu_items = (
    NavMenuTab(
        name="Dummy Tab",
        weight=150,
        groups=(
            NavMenuGroup(
                name="Dummy Group 1",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:dummy_plugin:dummymodel_list",
                        link_text="Dummy Model",
                        permissions=[
                            "dummy_plugin.view_dummymodel"
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:dummy_plugin:dummymodel_add",
                                permissions=[
                                    "dummy_plugin.add_dummymodel",
                                ],
                            ),
                            NavMenuImportButton(
                                link="plugins:dummy_plugin:dummymodel_import",
                                permissions=[
                                    "dummy_plugin.add_dummymodel"
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
```

## Modifying existing tab

By defining an object with the same identifier, a developer can modify existing objects. The example below shows modifying an existing tab to have a new group.

A tab object is being created with the same identifer as an existing object using the `name` attribute. Then a group is being created with a weight of `150`, which means it will appear between the already defined `Circuits` and `Provider` groups.

Weights for already existing items can be found in the nautobot source code (in `navigation.py`) or with a web session open to your nautobot instance, you can inspect an element of the navbar using the developer tools. Each type of element will have an attribute `data-{type}-weight`. The type can be `tab`, `group`, `item` or `button`.

This pattern works for modifying all objects in the tree. New items can be added to groups and new buttons can be added to items.

``` python
menu_tabs = (
    NavMenuTab(
        name="Circuits",
        groups=(
            NavMenuGroup(
                name="Dummy Circuit Group",
                weight=150,
                items=(
                    NavMenuItem(
                        link="plugins:dummy_plugin:dummymodel_list",
                        link_text="Dummy Model",
                        permissions=[
                            "dummy_plugin.view_dummymodel"
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:dummy_plugin:dummymodel_add",
                                permissions=[
                                    "dummy_plugin.add_dummymodel",
                                ],
                            ),
                            NavMenuImportButton(
                                link="plugins:dummy_plugin:dummymodel_import",
                                permissions=[
                                    "dummy_plugin.add_dummymodel"
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
```

## Classes and Attributes

A `NavMenuGroup` has the following attributes:

* `name` - Display name to be shown in navigation menu. Identifier for this object type
* `weight` - Defines the position the object should be displayed at (optional)
* `groups` - List or tuple of `NavMenuGroup`

A `NavMenuGroup` has the following attributes:

* `name` - Display name to be shown in navigation menu. Identifier for this object type
* `weight` - Defines the position the object should be displayed at (optional)
* `items` - List or tuple of `NavMenuItem`

A `NavMenuItem` has the following attributes:

* `link` - The name of the URL path to which this menu item links. Identifier for this object type
* `link_text` - The text presented to the user
* `weight` - Defines the position the object should be displayed at (optional)
* `permissions` - A list of permissions required to display this link (optional)
* `buttons` - An iterable of NavMenuButton instances to display (optional)

A `NavMenuButton` has the following attributes:

* `title` - The tooltip text (displayed when the mouse hovers over the button). Identifier for this object type
* `link` - The name of the URL path to which this button links
* `weight` - Defines the position the object should be displayed at (optional)
* `icon_class` - Button icon CSS classes (Nautobot currently supports [Material Design Icons](https://materialdesignicons.com) or one of the choices provided by `ButtonActionIconChoices`)
* `button_class` - One of the choices provided by `ButtonActionColorChoices` (optional)
* `permissions` - A list of permissions required to display this button (optional)
