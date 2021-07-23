# Populating the Homepage

Both core applications and plugins can contribute items to the Nautobot home page by defining `layout` inside of their app's `homepage.py`. Using a key and weight system, a developer can integrate amongst existing home page panels or can create entirely new panels as desired.

## Adding a new Homepage Object

The code below shows how to add a new panel to the home page. A panel is defined by a `HomePagePanel` object. A `HomePagePanel` may contain either or both of `HomePageItem` and/or `HomePageGroup` objects, or may define custom content via a referenced Django template. A `HomePageGroup` may itself contain `HomePageItem` objects as well.

Some examples:

![DCIM Panel](../media/development/homepage_dcim_panel.png "DCIM Panel")

This is a single `HomePagePanel` (defined in `nautobot/dcim/homepage.py`) containing four `HomePageItem` and one `HomePageGroup` (the `Connections` group, which in turn contains four more `HomePageItem`. Using these objects together allows you to create panels that match the visual style of most other panels on the Nautobot home page.

![Changelog Panel](../media/development/homepage_changelog_panel.png "Changelog Panel")

This is a `HomePagePanel` (defined in `nautobot/extras/homepage.py`) that uses a custom template to render content that doesn't fit into the `HomePageGroup`/`HomePageItem` pattern.

The position in the home page is defined by the weight. The lower the weight the closer to the start (top/left) of the home page the object will be. All core objects have weights in multiples of 100, meaning there is plenty of space around the objects for plugins to customize.

In the below code example, you can see that the `Dummy Plugin` panel has a weight value of `150`. This means it will appear between `Organization` (weight `100`) and `DCIM` (weight `200`).

Example of custom code being used in a panel can be seen in the `Custom Dummy Plugin` panel below. The attribute `custom_template` is used to refer to the filename of a template. Templates need to be stored in the templates `inc` folder for the plugin (`/dummy_plugin/templates/dummy_plugin/inc/`).

If additional data is needed to render the custom template, callback functions can be used to collect this data. In the below example, the `Custom Dummy Plugin` panel is using the callback `get_dummy_data()` to dynamically populate the key `dummy_data` into the rendering context of this panel.

!!! tip
    Weights for already existing items can be found in the Nautobot source code (in `nautobot/<app>/homepage.py`) or with a web session open to your Nautobot instance, you can inspect an element of the home page using the developer tools.

``` python
from nautobot.core.apps import HomePageItem, HomePagePanel
from .models import DummyModel


def get_dummy_data(request):
    return DummyModel.objects.all()


layout = (
    HomePagePanel(
        name="Dummy Plugin",
        weight=150,
        items=(
            HomePageItem(
                name="Dummy Models",
                link="plugins:dummy_plugin:dummymodel_list",
                description="List dummy plugin models.",
                permissions=["dummy_plugin.view_dummymodel"],
                weight=100,
            ),
        ),
    ),
    HomePagePanel(
        name="Custom Dummy Plugin",
        custom_template="panel_dummy_example.html",
        custom_data={"dummy_data": get_dummy_data},
        permissions=["dummy_plugin.view_dummymodel"],
        weight=350,
    ),
)
```
