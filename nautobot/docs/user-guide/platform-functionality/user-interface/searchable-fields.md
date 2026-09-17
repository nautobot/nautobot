---
render_macros: true
---

# Searchable Fields by Model

When you use a list view's search bar (the `q=` search), Nautobot matches your query against a specific set of fields for that model. This page documents which fields are searchable for each model.

This page is generated automatically from each model's `SearchFilter` definition, so it always reflects the current behavior of the code. It is not maintained by hand.

A few notes on reading the tables below:

- Matches are case-insensitive partial matches unless otherwise defined by the model's filter.
- A field name containing `__` (for example, `circuit_terminations__description`) searches a field on a related object.
- The `id` field matches an object's primary-key UUID exactly.

!!! tip
    To scope a global search to a single model, prefix your query with `in:$model` (for example, `in:Devices`). See [Search](search.md) for details.

{% for app_label, app in searchable_fields.items() %}

## {{ app.app_name }}

| Model | Searchable Fields |
| ----- | ----------------- |
{% for model in app.models %}| {{ model.name }} | {% for field in model.fields %}`{{ field }}`{% if not loop.last %}, {% endif %}{% endfor %} |
{% endfor %}
{% endfor %}
