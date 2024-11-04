# Migrating to UI Component Framework
A guide for app developers transitioning to the UI Component Framework.

## Introduction

This guide helps you migrate your existing Nautobot app views to use the new UI Framework. The framework provides a declarative approach to building object detail views, reducing boilerplate code while ensuring consistency across the platform.

For complete UI Framework documentation, see: [Nautobot UI Framework Documentation](../../core/ui-component-framework.md)

## Why Migrate?

### Benefits
- Reduced template maintenance
- Consistent UI patterns across apps
- Built-in responsive layouts
- Standardized component behavior

### Before and After Example

Before (Template-based):
```python
# views.py
class DeviceDetailView(generic.ObjectView):
    queryset = Device.objects.all()
    template_name = 'myapp/device_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_devices'] = self.object.related_devices.all()
        context['custom_fields'] = self.object.get_custom_fields()
        return context

# template.html
{% extends 'base.html' %}
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
from nautobot.core.views import ObjectView
from nautobot.core.views.content import ObjectDetailContent
from nautobot.core.views.panels import (
    ObjectFieldsPanel,
    ObjectsTablePanel,
    TextPanel,
)

class DeviceDetailView(ObjectView):
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

### 3. Convert Views

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

### 4. Layout Organization

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

### 5. Custom Content

For custom content that doesn't fit existing panels:

1. Consider using `TextPanel` with custom formatting
2. Use `KeyValueTablePanel` with transformed data
3. Create a custom Panel class if needed:

```python
from nautobot.core.views.panels import Panel

class CustomPanel(Panel):
    def get_content(self, context):
        # Custom rendering logic
        return self.render_template(
            template_path="custom_template.html",
            extra_context={
                "data": self.transform_data(context)
            }
        )
```

## Best Practices for Migration

1. **Incremental Migration**
   - Migrate one view at a time
   - Test thoroughly after each conversion
   - Keep backup of template-based views

2. **Panel Organization**
   - Use consistent weight ranges (100-900)
   - Group related panels together
   - Consider mobile viewport display

3. **Performance Considerations**
   - Use select_related/prefetch_related in ObjectsTablePanel
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
- [ ] Update view classes and remove templates
- [ ] Test responsive layout behavior
- [ ] Verify all functionality works as before
- [ ] Remove deprecated template files
- [ ] Update documentation and tests
