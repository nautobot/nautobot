# Extending the Base Template

Nautobot provides a base template to ensure a consistent user experience, which apps can extend with their own content. This template includes four content blocks:

* `title` - The page title
* `header` - The upper portion of the page
* `content` - The main page body
* `javascript` - A section at the end of the page for including Javascript code

For more information on how template blocks work, consult the [Django documentation](https://docs.djangoproject.com/en/stable/ref/templates/builtins/#block).

```jinja2
{# templates/nautobot_animal_sounds/animal.html #}
{% extends 'base.html' %}

{% block content %}
    {% with config=settings.PLUGINS_CONFIG.nautobot_animal_sounds %}
        <h2 class="text-center" style="margin-top: 200px">
            {% if animal %}
                The {{ animal.name|lower }} says
                {% if config.loud %}
                    {{ animal.sound|upper }}!
                {% else %}
                    {{ animal.sound }}
                {% endif %}
            {% else %}
                No animals have been created yet!
            {% endif %}
        </h2>
    {% endwith %}
{% endblock %}

```

The first line of the template instructs Django to extend the Nautobot base template and inject our custom content within its `content` block.

!!! note
    Django renders templates with its own custom [template language](https://docs.djangoproject.com/en/stable/topics/templates/#the-django-template-language). This template language is very similar to Jinja2, however there are some important differences to keep in mind.
