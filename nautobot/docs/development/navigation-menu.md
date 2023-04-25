# Populating the Navigation Menu

Both core applications and plugins can contribute items to the navigation menu by defining `menu_items` inside of their app's `navigation.py`. Using the key and weight system, a developer can integrate amongst existing menu tabs, groups, and items.

## Modifying Existing Menu

By defining an object with the same identifier, a developer can modify existing objects. The example below shows modifying an existing tab to have a new group.

A tab object is being created with the same identifier as an existing object using the `name` attribute. Then a group is being created with a weight of `150`, which means it will appear between the already defined `Circuits` and `Provider` groups. (TODO update this example)

!!! tip
    Weights for already existing items can be found in the nautobot source code (in `navigation.py`) or with a web session open to your nautobot instance, you can inspect an element of the navbar using the developer tools. Each type of element will have an attribute `data-{type}-weight`. The type can be `tab`, `group`, or `item`.

This pattern works for modifying all objects in the tree. New groups can be added to existing tabs and new items can be added to existing groups. The set of tabs is fixed at this time and cannot generally be changed.

``` python
menu_tabs = (
    NavMenuTab(
        name="Circuits",
        groups=(
            NavMenuGroup(
                name="Example Circuit Group",
                weight=150,
                items=(
                    NavMenuItem(
                        link="plugins:example_plugin:examplemodel_list",
                        name="Example Model",
                        permissions=[
                            "example_plugin.view_examplemodel"
                        ],
                    ),
                ),
            ),
        ),
    ),
)
```

## Classes and Attributes

!!! note
    For the `NavMenuTab`, `NavMenuGroup`, and `NavMenuItem` objects to be hidden when the user does not have permissions, set `HIDE_RESTRICTED_UI = True` in the `nautobot_config.py`.
    Please refer to [HIDE_RESTRICTED_UI](../configuration/optional-settings.md#hide_restricted_ui)

A `NavMenuTab` has the following attributes:

* `name` - Display name to be shown in navigation menu
* `weight` - Defines the position the object should be displayed at (optional)
* `permissions` - A list of permissions required to display this link (optional)
* `groups` - List or tuple of `NavMenuGroup`

A `NavMenuGroup` has the following attributes:

* `name` - Display name to be shown in navigation menu
* `weight` - Defines the position the object should be displayed at (optional)
* `permissions` - A list of permissions required to display this link (optional)
* `items` - List or tuple of `NavMenuGroup` and/or `NavMenuItem`

A `NavMenuItem` has the following attributes:

* `link` - The name of the URL path to which this menu item links
* `name` - The text presented to the user
* `weight` - Defines the position the object should be displayed at (optional)
* `permissions` - A list of permissions required to display this link (optional)
