# Nautobot UI Component Framework

## Table of Contents

- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Core Concepts](#core-concepts)
- [Panel Types](#panel-types)
- [Button Types](#button-types)
- [Complete Example](#complete-example)
- [Layouts and Sections](#layouts-and-sections)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Introduction

The Nautobot UI Framework revolutionizes how you create object detail views in your applications. Instead of writing HTML templates, you declaratively define your UI structure using Python objects, resulting in consistent, maintainable, and responsive interfaces.

<!-- pyml disable-num-lines 5 no-inline-html -->
<div class="grid cards example-images" markdown>

- ![UI Framework Example](../../media/development/core/ui-component-framework/ui-framework-example.png){ .on-glb }

</div>

### Why Use the UI Framework?

- ✨ **Reduced Development Time**: Eliminate boilerplate HTML/CSS
- 🎯 **Consistency**: Automatic adherence to Nautobot's design patterns
- 🔄 **Reusable Components**: Compose views from pre-built panels
- 🛠 **Extensible**: Easy to customize and extend

## Getting Started

### Basic Setup

1. Create a view that inherits from `NautobotUIViewSet`:

```python
from nautobot.apps import views
from nautobot.apps.ui import ObjectDetailContent, SectionChoices, ObjectFieldsPanel

class ExampleUIViewSet(views.NautobotUIViewSet):
    queryset = Example.objects.all()
    ...

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
               weight=100,
               section=SectionChoices.LEFT_HALF,
                fields="__all__"
            )
        ]
    )
```

## Core Concepts

### ObjectDetailContent Definition

Each object detail view (whether based on a `NautobotUIViewSet` or a legacy `ObjectView`) that implements the UI Framework does so by defining an `object_detail_content` attribute which is an instance of the `ObjectDetailContent` class. This class automatically does a lot of the "heavy lifting" for you as a developer, but you'll generally want to configure it for your specific data model, usually by defining any of the following:

- Extra `Tab`s (beyond the default "main", "advanced", "contacts", etc. tabs that are automatically provided)
- `Panel`s in the "main" tab or any extra tabs
- Extra `Button`s to display at the top of the page (beyond the default "actions" dropdown)

### Tabs

A `Tab` is one of the major building blocks of your UI. The user can toggle between tabs, each of which displays distinct page content, typically consisting of one or more `Panel`s. Multiple tabs can be rendered in a single HTML response (for example, the "main" and "advanced" tabs are both part of the same page; toggling between them is a client-side action only and does not require Nautobot to reload or re-render the page), while to optimize performance, certain other tabs may correspond to distinct `View`s that are retrieved and rendered on request. The UI Framework supports both patterns.

### Panels

`Panel`s are another of the major building blocks of your UI. They contain specific types of content and can be positioned within sections within a Tab.

<!-- pyml disable-num-lines 5 no-inline-html -->
<div class="grid cards example-images" markdown>

- ![Basic Panel Layout](../../media/development/core/ui-component-framework/basic-panel-layout.png){ .on-glb }

</div>

### Buttons

`Button`s are the third major building block for the UI. Defining `extra_buttons` on your `ObjectDetailContent` instance allows you to add buttons that appear at the top of the page, alongside the standard "actions" dropdown and any custom buttons added by Apps. These buttons may operate as simple hyperlinks, or may use JavaScript to provide more advanced functionality.

#### Buttons Example

```python
from nautobot.apps.ui import ObjectDetailContent, Button

object_detail_content = ObjectDetailContent(
        panels=[...],
        extra_buttons=[
            Button(
                weight=100,
                label="Check Secret",
                icon="mdi-test-tube",
                javascript_template_path="extras/secret_check.js",
                attributes={"onClick": "checkSecret()"},
            ),
        ],
    )
```

<!-- pyml disable-num-lines 5 no-inline-html -->
<div class="grid cards example-images" markdown>

- ![Buttons Example](../../media/development/core/ui-component-framework/buttons-example.png){ .on-glb }

</div>

## Panel Types

### Base Panel

The Panel component serves as a base class for creating individual display panels within a Layout system. You'll rarely use it directly, but it's important to understand as the base class for the more feature-filled subclasses described below.

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.Panel)

#### Panel Examples

```python
from nautobot.apps.ui import Panel, SectionChoices

Panel(
   weight=100,
   section=SectionChoices.FULL_WIDTH,
   label="Panel Header",
)
```

```python
from nautobot.apps.ui import Panel, SectionChoices

Panel(
    weight=200,
    section=SectionChoices.RIGHT_HALF,
    label="Optional Params Included",
    body_content_template_path="path/to/template/body_content_template.html",
    header_extra_content_template_path="path/to/template/header_extra_content_template.html",
    footer_content_template_path="path/to/template/footer_content_template.html",
    template_path="path/to/template/template.html",
    body_wrapper_template_path="path/to/template/body_wrapper_template.html",
)
```

### ObjectFieldsPanel

`ObjectFieldsPanel` is designed to automatically render object attributes in a table format. It's particularly useful for displaying model instances or any object with defined attributes. This panel inherits from `KeyValueTablePanel`.

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.ObjectFieldsPanel)

NOTE:
    When `fields="__all__"`, the panel automatically excludes:

    - ManyToMany fields and reverse relations (these should be displayed via `ObjectsTablePanel` if desired)
    - hidden fields (name starting with `_` or explicitly declared as `hidden=True`)
    - `id`, `created`, `last_updated` (these are automatically displayed elsewhere in the standard view template)
    - `comments`, `tags` (these are automatically added as standalone panels)

#### ObjectFieldsPanel Examples

```python
from nautobot.apps.ui import ObjectFieldsPanel, SectionChoices

ObjectFieldsPanel(
   weight=100,
   section=SectionChoices.LEFT_HALF,
   label="Object Fields Panel",
   context_object_key="obj",
)
```

```python
from nautobot.apps import ui
from nautobot.core.templatetags import helpers


panels = ui.ObjectFieldsPanel(
    weight=200,
    section=ui.SectionChoices.LEFT_HALF,
    label="Object Fields Panel",
    fields=["name", "number", "notes", "notexists"],
    context_object_key="obj",
    ignore_nonexistent_fields=True,
    value_transforms={
        "name": [helpers.bettertitle],
        "number": [lambda v: helpers.hyperlinked_field(v, "https://nautobot.com")]
    },
),
```

<!-- pyml disable-num-lines 5 no-inline-html -->
<div class="grid cards example-images" markdown>

- ![ObjectFieldsPanel Example](../../media/development/core/ui-component-framework/object-fields-panel-example.png){ .on-glb }
- ![ObjectFieldsPanel Example](../../media/development/core/ui-component-framework/object-fields-panel-example_2.png){ .on-glb }

</div>

### KeyValueTablePanel

`KeyValueTablePanel` is a Panel component that displays data in a two-column table format, commonly used in object detail views. It extends the base `Panel` class and provides additional functionality for data display and transformation.

!!! tip
    For displaying the attributes of a specific data model instance, you'll more commonly want to use the `ObjectFieldsPanel` subclass rather than using a `KeyValueTablePanel` directly.

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.KeyValueTablePanel)

#### KeyValueTablePanel Examples

```python
from nautobot.apps.ui import KeyValueTablePanel

KeyValueTablePanel(
    weight=100,
    data={
        "speed": "1000000",
        "notes": "**Important**"
    },
)
```

```python
from nautobot.apps.ui import KeyValueTablePanel

KeyValueTablePanel(
    weight=100,
    data={
        "speed": "1000000",
        "notes": "**Important**",
    },
    hide_if_unset=(),
    value_transforms={
        "speed": [             # List of functions to apply in order
            humanize_speed,    # Convert 1000000 to "1 Gbps"
            placeholder        # Show placeholder if empty
        ],
        "notes": [
            render_markdown,   # Convert markdown to HTML
            placeholder       # Show placeholder if empty
        ]
    },
)
```

### GroupedKeyValueTablePanel

`GroupedKeyValueTablePanel` is a specialized version of `KeyValueTablePanel` that organizes data into collapsible accordion groups. This is used in the standard template for displaying grouped custom/computed fields when present.

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.GroupedKeyValueTablePanel)

#### GroupedKeyValueTablePanel Examples

```python
from nautobot.apps.ui import GroupedKeyValueTablePanel, SectionChoices

GroupedKeyValueTablePanel(
    weight=300,
    section=SectionChoices.FULL_WIDTH,
    label="Grouped Information",
    body_id="network-details",
    # Data Structure
    data={
        "Network": {            # Group name (shown as accordion header)
            "VLAN": "100",      # Key-value pairs in this group
            "IP Range": "192.168.1.0/24"
        },
        "Physical": {           # Another group
            "Location": "Rack A1",
            "Height": "2U"
        },
        "": {                   # Empty string for ungrouped items
            "Notes": "Important info"
        }
    },
)
```

<!-- pyml disable-num-lines 7 no-inline-html -->
<div class="grid cards example-images" markdown>

- ![GroupedKeyValueTablePanel Example 1](../../media/development/core/ui-component-framework/grouped-key-value-table-panel-example-1.png){ .on-glb }

- ![GroupedKeyValueTablePanel Example 2](../../media/development/core/ui-component-framework/grouped-key-value-table-panel-example-2.png){ .on-glb }

</div>

### StatsPanel

`StatsPanel` is a Panel component that displays statistical information with clickable links to filtered views of related models. It's particularly useful for dashboards and summary views that provide quick access to filtered data sets.

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.StatsPanel)

