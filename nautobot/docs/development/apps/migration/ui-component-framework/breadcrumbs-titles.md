# Breadcrumbs and titles migration

## `NautobotUIViewSet` views

1. Check the default `Breadcrumbs`, `DocumentTitles` and `PageHeadings` classes if defaults values are sufficient for your needs.
`breadcrumbs`, `document_titles` and `page_heading` will be attached automatically to the context and instatiate if needed.

```python

class ExampleView:

    breadcrumbs = Breadcrumbs(...)  # Update defaults if needed
    page_heading = PageHeadings(...)
    document_titles = DocumentTitles(...)
```

Refer to the [Nautobot UI Framework Documentation](../../../core/ui-component-framework.md) if you need to update some of the default values.

1. Remove custom html code from `{% block breadcrumbs %}` and `{% block title %}`. Use the built-in template tags to render the breadcrumbs and title.

```html
{% load ui_framework %}

{% block content %}
<div class="row noprint">
    <div class="col-md-12">
        {% block breadcrumbs %}
            {% render_breadcrumbs %}
        {% endblock breadcrumbs %}
    </div>
</div>

<h1>{% block title %}{% render_titles page_heading %}{% endblock %}</h1>
{% endblock %}
```

!!! note
    For most use cases, using `{% render_titles page_heading %}` within a `{% block title %}` will be sufficient.
    But default `PageHeading` generates some html for list action and if you use it within a `{% block title %}` browser will output this html in document title as well.
    If your custom titles uses some html code, make sure that you will use both `page_heading` and `document_titles` separately.

    ```html
    {% block title %}{% render_titles document_titles %}{% endblock %} <!-- block title moved outside of content to render only as document title / browser tab name. -->
    {% block content %}
        <h1>{% render_titles page_heading %}</h1> <!-- page heading is rendered within h1 -->
    {% endblock %}
    ```

## Generic views

If you're not using the `NautobotUIViewSet` and the `NautobotHTMLRenderer` you need to make sure that `context` will have:
- `view_action` - based on that `Breadcrumbs` and `PageHeadings` / `DocumentTitles` will know what action they need to render.
- actual `Breadcrumbs` instance, under `context['breadcrumbs']` to be properly rendered by `{% render_breadcrumbs %}`
- `PageHeadings` / `DocumentTitles` instances or just base `Titles` instance

### Example:

#### Before

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

#### After

```python
class SomeGenericView(GenericView):
    """
    Custom example view.
    """

    breadcrumbs = Breadcrumbs(
        items={"generic": [ViewNameBreadcrumbItem(view_name="apps:custom_url", label="My Item")]}
    )
    generic_titles = Titles(titles={"generic": "My Title"})

    def get(self, request):
        my_data = get_some_data()
        return render(
            request,
            "custom/template.html",
            {
                "my_data": my_data,
                "view_action": "generic",
                "breadcrumbs": self.breadcrumbs,
                "generic_titles": self.generic_titles,
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
            {% block breadcrumbs %}
                {% render_breadcrumbs %}
            {% endblock breadcrumbs %}
        </div>
    </div>

    <h1>{% block title %}{% render_title generic_titles %}{% endblock %}</h1>

    <div class="row">
        Some data
    </div>
{% endblock %}
```

!!! note
    Wrapper `<ol class="breadcrumb">` tag will be now rendered by `render_breadcrumbs`.
