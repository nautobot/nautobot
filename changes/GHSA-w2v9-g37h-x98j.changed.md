Changed the `meta` filter in Jinja2 templates to return only the attributes that identify a model, such as `app_label` and `verbose_name`; any other `_meta` attribute now raises an error.
