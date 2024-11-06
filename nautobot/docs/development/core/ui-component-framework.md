# Nautobot UI Framework

## Table of Contents
- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Core Concepts](#core-concepts)
- [Panel Types](#panel-types)
- [Complete Example](#complete-example)
- [Layouts and Sections](#layouts-and-sections)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Introduction

The Nautobot UI Framework revolutionizes how you create object detail views in your applications. Instead of writing HTML templates, you declaratively define your UI structure using Python objects, resulting in consistent, maintainable, and responsive interfaces.

//TODO: (include image) <img src="/api/placeholder/800/400" alt="UI Framework Example" />
*Example of a detail view created with the UI Framework*

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

class ExampleUIViewSet(views.NautobotUIViewSet):
    queryset = Example.objects.all()
    ...

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__"
            )
        ]
    )
```

//TODO: (include image) <img src="/api/placeholder/600/300" alt="Basic Panel Layout" />
*Basic panel layout with ObjectFieldsPanel*

## Core Concepts

### ViewSet Configuration
The UI Framework is built around the concept of configurable ViewSets. Each ViewSet defines:
- Query handling
- Panel layouts
- Content organization

### Panels
Panels are the building blocks of your UI. They contain specific types of content and can be positioned within sections.

//TODO: (include image) <img src="/api/placeholder/700/350" alt="Panel Structure" />
*Panel structure showing different sections and layouts*

## Panel Types

### Base Panel Properties
The Panel component serves as a base class for creating individual display panels within a Layout system.

#### Configuration Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `label` | No | `""` | The display label for the panel. If empty, no label will be shown. |
| `section` | No | `SectionChoices.FULL_WIDTH` | Determines which layout section the panel belongs to. |
| `weight` | Yes | - | Integer determining component's rendering order relative to peers |
| `body_id` | No | `None` | HTML element ID to attach to the panel's body wrapper. |
| `body_content_template_path` | No | `None` | Template path for rendering content within the panel body. |
| `header_extra_content_template_path` | No | `None` | Template path for additional header content besides the label. |
| `footer_content_template_path` | No | `None` | Template path for footer content. |
| `template_path` | No | `"components/panel/panel.html"` | Template path for the overall panel structure. |
| `body_wrapper_template_path` | No | `"components/panel/body_wrapper_generic.html"` | Template path for the panel body wrapper. |

#### Examples

```python
Panel(
    label="Panel Header",
    section=SectionChoices.FULL_WIDTH,
    weight=100,
)
```

```python
Panel(
    label="Optional Params Included",
    section=SectionChoices.RIGHT_HALF,
    weight=200,
    body_content_template_path="path/to/template/body_content_template.html"
    header_extra_content_template_path="path/to/template/header_extra_content_template.html"
    footer_content_template_path="path/to/template/footer_content_template.html"
    template_path="path/to/template/template.html"
    body_wrapper_template_path="path/to/template/body_wrapper_template.html"
)
```

### 1. ObjectFieldsPanel
`ObjectFieldsPanel` is designed to automatically render object attributes in a table format. It's particularly useful for displaying model instances or any object with defined attributes. This panel inherits from `KeyValueTablePanel`.

#### Configuration Parameters

Note: This panel inherits all parameters from both `Panel` and `KeyValueTablePanel` base classes.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `fields` | No | `"__all__"` | List of fields to display or `"__all__"` for automatic field discovery |
| `exclude_fields` | No | `()` | List of fields to exclude when using `"__all__"` |
| `context_object_key` | No | `"object"` | Key in the render context containing the target object |
| `ignore_nonexistent_fields` | No | `False` | Whether to ignore fields listed in `fields` that don't exist on the object |
| `value_transforms` | No | `{}` | Dictionary mapping keys to lists of transform functions for custom rendering. |
| `label` | No | `None` | Panel label (defaults to object's `verbose_name` if not provided) |
| `hide_if_unset` | No | `()` | List of keys to hide completely when their values are falsey. |

NOTE:
    When `fields="__all__"`, the panel automatically excludes: ManyToMany fields, Reverse relations, Hidden fields and Special fields (`id`, `created`, `last_updated`, `comments`, `tags`). `comments` and `tags` are automatically added as standalone panels.

#### Examples

```python
ObjectFieldsPanel(
    label="Object Fields Panel",
    section=SectionChoices.LEFT_HALF,
    context_object_key="obj",
)
```

```python
ObjectFieldsPanel(
    label="Object Fields Panel",
    fields=["name", "status", "type", "notes"],
    section=SectionChoices.LEFT_HALF,
    context_object_key="obj",
    ignore_nonexistent_fields=True,
    weight=200,
    value_transforms={
        "status": [status_to_badge],
        "type": [type_to_link]
    },
)
```

//TODO: (include image) <img src="/api/placeholder/600/200" alt="ObjectFieldsPanel Example" />
*ObjectFieldsPanel with field descriptions*

### 2. KeyValueTablePanel
`KeyValueTablePanel` is a Panel component that displays data in a two-column table format, commonly used in object detail views. It extends the base `Panel` class and provides additional functionality for data display and transformation.

#### Configuration Parameters

Note: This panel inherits all parameters from `Panel` base classes.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `data` | Yes | None | Dictionary of key-value pairs to display. Can be `None` if using dynamic data via `get_data()`. |
| `hide_if_unset` | No | `()` | List of keys to hide completely when their values are falsey. |
| `value_transforms` | No | `{}` | Dictionary mapping keys to lists of transform functions for custom rendering. |
| `body_wrapper_template_path` | No | `"components/panel/body_wrapper_key_value_table.html"` | Template for the table wrapper. |


#### Examples

```python
KeyValueTablePanel(
    data={
        "speed": "1000000",
        "notes": "**Important**"
    },
)
```

```python
KeyValueTablePanel(
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

//TODO: (include image) <img src="/api/placeholder/600/200" alt="ObjectFieldsPanel Example" />
*ObjectFieldsPanel with field descriptions*


### 3. GroupedKeyValueTablePanel
`GroupedKeyValueTablePanel` is a specialized version of `KeyValueTablePanel` that organizes data into collapsible accordion groups. It's particularly useful for displaying hierarchical key-value data or grouped custom fields.

#### Configuration Parameters

Note: This panel inherits all parameters from both `Panel` and `KeyValueTablePanel` base classes.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `body_id` | Yes | None | HTML element ID to attach to the panel's body wrapper. |


#### Examples

```python
GroupedKeyValueTablePanel(
    body_id="network-details"
    label="Grouped Information",
    weight=300,
    section=SectionChoices.FULL_WIDTH,
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

//TODO: (include image) <img src="/api/placeholder/600/200" alt="ObjectFieldsPanel Example" />
*ObjectFieldsPanel with field descriptions*


### 4. StatsPanel

`StatsPanel` is a Panel component that displays statistical information with clickable links to filtered views of related models. It's particularly useful for dashboards and summary views that provide quick access to filtered data sets.

#### Configuration Parameters

Note: This panel inherits all parameters from `Panel` base classes.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `filter_name` | Yes | - | Query parameter name for filtering (e.g., 'tenant', 'location') |
| `related_models` | No | `None` | List of models or (model, query_string) tuples to show stats for |
| `body_content_template_path` | No | `"components/panel/stats_panel_body.html"` | Template for panel content |


#### Examples

```python
StatsPanel(
    filter_name="location",
    related_models=[           # Models to show statistics for
        Device,               # Direct model reference
                             # Will count all devices related to this object

        (Circuit, "circuit_terminations__location__in"),
                             # Tuple of (Model, query_string)
                             # For complex relationships

        (VirtualMachine, "cluster__location__in")
                             # Another complex relationship example
    ],
    label="Statistics",
    section=SectionChoices.RIGHT_HALF,
    weight=700,
)
```

//TODO: (include image) <img src="/api/placeholder/600/200" alt="ObjectFieldsPanel Example" />
*ObjectFieldsPanel with field descriptions*

### Text Panels Family

`BaseTextPanel` is a specialized Panel component designed to display single values in various text formats including plaintext, JSON, YAML, Markdown, and code snippets.

#### Configuration Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `render_as` | No | `RenderOptions.MARKDOWN` | The format to use for rendering content |
| `render_placeholder` | No | `True` | Whether to show placeholder text for empty values |
| `body_content_template_path` | No | `"components/panel/body_content_text.html"` | Template path for rendering the content |


### 5. ObjectTextPanel

`ObjectTextPanel` renders content from a specific field of an object in the context. It simplifies the display of object attributes in various text formats (Markdown, JSON, YAML, etc.).

#### Configuration Parameters

Note: This panel inherits all parameters from both `Panel` and `BaseTextPanel` base classes.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `object_field` | No | `None` | The name of the field to render from the context object |
| All BaseTextPanel parameters | No | - | Inherits all parameters from BaseTextPanel |


#### Examples

```python
ObjectTextPanel(
    object_field="description",
    render_as=BaseTextPanel.RenderOptions.MARKDOWN,
    render_placeholder=True,
    label="Description",
    section=SectionChoices.FULL_WIDTH,
    weight=500
)
```

//TODO: (include image) <img src="/api/placeholder/600/200" alt="ObjectFieldsPanel Example" />
*ObjectFieldsPanel with field descriptions*

### 6. TextPanel

`TextPanel` renders content from a specified context field. It provides a simple way to display text content in various formats (Markdown, JSON, YAML, plaintext, or code) from the rendering context.

#### Configuration Parameters

Note: This panel inherits all parameters from both `Panel` and `BaseTextPanel` base classes.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `context_field` | No | `"text"` | The name of the field in the context to render |
| All BaseTextPanel parameters | No | - | Inherits all parameters from BaseTextPanel |


#### Examples

```python
TextPanel(
    context_field="text",
    render_as=BaseTextPanel.RenderOptions.CODE,
    render_placeholder=True,
    label="Custom Content",
    section=SectionChoices.FULL_WIDTH,
    weight=600
)
```

//TODO: (include image) <img src="/api/placeholder/600/200" alt="ObjectFieldsPanel Example" />
*ObjectFieldsPanel with field descriptions*

### Table Panels Family

### 7. DataTablePanel

`DataTablePanel` is a Panel component that renders tabular data directly from a list of dictionaries, providing a lightweight alternative to django_tables2 Table classes.

#### Configuration Parameters

Note: This panel inherits all parameters from `Panel` base classes.

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `context_data_key` | Yes | - | Key in the render context containing the table data |
| `columns` | No | `None` | List of dictionary keys defining column order |
| `context_columns_key` | No | `None` | Context key containing column definitions |
| `column_headers` | No | `None` | List of column header labels |
| `context_column_headers_key` | No | `None` | Context key containing header labels |
| `body_wrapper_template_path` | No | `"components/panel/body_wrapper_table.html"` | Template for table wrapper |
| `body_content_template_path` | No | `"components/panel/body_content_data_table.html"` | Template for table content |

Note:
    `columns`/`context_columns_key` and `column_headers`/`context_column_headers_key` are mutually exclusive pairs.


#### Examples

```python
DataTablePanel(
    context_data_key="data",
    weight=100,
    columns=[1, 2, 3],
    column_headers=["One", "Two", "Three"]
)
```

//TODO: (include image) <img src="/api/placeholder/600/200" alt="ObjectFieldsPanel Example" />
*ObjectFieldsPanel with field descriptions*

### 8. ObjectsTablePanel

The `ObjectsTablePanel` is a powerful component for rendering tables of Django model objects, particularly suited for displaying related objects within a detail view. It integrates with django_tables2 and provides extensive customization options.

#### Configuration Parameters

Note: This panel inherits all parameters from `Panel` base classes.

##### Core Configuration
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `context_table_key` | No | `None` | Key for pre-configured table in render context |
| `table_class` | No | `None` | Table class to instantiate (e.g., DeviceTable) |
| `table_filter` | No | `None` | Filter name for queryset (e.g., 'location_type') |
| `table_attribute` | No | `None` | Object attribute containing queryset |
| `table_title` | No | Model's plural name | Title displayed in panel heading |

##### Query Optimization
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `select_related_fields` | No | `None` | Fields to include in select_related() |
| `prefetch_related_fields` | No | `None` | Fields to include in prefetch_related() |
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


#### Examples

```python
ObjectsTablePanel(
    section=SectionChoices.RIGHT_HALF,
    weight=100,
    table_class=ExampleTable,
    table_filter="example_name",
    table_title="Example Table",

)
```

```python
ObjectsTablePanel(
    section=SectionChoices.FULL_WIDTH,
    weight=200,
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



//TODO: (include image) <img src="/api/placeholder/600/200" alt="ObjectFieldsPanel Example" />
*ObjectFieldsPanel with field descriptions*

## Complete Example

```python
class LocationUIViewSet(NautobotViewSetMixin):
    queryset = Location.objects.all()

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                fields="__all__,
                weight=100,
            ),
            StatsPanel(
                filter_name="location",
                related_models=[
                    Device,
                    (Circuit, "circuit_terminations__location__in")
                ],
                section=SectionChoices.RIGHT_HALF,
                weight=100,
            ),
            GroupedKeyValueTablePanel(
                body_id="custom-fields",
                data={
                    "Network": {
                        "VLAN": "100",
                        "IP Range": "192.168.1.0/24"
                    }
                },
                section=SectionChoices.FULL_WIDTH,
                weight=300,
            ),
            ObjectTextPanel(
                object_field="description",
                render_as=BaseTextPanel.RenderOptions.MARKDOWN,
                section=SectionChoices.FULL_WIDTH,
                weight=400,
            )
        )
    )
```

//TODO: (include image) <img src="/api/placeholder/800/600" alt="Complete Example" />
*Complete example showing all panel types in action*

## Layouts and Sections

### Render Options

The panel supports multiple rendering formats through the `RenderOptions` enum:

| Option | Description |
|--------|-------------|
| `PLAINTEXT` | Renders content as plain text without formatting |
| `JSON` | Formats and syntax-highlights content as JSON |
| `YAML` | Formats and syntax-highlights content as YAML |
| `MARKDOWN` | Renders content as Markdown with HTML output |
| `CODE` | Displays content as syntax-highlighted code |

### Section Options

The panel supports multiple rendering formats through the `RenderOptions` enum:

| Option | Description |
|--------|-------------|
| `LEFT_HALF` | Left side of the view |
| `RIGHT_HALF` | Right side of the view |
| `FULL_WIDTH` | Spans entire width |


## Best Practices

### 1. Panel Organization
- Use consistent weights across your application
- Group related information in adjacent panels
- Consider mobile viewports when choosing sections

### 2. Performance
- Be specific with field selections
- Use appropriate indexes for StatsPanel queries

### 3. User Experience
- Provide clear, descriptive labels
- Use consistent patterns across views
- Implement proper error handling

### 4. Maintenance
- Document custom transformations
- Keep related model lists updated
- Use meaningful body_id values

## Troubleshooting

### Common Issues and Solutions

1. **Panels Not Appearing**
   - Verify section choices
   - Check panel weights
   - Confirm data availability

2. **Performance Issues**
   - Review query complexity in StatsPanel
   - Optimize field selections
   - Check database indexes

3. **Layout Problems**
   - Validate section assignments
   - Review weight ordering
   - Check responsive behavior

4. **Value Rendering**
   - Verify transform functions
   - Check data types
   - Confirm template paths
