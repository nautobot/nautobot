from django.apps import apps


def search_model_choices():
    """
    Get tuples suitable for use as the `choices` of a `ChoiceField`, listing all searchable models, grouped by app.
    """
    choices = [("", "All Objects")]
    for app_config in apps.get_app_configs():
        searchable_models = getattr(app_config, "searchable_models", None)
        if not searchable_models:
            continue
        app_label = app_config.verbose_name
        model_tuples = [
            (modelname, app_config.get_model(modelname)._meta.verbose_name_plural) for modelname in searchable_models
        ]
        choices.append((app_label, model_tuples))
    return choices
