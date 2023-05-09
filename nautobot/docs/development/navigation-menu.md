# Populating the Navigation Menu

Both core applications and plugins can contribute items to the navigation menu by defining `menu_items` inside of their app's `navigation.py`. Using the key and weight system, a developer can integrate amongst existing menu contexts (a.k.a. tabs), groups, and items.

--- 2.0.0
    The updated UI does not permit including buttons into the navigation menu items. As such, `NavMenuButton` and its subclasses have been removed, and the `buttons` parameter to `NavMenuItem` is no longer supported.

## Defining and Modifying Menus

Nautobot will intelligently merge the contents of all apps' `menu_items` defined in their `navigation.py` to create the final navigation menu structure. This is done by matching on objects' `name` fields to identify items that need to be consolidated.

The example below shows adding a new group containing a new item under the base `Inventory` menu context. The group is being defined with a weight of `150`, which means it will appear between the already defined `Devices` (weight `100`) and `Organization` (weight `200`) groups in this context.

!!! tip
    Weights for already existing items can be found in the nautobot source code (in `navigation.py`).

This pattern works for modifying all objects in the tree. New groups can be added to existing tabs and new items can be added to existing groups. The set of tabs is defined by the Nautobot `nautobot.core.apps.MENU_TABS` constant and cannot generally be changed.

``` python
menu_items = (
    NavMenuTab(
        name="Inventory",
        groups=(
            NavMenuGroup(
                name="Example App",
                weight=150,
                items=(
                    NavMenuItem(
                        name="Example Model",
                        weight=100,
                        link="plugins:example_plugin:examplemodel_list",
                        permissions=["example_plugin.view_examplemodel"],
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
* `permissions` - A list of permissions required to display this object (optional)
* `groups` - List or tuple of `NavMenuGroup`

--- 2.0.0
    As the sequence of menu "tabs"/"contexts" in Nautobot is now constant, the `weight` property has been removed from `NavMenuTab`.

A `NavMenuGroup` has the following attributes:

* `name` - Display name to be shown in navigation menu
* `weight` - Defines the position the object should be displayed at (optional)
* `permissions` - A list of permissions required to display this object (optional)
* `items` - List or tuple of `NavMenuGroup` and/or `NavMenuItem`

A `NavMenuItem` has the following attributes:

* `link` - The name of the URL path to which this menu item links
* `name` - The text presented to the user
* `weight` - Defines the position the object should be displayed at (optional)
* `permissions` - A list of permissions required to display this link (optional)

--- 2.0.0
    The `buttons` attribute was removed from `NavMenuItem`.
