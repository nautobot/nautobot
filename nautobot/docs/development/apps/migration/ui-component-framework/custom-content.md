# Custom Content

For custom content that doesn't fit existing panels:

## Consider using `TextPanel` with custom formatting

```python title="views.py"
from nautobot.apps import views
from nautobot.apps.ui import TextPanel

class DeviceDetailView(views.NautobotUIViewSet):
    panels = [
        TextPanel(weight=100, context_field="custom_content"),
    ]

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        context["custom_content"] = "My Custom Content"
        return context
```

## Use `KeyValueTablePanel` with transformed data

```python title="views.py"
from nautobot.apps import views
from nautobot.apps.ui import KeyValueTablePanel, ObjectDetailContent
from nautobot.core.templatetags.helpers import (
    divide,
    placeholder,
    slugify,
    split,
)

class DeviceUIViewSet(views.NautobotUIViewSet):
    object_detail_content = ObjectDetailContent(
        panels=[
            KeyValueTablePanel(weight=100, value_transforms={
                "name": [slugify, placeholder],
                "list_of_names": split,
                "number_value": lambda v: divide(v, 3),
            }),
        ]
    )

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        context["data"] = {
            "name": "Some Example Name",
            "list_of_names": "Name1 Name2 Name3",
            "number_value": 1000,
        }
        return context
```

More built-in filters can be found in [`Nautobot Built-In Filters`](../../../../user-guide/platform-functionality/template-filters.md#nautobot-built-in-filters)

## Create a custom Panel class if needed

```python title="custom_panel.py"
from django.template.loader import get_template
from nautobot.apps.ui import Panel

class CustomPanel(Panel):

    # You can override default body panel
    def __init__(self, *, body_content_template_path="my_app/custom_panel/body_content.html", **kwargs):
        super().__init__(body_content_template_path=body_content_template_path, **kwargs)

    # Adding some extra context specially for this panel / or this custom template
    def get_extra_context(self, context):
        # This context will be passed to the label, header, body and footer render methods
        return {"custom_data": "I love Nautobot!"}
```

```python title="views.py"
from nautobot.apps import views
from nautobot.apps.ui import ObjectDetailContent
from device_app.custom_panel import CustomPanel

class DeviceUIViewSet(views.NautobotUIViewSet):
    object_detail_content = ObjectDetailContent(
        panels=[
            CustomPanel(weight=100),
        ]
    )
```

!!! Note
    If more custom behaviour is needed, you can override other `Panel` rendering methods.
    For more details please refer to the [`Panel` Code Reference.](../../../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.Panel)