#### StatsPanel Examples

```python
from nautobot.apps.ui import StatsPanel, SectionChoices

StatsPanel(
    weight=700,
    section=SectionChoices.RIGHT_HALF,
    label="Statistics",
    filter_name="location",
    related_models=[  # Models to show statistics for
        Device,  # Direct model reference
                 # Will count all devices related to this object by their `location` key
        (Circuit, "circuit_terminations__location__in"),
                 # Tuple of (Model, query_string)
                 # For complex relationships
        (VirtualMachine, "cluster__location__in")
                 # Another complex relationship example
    ],
)
```

<!-- pyml disable-num-lines 5 no-inline-html -->
<div class="grid cards example-images" markdown>

- ![StatsPanel Code Example](../../media/development/core/ui-component-framework/stats-panel-example-code.png){ .on-glb }
- ![StatsPanel Example](../../media/development/core/ui-component-framework/stats-panel-example.png){ .on-glb }

</div>

### BaseTextPanel

`BaseTextPanel` is a specialized Panel component designed to display single values in various text formats including plaintext, JSON, YAML, Markdown, and code snippets.

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.BaseTextPanel)

<!-- pyml disable-num-lines 5 no-inline-html -->
<div class="grid cards" style="width: 300px;" markdown>

- ![Text Panels Family](../../media/development/core/ui-component-framework/text-panels-family.png){ .on-glb }

