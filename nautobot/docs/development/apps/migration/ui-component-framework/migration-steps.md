# Migration Steps

## 1. Identify View Components

First, analyze your existing view to identify its components:

- Object fields display
- Related object tables
- Custom field groups
- Statistics/counts
- Text content (descriptions, notes)
- Custom template sections

## 2. Choose Appropriate Panels

Map your existing components to UI Framework panels:

| Current Feature              | UI Framework Panel                                                                               |
|------------------------------|--------------------------------------------------------------------------------------------------|
| Basic field display          | [`ObjectFieldsPanel`](../../../core/ui-component-framework.md#objectfieldspanel)                 |
| Related object tables        | [`ObjectsTablePanel`](../../../core/ui-component-framework.md#objectstablepanel)                 |
| Key-value data               | [`KeyValueTablePanel`](../../../core/ui-component-framework.md#objectfieldspanel)                |
| Grouped fields               | [`GroupedKeyValueTablePanel`](../../../core/ui-component-framework.md#groupedkeyvaluetablepanel) |
| Statistics of related models | [`StatsPanel`](../../../core/ui-component-framework.md#statspanel)                               |
| Markdown/JSON/text content   | [`TextPanel` or `ObjectTextPanel`](../../../core/ui-component-framework.md#basetextpanel)        |

## 3. Convert Views

### 1. Update your view class

```python
# Before
from nautobot.core.views import generic

class MyDetailView(generic.ObjectView):
    template_name = 'myapp/detail.html'

# After
from nautobot.apps import views

class MyDetailView(views.ObjectDetailViewMixin):
    object_detail_content = ObjectDetailContent(
        panels=[
            # Panel definitions
        ]
    )
```

### 2. Move context data into panels

In new approach most of the logic that currently sits in the `get_context_data` can be removed
and appropriate panel will handle data generation automatically.

#### Example

**Before:**

```python title="views.py"
from nautobot.core.views import generic
from my_app.models import Tenant, Circuit, Cluster, Device

class TenantView(generic.ObjectView):
    queryset = Tenant.objects.select_related("tenant_group")

    def get_extra_context(self, request, instance):
        stats = {
            "circuit_count": Circuit.objects.restrict(request.user, "view").filter(tenant=instance).count(),
            "cluster_count": Cluster.objects.restrict(request.user, "view").filter(tenant=instance).count(),
            "device_count": Device.objects.restrict(request.user, "view").filter(tenant=instance).count(),
        }

        return {"stats": stats, **super().get_extra_context(request, instance)}
```

**After:**

```python title="views.py"
from nautobot.apps import views
from my_app.models import Tenant, Circuit, Cluster, Device

class TenantView(views.ObjectDetailViewMixin):
    queryset = Tenant.objects.select_related("tenant_group")

    object_detail_content = ObjectDetailContent(
        panels=(
            StatsPanel(
                weight=100,
                label="Stats",
                section=SectionChoices.RIGHT_HALF,
                filter_name="tenant",
                related_models=[
                    Circuit,
                    Cluster,
                    Device,
                ],
            ),
        )
    )
```

## 4. Layout Organization

By using panels weights and sections you can determine how your app will display data.
The panel weight determines the order of panels within a section and depends on the chosen layout.
Panels in the same section (left/right/full-width) will be arranged based on their weight,
with lower-weight panels appearing first,
but the [layout choice](../../../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.SectionChoices)
(`TWO_OVER_ONE` or `ONE_OVER_TWO`)
decides what sections will be at the top.

**Organize your panels using sections and weights:**

```python
object_detail_content = ObjectDetailContent(
    panels=[
        # Left column
        ObjectFieldsPanel(
            weight=100,
            section=SectionChoices.LEFT_HALF,
        ),

        # Right column
        StatsPanel(
            weight=100,
            section=SectionChoices.RIGHT_HALF,
        ),

        # Full width at bottom
        ObjectsTablePanel(
            weight=200,
            section=SectionChoices.FULL_WIDTH,
        ),
    ]
)
```

## Migration Checklist

- [&nbsp;&nbsp;] Identify all template-based views to migrate
- [&nbsp;&nbsp;] Map current features to UI Framework panels
- [&nbsp;&nbsp;] Update view classes
- [&nbsp;&nbsp;] Verify all functionality works as before
- [&nbsp;&nbsp;] Remove deprecated template files
- [&nbsp;&nbsp;] Update documentation and tests
