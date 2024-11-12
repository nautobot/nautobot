# Migrating to UI Component Framework

A guide for app developers transitioning to the UI Component Framework.

## Introduction

This guide helps you migrate your existing Nautobot app views to use the new UI Component Framework. The framework provides a declarative approach to building object detail views, reducing boilerplate code while ensuring consistency across the platform.

For complete UI Component Framework documentation, see: [Nautobot UI Framework Documentation](../../../core/ui-component-framework.md)

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

```python title="views.py"
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
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
            ObjectsTablePanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                table_class=RelatedDeviceTable,
                table_attribute="related_devices",
            ),
        ]
    )
```