</div>

### ObjectTextPanel

`ObjectTextPanel` renders content from a specific field of an object in the context. It simplifies the display of object attributes in various text formats (Markdown, JSON, YAML, etc.).

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.ObjectTextPanel)

#### ObjectTextPanel Examples

```python
from nautobot.apps.ui import ObjectTextPanel, SectionChoices

ObjectTextPanel(
   weight=500,
   section=SectionChoices.FULL_WIDTH,
   label="Description",
   object_field="description",
   render_as=ObjectTextPanel.RenderOptions.MARKDOWN,
   render_placeholder=True,
)
```

### TextPanel

`TextPanel` renders content from a specified context field. It provides a simple way to display text content in various formats (Markdown, JSON, YAML, plaintext, or code) from the rendering context.

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.TextPanel)

#### TextPanel Examples

```python
from nautobot.apps.ui import TextPanel, SectionChoices

TextPanel(
   weight=600,
   section=SectionChoices.FULL_WIDTH,
   label="Custom Content",
   context_field="text",
   render_as=TextPanel.RenderOptions.CODE,
   render_placeholder=True,
)
```

### DataTablePanel

`DataTablePanel` is a Panel component that renders tabular data directly from a list of dictionaries, providing a lightweight alternative to `django_tables2` Table classes.

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.DataTablePanel)

