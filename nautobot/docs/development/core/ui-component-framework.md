# Nautobot UI Framework

## Table of Contents
- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Core Concepts](#core-concepts)
- [Panel Types](#panel-types)
- [Layouts and Sections](#layouts-and-sections)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Introduction

The Nautobot UI Framework provides a declarative way to create rich object-detail views without writing custom Django HTML templates. Instead of crafting HTML templates manually, you define your UI structure using Python objects.

//TODO: (include image) <img src="/api/placeholder/800/400" alt="UI Framework Example" />
*Example of a detail view created with the UI Framework*

### Key Benefits
- Reduced boilerplate code
- Consistent UI patterns
- Reusable components
- Declarative configuration
- Built-in responsive layouts

## Getting Started

### Basic Setup

1. Create a view that inherits from `NautobotViewSetMixin`, in this example `NautobotUIViewSet`:

```python
from nautobot.apps.ui import (
    NautobotUIViewSet,
    ObjectDetailContent,
    ObjectFieldsPanel,
    SectionChoices
)

class ExampleUIViewSet(NautobotUIViewSet):
    queryset = Example.objects.all()
    ...
    
    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=["name", "status", "type"]
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
- Tab structure

### Panels
Panels are the building blocks of your UI. They contain specific types of content and can be positioned within sections.

//TODO: (include image) <img src="/api/placeholder/700/350" alt="Panel Structure" />
*Panel structure showing different sections and layouts*

## Panel Types

### Base Panel Properties
All panel types inherit these base properties:

```python
Panel(
    # Visual Organization
    label="",                    # Text label shown in panel header
    section=SectionChoices.FULL_WIDTH,  # Panel placement in layout
    weight=100,                  # Order within section (lower numbers appear first)
    
    # HTML/Template Configuration
    body_id=None,                # HTML ID for the panel body element
    body_content_template_path=None,  # Template for panel content
    header_extra_content_template_path=None,  # Additional header content
    footer_content_template_path=None,  # Footer content template
    template_path="components/panel/panel.html",  # Overall panel template
    body_wrapper_template_path="components/panel/body_wrapper_generic.html"  # Body wrapper template
)
```

### 1. KeyValueTablePanel
Displays custom key-value pairs with optional transformations.

```python
KeyValueTablePanel(
    # Data Configuration
    data={                      # Dictionary of key-value pairs to display
        "speed": "1000000",
        "notes": "**Important**"
    },
    
    hide_if_unset=(),          # Keys to hide if value is falsey
                               # Example: ["optional_field", "notes"]
    
    value_transforms={          # Transform functions for specific keys
        "speed": [             # List of functions to apply in order
            humanize_speed,    # Convert 1000000 to "1 Gbps"
            placeholder        # Show placeholder if empty
        ],
        "notes": [
            render_markdown,   # Convert markdown to HTML
            placeholder       # Show placeholder if empty
        ]
    },       # Order within section
)
```

### 2. ObjectFieldsPanel
Displays object attributes in a key-value table format. This panel inherits from `KeyValueTablePanel`.

```python
ObjectFieldsPanel(
    # Field Selection
    fields="__all__",           # List of field names to display or "__all__" for all fields
                                # Example: ["name", "status", "type", "serial"]
    
    exclude_fields=(),          # Fields to exclude when using "__all__"
                                # Example: ["internal_id", "created_date"]
    
    context_object_key="object", # Key in template context containing the object
                                # Default is "object"
    
    ignore_nonexistent_fields=False,  # If True, skip fields that don't exist
                                     # If False, raise error for missing fields
    
    
    # Advanced Configuration
    value_transforms={          # Custom field value transformations
        "status": [status_to_badge],
        "type": [type_to_link]
    }
)
```

//TODO: (include image) <img src="/api/placeholder/600/200" alt="ObjectFieldsPanel Example" />
*ObjectFieldsPanel with field descriptions*

### 3. GroupedKeyValueTablePanel
Organizes key-value pairs in collapsible groups. This panel inherits from `KeyValueTablePanel`.

```python
GroupedKeyValueTablePanel(
    # Required Configuration
    body_id="network-details",  # Required for accordion functionality
    
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
    
    # Value Transformation
    value_transforms={          # Same as KeyValueTablePanel
        "IP Range": [ip_range_to_link],
        "Notes": [render_markdown]
    },
    
    hide_if_unset=(),          # Keys to hide if empty
    
    # Inheritance from Base Panel
    label="Grouped Information",
    section=SectionChoices.FULL_WIDTH,
    weight=300
)
```

### 4. Text Panels Family

#### BaseTextPanel
Base class for text rendering with multiple format options.

```python
BaseTextPanel(
    # Rendering Configuration
    render_as=BaseTextPanel.RenderOptions.MARKDOWN,  # How to render the text
        # Available options:
        # - PLAINTEXT: Simple text
        # - MARKDOWN: Markdown formatting
        # - JSON: Formatted JSON with syntax highlighting
        # - YAML: Formatted YAML with syntax highlighting
        # - CODE: Generic code with syntax highlighting
    
    render_placeholder=True,    # Show placeholder for empty values
    
    # Template Configuration
    body_content_template_path="components/panel/body_content_text.html",
    
    # Inheritance from Base Panel
    label="Text Content",
    section=SectionChoices.FULL_WIDTH,
    weight=400
)
```

#### ObjectTextPanel
Renders text from a specific object field.

```python
ObjectTextPanel(
    # Field Configuration
    object_field="description",  # Name of the field to render
                                # Must be a text field on the object
    
    # Inherited from BaseTextPanel
    render_as=BaseTextPanel.RenderOptions.MARKDOWN,
    render_placeholder=True,
    
    # Inheritance from Base Panel
    label="Description",
    section=SectionChoices.FULL_WIDTH,
    weight=500
)
```

#### TextPanel
Renders text from a context field.

```python
TextPanel(
    # Content Configuration
    context_field="text",       # Key in template context containing text
    
    # Inherited from BaseTextPanel
    render_as=BaseTextPanel.RenderOptions.CODE,
    render_placeholder=True,
    
    # Inheritance from Base Panel
    label="Custom Content",
    section=SectionChoices.FULL_WIDTH,
    weight=600
)
```

### 5. StatsPanel
Displays count statistics for related models with filterable links.

```python
StatsPanel(
    # Query Configuration
    filter_name="location",     # URL query parameter name
                               # Example: ?location=123
    
    related_models=[           # Models to show statistics for
        Device,               # Direct model reference
                             # Will count all devices related to this object
        
        (Circuit, "circuit_terminations__location__in"),
                             # Tuple of (Model, query_string)
                             # For complex relationships
        
        (VirtualMachine, "cluster__location__in")
                             # Another complex relationship example
    ],
    
    # Inheritance from Base Panel
    label="Statistics",
    section=SectionChoices.RIGHT_HALF,
    weight=700,
    
    # Template Configuration
    body_content_template_path="components/panel/stats_panel_body.html"
)
```

## Layouts and Sections

### Section Choices
- `LEFT_HALF`: Left side of the view
- `RIGHT_HALF`: Right side of the view
- `FULL_WIDTH`: Spans entire width

### Panel Weights
Standard panel weights for consistent ordering:
```python
WEIGHT_COMMENTS_PANEL = 200
WEIGHT_CUSTOM_FIELDS_PANEL = 300
WEIGHT_COMPUTED_FIELDS_PANEL = 400
WEIGHT_RELATIONSHIPS_PANEL = 500
WEIGHT_TAGS_PANEL = 600
```

//TODO: (include image) <img src="/api/placeholder/800/400" alt="Layout Sections" />
*Layout sections and panel ordering*

## Complete Example

```python
class LocationUIViewSet(NautobotViewSetMixin):
    queryset = Location.objects.all()
    
    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                fields=["name", "status", "type"],
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

## Best Practices

### 1. Panel Organization
- Use consistent weights across your application
- Group related information in adjacent panels
- Consider mobile viewports when choosing sections

### 2. Performance
- Be specific with field selections
- Use appropriate indexes for StatsPanel queries
- Consider lazy loading for heavy content

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

## Migration Guide

When migrating from template-based views:

1. Identify template blocks
2. Map to appropriate panels
3. Configure sections and weights
4. Test responsive behavior
5. Verify all functionality