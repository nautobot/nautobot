# Populating the Homepage

Both core applications and plugins can contribute items to the homepage by defining `layout` inside of their app's `homepage.py`. Using key and weight system, a developer can integrate amongst existing homepage objects or can create entirely new objects as desired.

## Modifying Existing Objects

By defining an object with the same identifier, a developer can modify existing objects. The object below shows modifying an existing object to have a custom template.

!!! tip
    Weights for already existing items can be found in the nautobot source code (in `homepage.py`) or with a web session open to your nautobot instance, you can inspect an element of the navbar using the developer tools.

``` python
layout = (
    HomePagePanel(
        name="Organization",
        items=(
            HomePageItem(
                name="Dummy Models",
                weight=150,
                link="plugins:dummy_plugin:dummymodel_list",
                description="List dummy plugin models.",
                permissions=["dummy_plugin.view_dummymodel"],
            ),
        ),
    ),
)
```

## Adding a new Homepage Object

The code below shows how to add a new panel to the navbar. A panel is defined by a `HomePagePanel` object. Similarly a group is defined using `HomePageGroup`. Both of these objects are used as containers for actual items.

The position in the homepage is defined by the weight. The lower the weight the closer to the start of the homepage the object will be. All core objects have weights in multiples of 100, meaning there is plenty of space around the objects for plugins to customize.

Below you can see `Dummy Plugin` has a weight value of `150`. This means the tab will appear between `Organization` and `DCIM`.

Example of custom code being used in a panel can be seen in `Custom Dummy Plugin`. The attribute `custom_template` is used to define either a string of HTML or a filename of a template. Templates need to be stored in the template and `inc` folder for the plugin (`dummy_plugin/templates/dummy_plugin/inc/`).

If additional data is needed for the custom template, callback functions can be used to collect data. Below is `get_dummy_data` which collects all records from `DummyModel`, the function is stored in a dictionary which is called when the homepage gets rendered.

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
