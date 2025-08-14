# Breadcrumbs and titles migration

## Overview

The new `Breadcrumbs` and `Titles` classes in Nautobot provide a flexible, declarative way to generate navigation
breadcrumbs and dynamic page/document titles.
Each breadcrumb or title item can use context variables and be automatically generated either by getting it from the context
or using callables.
There are new simple tags in `{% load ui_framework %}` that allows you to automatically render breadcrumbs and title:

- `{% render_breadcrumbs %}` - expects `Breadcrumbs` instance in `context["breadcrumbs"]`
- `{% render_title %}` - expects `Titles` instance in `context["view_titles"]` - you can pass rendering mode `plain (default) | html`

## `NautobotUIViewSet` views

- Check the default `Breadcrumbs` and `Titles` classes if defaults values are sufficient for your needs.
`breadcrumbs` and `view_titles` will be attached automatically to the context and instantiate if needed.

```python

class ExampleView:

    breadcrumbs = Breadcrumbs(...)  # Update defaults if needed
    view_titles = Titles(...)
```

Refer to the [Nautobot UI Framework Documentation](../../../core/ui-component-framework.md) if you need to update some of the default values.

- Remove custom html code from `{% block breadcrumbs %}` and `{% block title %}`.
- Use the built-in template tags to render the breadcrumbs and title: `{% render_breadcrumbs %}` and `{% render_title %}`

Complete example:

```html
{% load ui_framework %}

{% block content %}
<div class="row noprint">
    <div class="col-md-12">
        <!-- you can remove the <ol> and {% block breadcrumbs %} - it's moved to default breadcrumbs template --->
        {% render_breadcrumbs %}
    </div>
</div>

<h1>{% block title %}{% render_title %}{% endblock %}</h1>
{% endblock %}
```

## Generic views

If you're not using the `NautobotUIViewSet` and the `NautobotHTMLRenderer` you need to make sure that `context` will have:
- `view_action` - based on that `Breadcrumbs` and `Titles` will know what action they need to render.
- actual `Breadcrumbs` instance, under `context['breadcrumbs']` to be properly rendered by `{% render_breadcrumbs %}`
- `Titles` instances, under `context['view_titles']` to be properly rendered by `{% render_title %}`

### Generic view "before" example

```python

class SomeGenericView(GenericView):
    """
    View for listing all installed Apps.
    """

    def get(self, request):
        my_data = get_some_data()
        return render(
            request,
            "custom/template.html",
            {
                "my_data": my_data,
            },
        )
```

```html
{% extends "base.html" %}
{% load helpers %}
{% load static %}
{% load ui_framework %}

{% block content %}
    <div class="row noprint">
        <div class="col-md-12">
             <ol class="breadcrumb">
                {% block breadcrumbs %}
                    <li><a href="{% url 'apps:custom_url' %}">My Item</a></li>
                {% endblock breadcrumbs %}
            </ol>
        </div>
    </div>

    <h1>{% block title %}My Title{% endblock %}</h1>

    <div class="row">
        Some data
    </div>
{% endblock %}
```

#### Generic view "after" example

```python
class SomeGenericView(GenericView):
    """
    Custom example view.
    """

    breadcrumbs = Breadcrumbs(
        items={"generic": [ViewNameBreadcrumbItem(view_name="apps:custom_url", label="My Item")]}
    )
    view_titles = Titles(titles={"generic": "My Title"})

    def get(self, request):
        my_data = get_some_data()
        return render(
            request,
            "custom/template.html",
            {
                "my_data": my_data,
                "view_action": "generic",
                "breadcrumbs": self.breadcrumbs,
                "view_titles": self.view_titles,
            },
        )
```

```html
{% extends "base.html" %}
{% load helpers %}
{% load static %}
{% load ui_framework %}

{% block content %}
    <div class="row noprint">
        <div class="col-md-12">
            <!-- you can remove the <ol> and {% block breadcrumbs %} - it's moved to default breadcrumbs template --->
            {% render_breadcrumbs %}
        </div>
    </div>

    <h1>{% block title %}{% render_title %}{% endblock %}</h1>

    <div class="row">
        Some data
    </div>
{% endblock %}
```

!!! info
    Default `{% render_breadcrumbs %}` template will add the `<ol class="breadcrumbs">` tag, and both `{% block breadcrumbs %}` and `{% block extra_breadcrumbs %}` blocks.