Note:
    `columns`/`context_columns_key` and `column_headers`/`context_column_headers_key` are mutually exclusive pairs.

<!-- pyml disable-num-lines 5 no-inline-html -->
<div class="grid cards example-images" markdown>

- ![Table Panels Family](../../media/development/core/ui-component-framework/table-panels-family.png){ .on-glb }

</div>

#### DataTablePanel Examples

```python
from nautobot.apps.ui import DataTablePanel

DataTablePanel(
   weight=100,
   context_data_key="data",
   columns=["one", "two", "three"],
   column_headers=["One", "Two", "Three"]
)
```

### ObjectsTablePanel

The `ObjectsTablePanel` is a powerful component for rendering tables of Django model objects,
particularly suited for displaying related objects within a detail view.
It integrates with `django_tables2` and provides extensive customization options.

#### Configuration Parameters

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.ObjectsTablePanel)

##### Core Configuration

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `context_table_key` | No | `None` | Key for pre-configured table in render context |
| `table_class` | No | `None` | Table class to instantiate (e.g., DeviceTable) |
| `table_filter` | No | `None` | Filter name for queryset (e.g., `location_type`) |
| `table_attribute` | No | `None` | Object attribute containing queryset |
| `table_title` | No | Model's plural name | Title displayed in panel heading |

##### Query Optimization

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `select_related_fields` | No | `None` | Fields to include in `select_related()` |
| `prefetch_related_fields` | No | `None` | Fields to include in `prefetch_related()` |
| `order_by_fields` | No | `None` | Fields to order queryset by |
| `max_display_count` | No | User preference | Maximum items to display |

##### Column Configuration

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `include_columns` | No | `None` | List of columns to display |
| `exclude_columns` | No | `None` | List of columns to hide |
| `hide_hierarchy_ui` | No | `False` | Disable tree model indentation |

##### Actions Configuration

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `add_button_route` | No | `"default"` | Route for "add" button URL |
| `add_permissions` | No | Model defaults | Required permissions for "add" button |
| `enable_bulk_actions` | No | `False` | Enable bulk action checkboxes |
| `related_field_name` | No | `table_filter` value | Field linking to base model |

#### ObjectsTablePanel Examples

```python
from nautobot.apps.ui import ObjectsTablePanel, SectionChoices

ObjectsTablePanel(
    weight=100,
    section=SectionChoices.RIGHT_HALF,
    table_class=ExampleTable,
    table_filter="example_name",
    table_title="Example Table",

)
```

```python
from nautobot.apps.ui import ObjectsTablePanel, SectionChoices

ObjectsTablePanel(
    weight=200,
    section=SectionChoices.FULL_WIDTH,
    context_table_key="example_table_instance",
    table_title="Example Table",
    hide_hierarchy_ui=True,
    related_field_name="example_id",
    enable_bulk_actions=True,
    add_permissions=["dcim:add_device"],
    max_display_count=10,
    prefetch_related_fields=["devices"],
    select_related_fields=["manufacturers", "locations"],
)
```

## Button Types

### Button

The Button component defines a single button in an object detail view.

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.Button)

#### Button Examples

```python
class SecretUIViewSet(...):
    ...
    object_detail_content = ObjectDetailContent(
        panels=[...],
        extra_buttons=[
            Button(
                weight=100,
                label="Check Secret",
                icon="mdi-test-tube",
                javascript_template_path="extras/secret_check.js",
                attributes={"onClick": "checkSecret()"},
            ),
        ],
    )
```

