# Adding Navigation Menu Items

Apps can extend the existing navigation bar layout. By default, Nautobot looks for a `menu_items` list inside of `navigation.py`. (This can be overridden by setting `menu_items` to a custom value on the app's `NautobotAppConfig`.)

Using a key and weight system, a developer can integrate the app's menu additions amongst existing menu tabs, groups, and items.

--- 2.0.0
    As part of the Nautobot 2.0 UI redesign, the option for apps to add entirely new top-level menu "tabs" has been removed. Additionally, buttons can no longer be added to menu items.

More documentation and examples can be found in the [Navigation Menu](../../../core/navigation-menu.md) guide.

!!! tip
    To reduce the amount of clutter in the navigation menu, if your app provides an "app configuration" view, we recommend [linking it from the main "Installed Plugins" page](../configuration-view.md) rather than adding it as a separate item in the navigation menu.

    Similarly, if your app provides an "app home" or "dashboard" view, consider linking it from the "Installed Plugins" page, and/or adding a link from the Nautobot home page (see below), rather than adding it to the navigation menu.
