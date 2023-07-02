# Populating the Home Page

+++ 1.2.0

Both core applications and plugins can contribute items to the Nautobot home page by defining `layout` inside of their app's `homepage.py`. Using a key and weight system, a developer can integrate amongst existing home page panels or can create entirely new panels as desired.

## Adding a new Home Page Panel

Each panel on the home page is defined by a `HomePagePanel` object. A `HomePagePanel` may contain either or both of `HomePageItem` and/or `HomePageGroup` objects, or may define custom content via a referenced Django template. A `HomePageGroup` may itself contain `HomePageItem` objects as well, and individual `HomePageItem` objects may also reference custom Django templates.

Some examples:

![DCIM Panel](../media/development/homepage_dcim_panel.png "DCIM Panel")

This is a single `HomePagePanel` (defined in `nautobot/dcim/homepage.py`) containing four `HomePageItem` and one `HomePageGroup` (the `Connections` group, which in turn contains four more `HomePageItem`). Using these objects together allows you to create panels that match the visual style of most other panels on the Nautobot home page.

![Changelog Panel](../media/development/homepage_changelog_panel.png "Changelog Panel")

This is a `HomePagePanel` (defined in `nautobot/extras/homepage.py`) that uses a custom template to render content that doesn't fit into the `HomePageGroup`/`HomePageItem` pattern.

The position of a panel in the home page is defined by its `weight`. The lower the weight the closer to the start (top/left) of the home page the object will be. All core objects have weights in multiples of 100, meaning there is plenty of space around the objects for plugins to customize.

In the below code example, you can see that the `Example Plugin` panel has a `weight` value of `150`. This means it will appear between `Organization` (weight `100`) and `DCIM` (weight `200`).

!!! tip
    Weights for already existing items can be found in the Nautobot source code (in `nautobot/<app>/homepage.py`) or with a web session open to your Nautobot instance, you can inspect an element of the home page using the developer tools.

Example of custom code being used in a panel can be seen in the `Custom Example Plugin` panel below. The attribute `custom_template` is used to refer to the filename of a template. Templates need to be stored in the templates `inc` folder for the plugin (`/example_plugin/templates/example_plugin/inc/`).

If additional data is needed to render the custom template, callback functions can be used to collect this data. In the below example, the `Custom Example Plugin` panel is using the callback `get_example_data()` to dynamically populate the key `example_data` into the rendering context of this panel.

``` python
from nautobot.core.apps import HomePageItem, HomePagePanel
from .models import ExampleModel


def get_example_data(request):
    return ExampleModel.objects.all()


layout = (
    HomePagePanel(
        name="Example Plugin",
        weight=150,
        items=(
            HomePageItem(
                name="Example Models",
                link="plugins:example_plugin:examplemodel_list",
                description="List example plugin models.",
                permissions=["example_plugin.view_examplemodel"],
                weight=100,
            ),
        ),
    ),
    HomePagePanel(
        name="Custom Example Plugin",
        custom_template="panel_example_example.html",
        custom_data={"example_data": get_example_data},
        permissions=["example_plugin.view_examplemodel"],
        weight=350,
    ),
)
```
