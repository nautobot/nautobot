# Migrating to UI Component Framework
A guide for app developers transitioning to the UI Component Framework.

## Introduction

This guide helps you migrate your existing Nautobot app views to use the new UI Framework. The framework provides a declarative approach to building object detail views, reducing boilerplate code while ensuring consistency across the platform.

For complete UI Framework documentation, see: [Nautobot UI Framework Documentation](../../core/ui-component-framework.md)

## Why Migrate?

### Benefits
- Reduced template maintenance
- Consistent UI patterns across apps
- Standardized component behavior

### Before and After Example

Before (Template-based):
```python title="views.py"
from device_app.models import Device
from nautobot.core.views import generic

class DeviceDetailView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = 'myapp/device_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_devices'] = self.object.related_devices.all()
        context['custom_fields'] = self.object.get_custom_fields()
        return context
```
```html title="template.html"
# template.html
{% extends 'generic/object_retrieve.html' %}
{% block content %}
<div class="row">
    <div class="col-md-6">
        <div class="panel">
            <!-- Manual HTML for device fields -->
        </div>
    </div>
    <div class="col-md-6">
        <!-- More manual HTML -->
    </div>
</div>
{% endblock %}
```

After (UI Framework):
```python
from device_app.models import Device, RelatedDeviceTable
from nautobot.apps import views
from nautobot.apps.ui import (
    ObjectDetailContent,
    ObjectFieldsPanel,
    ObjectsTablePanel,
    SectionChoices,
)

class DeviceUIViewSet(views.NautobotUIViewSet):
    queryset = Device.objects.all()

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                fields="__all__",
                section=SectionChoices.LEFT_HALF,
                weight=100,
            ),
            ObjectsTablePanel(
                table_class=RelatedDeviceTable,
                table_attribute="related_devices",
                section=SectionChoices.RIGHT_HALF,
                weight=100,
            ),
        ]
    )
```

## Migration Steps

### 1. Identify View Components
First, analyze your existing view to identify its components:

- Object fields display
- Related object tables
- Custom field groups
- Statistics/counts
- Text content (descriptions, notes)
- Custom template sections

### 2. Choose Appropriate Panels

Map your existing components to UI Framework panels:

| Current Feature | UI Framework Panel |
|----------------|-------------------|
| Basic field display | `ObjectFieldsPanel` |
| Related object tables | `ObjectsTablePanel` |
| Key-value data | `KeyValueTablePanel` |
| Grouped fields | `GroupedKeyValueTablePanel` |
| Statistics | `StatsPanel` |
| Markdown/text content | `TextPanel` or `ObjectTextPanel` |

### 3. Select right panels weights/sections and tab layout.

The panel weight determines the order of panels within a section and depends on the chosen layout.
Panels in the same section (left/right/full-width) will be arranged based on their weight,
with lower-weight panels appearing first,
but the [layout choice](../../../../code-reference/nautobot/apps/ui/#nautobot.apps.ui.SectionChoices)
+(TWO_OVER_ONE or ONE_OVER_TWO)
decides what sections will be at the top.

### 4. Convert Views

1. Update your view class:
```python
# Before
class MyDetailView(generic.ObjectView):
    template_name = 'myapp/detail.html'

# After
class MyDetailView(ObjectView):
    object_detail_content = ObjectDetailContent(
        panels=[
            # Panel definitions
        ]
    )
```

2. Move context data into panels:
```python
# Before
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['stats'] = self.get_stats()
    return context

# After
StatsPanel(
    filter_name="device",
    related_models=[
        Device,
        (Circuit, "circuit_terminations__device__in")
    ],
    section=SectionChoices.RIGHT_HALF,
    weight=100,
)
```

### 5. Layout Organization

Organize your panels using sections and weights:

```python
object_detail_content = ObjectDetailContent(
    panels=[
        # Left column
        ObjectFieldsPanel(
            section=SectionChoices.LEFT_HALF,
            weight=100,
        ),

        # Right column
        StatsPanel(
            section=SectionChoices.RIGHT_HALF,
            weight=100,
        ),

        # Full width at bottom
        ObjectsTablePanel(
            section=SectionChoices.FULL_WIDTH,
            weight=200,
        ),
    ]
)
```

### 6. Custom Content

For custom content that doesn't fit existing panels:

1. Consider using `TextPanel` with custom formatting

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

2. Use `KeyValueTablePanel` with transformed data

```python title="views.py"
from nautobot.apps import views
from nautobot.apps.ui import KeyValueTablePanel
from nautobot.core.templatetags.helpers import (
    divide,
    placeholder,
    slugify,
    split,
)

class DeviceDetailView(views.NautobotUIViewSet):
    panels = [
        KeyValueTablePanel(weight=100, value_transforms={
            "name": [slugify, placeholder],
            "list_of_names": split,
            "number_value": lambda v: divide(v, 3),
        }),
    ]

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        context["data"] = {
            "name": "Some Example Name",
            "list_of_names": "Name1 Name2 Name3",
            "number_value": 1000,
        }
        return context
```

More built-in filters can be found in [`Nautobot Built-In Filters`](../../../user-guide/platform-functionality/template-filters.md#nautobot-built-in-filters)


3. Create a custom Panel class if needed:

```python title="custom_panel.py"
from django.template.loader import get_template
from nautobot.apps.ui import Panel

class CustomPanel(Panel):

    # You can override default body panel
    def __init__(self, *, body_content_template_path="custom_template_path.html", **kwargs):
        super().__init__(body_content_template_path=body_content_template_path, **kwargs)

    # Adding some extra context specially for this panel / or this custom template
    def get_extra_context(self, context):
        # This context will be passed to the label, header, body and footer render methods
        return {"custom_data": "I love Nautobot!"}
```
```python title="views.py"
from nautobot.apps import views
from device_app.custom_panel import CustomPanel

class DeviceDetailView(views.NautobotUIViewSet):
    panels = [
        CustomPanel(weight=100),
    ]
```

If need more custom behaviour, you can override other `Panel` rendering methods. For more details please refer to the [`Panel` Code Reference.](#todo: link goes here)

## Best Practices for Migration

1. **Incremental Migration**
   - Migrate one view at a time
   - Test thoroughly after each conversion
   - Keep backup of template-based views

2. **Panel Organization**
   - Use weights relative to the `Panel.`WEIGHT_*_PANEL` constants for consistency.
   - Group related panels together

3. **Performance Considerations**
   - Use select_related/prefetch_related in ObjectsTablePanel (though note that BaseTable may handle some simple optimizations automatically)
   - Optimize StatsPanel queries
   - Cache complex transformations

4. **Common Patterns**
```python
# Statistics and related objects
StatsPanel(
    filter_name="device_type",
    related_models=[Device],
    section=SectionChoices.RIGHT_HALF,
    weight=100,
)

# Custom fields grouping
GroupedKeyValueTablePanel(
    body_id="custom-fields",
    data=self.get_custom_field_groups(),
    section=SectionChoices.FULL_WIDTH,
    weight=200,
)

# Description with markdown
ObjectTextPanel(
    object_field="description",
    render_as=BaseTextPanel.RenderOptions.MARKDOWN,
    section=SectionChoices.FULL_WIDTH,
    weight=300,
)
```


## Migration Checklist

- [ ] Identify all template-based views to migrate
- [ ] Map current features to UI Framework panels
- [ ] Update view classes
- [ ] Verify all functionality works as before
- [ ] Remove deprecated template files
- [ ] Update documentation and tests
