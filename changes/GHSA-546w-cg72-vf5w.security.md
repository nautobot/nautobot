Fixed a bypass of the `sensitive_fields` control where a user-authored Jinja2 template could infer a sensitive field's value by filtering a queryset on it.