<!-- pyml disable-num-lines 5 no-inline-html -->
<div class="grid cards example-images" markdown>

- ![Button Example](../../media/development/core/ui-component-framework/button-example.png){ .on-glb }

</div>

### DropdownButton

`DropdownButton` is a subclass of `Button` that may itself contain other `Buttons` as its `children`, which it will render as a dropdown menu. For an example of usage, refer to the `Add Components` dropdown on the Device detail view.

[Code reference](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.DropdownButton)

#### DropdownButton Examples

```python
class DeviceView(generic.ObjectView):
    ...
    object_detail_content = ObjectDetailContent(
        extra_buttons=[
            object_detail.DropdownButton(
                weight=100,
                color=ButtonColorChoices.BLUE,
                label="Add Components",
                icon="mdi-plus-thick",
                required_permissions=["dcim.change_device"],
                children=(
                    object_detail.Button(
                        weight=100,
                        link_name="dcim:device_consoleports_add",
                        label="Console Ports",
                        icon="mdi-console",
                        required_permissions=["dcim.add_consoleport"],
                    ),
                    object_detail.Button(
                        weight=200,
                        link_name="dcim:device_consoleserverports_add",
                        label="Console Server Ports",
                        icon="mdi-console-network-outline",
                        required_permissions=["dcim.add_consoleserverport"],
                    ),
                    ...
                ),
            ),
        ],
    )
```

<!-- pyml disable-num-lines 5 no-inline-html -->
<div class="grid cards example-images" markdown>

- ![DropdownButton Example](../../media/development/core/ui-component-framework/dropdown-button-example.png){ .on-glb }

</div>

## Complete Example

```python title="views.py"
from nautobot.apps.ui import (
    SectionChoices,
    ObjectFieldsPanel,
    ObjectDetailContent,
    StatsPanel,
)
from nautobot.apps import views
from your_app.models import Location, Device, Circuit

class LocationUIViewSet(views.NautobotUIViewSet):
    queryset = Location.objects.all()

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
               weight=100,
               section=SectionChoices.LEFT_HALF,
               fields="__all__",
            ),
            StatsPanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                filter_name="location",
                related_models=[
                    Device,
                    (Circuit, "circuit_terminations__location__in")
                ],
            ),
            GroupedKeyValueTablePanel(
                weight=300,
                section=SectionChoices.FULL_WIDTH,
                body_id="custom-fields",
                data={
                    "Network": {
                        "VLAN": "100",
                        "IP Range": "192.168.1.0/24"
                    }
                },
            ),
            ObjectTextPanel(
                weight=400,
                section=SectionChoices.FULL_WIDTH,
                object_field="description",
                render_as=BaseTextPanel.RenderOptions.MARKDOWN,
            ),
        ]
    )
```

## Layouts and Sections

### [Render Options](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.BaseTextPanel.RenderOptions)

### [Section Options](../../code-reference/nautobot/apps/ui.md#nautobot.apps.ui.SectionChoices)

## Best Practices

### 1. Panel Organization

- Use consistent weights across your application
- Group related information in adjacent panels
- Consider various screen sizes when choosing sections, especially for ObjectsTablePanel

### 2. Performance

- Be specific with field selections - select only needed fields for better performance
- Ensure usage of `select_related` or `prefetch_related`

### 3. User Experience

- Provide clear, descriptive labels
- Use consistent patterns across views
- Implement proper error handling for custom business logic if writing custom panels

### 4. Maintenance

- Document custom transformations
- Keep related model lists updated
- Use meaningful `body_id` values

## Troubleshooting

### Common Issues and Solutions

1. Panels Not Appearing
    - Verify section choices
    - Check panel weights
    - Confirm data availability

2. Performance Issues
    - Review query complexity in StatsPanel
    - Optimize field selections
    - Check database indexes

3. Layout Problems
    - Validate section assignments
    - Review weight ordering
    - Check responsive behavior

4. Value Rendering
    - Verify transform functions
    - Check data types
    - Confirm template paths
