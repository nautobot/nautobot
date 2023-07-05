# Adding Home Page Content

+++ 1.2.0

Apps can add content to the Nautobot home page. By default, Nautobot looks for a `layout` list inside of `homepage.py`. (This can be overridden by setting `homepage_layout` to a custom value on the app's `NautobotAppConfig`.)

Using a key and weight system, a developer can integrate the app content amongst existing panels, groups, and items and/or create entirely new panels as desired.

More documentation and examples can be found in the guide on [Home Page Panels](../../../core/homepage.md).
